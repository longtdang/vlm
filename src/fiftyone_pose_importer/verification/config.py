from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import DeterministicRuleConfig, RuleCategoryConfig, RuleSpec


class VerificationConfigError(ValueError):
    pass


DEFAULT_PADDING_PX = 16
KNOWN_RULES: dict[str, set[str]] = {
    "detection": {"bbox_format", "bbox_non_empty"},
    "attribute": {"required_attributes", "roll_count_positive", "clamp_type_allowed"},
    "skeleton-count": {"keypoint_count"},
    "visibility-format": {"visibility_codes"},
}
DEFAULT_RULES: dict[str, list[str]] = {
    "detection": ["bbox_format"],
    "attribute": ["required_attributes"],
    "skeleton-count": ["keypoint_count"],
    "visibility-format": ["visibility_codes"],
}


@dataclass(frozen=True)
class VerificationConfig:
    padding_px: int
    global_rules: DeterministicRuleConfig
    label_overrides: dict[str, DeterministicRuleConfig]

    def rules_for_label(self, label: str) -> DeterministicRuleConfig:
        return self.label_overrides.get(label, self.global_rules)


def _as_rule_specs(category: str, raw_rules: Any, warnings: list[str], scope: str) -> list[RuleSpec]:
    if raw_rules is None:
        raw_rules = []
    if not isinstance(raw_rules, list):
        raise VerificationConfigError(f"{scope}.{category} must be a list")

    specs: list[RuleSpec] = []
    for entry in raw_rules:
        if isinstance(entry, str):
            name = entry
            enabled = True
            params = None
        elif isinstance(entry, dict):
            name = entry.get("name")
            enabled = bool(entry.get("enabled", True))
            params_raw = entry.get("params")
            if params_raw is not None and not isinstance(params_raw, dict):
                raise VerificationConfigError(f"{scope}.{category}.{name}.params must be a mapping")
            params = params_raw
        else:
            raise VerificationConfigError(f"{scope}.{category} contains invalid rule entry type: {type(entry).__name__}")

        if not isinstance(name, str) or not name:
            raise VerificationConfigError(f"{scope}.{category} rule names must be non-empty strings")
        if name not in KNOWN_RULES[category]:
            warnings.append(f"Unknown deterministic rule {name} in {scope}.{category}; ignored")
            continue
        specs.append(RuleSpec(name=name, enabled=enabled, params=params))

    return specs


def _category_key(raw: dict[str, Any], key: str) -> Any:
    if key in raw:
        return raw[key]
    alt = key.replace("-", "_")
    return raw.get(alt)


def _parse_rule_block(raw_block: dict[str, Any] | None, warnings: list[str], scope: str, fallback: DeterministicRuleConfig | None = None) -> DeterministicRuleConfig:
    block = raw_block or {}
    if not isinstance(block, dict):
        raise VerificationConfigError(f"{scope} must be a mapping")

    categories: dict[str, RuleCategoryConfig] = {}
    for category in ("detection", "attribute", "skeleton-count", "visibility-format"):
        raw_value = _category_key(block, category)
        if raw_value is None:
            if fallback is not None:
                categories[category] = getattr(fallback, category.replace("-", "_"))
                continue
            raw_value = list(DEFAULT_RULES[category])

        specs = _as_rule_specs(category, raw_value, warnings, scope)
        if not specs:
            if fallback is not None:
                inherited = getattr(fallback, category.replace("-", "_"))
                categories[category] = inherited
            else:
                default_specs = [RuleSpec(name=name) for name in DEFAULT_RULES[category]]
                categories[category] = RuleCategoryConfig(rules=default_specs)
        else:
            categories[category] = RuleCategoryConfig(rules=specs)

    return DeterministicRuleConfig(
        detection=categories["detection"],
        attribute=categories["attribute"],
        skeleton_count=categories["skeleton-count"],
        visibility_format=categories["visibility-format"],
    )


def load_verification_config(raw_config: dict[str, Any] | None) -> tuple[VerificationConfig, list[str]]:
    raw = raw_config or {}
    if not isinstance(raw, dict):
        raise VerificationConfigError("Verification config must be a mapping")

    padding_px = raw.get("padding_px", DEFAULT_PADDING_PX)
    if not isinstance(padding_px, int):
        raise VerificationConfigError("padding_px must be an integer")
    if padding_px < 0:
        raise VerificationConfigError("padding_px must be >= 0")

    warnings: list[str] = []
    rules_root = raw.get("rules") or {}
    if not isinstance(rules_root, dict):
        raise VerificationConfigError("rules must be a mapping")

    global_rules = _parse_rule_block(rules_root.get("global"), warnings, "rules.global")

    overrides_raw = rules_root.get("overrides") or {}
    if not isinstance(overrides_raw, dict):
        raise VerificationConfigError("rules.overrides must be a mapping")

    label_overrides: dict[str, DeterministicRuleConfig] = {}
    for label, rule_block in overrides_raw.items():
        if not isinstance(label, str) or not label:
            raise VerificationConfigError("rules.overrides keys must be non-empty label strings")
        label_overrides[label] = _parse_rule_block(rule_block, warnings, f"rules.overrides.{label}", fallback=global_rules)

    return VerificationConfig(padding_px=padding_px, global_rules=global_rules, label_overrides=label_overrides), warnings
