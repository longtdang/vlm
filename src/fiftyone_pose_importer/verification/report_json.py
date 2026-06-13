from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ObjectVerificationResult


def _sorted_results(results: list[ObjectVerificationResult]) -> list[ObjectVerificationResult]:
    return sorted(results, key=lambda result: (result.sample_id, result.object_id))


def serialize_object_result(result: ObjectVerificationResult) -> dict[str, Any]:
    ordered_rules = sorted(
        result.rule_results,
        key=lambda rule: (rule.category.value, rule.rule_name),
    )
    return {
        "sample_id": result.sample_id,
        "object_id": result.object_id,
        "label": result.label,
        "verdict": result.verdict.value,
        "crop_path": result.crop_path,
        "failure_reasons": sorted(result.failure_reasons),
        "rule_results": [
            {
                "rule_name": rule.rule_name,
                "category": rule.category.value,
                "verdict": rule.verdict.value,
                "reason": rule.reason,
                "evaluable": rule.evaluable,
            }
            for rule in ordered_rules
        ],
    }


def write_json_report(results: list[ObjectVerificationResult], output_path: Path) -> Path:
    payload = {"objects": [serialize_object_result(result) for result in _sorted_results(results)]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return output_path
