from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .vlm_types import VlmVerdict


class VlmConfigError(ValueError):
    pass


VALID_ZOO_MODEL_NAMES: frozenset[str] = frozenset(
    {
        "qwen3-vl-2b-instruct-torch",
        "qwen3-vl-4b-instruct-torch",
        "qwen3-vl-8b-instruct-torch",
    }
)
VALID_VLM_RULES: frozenset[str] = frozenset(
    {
        "bbox_localization",
        "bbox_coverage",
        "clamp_type",
        "roll_count",
        "keypoint_position",
        "occlusion_state",
    }
)
DEFAULT_PROMPT_TEMPLATE = """You are verifying annotation quality for label '{label}' and rule '{rule}'.
Use only the provided annotation fields JSON:
{annotation_fields_json}
Return ONLY strict JSON, with no markdown and no prose:
{"error_probability": <float between 0 and 1>, "reason": "<brief reason>"}
"""


@dataclass(frozen=True)
class VlmThresholds:
    pass_below: float = 0.20
    review_below: float = 0.60


@dataclass(frozen=True)
class VlmGeneration:
    max_new_tokens: int = 256
    timeout_seconds: float = 8.0
    batch_size: int = 1


@dataclass(frozen=True)
class VlmLabelConfig:
    enabled: bool
    rules: list[str]
    thresholds: VlmThresholds | None
    prompts: dict[str, str]


@dataclass(frozen=True)
class VlmConfig:
    model_name: str
    thresholds: VlmThresholds
    generation: VlmGeneration
    default_prompt_template: str
    labels: dict[str, VlmLabelConfig]

    def is_label_enabled(self, label: str) -> bool:
        cfg = self.labels.get(label)
        return bool(cfg.enabled) if cfg is not None else False

    def rules_for_label(self, label: str) -> list[str]:
        cfg = self.labels.get(label)
        if cfg is None or not cfg.enabled:
            return []
        return list(cfg.rules)

    def thresholds_for_label(self, label: str) -> VlmThresholds:
        cfg = self.labels.get(label)
        if cfg is None or cfg.thresholds is None:
            return self.thresholds
        return cfg.thresholds

    def prompt_for_label_rule(self, label: str, rule: str) -> str | None:
        cfg = self.labels.get(label)
        if cfg is None:
            return None
        return cfg.prompts.get(rule)


def _parse_thresholds(raw: dict[str, Any] | None, scope: str) -> VlmThresholds:
    block = raw or {}
    if not isinstance(block, dict):
        raise VlmConfigError(f"{scope} must be a mapping")
    pass_below = block.get("pass_below", 0.20)
    review_below = block.get("review_below", 0.60)
    if not isinstance(pass_below, (int, float)) or not isinstance(review_below, (int, float)):
        raise VlmConfigError(f"{scope}.pass_below and {scope}.review_below must be numeric")
    pass_v = float(pass_below)
    review_v = float(review_below)
    if not (0.0 < pass_v < review_v <= 1.0):
        raise VlmConfigError(f"{scope} must satisfy 0.0 < pass_below < review_below <= 1.0")
    return VlmThresholds(pass_below=pass_v, review_below=review_v)


def _parse_generation(raw: dict[str, Any] | None) -> VlmGeneration:
    block = raw or {}
    if not isinstance(block, dict):
        raise VlmConfigError("generation must be a mapping")
    max_new_tokens = block.get("max_new_tokens", 256)
    timeout_seconds = block.get("timeout_seconds", 8.0)
    batch_size = block.get("batch_size", 1)
    if not isinstance(max_new_tokens, int) or max_new_tokens <= 0:
        raise VlmConfigError("generation.max_new_tokens must be a positive integer")
    if not isinstance(timeout_seconds, (int, float)) or float(timeout_seconds) <= 0:
        raise VlmConfigError("generation.timeout_seconds must be > 0")
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise VlmConfigError("generation.batch_size must be a positive integer")
    return VlmGeneration(max_new_tokens=max_new_tokens, timeout_seconds=float(timeout_seconds), batch_size=batch_size)


def load_vlm_config(raw: dict[str, Any] | None) -> tuple[VlmConfig, list[str]]:
    _ = VlmVerdict.PASS
    config = raw or {}
    if not isinstance(config, dict):
        raise VlmConfigError("VLM config must be a mapping")

    model_name = config.get("model_name")
    if not isinstance(model_name, str) or not model_name.strip():
        raise VlmConfigError("model_name is required and must be a non-empty string")

    warnings: list[str] = []
    if model_name not in VALID_ZOO_MODEL_NAMES:
        warnings.append(
            f"Unknown model_name '{model_name}' not in known zoo models; proceeding as configured"
        )

    thresholds = _parse_thresholds(config.get("thresholds"), "thresholds")
    generation = _parse_generation(config.get("generation"))

    default_prompt_template = config.get("default_prompt_template") or DEFAULT_PROMPT_TEMPLATE
    if not isinstance(default_prompt_template, str):
        raise VlmConfigError("default_prompt_template must be a string")

    labels_raw = config.get("labels") or {}
    if not isinstance(labels_raw, dict):
        raise VlmConfigError("labels must be a mapping")

    labels: dict[str, VlmLabelConfig] = {}
    for label, label_raw in labels_raw.items():
        if not isinstance(label, str) or not label:
            raise VlmConfigError("labels keys must be non-empty strings")
        if label_raw is None:
            label_block: dict[str, Any] = {}
        elif isinstance(label_raw, dict):
            label_block = label_raw
        else:
            raise VlmConfigError(f"labels.{label} must be a mapping")

        enabled = label_block.get("enabled", True)
        if not isinstance(enabled, bool):
            raise VlmConfigError(f"labels.{label}.enabled must be a boolean")

        rules_raw = label_block.get("rules", [])
        if not isinstance(rules_raw, list):
            raise VlmConfigError(f"labels.{label}.rules must be a list")
        rules: list[str] = []
        for rule in rules_raw:
            if not isinstance(rule, str) or not rule:
                raise VlmConfigError(f"labels.{label}.rules entries must be non-empty strings")
            if rule not in VALID_VLM_RULES:
                warnings.append(f"Unknown VLM rule '{rule}' in labels.{label}.rules; ignored")
                continue
            rules.append(rule)

        label_thresholds_raw = label_block.get("thresholds")
        label_thresholds = None
        if label_thresholds_raw is not None:
            label_thresholds = _parse_thresholds(label_thresholds_raw, f"labels.{label}.thresholds")

        prompts_raw = label_block.get("prompts") or {}
        if not isinstance(prompts_raw, dict):
            raise VlmConfigError(f"labels.{label}.prompts must be a mapping")
        prompts: dict[str, str] = {}
        for rule_key, template in prompts_raw.items():
            if not isinstance(rule_key, str) or not rule_key:
                raise VlmConfigError(f"labels.{label}.prompts keys must be non-empty strings")
            if not isinstance(template, str):
                raise VlmConfigError(f"labels.{label}.prompts.{rule_key} must be a string")
            if rule_key not in VALID_VLM_RULES:
                warnings.append(
                    f"Unknown VLM rule '{rule_key}' in labels.{label}.prompts; ignored"
                )
                continue
            prompts[rule_key] = template

        labels[label] = VlmLabelConfig(
            enabled=enabled,
            rules=rules,
            thresholds=label_thresholds,
            prompts=prompts,
        )

    return (
        VlmConfig(
            model_name=model_name,
            thresholds=thresholds,
            generation=generation,
            default_prompt_template=default_prompt_template,
            labels=labels,
        ),
        warnings,
    )
