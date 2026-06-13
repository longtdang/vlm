# Phase 5: Contracts & Preflight - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock import-time contracts so Datumaro skeleton/visibility semantics map deterministically into FiftyOne before any verification logic is added.

</domain>

<decisions>
## Implementation Decisions

### Field identity contract
- **D-01:** Use `label_id` as canonical skeleton identity.
- **D-02:** Target keypoint field naming must be stable and ID-based: `keypoints_label_<id>`.
- **D-03:** Human-readable label slug/name is metadata only; it must not drive field identity.
- **D-04:** If label text changes while `label_id` is unchanged, keep the same field name and update alias metadata only.

### Visibility preflight policy
- **D-05:** Visibility vectors with invalid values (not in `{0,1,2}`) or length mismatches against points are hard preflight failures that block import.
- **D-06:** Missing visibility with valid points is allowed; default to `2` and record warning/count in summary.

### Mapping metadata artifact
- **D-07:** Persist mapping metadata in run summary JSON under a dedicated `mapping` section.
- **D-08:** Minimum mapping entry fields are: `label_id`, `source_label_name`, `target_field`, `skeleton_labels`, `skeleton_edges`, `visibility_policy`.

### the agent's Discretion
No open discretion items; implementation decisions above are locked.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope and phase contracts
- `.planning/ROADMAP.md` — phase goals, success criteria, and v1.1 sequencing.
- `.planning/REQUIREMENTS.md` — REQ-to-phase mapping and locked requirement statements.
- `.planning/PROJECT.md` — milestone goal context and constraints.
- `.planning/STATE.md` — current milestone focus and current-position status.

### Import mapping behavior
- `src/main.py` — existing per-skeleton-type field mapping pattern (`dataset.skeletons` keyed by field, not class label).
- `src/fiftyone_pose_importer/run_import.py` — current canonical importer flow, summary output model, visibility handling, and preflight behavior.
- `src/fiftyone_pose_importer/config_model.py` — current config contract used by importer.

### Verification design intent referenced by user
- `workflow.md` — user-provided intended verification flow/rules and risk aggregation behavior.
- `data/datumaro.json` — category and skeleton source schema used for mapping/contract validation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_import.py` summary structure and `write_summary()` path handling can be extended for `mapping` metadata output.
- `pose_contract.py` contract extraction already resolves per-`label_id` skeleton contracts and is reusable for Phase 5 mapping validation.
- `main.py` already demonstrates per-type field creation and `dataset.skeletons` assignment pattern.

### Established Patterns
- Fail-fast schema mismatch handling is already used in preflight (`SchemaContractError` + summary failure section).
- Visibility normalization uses explicit `0/1/2` semantics and records warnings for defaulted values.

### Integration Points
- Import contract and mapping metadata changes should land in `src/fiftyone_pose_importer/run_import.py` and related contract/config helpers.
- Phase 5 output must remain compatible with existing CLI summary output flow in `src/fiftyone_pose_importer/cli.py`.

</code_context>

<specifics>
## Specific Ideas

- Maintain explicit pipeline framing: Datumaro -> Importer -> FiftyOne dataset.
- Keep skeleton types separated per field to preserve edge rendering by type.
- Preserve deterministic contract behavior before Phase 6/7 verification additions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-Contracts & Preflight*
*Context gathered: 2026-06-13*
