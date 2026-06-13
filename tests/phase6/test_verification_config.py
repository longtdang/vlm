from __future__ import annotations

import pytest

from fiftyone_pose_importer.verification.config import (
    VerificationConfigError,
    load_verification_config,
)


def test_defaults_and_label_override_merge() -> None:
    cfg, warnings = load_verification_config(
        {
            "padding_px": 24,
            "rules": {
                "global": {
                    "detection": ["bbox_format"],
                    "attribute": ["required_attributes"],
                    "skeleton-count": ["keypoint_count"],
                    "visibility-format": ["visibility_codes"],
                },
                "overrides": {
                    "forklift-with-roll": {
                        "attribute": ["required_attributes", "roll_count_positive"]
                    }
                },
            },
        }
    )

    assert cfg.padding_px == 24
    assert warnings == []

    inherited = cfg.rules_for_label("forklift-no-roll")
    assert [r.name for r in inherited.detection.rules] == ["bbox_format"]

    overridden = cfg.rules_for_label("forklift-with-roll")
    assert [r.name for r in overridden.attribute.rules] == ["required_attributes", "roll_count_positive"]
    assert [r.name for r in overridden.visibility_format.rules] == ["visibility_codes"]


def test_unknown_rule_is_warning_not_error() -> None:
    cfg, warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_format", "not_a_rule"],
                }
            }
        }
    )

    assert any("not_a_rule" in warning for warning in warnings)
    assert [r.name for r in cfg.global_rules.detection.rules] == ["bbox_format"]


def test_invalid_padding_fails_fast() -> None:
    with pytest.raises(VerificationConfigError):
        load_verification_config({"padding_px": -1})


def test_required_categories_exist_by_default() -> None:
    cfg, warnings = load_verification_config({})

    assert warnings == []
    assert cfg.global_rules.detection.rules
    assert cfg.global_rules.attribute.rules
    assert cfg.global_rules.skeleton_count.rules
    assert cfg.global_rules.visibility_format.rules
