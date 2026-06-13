from __future__ import annotations

from dataclasses import replace
import json
import time

from PIL import Image

from fiftyone_pose_importer.verification.types import DeterministicVerdict, ObjectVerificationResult
from fiftyone_pose_importer.verification.vlm_client import MockVlmAdapter
from fiftyone_pose_importer.verification.vlm_config import load_vlm_config
from fiftyone_pose_importer.verification.vlm_engine import _FENCE_RE, build_prompt, evaluate_vlm_object, parse_vlm_response
from fiftyone_pose_importer.verification.vlm_types import VlmVerdict


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
    label: str = "forklift",
    rules: list[str] | None = None,
    pass_below: float = 0.20,
    review_below: float = 0.60,
):
    config, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "thresholds": {"pass_below": pass_below, "review_below": review_below},
            "default_prompt_template": "label={label} rule={rule} fields={annotation_fields_json}",
            "labels": {
                label: {
                    "enabled": True,
                    "rules": rules or ["bbox_localization", "bbox_coverage"],
                }
            },
        }
    )
    return config


def _make_crop_image() -> Image.Image:
    return Image.new("RGB", (10, 10), (20, 30, 40))


def test_fence_regex_extracts_json_block() -> None:
    raw = '```json\n{"error_probability": 0.5}\n```'
    match = _FENCE_RE.search(raw)
    assert match is not None
    assert '"error_probability"' in match.group(1)


def test_build_prompt_substitutes_placeholders() -> None:
    result = build_prompt(
        "label={label} rule={rule} fields={annotation_fields_json}",
        "forklift",
        "bbox_localization",
        {"bbox": [1, 2, 3, 4]},
    )
    assert "label=forklift" in result
    assert "rule=bbox_localization" in result
    assert '"bbox"' in result


def test_build_prompt_filters_annotation_fields_by_rule() -> None:
    annotation = {
        "bbox": [1, 2, 3, 4],
        "attributes": {"clamp_type": "2-arm"},
        "keypoints": [[1, 1]],
        "visibility": [2],
    }
    result_bbox = build_prompt("{annotation_fields_json}", "l", "bbox_localization", annotation)
    parsed_bbox = json.loads(result_bbox)
    assert set(parsed_bbox) == {"bbox"}

    result_kp = build_prompt("{annotation_fields_json}", "l", "keypoint_position", annotation)
    parsed_kp = json.loads(result_kp)
    assert set(parsed_kp) == {"keypoints", "visibility"}


def test_parse_vlm_response_valid_json() -> None:
    result = parse_vlm_response('{"error_probability": 0.3, "reason": "ok", "evidence": "e1"}', "rule1")
    assert result.error_probability == 0.3
    assert result.reason == "ok"
    assert result.evidence == "e1"
    assert result.invalid_output is False


def test_parse_vlm_response_integer_zero_is_valid() -> None:
    result = parse_vlm_response('{"error_probability": 0, "reason": "clean"}', "r")
    assert result.invalid_output is False
    assert result.error_probability == 0.0


def test_parse_vlm_response_fence_wrapped_json() -> None:
    raw = '```json\n{"error_probability": 0.5, "reason": "fence test"}\n```'
    result = parse_vlm_response(raw, "r")
    assert result.invalid_output is False
    assert result.error_probability == 0.5


def test_parse_vlm_response_not_json() -> None:
    result = parse_vlm_response("I cannot evaluate this.", "r")
    assert result.invalid_output is True
    assert result.error_probability is None
    assert "JSON parse failed" in result.reason


def test_parse_vlm_response_out_of_range() -> None:
    result = parse_vlm_response('{"error_probability": 1.5, "reason": "bad"}', "r")
    assert result.invalid_output is True


def test_parse_vlm_response_missing_ep() -> None:
    result = parse_vlm_response('{"reason": "no ep"}', "r")
    assert result.invalid_output is True


def test_evaluate_vlm_object_pass_verdict() -> None:
    adapter = MockVlmAdapter(
        responses={
            "bbox_localization": '{"error_probability": 0.1, "reason": "ok"}',
            "bbox_coverage": '{"error_probability": 0.15, "reason": "ok"}',
        },
    )
    result = _make_det_result("s1", "o1", "forklift")
    cfg = _make_vlm_config("forklift", rules=["bbox_localization", "bbox_coverage"])
    vlm_result = evaluate_vlm_object(
        result=result,
        annotation={"bbox": [1, 2, 3, 4], "attributes": {}, "keypoints": [], "visibility": []},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.PASS
    assert vlm_result.object_risk == 0.15


def test_evaluate_vlm_object_review_threshold() -> None:
    adapter = MockVlmAdapter(default_response='{"error_probability": 0.45, "reason": "uncertain"}')
    result = _make_det_result("s1", "o1", "forklift")
    cfg = _make_vlm_config("forklift", rules=["bbox_localization"])
    vlm_result = evaluate_vlm_object(
        result=result,
        annotation={"bbox": [1, 2, 3, 4], "attributes": {}, "keypoints": [], "visibility": []},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.REVIEW
    assert vlm_result.object_risk == 0.45


def test_evaluate_vlm_object_fail_threshold() -> None:
    adapter = MockVlmAdapter(default_response='{"error_probability": 0.8, "reason": "bad"}')
    cfg = _make_vlm_config("forklift", rules=["bbox_localization"])
    vlm_result = evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={"bbox": [1, 2, 3, 4], "attributes": {}, "keypoints": [], "visibility": []},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.FAIL
    assert vlm_result.object_risk == 0.8


def test_evaluate_vlm_object_adapter_error_returns_review() -> None:
    class FailAdapter:
        def generate_text(self, image, prompt):
            raise RuntimeError("GPU OOM")

    cfg = _make_vlm_config("forklift", rules=["bbox_localization"])
    vlm_result = evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={},
        crop_image=_make_crop_image(),
        adapter=FailAdapter(),
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.REVIEW
    assert vlm_result.object_risk is None
    assert vlm_result.failure_reason is not None
    assert vlm_result.failure_reason.startswith("adapter_error:")


def test_evaluate_vlm_object_timeout_review() -> None:
    class SlowMockAdapter:
        def generate_text(self, image, prompt):
            time.sleep(0.2)
            return '{"error_probability": 0.1, "reason": "ok"}'

    config = _make_vlm_config("forklift", rules=["bbox_localization"])
    config = replace(config, generation=replace(config.generation, timeout_seconds=0.01))
    result = evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=SlowMockAdapter(),
        vlm_config=config,
    )
    assert result.vlm_status == VlmVerdict.REVIEW
    assert result.failure_reason is not None
    assert result.failure_reason.startswith("adapter_timeout:")


def test_evaluate_vlm_object_all_invalid_output_returns_review() -> None:
    adapter = MockVlmAdapter(default_response="not json at all")
    cfg = _make_vlm_config("forklift", rules=["bbox_localization", "bbox_coverage"])
    vlm_result = evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.REVIEW
    assert vlm_result.failure_reason == "all_invalid_output"


def test_evaluate_vlm_object_per_label_threshold() -> None:
    adapter = MockVlmAdapter(default_response='{"error_probability": 0.25, "reason": "ok"}')
    cfg_raw = {
        "model_name": "qwen3-vl-2b-instruct-torch",
        "thresholds": {"pass_below": 0.20, "review_below": 0.60},
        "labels": {
            "forklift": {
                "enabled": True,
                "rules": ["bbox_localization"],
                "thresholds": {"pass_below": 0.30, "review_below": 0.60},
            }
        },
    }
    cfg, _ = load_vlm_config(cfg_raw)
    vlm_result = evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )
    assert vlm_result.vlm_status == VlmVerdict.PASS


def test_evaluate_vlm_object_prompt_template_override() -> None:
    class CaptureAdapter:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate_text(self, image, prompt):
            self.prompts.append(prompt)
            return '{"error_probability": 0.1, "reason": "ok"}'

    cfg, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "default_prompt_template": "default-{rule}",
            "labels": {
                "forklift": {
                    "enabled": True,
                    "rules": ["bbox_localization", "bbox_coverage"],
                    "prompts": {"bbox_coverage": "custom-{rule}"},
                }
            },
        }
    )
    adapter = CaptureAdapter()
    evaluate_vlm_object(
        result=_make_det_result("s1", "o1", "forklift"),
        annotation={"bbox": [1, 2, 3, 4]},
        crop_image=_make_crop_image(),
        adapter=adapter,
        vlm_config=cfg,
    )

    assert any(prompt.startswith("default-bbox_localization") for prompt in adapter.prompts)
    assert any(prompt.startswith("custom-bbox_coverage") for prompt in adapter.prompts)
