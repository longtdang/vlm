from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import fiftyone as fo

from .config_loader import load_config
from .datumaro_reader import load_datumaro
from .image_index import build_image_index
from .matching import build_matches
from .pose_contract import SchemaContractError, SkeletonContract, extract_canonical_skeleton_contract
from .preflight import PreflightReport
from .summary import write_summary


def _extract_points_and_visibility(annotation: dict[str, Any]) -> tuple[list[list[float]], list[int], list[int], bool]:
    raw_points = annotation.get("points") or []
    source_visibility = annotation.get("visibility")
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
    points_annotations = [ann for ann in (item.get("annotations") or []) if ann.get("type") == "points"]
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

    contract: SkeletonContract | None = None
    try:
        contract = extract_canonical_skeleton_contract(data)
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
        "visibility": {"absent": 0, "hidden": 0, "visible": 0, "defaulted_annotations": 0},
    }

    if report.has_errors():
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    samples: list[fo.Sample] = []
    assert contract is not None
    label_count = len(contract.labels)
    for image_path, item in matches:
        image_meta = (item.get("image") or {}).get("size") or []
        width = float(image_meta[1]) if len(image_meta) >= 2 else None
        height = float(image_meta[0]) if len(image_meta) >= 2 else None

        sample = fo.Sample(filepath=str(image_path))
        keypoints: list[fo.Keypoint] = []

        sample_id = str(item.get("id", "unknown"))
        for ann in _ordered_point_annotations(item):
            try:
                points, visibility, source_visibility, visibility_defaulted = _extract_points_and_visibility(ann)
                if width is None or height is None or width <= 0 or height <= 0:
                    raise SchemaContractError("missing_image_size", "Missing valid image size metadata")
                points, visibility = _align_points_to_contract(points, visibility, label_count, sample_id)
                norm = _normalize_points(points, width, height, visibility)
                kp = fo.Keypoint(points=norm)
                kp["visibility"] = visibility
                kp["source_visibility"] = source_visibility
                kp["visibility_defaulted"] = visibility_defaulted
                summary["visibility"]["absent"] += visibility.count(0)
                summary["visibility"]["hidden"] += visibility.count(1)
                summary["visibility"]["visible"] += visibility.count(2)
                if visibility_defaulted:
                    summary["visibility"]["defaulted_annotations"] += 1
                keypoints.append(kp)
            except SchemaContractError as exc:
                report.add_schema_mismatch(exc.category, sample_id)
            except ValueError:
                report.add_schema_mismatch("invalid_annotation", sample_id)

        sample[cfg.label_field] = fo.Keypoints(keypoints=keypoints)
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
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    dataset = fo.Dataset(cfg.dataset_name)
    dataset.default_skeleton = _to_fo_skeleton(contract)

    dataset.add_samples(samples)
    dataset.save()
    summary["written_samples"] = len(samples)
    summary_path = write_summary(cfg.config_path, summary)
    summary["summary_path"] = str(summary_path)

    if launch_app:
        fo.launch_app(dataset)

    return True, summary
