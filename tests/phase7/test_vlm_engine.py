from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time

from PIL import Image

from fiftyone_pose_importer.verification.types import DeterministicVerdict, ObjectVerificationResult
from fiftyone_pose_importer.verification.vlm_client import MockVlmAdapter
from fiftyone_pose_importer.verification.vlm_config import load_vlm_config
from fiftyone_pose_importer.verification.vlm_types import VlmVerdict
from fiftyone_pose_importer.verification.vlm_engine import build_prompt, parse_vlm_response, evaluate_vlm_object


def _make_det_result(
    sample_id: str = "s1",
    object_id: str = "o1",
    label: str = "forklift",
    verdict: DeterministicVerdict = DeterministicVerdict.PASS,
    crop_path: str = "crop.png",
) -> ObjectVerificationResult:
    return ObjectVerificationResult(
        sample_id=sample_id,
        object_id=object_id,
        label=label,
        verdict=verdict,
        crop_path=crop_path,
        rule_results=[],
        failure_reasons=[],
    )


def _make_vlm_config(
    *,
    label: str = "forklift",
    rules: list[str] | None = None,
    pass_below: float = 0.20,
    review_below: float = 0.60,
):
    cfg, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "thresholds": {"pass_below": pass_below, "review_below": review_below},
            "labels": {
                label: {
                    "enabled": True,
                    "rules": rules or ["bbox_localization", "bbox_coverage"],
                }
            },
        }
    )
    return cfg


def _make_crop_image() -> Image.Image:
    return Image.new("RGB", (10, 10), (20, 30, 40))


def test_build_prompt_filters_annotation_fields_by_rule() -> None:
    annotation = {
        "bbox": [1, 2, 3, 4],
        "attributes": {"clamp_type": "2-arm"},
        "keypoints": [[1, 1]],
        "visibility": [2],
    }
    result = build_prompt("{annotation_fields_json}", "forklift", "bbox_localization", annotation)
    assert '"bbox"' in result
    assert '"keypoints"' not in result


def test_parse_vlm_response_accepts_fence_and_zero_integer() -> None:
    result = parse_vlm_response('```json\n{"error_probability": 0, "reason": "fine"}\n```', "rule1")
    assert result.invalid_output is False
    assert result.error_probability == 0.0


def test_parse_vlm_response_invalid_json_returns_invalid_output() -> None:
    result = parse_vlm_response("not-json", "rule1")
    assert result.invalid_output is True
    assert result.error_probability is None


def test_evaluate_vlm_object_adapter_error_returns_review() -> None:
    class FailAdapter:
        def generate_text(self, image, prompt):
            raise RuntimeError("GPU OOM")

    out = evaluate_vlm_object(
        result=_make_det_result(),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=FailAdapter(),
        vlm_config=_make_vlm_config(rules=["bbox_localization"]),
    )
    assert out.vlm_status is VlmVerdict.REVIEW
    assert out.object_risk is None
    assert out.failure_reason is not None and out.failure_reason.startswith("adapter_error:")


def test_evaluate_vlm_object_timeout_returns_review() -> None:
    class SlowAdapter:
        def generate_text(self, image, prompt):
            time.sleep(0.2)
            return '{"error_probability": 0.1, "reason": "late"}'

    cfg = _make_vlm_config(rules=["bbox_localization"])
    cfg = replace(cfg, generation=replace(cfg.generation, timeout_seconds=0.01))

    out = evaluate_vlm_object(
        result=_make_det_result(),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=SlowAdapter(),
        vlm_config=cfg,
    )
    assert out.vlm_status is VlmVerdict.REVIEW
    assert out.object_risk is None
    assert out.failure_reason is not None and out.failure_reason.startswith("adapter_timeout:")


def test_evaluate_vlm_object_risk_aggregation_and_thresholds() -> None:
    adapter = MockVlmAdapter(
        responses={
            "bbox_localization": '{"error_probability": 0.1, "reason": "ok"}',
            "bbox_coverage": '{"error_probability": 0.25, "reason": "mid"}',
        }
    )
    out = evaluate_vlm_object(
        result=_make_det_result(),
        annotation={"bbox": [1, 2, 3, 4], "attributes": {}, "keypoints": [], "visibility": []},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=_make_vlm_config(rules=["bbox_localization", "bbox_coverage"]),
    )
    assert out.object_risk == 0.25
    assert out.vlm_status is VlmVerdict.REVIEW


def test_evaluate_vlm_object_all_invalid_output_returns_review() -> None:
    out = evaluate_vlm_object(
        result=_make_det_result(),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=MockVlmAdapter(default_response="not-json"),
        vlm_config=_make_vlm_config(rules=["bbox_localization", "bbox_coverage"]),
    )
    assert out.vlm_status is VlmVerdict.REVIEW
    assert out.object_risk is None
    assert out.failure_reason == "all_invalid_output"
