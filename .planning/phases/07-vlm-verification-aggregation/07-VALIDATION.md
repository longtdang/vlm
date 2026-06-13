---
phase: 07
slug: vlm-verification-aggregation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `pytest tests/phase7/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/phase7/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| VLM-01 | `load_vlm_config` returns correct per-label enabled flags | unit | `pytest tests/phase7/test_vlm_config.py -x` | ❌ W0 |
| VLM-01 | Labels not in VLM scope produce no VlmObjectResult | unit | `pytest tests/phase7/test_vlm_engine.py::test_non_vlm_label_skipped -x` | ❌ W0 |
| VLM-02 | Per-label per-rule prompt templates override global default | unit | `pytest tests/phase7/test_vlm_engine.py::test_prompt_template_override -x` | ❌ W0 |
| VLM-02 | Annotation fields injected into prompt correctly | unit | `pytest tests/phase7/test_vlm_engine.py::test_prompt_annotation_fields -x` | ❌ W0 |
| VLM-03 | `object_risk = max(error_probabilities)` | unit | `pytest tests/phase7/test_vlm_engine.py::test_risk_aggregation_is_max -x` | ❌ W0 |
| VLM-03 | Deterministic FAIL objects skip VLM stage entirely | unit | `pytest tests/phase7/test_vlm_engine.py::test_deterministic_fail_skips_vlm -x` | ❌ W0 |
| VLM-03 | Integration with mock adapter emits VLM artifacts | integration | `pytest tests/phase7/test_run_verify_vlm.py -x` | ❌ W0 |
| VLM-04 | invalid_output response produces REVIEW with reason | unit | `pytest tests/phase7/test_vlm_engine.py::test_invalid_output_review -x` | ❌ W0 |
| VLM-04 | Adapter exception produces REVIEW with failure_reason | unit | `pytest tests/phase7/test_vlm_engine.py::test_adapter_failure_review -x` | ❌ W0 |
| VLM-04 | `error_probability=0` is valid, not invalid_output | unit | `pytest tests/phase7/test_vlm_engine.py::test_zero_probability_valid -x` | ❌ W0 |
| VLM-05 | model_name from config is passed to FiftyOneZooAdapter | unit | `pytest tests/phase7/test_vlm_client.py::test_model_name_forwarded -x` | ❌ W0 |
| D-19 | `vlm_report.csv`, `vlm_report.json`, `vlm_trace.ndjson` in same run_dir | unit | `pytest tests/phase7/test_report_vlm.py::test_vlm_artifacts_in_run_dir -x` | ❌ W0 |
| D-21 | review_queue sorted risk desc -> adapter_failure first -> IDs asc | unit | `pytest tests/phase7/test_report_vlm.py::test_review_queue_ordering -x` | ❌ W0 |

---

## Wave 0 Requirements

- [ ] `tests/phase7/__init__.py`
- [ ] `tests/phase7/test_vlm_config.py`
- [ ] `tests/phase7/test_vlm_engine.py`
- [ ] `tests/phase7/test_vlm_client.py`
- [ ] `tests/phase7/test_report_vlm.py`
- [ ] `tests/phase7/test_run_verify_vlm.py`

---

## Validation Sign-Off

- [ ] All Phase 7 tests exist and are green
- [ ] Sampling continuity maintained through waves
- [ ] Wave 0 gaps fully closed
- [ ] `nyquist_compliant: true` set in frontmatter when complete

**Approval:** pending
