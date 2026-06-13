from __future__ import annotations

import json
from pathlib import Path

from .report_json import _sorted_results, serialize_object_result
from .types import ObjectVerificationResult


def write_ndjson_report(results: list[ObjectVerificationResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for result in _sorted_results(results):
            record = serialize_object_result(result)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return output_path
