from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .datumaro_reader import load_datumaro, parse_keypoints_and_visibility
from .verification.config import load_verification_config
from .verification.cropper import annotation_to_crop_space, materialize_crop, plan_crop
from .verification.engine import evaluate_object
from .verification.report_csv import _safe_run_dir, _safe_run_timestamp, write_run_reports
from .verification.report_json import serialize_object_result
from .verification.report_ndjson import NdjsonStreamWriter
from .verification.types import DeterministicVerdict, ObjectVerificationResult

if TYPE_CHECKING:
    from .verification.vlm_client import VlmAdapter


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


def _parse_bbox(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = annotation.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except (TypeError, ValueError):
        return None


def _derive_bbox_from_annotation(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Derive AABB (x, y, w, h) from polygon, skeleton, or points annotation when no bbox field exists."""
    ann_type = annotation.get("type")
    points_raw = annotation.get("points")
    if not isinstance(points_raw, list) or not points_raw:
        return None
    try:
        if ann_type == "skeleton" and len(points_raw) >= 3 and len(points_raw) % 3 == 0:
            # skeleton: [x0, y0, v0, x1, y1, v1, ...]
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 3)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 3)]
        elif len(points_raw) >= 2 and len(points_raw) % 2 == 0:
            # polygon or points: [x0, y0, x1, y1, ...]
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 2)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 2)]
        else:
            return None
    except (TypeError, ValueError):
        return None
    if not xs:
        return None
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


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


def run_verify(config_path: str, _vlm_adapter: "VlmAdapter | None" = None) -> tuple[bool, dict[str, Any]]:
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

    image_dir_raw = verification_root.get("image_dir") or raw_config.get("image_dir")
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
    run_dir.mkdir(parents=True, exist_ok=True)

    vlm_enabled = bool(((verification_root.get("vlm") or {}).get("enabled", False)))

    label_names = _label_lookup(data)

    ndjson_trace_path = run_dir / "deterministic_trace.ndjson"

    class _StreamingResults:
        """List-like that streams each append to an NDJSON writer immediately.

        Avoids buffering the full result list for NDJSON output — the trace
        file is written line-by-line during processing rather than all at once
        after the loop. CSV and JSON reports still use the accumulated list,
        which is bounded by annotation count.
        """

        def __init__(self, writer: NdjsonStreamWriter) -> None:
            self._list: list[ObjectVerificationResult] = []
            self._writer = writer

        def append(self, result: ObjectVerificationResult) -> None:
            self._list.append(result)
            self._writer.write(result)

        # Delegate all list operations used elsewhere in this function
        def __iter__(self):  # type: ignore[override]
            return iter(self._list)

        def __len__(self) -> int:
            return len(self._list)

        def as_list(self) -> list[ObjectVerificationResult]:
            return self._list

    warnings: list[str] = list(config_warnings)
    items = data.get("items") or []
    annotation_payloads: dict[tuple[str, str], dict[str, Any]] = {}

    with NdjsonStreamWriter(ndjson_trace_path) as ndjson_writer:
        results = _StreamingResults(ndjson_writer)

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

                object_id = str(annotation.get("id") or f"ann-{annotation_index}")
                label_id = annotation.get("label_id")
                label = label_names.get(label_id, str(annotation.get("label") or "unknown")) if isinstance(label_id, int) else str(annotation.get("label") or "unknown")
                crop_file = _crop_output_path(run_dir=run_dir, sample_id=sample_id, object_id=object_id)
                crop_path = str(crop_file)

                try:
                    keypoints, visibility, _, _ = parse_keypoints_and_visibility(annotation)
                except ValueError:
                    keypoints, visibility = [], []
                bbox = _parse_bbox(annotation)
                if bbox is None:
                    bbox = _derive_bbox_from_annotation(annotation)

                if image_size is None:
                    results.append(_failure_result(sample_id=sample_id, object_id=object_id, label=label, crop_path=crop_path, reason="invalid_image_size"))
                    continue
                if bbox is None:
                    results.append(_failure_result(sample_id=sample_id, object_id=object_id, label=label, crop_path=crop_path, reason="bbox_missing_or_malformed"))
                    continue

                width, height = image_size
                ann_type = annotation.get("type")
                _SKELETON_ANN_TYPES = {"points", "skeleton"}
                _NON_SKELETON_ANN_TYPES = {"polygon", "bbox", "mask", "ellipse", "polyline"}
                if ann_type in _SKELETON_ANN_TYPES:
                    is_skeleton = True
                elif ann_type in _NON_SKELETON_ANN_TYPES or ann_type is None:
                    is_skeleton = False
                else:
                    print(
                        f"[run_verify] warning: unknown ann_type={ann_type!r} for object_id={object_id}; defaulting is_skeleton=False",
                        file=sys.stderr,
                    )
                    is_skeleton = False

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
                    # Translate coordinates to crop-space so VLM rules can correlate
                    # annotation values with what the model sees in the crop image.
                    annotation_payload = annotation_to_crop_space(annotation_payload, crop)
                    engine_outcome = evaluate_object(
                        sample_id=sample_id,
                        object_id=object_id,
                        label=label,
                        crop_path=crop_path,
                        annotation=annotation_payload,
                        config=verification_config,
                    )
                    warnings.extend(engine_outcome.warnings)
                    annotation_payloads[(sample_id, object_id)] = annotation_payload
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

    artifact_paths = write_run_reports(
        results.as_list(),
        run_root=run_root,
        run_timestamp=safe_timestamp,
        ndjson_path=ndjson_trace_path,
    )

    vlm_results: list[Any] = []
    vlm_artifact_paths: dict[str, Path] = {}
    if vlm_enabled:
        from PIL import Image as PILImage

        from .verification.report_vlm import serialize_vlm_object_result, write_vlm_reports as write_vlm_run_reports
        from .verification.vlm_client import FiftyOneZooAdapter
        from .verification.vlm_config import VlmConfigError, load_vlm_config
        from .verification.vlm_engine import evaluate_vlm_batch
        from .verification.vlm_types import VlmObjectResult, VlmVerdict

        vlm_config_raw = verification_root.get("vlm") or {}
        try:
            vlm_config, vlm_cfg_warnings = load_vlm_config(vlm_config_raw)
            warnings.extend(vlm_cfg_warnings)
        except VlmConfigError as exc:
            warnings.append(f"vlm_config_error:{exc}")
            vlm_config = None

        if vlm_config is not None:
            adapter = _vlm_adapter if _vlm_adapter is not None else FiftyOneZooAdapter(
                model_name=vlm_config.model_name,
                max_new_tokens=vlm_config.generation.max_new_tokens,
            )

            batch_size = vlm_config.generation.batch_size
            vlm_ndjson_trace_path = run_dir / "vlm_trace.ndjson"
            with NdjsonStreamWriter(vlm_ndjson_trace_path, serializer=serialize_vlm_object_result) as vlm_ndjson_writer:
                pending: list[tuple[Any, dict[str, Any], Any]] = []

                def _flush_pending() -> None:
                    if not pending:
                        return
                    for outcome in evaluate_vlm_batch(pending, adapter=adapter, vlm_config=vlm_config):
                        vlm_results.append(outcome)
                        vlm_ndjson_writer.write(outcome)
                    pending.clear()

                for result in results:
                    if result.verdict is not DeterministicVerdict.PASS:
                        continue
                    if not vlm_config.is_label_enabled(result.label):
                        continue

                    try:
                        with PILImage.open(result.crop_path) as loaded:
                            crop_img = loaded.convert("RGB")
                    except Exception as exc:
                        vlm_outcome = VlmObjectResult(
                            sample_id=result.sample_id,
                            object_id=result.object_id,
                            label=result.label,
                            vlm_status=VlmVerdict.REVIEW,
                            object_risk=None,
                            rule_results=[],
                            adapter_model=vlm_config.model_name,
                            failure_reason=f"crop_load_error:{type(exc).__name__}",
                            crop_path=result.crop_path,
                        )
                        vlm_results.append(vlm_outcome)
                        vlm_ndjson_writer.write(vlm_outcome)
                        continue

                    annotation = annotation_payloads.get((result.sample_id, result.object_id), {})
                    pending.append((result, annotation, crop_img))

                    if len(pending) >= batch_size:
                        _flush_pending()

                _flush_pending()  # flush any remaining items

            vlm_artifact_paths = write_vlm_run_reports(
                vlm_results, run_root=run_root, run_timestamp=safe_timestamp,
                ndjson_path=vlm_ndjson_trace_path,
            )

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
    if vlm_enabled and vlm_results:
        summary["vlm_counts"] = {
            "vlm_total": len(vlm_results),
            "vlm_pass": sum(1 for row in vlm_results if row.vlm_status.value == "PASS"),
            "vlm_review": sum(1 for row in vlm_results if row.vlm_status.value == "REVIEW"),
            "vlm_fail": sum(1 for row in vlm_results if row.vlm_status.value == "FAIL"),
        }
        summary["vlm_artifacts"] = {name: str(path) for name, path in vlm_artifact_paths.items()}
    elif vlm_enabled:
        summary["vlm_counts"] = {"vlm_total": 0, "vlm_pass": 0, "vlm_review": 0, "vlm_fail": 0}
        summary["vlm_artifacts"] = {}

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
