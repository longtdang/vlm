from __future__ import annotations

import json
from pathlib import Path

from fiftyone_pose_importer.verification.report_vlm import serialize_vlm_object_result, write_vlm_reports
from fiftyone_pose_importer.verification.vlm_types import VlmObjectResult, VlmRuleResult, VlmVerdict


def _make_vlm_result(
    sample_id: str,
    object_id: str,
    label: str,
    vlm_status: VlmVerdict,
    object_risk: float | None,
    *,
    failure_reason: str | None = None,
    rules: list[VlmRuleResult] | None = None,
) -> VlmObjectResult:
    return VlmObjectResult(
        sample_id=sample_id,
        object_id=object_id,
        label=label,
        vlm_status=vlm_status,
        object_risk=object_risk,
        rule_results=rules or [],
        adapter_model="qwen3-vl-2b-instruct-torch",
        failure_reason=failure_reason,
        crop_path="crop.png",
    )


def test_serialize_vlm_object_result_has_required_fields() -> None:
    result = _make_vlm_result(
        "s1",
        "o1",
        "forklift",
        VlmVerdict.PASS,
        0.12,
        rules=[
            VlmRuleResult(
                rule_name="bbox_localization",
                error_probability=0.12,
                reason="ok",
                evidence=None,
                invalid_output=False,
            )
        ],
    )
    payload = serialize_vlm_object_result(result)
    assert payload["sample_id"] == "s1"
    assert payload["vlm_status"] == "PASS"
    assert "bbox_localization_ep" in payload
    assert "occlusion_state_reason" in payload


def test_write_vlm_reports_outputs_files_and_review_queue_order(tmp_path: Path) -> None:
    results = [
        _make_vlm_result("s1", "high", "l", VlmVerdict.FAIL, 0.9),
        _make_vlm_result(
            "s1",
            "adapter",
            "l",
            VlmVerdict.REVIEW,
            None,
            failure_reason="adapter_timeout:after 0.1s",
        ),
        _make_vlm_result("s1", "pass", "l", VlmVerdict.PASS, 0.1),
    ]
    paths = write_vlm_reports(results, run_root=tmp_path / "runs", run_timestamp="20260614T000000Z")
    assert Path(paths["vlm_csv"]).exists()
    assert Path(paths["vlm_json"]).exists()
    assert Path(paths["vlm_ndjson"]).exists()

    payload = json.loads(Path(paths["vlm_json"]).read_text(encoding="utf-8"))
    queue_ids = [row["object_id"] for row in payload["review_queue"]]
    assert queue_ids == ["adapter", "high"]
