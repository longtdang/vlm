# Phase 2 Research: Pose Contract Mapping

**Phase:** 2 - Pose Contract Mapping  
**Date:** 2026-06-12  
**Status:** complete  
**Confidence:** medium

## Summary

This phase should harden the existing importer from permissive pose parsing to a strict, deterministic pose contract that matches Phase 2 context decisions (D-01..D-12) and requirements `POSE-01`, `POSE-02`, `POSE-03`, `OUT-03`.

## Verified Findings

1. Current implementation does not enforce the strict Phase 2 skeleton contract.
   - `run_import.py::_build_skeleton_from_datumaro()` currently accepts multiple shapes and may silently choose a candidate or return `None`.
   - This conflicts with locked decisions requiring fail-fast behavior for missing/ambiguous skeletons.

2. FiftyOne supports normalized keypoint coordinates and skeleton-backed rendering.
   - Keypoint points should be normalized to `[0, 1]`.
   - Missing joints can be represented as `[nan, nan]` while preserving index position.
   - Skeleton integration belongs on dataset-level skeleton fields.

3. Datumaro canonical pose structures align with strict contract validation.
   - Pose schema is rooted in `categories.points` labels/joints.
   - Visibility values map to absent/hidden/visible (`0/1/2`) and may be absent (default visible semantics).

4. Required schema checks should run preflight before sample writes.
   - Single unambiguous skeleton spec required.
   - Strict joint index/type checks.
   - Strict keypoint-count and visibility validation.
   - Aggregated mismatch reporting with bounded sample IDs in summary output.

## Risks and Pitfalls

- Silent fallback behavior in current skeleton parsing can produce corrupted or inconsistent mappings.
- Potential 0-based vs 1-based `joints` index ambiguity in incoming Datumaro exports must be explicitly handled by contract rules.
- Local environment may not have importable `fiftyone`; plan should include an environment readiness gate for integration validation.

## Planning Guidance

- Extend `PreflightReport` with schema mismatch categories, while preserving current preflight-first failure flow.
- Refactor skeleton parsing into strict contract validation helpers with explicit error taxonomy.
- Keep mapping deterministic: skeleton-label order is canonical; preserve annotation order (optionally sorted by annotation ID when present).
- Ensure summary diagnostics remain machine-readable and include first-N identifiers for each mismatch class.

## Source Files Consulted

- `.planning/phases/02-pose-contract-mapping/02-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `src/fiftyone_pose_importer/run_import.py`
- `src/fiftyone_pose_importer/preflight.py`
- `src/fiftyone_pose_importer/summary.py`
- `src/fiftyone_pose_importer/datumaro_reader.py`
- `.scratch_datumaro/src/datumaro/components/annotation.py`
- `.scratch_datumaro/src/datumaro/components/dataset/base.py`
- `.scratch_datumaro/src/datumaro/plugins/data_formats/datumaro/exporter.py`
