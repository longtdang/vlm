from __future__ import annotations

import pytest

from fiftyone_pose_importer.verification.types import (
    DeterministicRuleConfig,
    DeterministicVerdict,
    ObjectVerificationResult,
    RuleCategory,
    RuleCategoryConfig,
    RuleResult,
    RuleSpec,
)


def test_deterministic_verdict_is_pass_fail_only() -> None:
    assert {v.value for v in DeterministicVerdict} == {"PASS", "FAIL"}
    with pytest.raises(ValueError):
        DeterministicVerdict("REVIEW")


def test_object_result_requires_crop_path_and_failure_reasons() -> None:
    rule = RuleResult(
        rule_name="bbox_format",
        category=RuleCategory.DETECTION,
        verdict=DeterministicVerdict.PASS,
        reason=None,
        evaluable=True,
    )

    result = ObjectVerificationResult(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        verdict=DeterministicVerdict.PASS,
        crop_path="runs/001/crops/sample-1_obj-1.png",
        rule_results=[rule],
        failure_reasons=[],
    )

    assert result.crop_path.endswith(".png")
    assert result.failure_reasons == []

    with pytest.raises(TypeError):
        ObjectVerificationResult(  # type: ignore[call-arg]
            sample_id="sample-1",
            object_id="obj-1",
            label="forklift-with-roll",
            verdict=DeterministicVerdict.FAIL,
            rule_results=[rule],
        )


def test_rule_config_requires_four_deterministic_categories() -> None:
    rule_cfg = DeterministicRuleConfig(
        detection=RuleCategoryConfig(rules=[RuleSpec(name="bbox_format")]),
        attribute=RuleCategoryConfig(rules=[RuleSpec(name="clamp_type")]),
        skeleton_count=RuleCategoryConfig(rules=[RuleSpec(name="count_exact")]),
        visibility_format=RuleCategoryConfig(rules=[RuleSpec(name="visibility_codes")]),
    )

    assert [spec.name for spec in rule_cfg.detection.rules] == ["bbox_format"]

    with pytest.raises(TypeError):
        DeterministicRuleConfig(  # type: ignore[call-arg]
            detection=RuleCategoryConfig(rules=[]),
            attribute=RuleCategoryConfig(rules=[]),
            skeleton_count=RuleCategoryConfig(rules=[]),
        )
