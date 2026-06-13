from __future__ import annotations

from fiftyone_pose_importer.verification.config import load_verification_config
from fiftyone_pose_importer.verification.engine import evaluate_object
from fiftyone_pose_importer.verification.types import DeterministicVerdict


def _valid_annotation() -> dict[str, object]:
    return {
        "bbox": [10.0, 20.0, 40.0, 50.0],
        "attributes": {"clamp_type": "2-arm", "roll_count": 2},
        "keypoints": [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]],
        "visibility": [2, 1, 2, 2],
    }


def test_any_failed_rule_forces_object_fail() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [
                        {"name": "required_attributes", "params": {"required": ["clamp_type"]}},
                        {"name": "roll_count_positive"},
                    ],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    bad = _valid_annotation()
    bad["attributes"] = {"clamp_type": "2-arm", "roll_count": 0}

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=bad,
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert "roll_count_non_positive" in outcome.result.failure_reasons
    assert {r.verdict.value for r in outcome.result.rule_results} <= {"PASS", "FAIL"}


def test_unevaluable_rule_is_converted_to_explicit_fail_reason() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    bad = _valid_annotation()
    bad["bbox"] = "not-a-bbox"

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=bad,
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert any(reason.startswith("unevaluable:") for reason in outcome.result.failure_reasons)


def test_unknown_rule_names_are_warning_only_and_skipped() -> None:
    config, warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty", "made_up_rule"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=_valid_annotation(),
        config=config,
    )

    assert any("made_up_rule" in warning for warning in warnings)
    assert all(result.rule_name != "made_up_rule" for result in outcome.result.rule_results)
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_per_label_override_rules_are_applied() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                },
                "overrides": {
                    "forklift-no-roll": {
                        "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type", "serial"]}}]
                    }
                },
            }
        }
    )

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-no-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=_valid_annotation(),
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert "missing_required_attribute:serial" in outcome.result.failure_reasons
