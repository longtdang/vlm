from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VlmVerdict(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True)
class VlmRuleResult:
    rule_name: str
    error_probability: float | None
    reason: str
    evidence: str | None
    invalid_output: bool


@dataclass(frozen=True)
class VlmObjectResult:
    sample_id: str
    object_id: str
    label: str
    vlm_status: VlmVerdict
    object_risk: float | None
    rule_results: list[VlmRuleResult]
    adapter_model: str
    failure_reason: str | None
    crop_path: str
