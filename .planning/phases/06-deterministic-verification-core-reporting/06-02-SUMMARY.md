---
phase: 06-deterministic-verification-core-reporting
plan: 02
subsystem: verification
tags: [deterministic-verification, cropper, rules-engine, pytest]
requires:
  - phase: 06-deterministic-verification-core-reporting
    provides: Verification contracts and config parser from 06-01
provides:
  - Deterministic crop planning with fixed-padding policies for skeleton and non-skeleton labels
  - Deterministic rule registry and object-level aggregation with PASS/FAIL-only semantics
  - Unit coverage for invalid bbox, unevaluable rules, and per-label rule override behavior
affects: [phase-06, phase-07, run-verify]
tech-stack:
  added: []
  patterns: [TDD red-green commits, explicit unevaluable fail reasons, rule-registry dispatch]
key-files:
  created:
    - src/fiftyone_pose_importer/verification/cropper.py
    - src/fiftyone_pose_importer/verification/rules.py
    - src/fiftyone_pose_importer/verification/engine.py
    - tests/phase6/test_cropper.py
    - tests/phase6/test_rules_engine.py
  modified:
    - src/fiftyone_pose_importer/verification/__init__.py
key-decisions:
  - "Skeleton crops preserve padded canvas while non-skeleton crops clip to image bounds"
  - "Unevaluable/runtime deterministic rules are converted into explicit FAIL reasons"
patterns-established:
  - "Rule evaluation flows through RULE_REGISTRY and category-aware dispatch in engine"
requirements-completed: [VER-01, VER-02]
duration: 2min
completed: 2026-06-13
---

# Phase 6 Plan 2: Deterministic Cropper and Rules Engine Summary

**Fixed-padding deterministic crop planning and PASS/FAIL-only rule aggregation now produce auditable object-level failures before reporting.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-13T06:38:24Z
- **Completed:** 2026-06-13T06:40:41Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added deterministic crop planning with locked skeleton/non-skeleton edge policies and invalid bbox failures.
- Implemented deterministic rule evaluators for detection, attribute, skeleton-count, and visibility-format categories.
- Added engine aggregation that enforces PASS/FAIL-only outcomes and explicit unevaluable/runtime failure reasons.

## Task Commits
1. **Task 1: Build deterministic cropper with locked edge policies (RED)** - `b3736bc` (test)
2. **Task 1: Build deterministic cropper with locked edge policies (GREEN)** - `0e507f7` (feat)
3. **Task 2: Build deterministic rules registry and aggregation engine (RED)** - `e9e5384` (test)
4. **Task 2: Build deterministic rules registry and aggregation engine (GREEN)** - `cf9742f` (feat)

## Files Created/Modified
- `src/fiftyone_pose_importer/verification/cropper.py` - deterministic crop planning and occlusion metadata adjustment.
- `src/fiftyone_pose_importer/verification/rules.py` - deterministic rule evaluators and registry dispatch.
- `src/fiftyone_pose_importer/verification/engine.py` - object-level deterministic evaluation and strict aggregation.
- `src/fiftyone_pose_importer/verification/__init__.py` - exports for cropper and engine APIs.
- `tests/phase6/test_cropper.py` - cropper policy and invalid bbox coverage.
- `tests/phase6/test_rules_engine.py` - aggregation, unevaluable path, unknown-rule warning, override coverage.

## Decisions Made
- Treated out-of-frame skeleton points as occluded (`v=1`) while keeping keypoints valid in metadata.
- Converted all unevaluable/runtime rule issues to deterministic FAIL entries to satisfy threat mitigation D-03.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- `gsd-tools` CLI is unavailable in this environment, so STATE/ROADMAP/REQUIREMENTS updates were applied directly in planning markdown files.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Reporting plan (06-03) can now consume stable `ObjectVerificationResult` payloads with deterministic fail reasons and crop metadata.

## Self-Check: PASSED
- FOUND: src/fiftyone_pose_importer/verification/cropper.py
- FOUND: src/fiftyone_pose_importer/verification/rules.py
- FOUND: src/fiftyone_pose_importer/verification/engine.py
- FOUND: tests/phase6/test_cropper.py
- FOUND: tests/phase6/test_rules_engine.py
- FOUND COMMIT: b3736bc
- FOUND COMMIT: 0e507f7
- FOUND COMMIT: e9e5384
- FOUND COMMIT: cf9742f
