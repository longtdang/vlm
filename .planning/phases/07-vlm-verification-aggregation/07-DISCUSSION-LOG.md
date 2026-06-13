# Phase 7 Discussion Log

**Phase:** 7 - VLM Verification & Aggregation
**Date:** 2026-06-13
**Status:** Complete — all gray areas resolved

---

## Gray Areas Discussed

### Area 1: VLM Adapter Strategy
- **Question:** What adapter mode for VLM calls?
- **Decision:** FiftyOne model-zoo only (no external HTTP endpoint). One configured model name at a time. Failure → REVIEW with reason.
- **Locked as:** D-01 through D-04

### Area 2: VLM Label Scope
- **Question:** Which labels are VLM-verified vs deterministic-only?
- **Decision:** Config-driven opt-in per label. Per VLM-enabled label, explicit per-rule list chosen from the 6 VLM rules.
- **Locked as:** D-05, D-06, D-07

### Area 3: VLM Execution Gate
- **Question:** What happens to deterministic-FAIL objects in VLM stage?
- **Decision:** Deterministic FAILs skip VLM entirely; final status remains FAIL.
- **Locked as:** D-08, D-09

### Area 4: Prompt and Response Contract
- **Question:** Prompt granularity, context, and expected format?
- **Decision:** Per-label per-rule templates with global default fallback. Context = crop image + label + rule name + relevant annotation fields. Response = strict JSON `{error_probability, reason, evidence?}`. Invalid response → `invalid_output` → REVIEW.
- **Locked as:** D-10 through D-14

### Area 5: Risk Aggregation and Thresholds
- **Question:** How to compute object risk and assign status?
- **Decision:** `object_risk = max(error_probability)`. Thresholds: PASS ≤ 0.20, REVIEW ≤ 0.60, FAIL > 0.60 — configurable globally with per-label overrides.
- **Locked as:** D-15 through D-18

### Area 6: Phase 7 Artifacts and Review Queue
- **Question:** Separate or merged VLM reports? Review queue ordering?
- **Decision:** Separate VLM artifacts (`vlm_report.csv/json/ndjson`) in same run directory. Review queue embedded in JSON: risk desc → adapter_failure first → sample_id/object_id.
- **Locked as:** D-19 through D-21

### Area 7: CI/Testing Strategy
- **Question:** How to test without real GPU/model?
- **Decision:** Mock FiftyOne model class (duck-type same interface) returning deterministic JSON — injected via test fixture.
- **Locked as:** D-22

---

## Deferred / Out of Scope

- External OpenAI-compatible HTTP adapter — removed from Phase 7 per user decision
- Interactive review dashboard (VLM-06) — deferred to future milestone
- Auto-apply VLM correction suggestions (VLM-07) — deferred to future milestone
