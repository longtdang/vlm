from __future__ import annotations

import pytest

from fiftyone_pose_importer.verification.vlm_config import VlmConfig, VlmConfigError, load_vlm_config


def test_load_vlm_config_raises_on_missing_model_name() -> None:
    with pytest.raises(VlmConfigError):
        load_vlm_config({})


def test_load_vlm_config_defaults() -> None:
    config, warnings = load_vlm_config({"model_name": "qwen3-vl-2b-instruct-torch", "labels": {}})

    assert isinstance(config, VlmConfig)
    assert config.thresholds.pass_below == 0.20
    assert config.thresholds.review_below == 0.60
    assert config.generation.max_new_tokens == 256
    assert config.generation.timeout_seconds == 8.0
    assert warnings == []


def test_load_vlm_config_unknown_model_name_warns_not_raises() -> None:
    config, warnings = load_vlm_config({"model_name": "qwen3-vl-99b-instruct-torch", "labels": {}})

    assert config.model_name == "qwen3-vl-99b-instruct-torch"
    assert warnings


def test_load_vlm_config_per_label_enabled_flag() -> None:
    config, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "labels": {
                "disabled": {"enabled": False},
                "enabled": {"enabled": True},
            },
        }
    )

    assert config.is_label_enabled("disabled") is False
    assert config.is_label_enabled("enabled") is True
    assert config.is_label_enabled("unknown") is False


def test_load_vlm_config_per_label_rules() -> None:
    config, warnings = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "labels": {
                "forklift": {
                    "rules": ["bbox_localization", "clamp_type", "unknown_rule"],
                }
            },
        }
    )

    assert config.rules_for_label("forklift") == ["bbox_localization", "clamp_type"]
    assert any("unknown_rule" in w for w in warnings)


def test_load_vlm_config_per_label_threshold_override() -> None:
    config, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "thresholds": {"pass_below": 0.20, "review_below": 0.60},
            "labels": {
                "forklift": {
                    "thresholds": {"pass_below": 0.30, "review_below": 0.70},
                }
            },
        }
    )

    assert config.thresholds_for_label("forklift").pass_below == 0.30
    assert config.thresholds_for_label("other-label").pass_below == 0.20


def test_load_vlm_config_per_label_prompt_override() -> None:
    config, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "labels": {
                "forklift": {
                    "prompts": {
                        "bbox_coverage": "custom template",
                    }
                }
            },
        }
    )

    assert config.prompt_for_label_rule("forklift", "bbox_coverage") == "custom template"
    assert config.prompt_for_label_rule("forklift", "roll_count") is None
    assert config.prompt_for_label_rule("unknown-label", "roll_count") is None


def test_load_vlm_config_default_prompt_template_override() -> None:
    config, _ = load_vlm_config(
        {
            "model_name": "qwen3-vl-2b-instruct-torch",
            "default_prompt_template": "my template {label} {rule} {annotation_fields_json}",
            "labels": {},
        }
    )

    assert config.default_prompt_template == "my template {label} {rule} {annotation_fields_json}"


def test_load_vlm_config_invalid_thresholds_raises() -> None:
    with pytest.raises(VlmConfigError):
        load_vlm_config(
            {
                "model_name": "qwen3-vl-2b-instruct-torch",
                "thresholds": {"pass_below": 0.70, "review_below": 0.30},
                "labels": {},
            }
        )
