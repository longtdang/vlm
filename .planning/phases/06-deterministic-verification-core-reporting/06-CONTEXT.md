# Phase 6: Deterministic Verification Core & Reporting - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a deterministic verification stage that evaluates annotations via fixed crop policy + deterministic rules, then exports auditable CSV/JSON/NDJSON reports without requiring any VLM service.

</domain>

<decisions>
## Implementation Decisions

### Deterministic verdict policy
- **D-01:** Deterministic stage supports only `PASS` and `FAIL` outcomes (no `REVIEW` in Phase 6).
- **D-02:** Object verdict aggregation is strict: any failed rule => object `FAIL`; otherwise `PASS`.
- **D-03:** If a deterministic rule cannot be evaluated (missing data, malformed value, runtime rule error), mark that object as `FAIL` with explicit reason.
- **D-04:** Only deterministic `PASS` objects are eligible for optional VLM checks in Phase 7.
- **D-05:** Runs must complete and return zero CLI exit code even when objects fail; failures are carried in report artifacts.

### Rule config shape
- **D-06:** Rule configuration uses global defaults plus per-label/class overrides.
- **D-07:** Labels without explicit overrides inherit all global deterministic rules.
- **D-08:** By default, each label/class must include all four deterministic categories: detection, attribute, skeleton-count, visibility-format.
- **D-09:** Unknown rule names in config are ignored with warning (not hard fail).

### Crop policy and edge handling
- **D-10:** Crop padding policy is fixed pixel padding.
- **D-11:** For skeleton/keypoint labels, preserve full padded crop canvas even when crop extends out of image bounds (outside-image region padded in output crop).
- **D-12:** For skeleton/keypoint annotations, out-of-frame points remain valid and should be treated as occluded (`v=1`).
- **D-13:** For non-skeleton labels (detection/segmentation), out-of-frame crop is clipped to image boundaries.
- **D-14:** Zero/negative-size boxes must fail object verification with reason `invalid_bbox`.

### Report schema and run artifacts
- **D-15:** Every run must emit all three artifacts: CSV, JSON, NDJSON trace.
- **D-16:** CSV and JSON must include both final object verdict and per-rule details.
- **D-17:** Output artifacts are written under a unique timestamped run directory.
- **D-18:** Report rows/traces must always include crop path and deterministic failure reasons.

### the agent's Discretion
No open discretion items for this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase contracts
- `.planning/ROADMAP.md` — Phase 6 goal/success criteria and phase dependencies.
- `.planning/REQUIREMENTS.md` — VER-01..VER-04 requirement contract and traceability.
- `.planning/PROJECT.md` — milestone-level constraints and deterministic-first policy context.
- `.planning/STATE.md` — active phase cursor and next action contract.

### Upstream phase decisions and implementation baseline
- `.planning/phases/05-contracts-preflight/05-CONTEXT.md` — locked import contracts (field identity, visibility semantics, mapping metadata).
- `.planning/phases/05-contracts-preflight/VERIFICATION.md` — verified behaviors and remaining manual checks from Phase 5.
- `src/fiftyone_pose_importer/run_import.py` — canonical import output schema, visibility handling, and summary writing entry points.
- `src/fiftyone_pose_importer/summary.py` — run summary write path pattern to align reporting artifacts.

### User-referenced verification flow
- `workflow.md` — user-intended verification process framing and rule workflow.
- `data/datumaro.json` — label/category source schema for rule/class mapping.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_import.py` already provides robust object-level validation/error categorization patterns and summary emission helpers reusable for deterministic verification output plumbing.
- `summary.py` establishes stable artifact writing conventions (path derivation + JSON serialization).
- Existing phase tests (`tests/phase4`, `tests/phase5`) show how to build additive schema assertions and fake FiftyOne-driven deterministic unit tests.

### Established Patterns
- Fail-fast validation is explicit and categorized (`SchemaContractError` buckets + summary failure counts).
- Visibility semantics are explicitly modeled as `0/1/2`, with controlled defaulting and warning counters.
- Reports are additive rather than schema-breaking across phases.

### Integration Points
- Phase 6 logic should integrate as a post-import stage that consumes existing importer outputs without mutating canonical imported annotations.
- Deterministic reports must align with Phase 5 mapping semantics (`keypoints_label_<id>` and mapping metadata).
- CLI integration should remain config-driven through existing entrypoint patterns in `src/fiftyone_pose_importer/cli.py`.

</code_context>

<specifics>
## Specific Ideas

- Deterministic-only stage must be fully useful without VLM enabled.
- Out-of-frame skeleton/keypoint handling must preserve padded crop context and enforce occlusion semantics.
- Reporting must favor triage ergonomics (flat CSV + structured JSON + stepwise NDJSON traces).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 6-Deterministic Verification Core & Reporting*
*Context gathered: 2026-06-13*
