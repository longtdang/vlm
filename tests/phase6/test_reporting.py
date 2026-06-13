from __future__ import annotations

import csv
import json
from pathlib import Path

from fiftyone_pose_importer.verification.report_csv import write_run_reports
from fiftyone_pose_importer.verification.report_json import write_json_report
from fiftyone_pose_importer.verification.report_ndjson import write_ndjson_report
from fiftyone_pose_importer.verification.types import (
    DeterministicVerdict,
    ObjectVerificationResult,
    RuleCategory,
    RuleResult,
)


def _object_results() -> list[ObjectVerificationResult]:
    return [
        ObjectVerificationResult(
            sample_id="sample-b",
            object_id="obj-2",
            label="=formula",
            verdict=DeterministicVerdict.FAIL,
            crop_path="runs/20260101T000000Z/crops/sample-b_obj-2.png",
            rule_results=[
                RuleResult(
                    rule_name="visibility_codes",
                    category=RuleCategory.VISIBILITY_FORMAT,
                    verdict=DeterministicVerdict.FAIL,
                    reason="invalid_visibility_code:3",
                    evaluable=True,
                ),
                RuleResult(
                    rule_name="bbox_non_empty",
                    category=RuleCategory.DETECTION,
                    verdict=DeterministicVerdict.PASS,
                    reason=None,
                    evaluable=True,
                ),
            ],
            failure_reasons=["=dangerous_formula"],
        ),
        ObjectVerificationResult(
            sample_id="sample-a",
            object_id="obj-1",
            label="forklift",
            verdict=DeterministicVerdict.PASS,
            crop_path="runs/20260101T000000Z/crops/sample-a_obj-1.png",
            rule_results=[
                RuleResult(
                    rule_name="bbox_non_empty",
                    category=RuleCategory.DETECTION,
                    verdict=DeterministicVerdict.PASS,
                    reason=None,
                    evaluable=True,
                )
            ],
            failure_reasons=[],
        ),
    ]


def test_json_ndjson_schema_and_order(tmp_path: Path) -> None:
    results = _object_results()

    json_path = write_json_report(results, tmp_path / "report.json")
    ndjson_path = write_ndjson_report(results, tmp_path / "trace.ndjson")

    report = json.loads(json_path.read_text(encoding="utf-8"))
    trace_records = [json.loads(line) for line in ndjson_path.read_text(encoding="utf-8").splitlines() if line]

    assert [record["sample_id"] for record in report["objects"]] == ["sample-a", "sample-b"]
    assert [record["sample_id"] for record in trace_records] == ["sample-a", "sample-b"]

    required = {"sample_id", "object_id", "label", "verdict", "crop_path", "failure_reasons", "rule_results"}
    assert required <= set(report["objects"][0])
    assert required <= set(trace_records[0])

    rule = report["objects"][1]["rule_results"][0]
    assert {"rule_name", "category", "verdict", "reason", "evaluable"} <= set(rule)

    second_json_path = write_json_report(results, tmp_path / "report-second.json")
    second_ndjson_path = write_ndjson_report(results, tmp_path / "trace-second.ndjson")

    assert json_path.read_text(encoding="utf-8") == second_json_path.read_text(encoding="utf-8")
    assert ndjson_path.read_text(encoding="utf-8") == second_ndjson_path.read_text(encoding="utf-8")


def test_csv_json_ndjson_emitted_with_required_columns(tmp_path: Path) -> None:
    outputs = write_run_reports(
        _object_results(),
        run_root=tmp_path,
        run_timestamp="20260613T070000Z",
    )

    assert outputs["run_dir"].name == "20260613T070000Z"
    assert outputs["csv"].exists()
    assert outputs["json"].exists()
    assert outputs["ndjson"].exists()
    assert outputs["csv"].parent == outputs["json"].parent == outputs["ndjson"].parent == outputs["run_dir"]

    with outputs["csv"].open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert list(rows[0]) == [
        "sample_id",
        "object_id",
        "label",
        "verdict",
        "crop_path",
        "failure_reasons",
        "rule_details",
    ]
    assert rows[1]["verdict"] == "FAIL"
    assert rows[1]["crop_path"].endswith("sample-b_obj-2.png")
    assert "invalid_visibility_code:3" in rows[1]["rule_details"]
    assert rows[1]["label"].startswith("'")
    assert rows[1]["failure_reasons"].startswith("'")
