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
            # future.cancel() is a no-op on already-running futures in Python's
            # concurrent.futures — the underlying thread continues until completion.
            # GPU/CPU resources remain in use until the thread finishes naturally.
            # True cancellation would require subprocess/multiprocessing isolation.
            raise TimeoutError(f"after {timeout_seconds}s") from exc


def _finalize_vlm_result(
    result: ObjectVerificationResult,
    rule_results: list[VlmRuleResult],
    vlm_config: VlmConfig,
) -> VlmObjectResult:
    """Compute verdict and risk from already-evaluated rule results."""
    adapter_model = vlm_config.model_name
    valid_results = [r for r in rule_results if not r.invalid_output]

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

    thresholds = vlm_config.thresholds_for_label(result.label)
    object_risk = max((r.error_probability or 0.0) for r in valid_results)
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


def _error_result(
    result: ObjectVerificationResult,
    adapter_model: str,
    failure_reason: str,
    rule_results: list[VlmRuleResult] | None = None,
) -> VlmObjectResult:
    return VlmObjectResult(
        sample_id=result.sample_id,
        object_id=result.object_id,
        label=result.label,
        vlm_status=VlmVerdict.REVIEW,
        object_risk=None,
        rule_results=rule_results or [],
        adapter_model=adapter_model,
        failure_reason=failure_reason,
        crop_path=result.crop_path,
    )


def evaluate_vlm_batch(
    items: list[tuple[ObjectVerificationResult, dict[str, Any], PILImage.Image]],
    *,
    adapter: VlmAdapter,
    vlm_config: VlmConfig,
) -> list[VlmObjectResult]:
    """Evaluate a batch of objects in as few generate() calls as possible.

    All eligible (image, prompt) pairs across all objects and rules are
    flattened into a single ``generate_text_batch()`` call when the adapter
    supports it, or fall back to sequential ``generate_text()`` calls.

    Items with no configured rules receive an immediate ``REVIEW`` result
    without touching the adapter.
    """
    adapter_model = vlm_config.model_name

    # Build flat (image, prompt) lists; track per-item slice boundaries
    all_images: list[PILImage.Image] = []
    all_prompts: list[str] = []
    item_slices: list[tuple[int, int, list[str]]] = []  # (start, end, rules)

    for result, annotation, crop_image in items:
        rules = vlm_config.rules_for_label(result.label)
        start = len(all_prompts)
        for rule in rules:
            tmpl = vlm_config.prompt_for_label_rule(result.label, rule)
            if tmpl is None:
                tmpl = vlm_config.default_prompt_template
            all_images.append(crop_image)
            all_prompts.append(build_prompt(tmpl, result.label, rule, annotation))
        item_slices.append((start, len(all_prompts), rules))

    if not all_prompts:
        return [
            _error_result(result, adapter_model, "no_rules_configured")
            for result, _, _ in items
        ]

    timeout = vlm_config.generation.timeout_seconds

    try:
        if hasattr(adapter, "generate_text_batch"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    adapter.generate_text_batch,  # type: ignore[attr-defined]
                    all_images,
                    all_prompts,
                )
                try:
                    raw_texts: list[str] = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError as exc:
                    raise TimeoutError(f"after {timeout}s") from exc
        else:
            raw_texts = [
                _call_with_timeout(
                    adapter.generate_text,
                    timeout_seconds=timeout,
                    image=image,
                    prompt=prompt,
                )
                for image, prompt in zip(all_images, all_prompts)
            ]
    except TimeoutError as exc:
        failure = f"adapter_timeout:{exc}"
        return [_error_result(result, adapter_model, failure) for result, _, _ in items]
    except Exception as exc:
        failure = f"adapter_error:{type(exc).__name__}:{exc}"
        return [_error_result(result, adapter_model, failure) for result, _, _ in items]

    # Reassemble per-item results from the flat response list
    outcomes: list[VlmObjectResult] = []
    for (result, _, _), (start, end, rules) in zip(items, item_slices):
        if not rules:
            outcomes.append(_error_result(result, adapter_model, "no_rules_configured"))
            continue
        rule_results = [
            parse_vlm_response(raw, rule)
            for raw, rule in zip(raw_texts[start:end], rules)
        ]
        outcomes.append(_finalize_vlm_result(result, rule_results, vlm_config))

    return outcomes


def evaluate_vlm_object(
    *,
    result: ObjectVerificationResult,
    annotation: dict[str, Any],
    crop_image: PILImage.Image,
    adapter: VlmAdapter,
    vlm_config: VlmConfig,
) -> VlmObjectResult:
    """Evaluate a single object. Delegates to evaluate_vlm_batch."""
    return evaluate_vlm_batch(
        [(result, annotation, crop_image)],
        adapter=adapter,
        vlm_config=vlm_config,
    )[0]
