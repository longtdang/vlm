# Phase 4: FiftyOne Viewing and Run Reporting - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Finalize user-facing output for import runs by ensuring reliable FiftyOne viewing launch behavior and complete run-report summaries (counts, warnings, failures) without changing core mapping semantics from Phase 2/3.

</domain>

<decisions>
## Implementation Decisions

### Viewing behavior
- **D-01:** Keep launch behavior explicitly opt-in via CLI `--launch`; no implicit app launch on import.
- **D-02:** Launch only on successful imports after dataset write path succeeds.
- **D-03:** Preserve compatibility with existing `fo.launch_app(dataset)` flow and avoid introducing new UI dependencies.

### Run summary contract
- **D-04:** Keep summary output as JSON at `<config_stem>.summary.json` written next to config.
- **D-05:** Summary must include user-observable import outcomes: sample counts, label-related counts, warnings, failures, and preflight diagnostics.
- **D-06:** Error paths must still emit machine-readable summary with explicit `summary_path`.

### Diagnostics shape and stability
- **D-07:** Reporting additions must be additive and backward-compatible with Phase 2/3 fields (no breaking key renames/removals).
- **D-08:** Failure/warning signals should be easy to aggregate (counts + categorized detail buckets).

### the agent's Discretion
Field naming for new warning/failure aggregate keys is delegated to implementation, as long as the schema remains machine-readable and stable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/PROJECT.md` — product intent and acceptance constraints.
- `.planning/REQUIREMENTS.md` — Phase 4 requirements (`OUT-01`, `OUT-02`).
- `.planning/ROADMAP.md` — Phase 4 goal, dependencies, and success criteria.
- `.planning/STATE.md` — current phase sequencing context.

### Upstream behavior contracts
- `.planning/phases/03-visibility-fidelity/03-CONTEXT.md` — locked visibility/reporting assumptions from prior phase.
- `src/fiftyone_pose_importer/cli.py` — CLI launch and exit-code contract.
- `src/fiftyone_pose_importer/run_import.py` — summary assembly + launch trigger integration.
- `src/fiftyone_pose_importer/summary.py` — persisted summary writer.
- `README.md` — documented runtime and troubleshooting expectations.

### Validation/security baselines
- `.planning/phases/03-visibility-fidelity/03-SECURITY.md` — accepted security constraints from prior phase.
- `.planning/phases/03-visibility-fidelity/03-VALIDATION.md` — existing validation cadence and test strategy.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_import` already centralizes preflight gating, dataset writes, summary assembly, and optional app launch.
- `write_summary` already standardizes JSON output location and serialization.
- CLI already maps `run_import` success/failure to process exit codes with summary output on both paths.

### Established Patterns
- Fail-fast preflight behavior is established and should remain primary error surface.
- Summary payload is the canonical machine-readable reporting artifact.
- New diagnostics should extend existing summary keys instead of replacing them.

### Integration Points
- Reporting enhancements integrate in `run_import` summary assembly and potentially `summary.py`.
- Viewing behavior refinements integrate in `cli.py` argument handling and launch guard logic.
- Tests should follow existing fake-FiftyOne harness pattern in `tests/phase2/test_pose_mapping_import.py`.

</code_context>

<specifics>
## Specific Ideas

- Ensure OUT-01 is validated through launch path behavior that is predictable and non-blocking when not requested.
- Ensure OUT-02 emphasizes actionable run-reporting (warnings/failures surfaced without log scraping).

</specifics>

<deferred>
## Deferred Ideas

- Advanced analytics and anomaly summaries (`ENH-02`) remain out of Phase 4 unless explicitly promoted.

</deferred>

---

*Phase: 4-fiftyone-viewing-and-run-reporting*
*Context gathered: 2026-06-12*
