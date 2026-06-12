---
phase: 02
slug: pose-contract-mapping
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-12
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/conftest.py |
| **Quick run command** | `pytest -q tests/phase2/test_pose_contract_preflight.py -x` |
| **Full suite command** | `pytest -q tests/phase2 -x` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/phase2/test_pose_contract_preflight.py -x`
- **After every plan wave:** Run `pytest -q tests/phase2 -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | POSE-02 | T-02-01 | Reject missing/ambiguous/invalid skeleton contract before write | unit | `pytest -q tests/phase2/test_pose_contract_preflight.py -k "extract_canonical_skeleton_contract" -x` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | OUT-03 | T-02-02, T-02-03 | Aggregate schema mismatches and fail preflight deterministically | unit | `pytest -q tests/phase2/test_pose_contract_preflight.py -k "preflight_schema_mismatch_aggregation" -x` | ✅ | ✅ green |
| 02-02-01 | 02 | 2 | POSE-01, POSE-03 | T-02-04, T-02-05 | Canonical mapping with deterministic order and validated visibility semantics | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "canonical_mapping_contract" -x` | ✅ | ✅ green |
| 02-02-02 | 02 | 2 | OUT-03 | T-02-03, T-02-06 | Fail-fast schema gate prevents invalid imports from writing samples | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "preflight_failfast_and_deterministic_pose_order" -x` | ✅ | ✅ green |
| 02-02-03 | 02 | 2 | POSE-02 | T-02-04 | Canonical skeleton labels/edges applied to dataset metadata | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "skeleton_labels_edges_applied" -x` | ✅ | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-12
