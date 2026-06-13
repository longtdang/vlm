from __future__ import annotations

import concurrent.futures
import json
import re
from typing import Any

from PIL import Image as PILImage

from .types import ObjectVerificationResult
from .vlm_client import VlmAdapter
from .vlm_config import VlmConfig
from .vlm_types import VlmObjectResult, VlmRuleResult, VlmVerdict

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)

RULE_ANNOTATION_FIELDS: dict[str, list[str]] = {
    "bbox_localization": ["bbox"],
    "bbox_coverage": ["bbox", "attributes"],
    "clamp_type": ["attributes"],
    "roll_count": ["attributes"],
    "keypoint_position": ["keypoints", "visibility"],
    "occlusion_state": ["keypoints", "visibility"],
}


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str, tuple, set)) and len(value) == 0:
        return False
    return True


def build_prompt(template: str, label: str, rule: str, annotation: dict[str, Any]) -> str:
    fields = RULE_ANNOTATION_FIELDS.get(rule)
    if fields is None:
        annotation_fields = {k: v for k, v in annotation.items() if _is_meaningful(v)}
    else:
        annotation_fields = {k: annotation[k] for k in fields if k in annotation and _is_meaningful(annotation[k])}

    annotation_fields_json = json.dumps(annotation_fields, ensure_ascii=False)
    prompt = template
    prompt = prompt.replace("{label}", label)
    prompt = prompt.replace("{rule}", rule)
    prompt = prompt.replace("{annotation_fields_json}", annotation_fields_json)
    return prompt


def parse_vlm_response(raw: str, rule_name: str) -> VlmRuleResult:
    stripped = raw.strip()
    match = _FENCE_RE.search(stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return VlmRuleResult(
            rule_name=rule_name,
            error_probability=None,
            reason="invalid_output: JSON parse failed",
            evidence=None,
            invalid_output=True,
        )

    ep = parsed.get("error_probability")
    if not isinstance(ep, (int, float)) or not (0.0 <= float(ep) <= 1.0):
        return VlmRuleResult(
            rule_name=rule_name,
            error_probability=None,
            reason=f"invalid_output: error_probability={ep!r}",
            evidence=None,
            invalid_output=True,
        )

    evidence = parsed.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        evidence = str(evidence)

    return VlmRuleResult(
        rule_name=rule_name,
        error_probability=float(ep),
        reason=str(parsed.get("reason", "")),
        evidence=evidence,
        invalid_output=False,
    )


def _call_with_timeout(fn, *, timeout_seconds: float, image: PILImage.Image, prompt: str) -> str:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, image, prompt)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"after {timeout_seconds}s") from exc


def evaluate_vlm_object(
    *,
    result: ObjectVerificationResult,
    annotation: dict[str, Any],
    crop_image: PILImage.Image,
    adapter: VlmAdapter,
    vlm_config: VlmConfig,
) -> VlmObjectResult:
    rules = vlm_config.rules_for_label(result.label)
    thresholds = vlm_config.thresholds_for_label(result.label)

    rule_results: list[VlmRuleResult] = []
    adapter_model = vlm_config.model_name

    for rule in rules:
        per_label_template = vlm_config.prompt_for_label_rule(result.label, rule)
        template = per_label_template if per_label_template is not None else vlm_config.default_prompt_template
        prompt = build_prompt(template, result.label, rule, annotation)

        try:
            raw_text = _call_with_timeout(
                adapter.generate_text,
                timeout_seconds=vlm_config.generation.timeout_seconds,
                image=crop_image,
                prompt=prompt,
            )
            rule_results.append(parse_vlm_response(raw_text, rule))
        except TimeoutError as exc:
            return VlmObjectResult(
                sample_id=result.sample_id,
                object_id=result.object_id,
                label=result.label,
                vlm_status=VlmVerdict.REVIEW,
                object_risk=None,
                rule_results=rule_results,
                adapter_model=adapter_model,
                failure_reason=f"adapter_timeout:{exc}",
                crop_path=result.crop_path,
            )
        except Exception as exc:
            return VlmObjectResult(
                sample_id=result.sample_id,
                object_id=result.object_id,
                label=result.label,
                vlm_status=VlmVerdict.REVIEW,
                object_risk=None,
                rule_results=rule_results,
                adapter_model=adapter_model,
                failure_reason=f"adapter_error:{type(exc).__name__}:{exc}",
                crop_path=result.crop_path,
            )

    valid_results = [rule_result for rule_result in rule_results if not rule_result.invalid_output]
    if not valid_results:
        return VlmObjectResult(
            sample_id=result.sample_id,
            object_id=result.object_id,
            label=result.label,
            vlm_status=VlmVerdict.REVIEW,
            object_risk=None,
            rule_results=rule_results,
            adapter_model=adapter_model,
            failure_reason="all_invalid_output",
            crop_path=result.crop_path,
        )

    object_risk = max((rule_result.error_probability or 0.0) for rule_result in valid_results)
    if object_risk <= thresholds.pass_below:
        vlm_status = VlmVerdict.PASS
    elif object_risk <= thresholds.review_below:
        vlm_status = VlmVerdict.REVIEW
    else:
        vlm_status = VlmVerdict.FAIL

    return VlmObjectResult(
        sample_id=result.sample_id,
        object_id=result.object_id,
        label=result.label,
        vlm_status=vlm_status,
        object_risk=object_risk,
        rule_results=rule_results,
        adapter_model=adapter_model,
        failure_reason=None,
        crop_path=result.crop_path,
    )
