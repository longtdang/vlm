from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .datumaro_reader import load_datumaro
from .verification.config import load_verification_config
from .verification.cropper import materialize_crop, plan_crop
from .verification.engine import evaluate_object
from .verification.report_csv import _safe_run_dir, _safe_run_timestamp, write_run_reports
from .verification.report_json import serialize_object_result
from .verification.types import DeterministicVerdict, ObjectVerificationResult


def _resolve_path(base_dir: Path, value: str | None) -> Path:
    if value is None:
        raise ValueError("Missing required configuration path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate.resolve()


def _is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ValueError(f"Config file does not exist: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")
    return raw


def _label_lookup(data: dict[str, Any]) -> dict[int, str]:
    labels = ((data.get("categories") or {}).get("label") or {}).get("labels") or []
    lookup: dict[int, str] = {}
    for index, raw in enumerate(labels):
        if isinstance(raw, dict):
            lookup[index] = str(raw.get("name") or f"label-{index}")
        else:
            lookup[index] = f"label-{index}"
    return lookup


def _keypoints_visibility(annotation: dict[str, Any]) -> tuple[list[list[float]], list[int]]:
    keypoints = annotation.get("keypoints")
    visibility = annotation.get("visibility")

    if isinstance(keypoints, list) and all(isinstance(point, list) and len(point) == 2 for point in keypoints):
        parsed_points = [[float(point[0]), float(point[1])] for point in keypoints]
        if isinstance(visibility, list) and len(visibility) == len(parsed_points):
            parsed_visibility = [int(v) for v in visibility]
        else:
            parsed_visibility = [2 for _ in parsed_points]
        return parsed_points, parsed_visibility

    points = annotation.get("points")
    if isinstance(points, list):
        if len(points) % 3 == 0 and annotation.get("type") == "skeleton":
            parsed_points = [[float(points[idx]), float(points[idx + 1])] for idx in range(0, len(points), 3)]
            parsed_visibility = [int(points[idx + 2]) for idx in range(0, len(points), 3)]
            return parsed_points, parsed_visibility
        if len(points) % 2 == 0:
            parsed_points = [[float(points[idx]), float(points[idx + 1])] for idx in range(0, len(points), 2)]
            parsed_visibility = [2 for _ in parsed_points]
            return parsed_points, parsed_visibility

    return [], []


def _parse_bbox(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = annotation.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except (TypeError, ValueError):
        return None


def _image_size(item: dict[str, Any]) -> tuple[int, int] | None:
    raw_size = ((item.get("image") or {}).get("size")) or []
    if not isinstance(raw_size, list) or len(raw_size) < 2:
        return None
    try:
        height = int(raw_size[0])
        width = int(raw_size[1])
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _resolve_item_image_path(*, item: dict[str, Any], config_dir: Path, image_root: Path | None) -> Path:
    image_meta = item.get("image") or {}
    if not isinstance(image_meta, dict):
        raise ValueError("image_path_missing_or_malformed")

    raw_path = image_meta.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("image_path_missing_or_malformed")

    allowed_roots: list[Path] = [config_dir]
    if image_root is not None:
        allowed_roots.append(image_root)

    candidate_path = Path(raw_path)
    if candidate_path.is_absolute():
        resolved = candidate_path.resolve()
    else:
        candidates: list[Path] = []
        if image_root is not None:
            candidates.append((image_root / candidate_path).resolve())
        candidates.append((config_dir / candidate_path).resolve())
        resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    if not any(_is_within(root, resolved) for root in allowed_roots):
        raise ValueError("image_path_outside_allowed_roots")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError("image_path_not_found")

    return resolved


def _safe_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "unknown"


def _crop_output_path(*, run_dir: Path, sample_id: str, object_id: str) -> Path:
    filename = f"{_safe_token(sample_id)}_{_safe_token(object_id)}.png"
    return run_dir / "crops" / filename


def _failure_result(*, sample_id: str, object_id: str, label: str, crop_path: str, reason: str) -> ObjectVerificationResult:
    return ObjectVerificationResult(
        sample_id=sample_id,
        object_id=object_id,
        label=label,
        verdict=DeterministicVerdict.FAIL,
        crop_path=crop_path,
        rule_results=[],
        failure_reasons=[reason],
    )


def run_verify(config_path: str) -> tuple[bool, dict[str, Any]]:
    config_file = Path(config_path).resolve()
    raw_config = _load_raw_config(config_file)

    datumaro_path = _resolve_path(config_file.parent, raw_config.get("datumaro_json"))
    data = load_datumaro(datumaro_path)

    verification_root = raw_config.get("verification") or {}
    if not isinstance(verification_root, dict):
        raise ValueError("verification config must be a mapping")

    deterministic_config_raw = verification_root.get("deterministic")
    verification_config, config_warnings = load_verification_config(deterministic_config_raw)

    output_dir_raw = verification_root.get("output_dir")
    if output_dir_raw is None:
        run_root = config_file.parent / "verification-runs"
    elif isinstance(output_dir_raw, str):
        run_root = _resolve_path(config_file.parent, output_dir_raw)
    else:
        raise ValueError("verification.output_dir must be a string path")

    image_dir_raw = verification_root.get("image_dir")
    if image_dir_raw is None:
        image_root = None
    elif isinstance(image_dir_raw, str):
        image_root = _resolve_path(config_file.parent, image_dir_raw)
    else:
        raise ValueError("verification.image_dir must be a string path")

    run_timestamp = verification_root.get("run_timestamp")
    if run_timestamp is not None and not isinstance(run_timestamp, str):
        raise ValueError("verification.run_timestamp must be a string when provided")
    safe_timestamp = _safe_run_timestamp(run_timestamp)
    run_dir = _safe_run_dir(run_root=run_root, run_timestamp=safe_timestamp)

    vlm_enabled = bool(((verification_root.get("vlm") or {}).get("enabled", False)))

    label_names = _label_lookup(data)

    results: list[ObjectVerificationResult] = []
    warnings: list[str] = list(config_warnings)
    items = data.get("items") or []

    for item_index, item in enumerate(items):
        if not isinstance(item, dict):
            warnings.append(f"Skipped malformed item at index {item_index}")
            continue

        sample_id = str(item.get("id") or f"sample-{item_index}")
        image_size = _image_size(item)

        annotations = item.get("annotations") or []
        if not isinstance(annotations, list):
            warnings.append(f"Sample {sample_id} annotations malformed; skipped")
            continue

        try:
            source_image_path = _resolve_item_image_path(item=item, config_dir=config_file.parent, image_root=image_root)
            image_path_error: str | None = None
        except ValueError as exc:
            source_image_path = None
            image_path_error = str(exc)

        for annotation_index, annotation in enumerate(annotations):
            if not isinstance(annotation, dict):
                warnings.append(f"Sample {sample_id} annotation index {annotation_index} malformed; skipped")
                continue

            object_id = str(annotation.get("id") or f"{sample_id}-ann-{annotation_index}")
            label_id = annotation.get("label_id")
            label = label_names.get(label_id, str(annotation.get("label") or "unknown")) if isinstance(label_id, int) else str(annotation.get("label") or "unknown")
            crop_file = _crop_output_path(run_dir=run_dir, sample_id=sample_id, object_id=object_id)
            crop_path = str(crop_file)

            keypoints, visibility = _keypoints_visibility(annotation)
            bbox = _parse_bbox(annotation)

            if image_size is None:
                results.append(_failure_result(sample_id=sample_id, object_id=object_id, label=label, crop_path=crop_path, reason="invalid_image_size"))
                continue
            if bbox is None:
                results.append(_failure_result(sample_id=sample_id, object_id=object_id, label=label, crop_path=crop_path, reason="bbox_missing_or_malformed"))
                continue

            width, height = image_size
            is_skeleton = annotation.get("type") in {"points", "skeleton"} or bool(keypoints)

            crop = plan_crop(
                image_width=width,
                image_height=height,
                bbox=bbox,
                padding_px=verification_config.padding_px,
                is_skeleton=is_skeleton,
                keypoints=[(point[0], point[1]) for point in keypoints] if keypoints else None,
                visibility=visibility if visibility else None,
            )

            if crop.verdict is DeterministicVerdict.FAIL:
                results.append(
                    _failure_result(
                        sample_id=sample_id,
                        object_id=object_id,
                        label=label,
                        crop_path=crop_path,
                        reason=crop.reason or "crop_failed",
                    )
                )
                continue

            if image_path_error is not None or source_image_path is None:
                results.append(
                    _failure_result(
                        sample_id=sample_id,
                        object_id=object_id,
                        label=label,
                        crop_path=crop_path,
                        reason=image_path_error or "image_path_unresolved",
                    )
                )
                continue

            try:
                materialize_crop(source_image_path=source_image_path, crop_plan=crop, output_path=crop_file)
            except Exception as exc:  # pragma: no cover - defensive guard for runtime isolation
                results.append(
                    _failure_result(
                        sample_id=sample_id,
                        object_id=object_id,
                        label=label,
                        crop_path=crop_path,
                        reason=f"crop_materialization_error:{type(exc).__name__}",
                    )
                )
                continue

            try:
                annotation_payload = {
                    "bbox": list(bbox),
                    "attributes": annotation.get("attributes") if isinstance(annotation.get("attributes"), dict) else {},
                    "keypoints": keypoints,
                    "visibility": crop.adjusted_visibility if crop.adjusted_visibility is not None else visibility,
                }
                engine_outcome = evaluate_object(
                    sample_id=sample_id,
                    object_id=object_id,
                    label=label,
                    crop_path=crop_path,
                    annotation=annotation_payload,
                    config=verification_config,
                )
                warnings.extend(engine_outcome.warnings)
                results.append(engine_outcome.result)
            except Exception as exc:  # pragma: no cover - defensive guard for runtime isolation
                results.append(
                    _failure_result(
                        sample_id=sample_id,
                        object_id=object_id,
                        label=label,
                        crop_path=crop_path,
                        reason=f"runtime_error:{type(exc).__name__}",
                    )
                )

    artifact_paths = write_run_reports(results, run_root=run_root, run_timestamp=safe_timestamp)

    object_records = []
    for result in sorted(results, key=lambda row: (row.sample_id, row.object_id)):
        record = serialize_object_result(result)
        record["vlm_eligible"] = result.verdict is DeterministicVerdict.PASS
        object_records.append(record)

    summary = {
        "ok": True,
        "config_path": str(config_file),
        "datumaro_json": str(datumaro_path),
        "vlm_enabled": vlm_enabled,
        "counts": {
            "objects_total": len(results),
            "deterministic_pass": sum(1 for result in results if result.verdict is DeterministicVerdict.PASS),
            "deterministic_fail": sum(1 for result in results if result.verdict is DeterministicVerdict.FAIL),
        },
        "artifacts": {name: str(path) for name, path in artifact_paths.items()},
        "warnings": warnings,
        "objects": object_records,
    }
    return True, summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run deterministic verification")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args(argv)

    try:
        ok, summary = run_verify(args.config)
        print(json.dumps(summary, indent=2))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
