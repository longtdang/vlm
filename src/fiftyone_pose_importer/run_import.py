from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import fiftyone as fo

from .config_loader import load_config
from .datumaro_reader import load_datumaro
from .image_index import build_image_index
from .matching import build_matches
from .pose_contract import (
    SchemaContractError,
    SkeletonContract,
    SkeletonContractBundle,
    extract_skeleton_contract_bundle,
)
from .preflight import PreflightReport
from .summary import write_summary


def _extract_points_and_visibility(annotation: dict[str, Any]) -> tuple[list[list[float]], list[int], list[int], bool]:
    ann_type = annotation.get("type")
    raw_points = annotation.get("points") or []
    source_visibility = annotation.get("visibility")

    if ann_type == "skeleton":
        if len(raw_points) % 3 != 0:
            raise ValueError("Invalid skeleton points payload (must be x,y,v triplets)")
        points = [[raw_points[i], raw_points[i + 1]] for i in range(0, len(raw_points), 3)]
        source_visibility = [int(raw_points[i + 2]) for i in range(0, len(raw_points), 3)]
        visibility_defaulted = False
        visibility = list(source_visibility)
    else:
        visibility_defaulted = source_visibility is None
        visibility = list(source_visibility) if source_visibility is not None else []
        if len(raw_points) % 2 != 0:
            raise ValueError("Invalid points payload (must be x,y pairs)")
        points = [[raw_points[i], raw_points[i + 1]] for i in range(0, len(raw_points), 2)]
        if not visibility:
            visibility = [2] * len(points)

    if len(visibility) != len(points):
        raise ValueError("Visibility length does not match points length")
    if any(vis not in (0, 1, 2) for vis in visibility):
        raise ValueError("Visibility values must be one of 0, 1, or 2")
    return points, visibility, list(source_visibility or []), visibility_defaulted


def _normalize_points(points: list[list[float]], width: float, height: float, visibility: list[int]) -> list[list[float]]:
    normalized: list[list[float]] = []
    for (x, y), vis in zip(points, visibility):
        if vis == 0:
            normalized.append([math.nan, math.nan])
            continue
        normalized.append([x / width, y / height])
    return normalized


def _ordered_point_annotations(item: dict[str, Any]) -> list[dict[str, Any]]:
    points_annotations = [ann for ann in (item.get("annotations") or []) if ann.get("type") in ("points", "skeleton")]
    if any("id" in ann for ann in points_annotations):
        return sorted(points_annotations, key=lambda ann: str(ann.get("id", "")))
    return points_annotations


def _align_points_to_contract(
    points: list[list[float]],
    visibility: list[int],
    label_count: int,
    sample_id: str,
) -> tuple[list[list[float]], list[int]]:
    if len(points) > label_count:
        raise SchemaContractError(
            "point_count_mismatch",
            f"Sample {sample_id}: points count {len(points)} exceeds skeleton label count {label_count}",
        )

    if len(points) < label_count:
        missing = label_count - len(points)
        points = points + [[math.nan, math.nan] for _ in range(missing)]
        visibility = visibility + [0 for _ in range(missing)]

    return points, visibility


def _to_fo_skeleton(contract: SkeletonContract) -> fo.KeypointSkeleton:
    return fo.KeypointSkeleton(labels=contract.labels, edges=contract.edges)


def _resolve_contract(bundle: SkeletonContractBundle, annotation: dict[str, Any]) -> SkeletonContract:
    if bundle.by_label_id:
        label_id = annotation.get("label_id")
        if not isinstance(label_id, int):
            raise SchemaContractError("missing_skeleton_label", "Missing label_id for multi-skeleton annotation")
        contract = bundle.by_label_id.get(label_id)
        if contract is None:
            raise SchemaContractError("unknown_skeleton_label", f"No skeleton contract found for label_id={label_id}")
        return contract
    assert bundle.default is not None
    return bundle.default


def _target_field_for_label_id(label_id: Any) -> str:
    if not isinstance(label_id, int):
        raise SchemaContractError("missing_skeleton_label", "Missing or invalid label_id for annotation routing")
    return f"keypoints_label_{label_id}"


def _ensure_dataset_skeleton_field(dataset: fo.Dataset, field_name: str, contract: SkeletonContract) -> None:
    skeletons = dict(getattr(dataset, "skeletons", {}) or {})
    skeletons[field_name] = _to_fo_skeleton(contract)
    dataset.skeletons = skeletons


def _target_field_for_annotation(
    annotation: dict[str, Any],
    bundle: SkeletonContractBundle,
    fallback_field: str,
) -> str:
    label_id = annotation.get("label_id")
    if isinstance(label_id, int):
        return _target_field_for_label_id(label_id)
    if bundle.by_label_id:
        raise SchemaContractError("missing_skeleton_label", "Missing or invalid label_id for annotation routing")
    return fallback_field


def _summary_mapping(bundle: SkeletonContractBundle, data: dict[str, Any]) -> list[dict[str, Any]]:
    points_categories = (data.get("categories") or {}).get("points") or {}
    source_names: dict[int, str] = {}
    if isinstance(points_categories, dict):
        raw_items = points_categories.get("items")
        if isinstance(raw_items, list):
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                label_id = raw.get("label_id")
                if isinstance(label_id, int):
                    source_names[label_id] = str(raw.get("label") or "")

    entries: list[dict[str, Any]] = []
    for label_id, contract in sorted(bundle.by_label_id.items()):
        entries.append(
            {
                "label_id": label_id,
                "source_label_name": source_names.get(label_id, ""),
                "target_field": _target_field_for_label_id(label_id),
                "skeleton_labels": contract.labels,
                "skeleton_edges": contract.edges,
                "visibility_policy": "invalid_or_mismatch=fail,missing=default_to_2_warn",
            }
        )
    return entries


def run_import(config_path: str, launch_app: bool = False) -> tuple[bool, dict[str, Any]]:
    cfg = load_config(config_path)
    data = load_datumaro(cfg.datumaro_json)
    items: list[dict[str, Any]] = data["items"]

    image_index, duplicate_keys = build_image_index(cfg.image_dir)
    matches, unmatched_keys, duplicate_annotation_keys, unmatched_image_keys = build_matches(image_index, items)
    malformed: list[str] = []

    report = PreflightReport(
        duplicate_image_keys=sorted(set(duplicate_keys)),
        duplicate_annotation_keys=sorted(set(duplicate_annotation_keys)),
        unmatched_annotation_keys=sorted(set(unmatched_keys)),
        unmatched_image_keys=sorted(set(unmatched_image_keys)),
        malformed_annotations=malformed,
        schema_mismatches={},
    )

    contract_bundle: SkeletonContractBundle | None = None
    try:
        contract_bundle = extract_skeleton_contract_bundle(data)
    except SchemaContractError as exc:
        report.add_schema_mismatch(exc.category, "global")

    summary: dict[str, Any] = {
        "dataset_name": cfg.dataset_name,
        "label_field": cfg.label_field,
        "image_count": len(image_index),
        "annotation_item_count": len(items),
        "matched_count": len(matches),
        "preflight": report.to_dict(),
        "written_samples": 0,
        "label_counts": {"keypoint_annotations": 0, "keypoint_positions_total": 0},
        "visibility": {"absent": 0, "hidden": 0, "visible": 0, "defaulted_annotations": 0},
        "warnings": {
            "counts": {
                "defaulted_visibility_annotations": 0,
                "unmatched_image_keys": len(sorted(set(unmatched_image_keys))),
                "unmatched_annotation_keys": len(sorted(set(unmatched_keys))),
            },
            "details": {
                "unmatched_image_keys": sorted(set(unmatched_image_keys)),
                "unmatched_annotation_keys": sorted(set(unmatched_keys)),
            },
        },
        "failures": {
            "counts": {
                "duplicate_image_keys": len(sorted(set(duplicate_keys))),
                "duplicate_annotation_keys": len(sorted(set(duplicate_annotation_keys))),
                "schema_mismatches_total": 0,
                "exceptions": 0,
            },
            "details": {
                "schema_mismatch_counts": {},
                "schema_mismatches": {},
                "exception": None,
            },
        },
        "launch": {"requested": launch_app, "attempted": False, "ok": None, "error": None},
        "mapping": [],
    }

    if contract_bundle is not None:
        summary["mapping"] = _summary_mapping(contract_bundle, data)

    if report.has_errors():
        summary["failures"]["counts"]["schema_mismatches_total"] = sum(len(v) for v in report.schema_mismatches.values())
        summary["failures"]["details"]["schema_mismatch_counts"] = summary["preflight"]["schema_mismatch_counts"]
        summary["failures"]["details"]["schema_mismatches"] = report.schema_mismatches
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    samples: list[fo.Sample] = []
    assert contract_bundle is not None
    canonical_contract = contract_bundle.default
    if canonical_contract is None and len(contract_bundle.by_label_id) == 1:
        canonical_contract = next(iter(contract_bundle.by_label_id.values()))
    routed_contracts: dict[str, SkeletonContract] = {}
    for image_path, item in matches:
        image_meta = (item.get("image") or {}).get("size") or []
        width = float(image_meta[1]) if len(image_meta) >= 2 else None
        height = float(image_meta[0]) if len(image_meta) >= 2 else None

        sample = fo.Sample(filepath=str(image_path))
        keypoints_by_field: dict[str, list[fo.Keypoint]] = {}

        sample_id = str(item.get("id", "unknown"))
        for ann in _ordered_point_annotations(item):
            try:
                contract = _resolve_contract(contract_bundle, ann)
                field_name = _target_field_for_annotation(ann, contract_bundle, cfg.label_field)
                label_count = len(contract.labels)
                points, visibility, source_visibility, visibility_defaulted = _extract_points_and_visibility(ann)
                if width is None or height is None or width <= 0 or height <= 0:
                    raise SchemaContractError("missing_image_size", "Missing valid image size metadata")
                points, visibility = _align_points_to_contract(points, visibility, label_count, sample_id)
                norm = _normalize_points(points, width, height, visibility)
                kp = fo.Keypoint(points=norm)
                kp["visibility"] = visibility
                kp["source_visibility"] = source_visibility
                kp["visibility_defaulted"] = visibility_defaulted
                kp["skeleton_labels"] = contract.labels
                kp["skeleton_edges"] = contract.edges
                summary["label_counts"]["keypoint_annotations"] += 1
                summary["label_counts"]["keypoint_positions_total"] += len(visibility)
                summary["visibility"]["absent"] += visibility.count(0)
                summary["visibility"]["hidden"] += visibility.count(1)
                summary["visibility"]["visible"] += visibility.count(2)
                if visibility_defaulted:
                    summary["visibility"]["defaulted_annotations"] += 1
                    summary["warnings"]["counts"]["defaulted_visibility_annotations"] += 1
                keypoints_by_field.setdefault(field_name, []).append(kp)
                routed_contracts[field_name] = contract
            except SchemaContractError as exc:
                report.add_schema_mismatch(exc.category, sample_id)
            except ValueError as exc:
                if "Visibility length" in str(exc):
                    report.add_schema_mismatch("visibility_length_mismatch", sample_id)
                elif "Visibility values" in str(exc):
                    report.add_schema_mismatch("invalid_visibility_values", sample_id)
                else:
                    report.add_schema_mismatch("invalid_annotation", sample_id)

        for field_name in sorted(keypoints_by_field):
            sample[field_name] = fo.Keypoints(keypoints=keypoints_by_field[field_name])
        samples.append(sample)

    if report.has_errors():
        summary["preflight"] = PreflightReport(
            duplicate_image_keys=sorted(set(duplicate_keys)),
            duplicate_annotation_keys=sorted(set(duplicate_annotation_keys)),
            unmatched_annotation_keys=sorted(set(unmatched_keys)),
            unmatched_image_keys=sorted(set(unmatched_image_keys)),
            malformed_annotations=sorted(set(malformed)),
            schema_mismatches=report.schema_mismatches,
        ).to_dict()
        summary["failures"]["counts"]["schema_mismatches_total"] = sum(len(v) for v in report.schema_mismatches.values())
        summary["failures"]["details"]["schema_mismatch_counts"] = summary["preflight"]["schema_mismatch_counts"]
        summary["failures"]["details"]["schema_mismatches"] = report.schema_mismatches
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    dataset = fo.Dataset(cfg.dataset_name)
    if canonical_contract is not None:
        dataset.default_skeleton = _to_fo_skeleton(canonical_contract)

    for field_name, contract in sorted(routed_contracts.items()):
        _ensure_dataset_skeleton_field(dataset, field_name, contract)

    dataset.add_samples(samples)
    dataset.save()
    summary["written_samples"] = len(samples)

    if launch_app:
        summary["launch"]["attempted"] = True
        try:
            fo.launch_app(dataset)
            summary["launch"]["ok"] = True
        except Exception as exc:
            summary["launch"]["ok"] = False
            summary["launch"]["error"] = str(exc)
            summary["failures"]["counts"]["exceptions"] += 1
            summary["failures"]["details"]["exception"] = str(exc)

    summary_path = write_summary(cfg.config_path, summary)
    summary["summary_path"] = str(summary_path)

    return summary["failures"]["counts"]["exceptions"] == 0, summary
