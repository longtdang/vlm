---
phase: 03
slug: visibility-fidelity
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-12
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/conftest.py |
| **Quick run command** | `pytest -q tests/phase2/test_pose_mapping_import.py -k "visibility_fidelity_mapping" -x` |
| **Full suite command** | `pytest -q tests/phase2 -x` |
| **Estimated runtime** | < 1 second |

---

## Sampling Rate

- **After visibility logic changes:** Run targeted visibility tests in `tests/phase2/test_pose_mapping_import.py`
- **After each plan wave:** Run `pytest -q tests/phase2 -x`
- **Before `/gsd-verify-work`:** Full phase suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | VIS-01, VIS-02 | T-03-01, T-03-02 | Enforce 0/1/2 semantics; absent remains non-rendered | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "visibility_fidelity_mapping" -x` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | VIS-03 | T-03-03 | Preserve source visibility and default-applied metadata | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "visibility_metadata_preserved" -x` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | VIS-02, VIS-03 | T-03-04, T-03-05 | Visibility summary counters reflect mapped outputs | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "visibility_summary_counts_and_defaults" -x` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | VIS-02 | T-03-06 | Invalid payloads fail fast before write path | integration | `pytest -q tests/phase2/test_pose_mapping_import.py -k "preflight_failfast_and_deterministic_pose_order" -x` | ✅ | ✅ green |
| 03-03-01 | 03 | 3 | n/a (gap_closure) | n/a | Canonical operator command guidance available | static | `rg -n "fiftyone-datumaro-import|PYTHONPATH=src python -m fiftyone_pose_importer.cli|ModuleNotFoundError" README.md` | ✅ | ✅ green |
| 03-03-02 | 03 | 3 | n/a (gap_closure) | n/a | Ambiguous skeleton troubleshooting documented | static | `rg -n "ambiguous_skeleton|local.verify.yaml" README.md config.example.yaml` | ✅ | ✅ green |

---

## Wave 0 Requirements

Existing test harness (`tests/conftest.py` + fake FiftyOne strategy in tests) is sufficient for this phase.

---

## Manual-Only Verifications

- UAT test for hidden-vs-visible visualization remains **blocked by dataset precondition** when source data reports `ambiguous_skeleton`; this is documented and routed through troubleshooting guidance in README.

---

## Validation Sign-Off

- [x] All implementation tasks have automated verification commands
- [x] Gap-closure tasks have deterministic static verification
- [x] Sampling continuity preserved across waves
- [x] No watch-mode flags used
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-12
