# Phase 2: Pose Contract Mapping - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Define and enforce the pose mapping contract from Datumaro points annotations into FiftyOne keypoint labels, including canonical skeleton selection, deterministic keypoint ordering, and fail-fast schema validation before writing corrupted pose labels.

</domain>

<decisions>
## Implementation Decisions

### Skeleton source-of-truth policy
- **D-01:** Datumaro `categories.points` is the canonical skeleton source when available; config-level skeleton data may be used only for validation.
- **D-02:** If Datumaro has no usable skeleton definition (missing labels/joints), fail fast with explicit schema diagnostics.
- **D-03:** Skeleton edge validation is strict: every edge endpoint must be an integer index in range of the label list; invalid edges fail import.
- **D-04:** If multiple skeleton specs are present, the importer must detect ambiguity and fail with clear diagnostics rather than guessing.

### Schema mismatch failure policy
- **D-05:** Run schema contract checks in preflight before sample creation.
- **D-06:** Any keypoint count mismatch between skeleton labels and annotation points is a hard failure with expected/actual counts in diagnostics.
- **D-07:** Missing visibility arrays default to all visible (`2`), but invalid visibility lengths/values are hard failures.
- **D-08:** Summary reporting should aggregate mismatches by type and include first-N sample IDs per type.

### Keypoint ordering contract
- **D-09:** Canonical keypoint order follows the canonical Datumaro skeleton label order.
- **D-10:** Missing joints are index-padded as `[NaN, NaN]` with `visibility=0` to preserve positional contract.
- **D-11:** Extra joints beyond skeleton label count are schema failures, not truncated.
- **D-12:** For multiple poses per image, preserve Datumaro order; when stable IDs exist, sort by annotation ID for deterministic ordering.

### the agent's Discretion
No discretionary implementation choices were delegated in this discussion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/PROJECT.md` — project intent, constraints, and core value.
- `.planning/REQUIREMENTS.md` — requirements mapped to this phase (`POSE-01/02/03`, `OUT-03`).
- `.planning/ROADMAP.md` — phase goal, boundaries, and success criteria for Phase 2.
- `.planning/phases/01-configured-ingestion-foundation/01-CONTEXT.md` — locked Phase 1 decisions that Phase 2 must preserve.

### Existing implementation surfaces
- `src/fiftyone_pose_importer/run_import.py` — current import orchestration, keypoint normalization, skeleton assignment.
- `src/fiftyone_pose_importer/datumaro_reader.py` — Datumaro payload loading boundary.
- `src/fiftyone_pose_importer/preflight.py` — current preflight error aggregation model.
- `src/fiftyone_pose_importer/config_model.py` — config contract and path resolution constraints.
- `src/fiftyone_pose_importer/summary.py` — machine-readable run summary output.

### Prior research context
- `.planning/research/SUMMARY.md` — synthesized risks and architecture constraints.
- `.planning/research/STACK.md` — stack and data-contract guidance.
- `.planning/research/ARCHITECTURE.md` — staged pipeline expectations.
- `.planning/research/PITFALLS.md` — known failure modes relevant to pose/schema mapping.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_import._extract_points_and_visibility` and `_normalize_points` provide the starting path for enforcing visibility and index alignment rules.
- `run_import._build_skeleton_from_datumaro` provides a skeleton parsing baseline to harden into strict contract validation.
- `PreflightReport` can be extended for schema mismatch categories and summarized diagnostics.
- `write_summary` already outputs machine-readable run artifacts; keep this as the reporting sink for mismatch evidence.

### Established Patterns
- Pipeline structure is preflight-first and fail-fast (`report.has_errors()` early exit) and should remain the control pattern.
- Strict validation is already a phase-1 invariant (unknown/invalid inputs fail rather than auto-heal).
- Deterministic matching and explicit diagnostics are established project behavior and should carry into pose mapping.

### Integration Points
- Schema and skeleton checks should plug into the preflight gate before dataset writes in `run_import`.
- Keypoint mapping rules should be applied in the annotation loop where `fo.Keypoint` objects are currently built.
- Summary diagnostics should feed through `summary["preflight"]` / schema sections to preserve existing CLI/reporting flow.

</code_context>

<specifics>
## Specific Ideas

- Keep pose mapping deterministic and strict: avoid silent repair paths that could mask labeling corruption.
- Prefer contract clarity over permissive import behavior for Phase 2 to protect downstream visualization trust.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-pose-contract-mapping*
*Context gathered: 2026-06-12*
