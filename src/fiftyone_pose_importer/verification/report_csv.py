from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
import re

from .report_json import _sorted_results, serialize_object_result, write_json_report
from .report_ndjson import write_ndjson_report
from .types import ObjectVerificationResult

_TIMESTAMP_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


def _sanitize_csv_cell(value: str) -> str:
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def _safe_run_timestamp(run_timestamp: str | None) -> str:
    if run_timestamp is None:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if ".." in run_timestamp or "/" in run_timestamp or "\\" in run_timestamp:
        raise ValueError("run_timestamp must not include path traversal tokens")
    if not _TIMESTAMP_PATTERN.fullmatch(run_timestamp):
        raise ValueError("run_timestamp must match YYYYMMDDTHHMMSSZ")
    return run_timestamp


def _safe_run_dir(run_root: Path, run_timestamp: str) -> Path:
    run_root_resolved = run_root.resolve()
    run_dir = (run_root / run_timestamp).resolve()
    if run_dir != run_root_resolved and run_root_resolved not in run_dir.parents:
        raise ValueError("run directory escapes run_root")
    return run_dir


def write_csv_report(results: list[ObjectVerificationResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "object_id",
        "label",
        "verdict",
        "failure_reasons",
        "rule_details",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for result in _sorted_results(results):
            record = serialize_object_result(result)
            rule_details = "; ".join(
                f"{rule['category']}:{rule['rule_name']}={rule['verdict']}"
                + (f"({rule['reason']})" if rule["reason"] else "")
                for rule in record["rule_results"]
            )
            failure_reasons = "; ".join(record["failure_reasons"])
            writer.writerow(
                {
                    "sample_id": _sanitize_csv_cell(record["sample_id"]),
                    "object_id": _sanitize_csv_cell(record["object_id"]),
                    "label": _sanitize_csv_cell(record["label"]),
                    "verdict": record["verdict"],
                    "failure_reasons": _sanitize_csv_cell(failure_reasons),
                    "rule_details": _sanitize_csv_cell(rule_details),
                }
            )

    return output_path


def write_run_reports(
    results: list[ObjectVerificationResult],
    *,
    run_root: Path,
    run_timestamp: str | None = None,
) -> dict[str, Path]:
    safe_timestamp = _safe_run_timestamp(run_timestamp)
    run_dir = _safe_run_dir(run_root=run_root, run_timestamp=safe_timestamp)
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_path = write_csv_report(results, run_dir / "deterministic_report.csv")
    json_path = write_json_report(results, run_dir / "deterministic_report.json")
    ndjson_path = write_ndjson_report(results, run_dir / "deterministic_trace.ndjson")

    return {
        "run_dir": run_dir,
        "csv": csv_path,
        "json": json_path,
        "ndjson": ndjson_path,
    }
