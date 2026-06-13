from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeterministicVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class RuleCategory(str, Enum):
    DETECTION = "detection"
    ATTRIBUTE = "attribute"
    SKELETON_COUNT = "skeleton-count"
    VISIBILITY_FORMAT = "visibility-format"


@dataclass(frozen=True)
class RuleSpec:
    name: str
    enabled: bool = True
    params: dict[str, object] | None = None


@dataclass(frozen=True)
class RuleCategoryConfig:
    rules: list[RuleSpec]


@dataclass(frozen=True)
class DeterministicRuleConfig:
    detection: RuleCategoryConfig
    attribute: RuleCategoryConfig
    skeleton_count: RuleCategoryConfig
    visibility_format: RuleCategoryConfig


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    category: RuleCategory
    verdict: DeterministicVerdict
    reason: str | None
    evaluable: bool


@dataclass(frozen=True)
class ObjectVerificationResult:
    sample_id: str
    object_id: str
    label: str
    verdict: DeterministicVerdict
    crop_path: str
    rule_results: list[RuleResult]
    failure_reasons: list[str]
