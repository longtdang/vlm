# Phase 3: Visibility Fidelity - Research

**Researched:** 2026-06-12  
**Domain:** Visibility semantics preservation for Datumaro -> FiftyOne keypoints  
**Confidence:** High

## Requirement Focus

- **VIS-01:** absent keypoints remain non-rendered in FiftyOne-compatible form.
- **VIS-02:** hidden (`1`) and visible (`2`) remain distinguishable after import.
- **VIS-03:** original source visibility is preserved as audit metadata.

## Current Baseline (from code)

1. `run_import._extract_points_and_visibility` validates visibility domain (`0/1/2`) and defaults missing visibility to `2`.
2. `run_import._normalize_points` already converts absent (`0`) to `[NaN, NaN]`.
3. `run_import` currently stores `kp["visibility"]` only, without explicit raw-source audit metadata or default-applied markers.
4. Summary output includes preflight mismatch counts but no visibility-state counters.

## Gaps To Close

1. No explicit source visibility preservation channel separate from normalized output metadata.
2. No explicit marker for fallback/default-applied visibility behavior.
3. No visibility-state aggregate reporting (`absent`, `hidden`, `visible`) in run summary.

## Recommended Implementation Strategy

### 1. Add visibility fidelity helper path in `run_import.py`
- Keep existing strict validation and missing-length checks.
- Return:
  - normalized visibility (`visibility`)
  - raw/source visibility (`source_visibility`)
  - `visibility_defaulted` boolean when visibility was not present in source.

### 2. Preserve semantics at keypoint level
- Keep `kp["visibility"]` for rendering compatibility.
- Add machine-readable audit fields to each keypoint, e.g.:
  - `kp["source_visibility"]`
  - `kp["visibility_defaulted"]`

### 3. Add run-level visibility counters
- Track totals across imported annotations:
  - `absent` (0), `hidden` (1), `visible` (2)
  - `defaulted_annotations`
- Emit under `summary["visibility"]` while preserving existing summary contract.

### 4. Preserve Phase 2 behavior invariants
- Keep deterministic annotation ordering (`_ordered_point_annotations`).
- Keep contract alignment/fail-fast schema behavior (`SchemaContractError`, preflight gating).

## Proposed Plan Split

### Plan 03-01: Visibility metadata fidelity
- Extend conversion path and keypoint metadata for VIS-02/VIS-03.
- Preserve strict validation and compatibility with existing output schema.

### Plan 03-02: Visibility diagnostics and tests
- Add run summary visibility counters and default/failure diagnostics.
- Add tests covering absent/hidden/visible preservation, source metadata, and defaulted visibility tracking.

## Testing Strategy

1. Unit-level behavior checks in importer tests with fake FiftyOne harness:
   - absent -> `[NaN, NaN]` + visibility `0`
   - hidden -> normalized coordinates + visibility `1`
   - visible -> normalized coordinates + visibility `2`
2. Metadata checks:
   - `source_visibility` preserved
   - `visibility_defaulted` true when source visibility omitted
3. Summary checks:
   - expected visibility counts and defaulted annotation count
4. Regression checks:
   - deterministic ordering by annotation id remains unchanged
   - schema mismatch fail-fast behavior still active

## Risks and Controls

- **Risk:** breaking consumers expecting only `visibility` metadata.
  - **Control:** additive metadata fields only; keep existing key names unchanged.
- **Risk:** ambiguity between missing visibility and explicit visible values.
  - **Control:** explicit `visibility_defaulted` marker.
- **Risk:** drift between per-keypoint and summary counts.
  - **Control:** derive summary counters from the same mapped visibility arrays used to write labels.
