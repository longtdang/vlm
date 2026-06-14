from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .report_csv import _safe_run_dir, _sanitize_csv_cell
from .vlm_types import VlmObjectResult, VlmVerdict

VLM_RULE_NAMES: list[str] = [
    "bbox_localization",
    "bbox_coverage",
    "clamp_type",
    "roll_count",
    "keypoint_position",
    "occlusion_state",
]

VLM_CSV_FIELDNAMES: list[str] = [
    "sample_id",
    "object_id",
    "label",
    "vlm_status",
    "object_risk",
    "adapter_model",
    "failure_reason",
] + [f"{rule}_ep" for rule in VLM_RULE_NAMES] + [f"{rule}_reason" for rule in VLM_RULE_NAMES]


def _sorted_results(results: list[VlmObjectResult]) -> list[VlmObjectResult]:
    return sorted(results, key=lambda result: (result.sample_id, result.object_id))


def serialize_vlm_object_result(result: VlmObjectResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sample_id": result.sample_id,
        "object_id": result.object_id,
        "label": result.label,
        "vlm_status": result.vlm_status.value,
        "object_risk": result.object_risk,
        "adapter_model": result.adapter_model,
        "failure_reason": result.failure_reason,
    }
    rule_lookup = {rule.rule_name: rule for rule in result.rule_results}

    for rule_name in VLM_RULE_NAMES:
        rule = rule_lookup.get(rule_name)
        if rule is None or rule.invalid_output:
            payload[f"{rule_name}_ep"] = None
            payload[f"{rule_name}_reason"] = None if rule is None else rule.reason or None
            continue

        payload[f"{rule_name}_ep"] = rule.error_probability
        payload[f"{rule_name}_reason"] = rule.reason or None

    return payload


def _review_queue_key(result: VlmObjectResult) -> tuple[int, float, str, str]:
    # Locked ordering: adapter failures first, then risk descending, then IDs ascending.
    is_adapter_failure = 0 if result.failure_reason else 1
    risk_desc = -(result.object_risk if result.object_risk is not None else 0.0)
    return (is_adapter_failure, risk_desc, result.sample_id, result.object_id)


def write_vlm_csv(results: list[VlmObjectResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VLM_CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()

        for result in _sorted_results(results):
            row = serialize_vlm_object_result(result)
            for key, value in list(row.items()):
                if isinstance(value, str):
                    row[key] = _sanitize_csv_cell(value)
            writer.writerow(row)

    return output_path


def write_vlm_json(results: list[VlmObjectResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    objects = [serialize_vlm_object_result(result) for result in _sorted_results(results)]

    review_queue_items = [
        result for result in results if result.vlm_status in (VlmVerdict.REVIEW, VlmVerdict.FAIL)
    ]
    review_queue_sorted = sorted(review_queue_items, key=_review_queue_key)
    review_queue = [serialize_vlm_object_result(result) for result in review_queue_sorted]

    payload = {"objects": objects, "review_queue": review_queue}
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    return output_path


def write_vlm_ndjson(results: list[VlmObjectResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for result in _sorted_results(results):
            record = serialize_vlm_object_result(result)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

    return output_path


def write_vlm_reports(
    results: list[VlmObjectResult],
    *,
    run_root: Path,
    run_timestamp: str,
    ndjson_path: Path | None = None,
) -> dict[str, Path]:
    run_dir = _safe_run_dir(run_root=run_root, run_timestamp=run_timestamp)
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_path = write_vlm_csv(results, run_dir / "vlm_report.csv")
    json_path = write_vlm_json(results, run_dir / "vlm_report.json")
    if ndjson_path is None:
        ndjson_path = write_vlm_ndjson(results, run_dir / "vlm_trace.ndjson")

    return {"vlm_csv": csv_path, "vlm_json": json_path, "vlm_ndjson": ndjson_path}
