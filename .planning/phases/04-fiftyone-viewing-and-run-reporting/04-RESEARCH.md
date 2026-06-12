# Phase 4: FiftyOne Viewing and Run Reporting - Research

**Researched:** 2026-06-12  
**Domain:** FiftyOne launch semantics and run-summary contract hardening  
**Confidence:** High

## Requirement Focus

- **OUT-01:** open imported dataset in FiftyOne and view connected skeleton rendering.
- **OUT-02:** output run summary with samples, labels, warnings, and failures.

## Current Baseline

1. `cli.py` already exposes `--launch` and forwards it into `run_import(..., launch_app=args.launch)`.
2. `run_import.py` already:
   - writes summary JSON,
   - writes dataset/default skeleton on success,
   - launches app only when `launch_app=True`.
3. Summary currently includes core counters and preflight/visibility, but lacks explicit top-level warning/failure rollups and label-count aggregates.

## Gaps To Close

1. No explicit standardized `warnings` and `failures` top-level summary buckets.
2. No dedicated label-count aggregates in summary for OUT-02 reporting clarity.
3. Launch outcome metadata is implicit; contract can be made explicit (`requested/attempted/ok/error`).

## Recommended Strategy

### 1. Expand summary contract additively
- Preserve all existing keys.
- Add new top-level blocks:
  - `label_counts`
  - `warnings` (counts + details)
  - `failures` (counts + details)
  - `launch` (requested/attempted/ok/error)

### 2. Keep launch behavior deterministic
- Keep `--launch` opt-in only.
- Attempt launch only after successful dataset save.
- Persist launch outcome in summary so OUT-01 is auditable.

### 3. Strengthen tests using existing fake FiftyOne pattern
- Add phase-4 tests for:
  - launch not called when `--launch` false,
  - launch called on successful import when requested,
  - launch not called on preflight failure,
  - summary schema includes warnings/failures/label counts/launch block.

## Plan Split Recommendation

1. **04-01:** Summary contract expansion (label counts + warning/failure rollups).
2. **04-02:** Launch semantics and launch outcome reporting.
3. **04-03:** Test and docs pass for user-visible workflow and troubleshooting.

## Risks and Controls

- **Risk:** Breaking existing summary consumers.
  - **Control:** additive-only summary changes; no key removals/renames.
- **Risk:** Launch failures obscuring import success data.
  - **Control:** persist explicit launch status block in summary.
- **Risk:** ambiguous warning/failure interpretation.
  - **Control:** define stable categorized counts and details fields.
