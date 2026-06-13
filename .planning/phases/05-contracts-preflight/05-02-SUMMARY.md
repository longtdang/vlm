---
phase: 05-contracts-preflight
plan: 02
subsystem: importer
tags: [fiftyone, datumaro, contracts, visibility]
requires: [05-01]
provides:
  - label_id-routed keypoint field writes (`keypoints_label_<id>`)
  - per-field skeleton assignment via `dataset.skeletons[field_name]`
  - strict visibility mismatch categories and mapping metadata emission
affects: [phase-05-plan-03, tests/phase2, tests/phase5]
tech-stack:
  added: []
  patterns: [label-id-routing, field-keyed-skeleton-contracts, strict-visibility-preflight]
key-files:
  created: []
  modified:
    - src/fiftyone_pose_importer/run_import.py
    - tests/phase5/test_contracts_preflight.py
    - tests/phase2/test_pose_mapping_import.py
key-decisions:
  - "Route annotations by label_id to keypoints_label_<id> when label_id is present; enforce label_id for multi-skeleton contracts."
  - "Assign `dataset.skeletons` per routed field and keep invalid/mismatched visibility as hard preflight failures."
  - "Emit `summary.mapping` with required SKEL metadata keys and explicit visibility policy."
requirements-completed: [SKEL-01, SKEL-02]
duration: 24min
completed: 2026-06-13
---

# Phase 5 Plan 02: Contracts & Preflight Summary

**Implemented deterministic per-label field routing and per-field skeleton assignment while preserving strict visibility preflight behavior.**

## Performance

- **Duration:** 24 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented `_target_field_for_label_id` and routed label-tagged annotations to `sample["keypoints_label_<id>"]`.
- Added `_ensure_dataset_skeleton_field` and populated `dataset.skeletons[field_name]` for routed fields.
- Preserved/strengthened visibility preflight categorization for invalid values and length mismatches.
- Added `summary.mapping` metadata entries with required keys (`label_id`, `source_label_name`, `target_field`, `skeleton_labels`, `skeleton_edges`, `visibility_policy`).
- Updated regression assertions in phase2 to validate multi-skeleton per-field routing behavior.

## Task Commits

1. **Task 1: Implement label_id-based keypoint field routing** — `ce20201` (feat)
2. **Task 2: Attach per-field skeleton contracts and keep visibility policy strict** — `6bd499f` (feat)

## Verification

- `pytest -q tests/phase5/test_contracts_preflight.py::test_per_label_id_field_mapping tests/phase5/test_contracts_preflight.py::test_no_single_field_collapse -x`
- `pytest -q tests/phase5/test_contracts_preflight.py::test_visibility_invalid_values_fail_preflight tests/phase5/test_contracts_preflight.py::test_missing_visibility_defaults_to_two -x`
- `pytest -q tests/phase5/test_contracts_preflight.py -x`
- `pytest -q tests/phase2/test_pose_mapping_import.py -x`

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 1 - Bug] Fixed malformed assertion in phase5 mapping contract test**
   - **Issue:** `entry[label_id]` used an undefined name and invalid f-string quoting.
   - **Fix:** Corrected assertion to `entry['label_id']`.
   - **Files:** `tests/phase5/test_contracts_preflight.py`
   - **Commit:** `6bd499f`

2. **[Rule 2 - Missing critical functionality] Added mapping metadata emission in importer summary**
   - **Issue:** Required `mapping` section (D-07/D-08) was absent, preventing contract verification.
   - **Fix:** Added `_summary_mapping()` and emitted `summary['mapping']` with required keys.
   - **Files:** `src/fiftyone_pose_importer/run_import.py`
   - **Commit:** `6bd499f`

3. **[Rule 1 - Regression alignment] Updated phase2 multi-skeleton regression expectations**
   - **Issue:** Regression test still expected collapsed `ground_truth` field for multi-skeleton imports.
   - **Fix:** Asserted routed per-label fields (`keypoints_label_10`, `keypoints_label_11`) and per-field visibility.
   - **Files:** `tests/phase2/test_pose_mapping_import.py`
   - **Commit:** `6bd499f`

## Auth Gates

None.

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: .planning/phases/05-contracts-preflight/05-02-SUMMARY.md
- FOUND: ce20201
- FOUND: 6bd499f
