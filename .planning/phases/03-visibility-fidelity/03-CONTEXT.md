# Phase 3: Visibility Fidelity - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Preserve and expose visibility semantics from source annotations through import output so absent, hidden, and visible keypoints remain distinguishable and auditable without changing the Phase 2 pose contract.

</domain>

<decisions>
## Implementation Decisions

### Visibility semantics mapping
- **D-01:** Preserve three-state visibility contract exactly: `0=absent`, `1=hidden`, `2=visible`.
- **D-02:** Absent (`0`) stays non-rendered (`[NaN, NaN]`) while preserving index position.
- **D-03:** Hidden (`1`) keeps normalized coordinates and remains distinguishable from visible (`2`) in output metadata.

### Source fidelity and metadata
- **D-04:** Preserve the original source visibility array in label metadata (raw values retained for audit).
- **D-05:** If source visibility is missing, default to visible (`2`) and mark the sample/annotation as default-applied in metadata.
- **D-06:** Invalid visibility length/value remains fail-fast (no silent repair paths).

### Output and diagnostics
- **D-07:** Run-level summary must report visibility-state counts (`absent`, `hidden`, `visible`) and mismatch/warning counts.
- **D-08:** Visibility fidelity changes must remain compatible with Phase 2 deterministic ordering and schema gate behavior.

### the agent's Discretion
Field names for supplemental audit metadata (`source_visibility`, `visibility_defaulted`, etc.) are delegated to implementation if behavior remains explicit and machine-readable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/PROJECT.md` — project intent and constraints.
- `.planning/REQUIREMENTS.md` — Phase 3 requirements (`VIS-01`, `VIS-02`, `VIS-03`).
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria.
- `.planning/phases/02-pose-contract-mapping/02-CONTEXT.md` — upstream locked pose contract assumptions.

### Upstream implementation and behavior contracts
- `src/fiftyone_pose_importer/run_import.py` — current visibility parsing/mapping path and summary wiring.
- `src/fiftyone_pose_importer/preflight.py` — mismatch aggregation and fail-fast signaling.
- `src/fiftyone_pose_importer/summary.py` — run-report output channel.
- `tests/phase2/test_pose_mapping_import.py` — current expected behavior for mapping/order/skeleton application.

### Prior security/validation artifacts
- `.planning/phases/02-pose-contract-mapping/02-SECURITY.md` — accepted/mitigated threat constraints from prior phase.
- `.planning/phases/02-pose-contract-mapping/02-VALIDATION.md` — existing automated verification baseline to extend.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_extract_points_and_visibility` already normalizes missing visibility and validates value domain.
- `_normalize_points` already encodes absent points as non-rendered (`NaN`) for visibility `0`.
- `PreflightReport` has schema mismatch aggregation suitable for visibility diagnostics expansion.

### Established Patterns
- Preflight-first fail-fast flow is already established before dataset writes.
- Machine-readable summary output (`write_summary`) is the canonical reporting surface.
- Deterministic ordering and canonical skeleton alignment from Phase 2 must remain unchanged.

### Integration Points
- Visibility fidelity logic extends annotation conversion in `run_import.py`.
- Metadata preservation and summary visibility counters should be wired into summary payload generation.
- New tests should extend `tests/phase2` patterns or create `tests/phase3` with the same fake FiftyOne harness style.

</code_context>

<specifics>
## Specific Ideas

- Preserve both render behavior and auditability: rendering compatibility for FiftyOne plus explicit retained source visibility metadata.
- Keep diagnostics actionable by separating schema failures from default-applied visibility fallbacks.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-visibility-fidelity*
*Context gathered: 2026-06-12*
