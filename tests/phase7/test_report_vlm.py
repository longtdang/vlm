from __future__ import annotations

import csv
import json
from pathlib import Path

from fiftyone_pose_importer.verification.report_csv import _safe_run_dir
from fiftyone_pose_importer.verification.report_vlm import serialize_vlm_object_result, write_vlm_reports
from fiftyone_pose_importer.verification.vlm_types import VlmObjectResult, VlmRuleResult, VlmVerdict


def _make_vlm_result(
    sample_id: str,
    object_id: str,
    label: str,
    vlm_status: VlmVerdict,
    object_risk: float | None,
    *,
    rules: list[str] | None = None,
    failure_reason: str | None = None,
    crop_path: str = "c.png",
    adapter_model: str = "qwen3-vl-2b-instruct-torch",
) -> VlmObjectResult:
    return VlmObjectResult(
        sample_id=sample_id,
        object_id=object_id,
        label=label,
        vlm_status=vlm_status,
        object_risk=object_risk,
        rule_results=[
            VlmRuleResult(
                rule_name=rule_name,
                error_probability=0.1,
                reason="ok",
                evidence=None,
                invalid_output=False,
            )
            for rule_name in (rules or [])
        ],
        adapter_model=adapter_model,
        failure_reason=failure_reason,
        crop_path=crop_path,
    )


def test_serialize_vlm_object_result_has_all_keys() -> None:
    result = _make_vlm_result("s1", "o1", "forklift", VlmVerdict.PASS, 0.1, rules=["bbox_localization"])
    payload = serialize_vlm_object_result(result)
    for key in [
        "sample_id",
        "object_id",
        "label",
        "vlm_status",
        "object_risk",
        "adapter_model",
        "failure_reason",
    ]:
        assert key in payload
    assert "bbox_localization_ep" in payload
    assert "occlusion_state_ep" in payload
    assert payload["occlusion_state_ep"] is None


def test_serialize_vlm_object_result_review_failure_reason() -> None:
    result = _make_vlm_result(
        "s1",
        "o2",
        "forklift",
        VlmVerdict.REVIEW,
        None,
        failure_reason="adapter_error:RuntimeError:boom",
    )
    payload = serialize_vlm_object_result(result)
    assert payload["failure_reason"] == "adapter_error:RuntimeError:boom"
    assert payload["object_risk"] is None


def test_write_vlm_reports_creates_three_files(tmp_path: Path) -> None:
    results = [_make_vlm_result("s1", "o1", "l", VlmVerdict.PASS, 0.1)]
    paths = write_vlm_reports(results, run_root=tmp_path / "runs", run_timestamp="20260614T000000Z")
    assert Path(paths["vlm_csv"]).exists()
    assert Path(paths["vlm_json"]).exists()
    assert Path(paths["vlm_ndjson"]).exists()


def test_vlm_csv_has_correct_header(tmp_path: Path) -> None:
    paths = write_vlm_reports([], run_root=tmp_path / "runs", run_timestamp="20260614T010000Z")
    with open(paths["vlm_csv"], encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "sample_id" in reader.fieldnames
        assert "vlm_status" in reader.fieldnames
        assert "bbox_localization_ep" in reader.fieldnames
        assert "occlusion_state_reason" in reader.fieldnames


def test_vlm_json_has_objects_and_review_queue(tmp_path: Path) -> None:
    results = [
        _make_vlm_result("s1", "o1", "l", VlmVerdict.PASS, 0.1),
        _make_vlm_result("s1", "o2", "l", VlmVerdict.REVIEW, 0.5),
        _make_vlm_result("s1", "o3", "l", VlmVerdict.FAIL, 0.8),
    ]
    paths = write_vlm_reports(results, run_root=tmp_path / "runs", run_timestamp="20260614T020000Z")
    payload = json.loads(Path(paths["vlm_json"]).read_text(encoding="utf-8"))
    assert "objects" in payload
    assert "review_queue" in payload
    assert len(payload["objects"]) == 3
    assert len(payload["review_queue"]) == 2
    assert payload["review_queue"][0]["vlm_status"] == "FAIL"
    assert payload["review_queue"][1]["vlm_status"] == "REVIEW"


def test_review_queue_adapter_failure_first(tmp_path: Path) -> None:
    results = [
        _make_vlm_result("s1", "high", "l", VlmVerdict.FAIL, 0.9),
        _make_vlm_result(
            "s1",
            "adapter_fail",
            "l",
            VlmVerdict.REVIEW,
            None,
            failure_reason="adapter_error:RuntimeError:GPU OOM",
        ),
    ]
    paths = write_vlm_reports(results, run_root=tmp_path / "runs", run_timestamp="20260614T030000Z")
    payload = json.loads(Path(paths["vlm_json"]).read_text(encoding="utf-8"))
    queue = payload["review_queue"]
    assert queue[0]["object_id"] == "adapter_fail"
    assert queue[1]["object_id"] == "high"


def test_vlm_ndjson_one_line_per_result(tmp_path: Path) -> None:
    results = [_make_vlm_result(f"s{i}", "o1", "l", VlmVerdict.PASS, 0.1) for i in range(5)]
    paths = write_vlm_reports(results, run_root=tmp_path / "runs", run_timestamp="20260614T040000Z")
    lines = Path(paths["vlm_ndjson"]).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5
    for line in lines:
        json.loads(line)


def test_write_vlm_reports_same_run_dir_as_deterministic(tmp_path: Path) -> None:
    expected_run_dir = _safe_run_dir(run_root=tmp_path / "runs", run_timestamp="20260614T050000Z")
    paths = write_vlm_reports([], run_root=tmp_path / "runs", run_timestamp="20260614T050000Z")
    assert Path(paths["vlm_csv"]).parent == expected_run_dir
