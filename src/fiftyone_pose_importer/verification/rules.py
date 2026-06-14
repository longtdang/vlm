from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .types import DeterministicVerdict, RuleCategory, RuleResult, RuleSpec


class UnevaluableRuleError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


RuleEvaluator = Callable[[dict[str, Any], RuleSpec], tuple[DeterministicVerdict, str | None]]


def _bbox_values(annotation: dict[str, Any]) -> tuple[float, float, float, float]:
    bbox = annotation.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise UnevaluableRuleError("bbox_missing_or_malformed")
    try:
        x, y, w, h = (float(v) for v in bbox)
    except (TypeError, ValueError) as exc:
        raise UnevaluableRuleError("bbox_missing_or_malformed") from exc
    return x, y, w, h


def evaluate_bbox_format(annotation: dict[str, Any], _spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    _bbox_values(annotation)
    return DeterministicVerdict.PASS, None


def evaluate_bbox_non_empty(annotation: dict[str, Any], _spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    _x, _y, w, h = _bbox_values(annotation)
    if w <= 0 or h <= 0:
        return DeterministicVerdict.FAIL, "invalid_bbox"
    return DeterministicVerdict.PASS, None


def evaluate_required_attributes(annotation: dict[str, Any], spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    attrs = annotation.get("attributes")
    if not isinstance(attrs, dict):
        raise UnevaluableRuleError("attributes_missing_or_malformed")

    required = []
    if spec.params is not None:
        required = spec.params.get("required", [])  # type: ignore[assignment]
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise UnevaluableRuleError("required_attribute_params_invalid")

    for key in required:
        if key not in attrs:
            return DeterministicVerdict.FAIL, f"missing_required_attribute:{key}"
    return DeterministicVerdict.PASS, None


def evaluate_roll_count_positive(annotation: dict[str, Any], _spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    attrs = annotation.get("attributes")
    if not isinstance(attrs, dict):
        raise UnevaluableRuleError("attributes_missing_or_malformed")

    value = attrs.get("roll_count")
    if value is None:
        return DeterministicVerdict.FAIL, "missing_roll_count"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise UnevaluableRuleError("roll_count_not_numeric")

    if parsed <= 0:
        return DeterministicVerdict.FAIL, "roll_count_non_positive"
    return DeterministicVerdict.PASS, None


def evaluate_clamp_type_allowed(annotation: dict[str, Any], spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    attrs = annotation.get("attributes")
    if not isinstance(attrs, dict):
        raise UnevaluableRuleError("attributes_missing_or_malformed")

    clamp_type = attrs.get("clamp_type")
    if not isinstance(clamp_type, str):
        raise UnevaluableRuleError("clamp_type_missing")

    allowed = ["2-arm", "3-arm"]
    if spec.params is not None and "allowed" in spec.params:
        raw_allowed = spec.params["allowed"]
        if not isinstance(raw_allowed, list) or not all(isinstance(item, str) for item in raw_allowed):
            raise UnevaluableRuleError("allowed_clamp_types_invalid")
        allowed = raw_allowed

    if clamp_type not in allowed:
        return DeterministicVerdict.FAIL, f"invalid_clamp_type:{clamp_type}"
    return DeterministicVerdict.PASS, None


def evaluate_keypoint_count(annotation: dict[str, Any], spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    keypoints = annotation.get("keypoints")
    if not isinstance(keypoints, list):
        raise UnevaluableRuleError("keypoints_missing_or_malformed")

    expected = None
    if spec.params is not None:
        expected = spec.params.get("expected")
    if not isinstance(expected, int):
        raise UnevaluableRuleError("expected_keypoint_count_missing")

    if len(keypoints) != expected:
        return DeterministicVerdict.FAIL, f"keypoint_count_mismatch:{len(keypoints)}!={expected}"
    return DeterministicVerdict.PASS, None


def evaluate_visibility_codes(annotation: dict[str, Any], _spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    visibility = annotation.get("visibility")
    if not isinstance(visibility, list):
        raise UnevaluableRuleError("visibility_missing_or_malformed")

    if any(code not in (0, 1, 2) for code in visibility):
        return DeterministicVerdict.FAIL, "invalid_visibility_codes"
    return DeterministicVerdict.PASS, None


def evaluate_out_of_frame_occluded(annotation: dict[str, Any], _spec: RuleSpec) -> tuple[DeterministicVerdict, str | None]:
    """Keypoints outside the original image frame must be marked occluded (visibility=1).

    Applies to skeleton annotations only. Out-of-frame indices are pre-computed
    by ``plan_crop()`` and stored in the annotation payload under
    ``out_of_frame_indices``. If the key is absent or empty, the rule passes.

    Fails if any out-of-frame point has visibility=2 (explicitly marked visible).

    The rule reads ``original_visibility`` when available (populated by ``plan_crop()``
    before the auto-correction step), falling back to ``visibility`` for backward
    compatibility.  This prevents a false-pass caused by ``plan_crop()`` silently
    changing out-of-frame visibility 2→1 in ``adjusted_visibility`` before the rule runs.
    """
    out_of_frame = annotation.get("out_of_frame_indices")
    if not isinstance(out_of_frame, list) or not out_of_frame:
        return DeterministicVerdict.PASS, None

    # Prefer original_visibility (pre-adjustment) so the rule sees what the annotator
    # actually submitted.  Fall back to visibility for backward compatibility.
    visibility = annotation.get("original_visibility") or annotation.get("visibility")
    if not isinstance(visibility, list):
        raise UnevaluableRuleError("visibility_missing_or_malformed")

    violations = [
        idx for idx in out_of_frame
        if isinstance(idx, int) and idx < len(visibility) and visibility[idx] == 2
    ]

    if violations:
        return DeterministicVerdict.FAIL, f"out_of_frame_points_visible:{violations}"
    return DeterministicVerdict.PASS, None


RULE_REGISTRY: dict[str, RuleEvaluator] = {
    "bbox_format": evaluate_bbox_format,
    "bbox_non_empty": evaluate_bbox_non_empty,
    "required_attributes": evaluate_required_attributes,
    "roll_count_positive": evaluate_roll_count_positive,
    "clamp_type_allowed": evaluate_clamp_type_allowed,
    "keypoint_count": evaluate_keypoint_count,
    "visibility_codes": evaluate_visibility_codes,
    "out_of_frame_occluded": evaluate_out_of_frame_occluded,
}


def evaluate_rule(
    *,
    annotation: dict[str, Any],
    category: RuleCategory,
    rule: RuleSpec,
) -> tuple[RuleResult | None, str | None]:
    evaluator = RULE_REGISTRY.get(rule.name)
    if evaluator is None:
        return None, f"Unknown deterministic rule {rule.name} in {category.value}; skipped"

    try:
        verdict, reason = evaluator(annotation, rule)
        return (
            RuleResult(
                rule_name=rule.name,
                category=category,
                verdict=verdict,
                reason=reason,
                evaluable=True,
            ),
            None,
        )
    except UnevaluableRuleError as exc:
        return (
            RuleResult(
                rule_name=rule.name,
                category=category,
                verdict=DeterministicVerdict.FAIL,
                reason=f"unevaluable:{exc.reason}",
                evaluable=False,
            ),
            None,
        )
    except Exception:
        return (
            RuleResult(
                rule_name=rule.name,
                category=category,
                verdict=DeterministicVerdict.FAIL,
                reason=f"rule_runtime_error:{rule.name}",
                evaluable=False,
            ),
            None,
        )
