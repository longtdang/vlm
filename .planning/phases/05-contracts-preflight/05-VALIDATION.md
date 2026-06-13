---
phase: 05
slug: contracts-preflight
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-13
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest -q tests/phase5` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/phase5`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SKEL-01 | T-05-01 | Guard per-label field routing and skeleton assignment behavior | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_per_label_id_field_mapping -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | SKEL-02 | T-05-02 | Prevent multi-type collapse into one field and preserve ID identity | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_no_single_field_collapse -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | SKEL-03 | T-05-03 | Validate mapping metadata contract keys and identity linkage | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_mapping_metadata_emitted_with_required_keys -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | SKEL-01, SKEL-02 | T-05-03 | Enforce routed field writes + per-field skeleton metadata + visibility semantics | integration | `pytest -q tests/phase5/test_contracts_preflight.py::test_visibility_invalid_values_fail_preflight tests/phase5/test_contracts_preflight.py::test_missing_visibility_defaults_to_two -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | SKEL-03 | T-05-06 | Ensure additive summary schema with `mapping` section | integration | `pytest -q tests/phase5/test_contracts_preflight.py tests/phase4/test_run_summary_schema.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase5/test_contracts_preflight.py` — routing, visibility, and mapping contract coverage for SKEL-01..03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skeleton edges visibly render per field in FiftyOne app | SKEL-01, SKEL-02 | Rendering correctness depends on viewer behavior | Import fixture dataset, open FiftyOne app, toggle each `keypoints_label_<id>` field, confirm edges appear and match expected skeleton type |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
