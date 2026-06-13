from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import VerificationConfig
from .rules import evaluate_rule
from .types import DeterministicVerdict, ObjectVerificationResult, RuleCategory, RuleSpec


@dataclass(frozen=True)
class EngineOutcome:
    result: ObjectVerificationResult
    warnings: list[str]


def _category_rules(config: VerificationConfig, label: str) -> list[tuple[RuleCategory, list[RuleSpec]]]:
    merged = config.rules_for_label(label)
    return [
        (RuleCategory.DETECTION, merged.detection.rules),
        (RuleCategory.ATTRIBUTE, merged.attribute.rules),
        (RuleCategory.SKELETON_COUNT, merged.skeleton_count.rules),
        (RuleCategory.VISIBILITY_FORMAT, merged.visibility_format.rules),
    ]


def evaluate_object(
    *,
    sample_id: str,
    object_id: str,
    label: str,
    crop_path: str,
    annotation: dict[str, Any],
    config: VerificationConfig,
) -> EngineOutcome:
    warnings: list[str] = []
    rule_results = []

    for category, rules in _category_rules(config, label):
        for rule in rules:
            if not rule.enabled:
                continue
            result, warning = evaluate_rule(annotation=annotation, category=category, rule=rule)
            if warning:
                warnings.append(warning)
                continue
            if result is not None:
                rule_results.append(result)

    failure_reasons = [
        r.reason
        for r in rule_results
        if r.verdict is DeterministicVerdict.FAIL and r.reason is not None
    ]
    verdict = DeterministicVerdict.FAIL if failure_reasons else DeterministicVerdict.PASS

    return EngineOutcome(
        result=ObjectVerificationResult(
            sample_id=sample_id,
            object_id=object_id,
            label=label,
            verdict=verdict,
            crop_path=crop_path,
            rule_results=rule_results,
            failure_reasons=failure_reasons,
        ),
        warnings=warnings,
    )
