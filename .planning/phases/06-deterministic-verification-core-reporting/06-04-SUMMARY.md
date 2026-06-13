---
phase: 06-deterministic-verification-core-reporting
plan: 04
subsystem: verification
tags: [deterministic-verification, cli, run-verify, reporting, pytest]
requires:
  - phase: 06-deterministic-verification-core-reporting
    provides: deterministic crop/rule engine and reporting writers from 06-02/06-03
provides:
  - Deterministic verification orchestrator runnable without VLM services
  - CLI verify command with run-complete exit semantics (0 with object fails)
  - Integration tests for deterministic-only run flow and fatal-startup failure paths
affects: [phase-06, phase-07, cli, verification-pipeline]
tech-stack:
  added: []
  patterns: [TDD red-green commits, per-object failure isolation, deterministic-to-vlm eligibility gating]
key-files:
  created:
    - src/fiftyone_pose_importer/run_verify.py
    - tests/phase6/test_run_verify.py
  modified:
    - src/fiftyone_pose_importer/cli.py
    - pyproject.toml
key-decisions:
  - "Use deterministic verification as a standalone pipeline that emits full artifacts even when objects fail"
  - "Return CLI exit 0 for completed deterministic runs; reserve non-zero for fatal config/runtime startup errors"
  - "Expose per-object vlm_eligible based strictly on deterministic PASS"
requirements-completed: [VER-04]
duration: 14min
completed: 2026-06-13
---

# Phase 6 Plan 4: Deterministic Runner + CLI Exit Semantics Summary

**Deterministic verification is now executable end-to-end without VLM, emits CSV/JSON/NDJSON artifacts, and enforces CLI semantics where object-level deterministic failures stay in reports while completed runs exit 0.**

## Performance

- **Duration:** 14 min
- **Tasks:** 2 (TDD RED/GREEN per task)
- **Files modified:** 4

## Accomplishments
- Implemented `run_verify.py` orchestrator to load YAML config + Datumaro data, evaluate crop/rules per object, continue on per-object runtime failures, and emit timestamped deterministic artifacts.
- Added deterministic `vlm_eligible` projection in run summary: true only when deterministic verdict is PASS.
- Wired CLI `verify` command path with exit code 0 for completed runs (even with deterministic FAIL rows) and non-zero for fatal startup/config errors.
- Added console script `fiftyone-datumaro-verify` and integration tests covering deterministic-only run path plus fatal startup behavior.

## Task Commits
1. **Task 1 RED:** `d7b4182` — failing deterministic-only run pipeline integration test.
2. **Task 1 GREEN:** `65c0ae9` — deterministic run orchestrator implementation.
3. **Task 2 RED:** `93a9dfa` — failing CLI verify exit-code contract tests.
4. **Task 2 GREEN:** `0df252f` — CLI verify wiring + entrypoint + exit semantics.

## Files Created/Modified
- `src/fiftyone_pose_importer/run_verify.py` — deterministic orchestration, per-object isolation, report emission.
- `src/fiftyone_pose_importer/cli.py` — verify subcommand + legacy import compatibility + exit contract handling.
- `pyproject.toml` — `fiftyone-datumaro-verify` entrypoint.
- `tests/phase6/test_run_verify.py` — deterministic-only + CLI contract integration tests.

## Verification Executed
- `pytest -q tests/phase6/test_run_verify.py::test_deterministic_only_pipeline_without_vlm -x`
- `pytest -q tests/phase6/test_run_verify.py::test_cli_exit_code_zero_with_object_failures -x`
- `pytest -q tests/phase6/test_run_verify.py -x`
- `pytest -q tests/phase6 -x`
- `pytest -q -x`

## Deviations from Plan
None - plan executed as written.

## Issues Encountered
- `gsd-tools` query commands returned empty/unavailable in this environment; planning state updates were applied directly to markdown state files.

## Known Stubs
None.

## Self-Check: PASSED
- FOUND: src/fiftyone_pose_importer/run_verify.py
- FOUND: src/fiftyone_pose_importer/cli.py
- FOUND: tests/phase6/test_run_verify.py
- FOUND: .planning/phases/06-deterministic-verification-core-reporting/06-04-SUMMARY.md
- FOUND COMMIT: d7b4182
- FOUND COMMIT: 65c0ae9
- FOUND COMMIT: 93a9dfa
- FOUND COMMIT: 0df252f
