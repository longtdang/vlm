# Phase 1: Configured Ingestion Foundation - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Define the config-first ingestion foundation for this project: parse validated config, locate image folder and Datumaro JSON from local filesystem paths, and enforce deterministic input matching and strict preflight failure behavior before downstream pose/skeleton mapping work.

</domain>

<decisions>
## Implementation Decisions

### Config format and path rules
- **D-01:** v1 config format is YAML only.
- **D-02:** Config accepts local filesystem paths only (no URL-based data sources in v1).
- **D-03:** Relative paths resolve from the config file directory.
- **D-04:** Unknown config fields are hard errors (no silent ignore).

### Image-annotation matching policy
- **D-05:** Primary match key is normalized basename stem.
- **D-06:** Duplicate matches are fatal errors.
- **D-07:** Import reports all mismatches, then fails if any unmatched ratio is greater than zero.
- **D-08:** Filename and extension matching is case-insensitive.

### Failure behavior
- **D-09:** Validation is preflight (before writing dataset samples).
- **D-10:** Any malformed keypoint sample causes full import failure after reporting all malformed records.
- **D-11:** Import writes a machine-readable JSON summary file next to the config.
- **D-12:** Exit code policy is strict: `0` only on success, non-zero on any validation/import failure.

### the agent's Discretion
No discretionary implementation choices were delegated in this discussion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/PROJECT.md` — project intent, constraints, and core value.
- `.planning/REQUIREMENTS.md` — v1 requirements and traceability.
- `.planning/ROADMAP.md` — phase goals and success criteria.

### Workflow and configuration
- `.planning/config.json` — workflow preferences (mode, granularity, agent toggles).
- `copilot-instructions.md` — generated project instruction context.

### Research findings
- `.planning/research/SUMMARY.md` — synthesized architecture and risk summary.
- `.planning/research/STACK.md` — recommended stack and visibility mapping contract.
- `.planning/research/ARCHITECTURE.md` — pipeline boundaries and build order.
- `.planning/research/PITFALLS.md` — known ingestion and visibility failure modes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.scratch_datumaro/` source tree can be used as a reference for Datumaro annotation semantics and parser behavior during implementation.

### Established Patterns
- No existing importer application code is present yet; Phase 1 should establish the baseline project structure and validation patterns.

### Integration Points
- New ingestion code will be introduced as initial project modules and should be organized to feed future Phase 2/3 mapping and visibility stages.

</code_context>

<specifics>
## Specific Ideas

- Keep v1 explicitly local-first and deterministic to avoid hidden behavior.
- Make mismatch and validation outputs explicit and machine-readable for repeatable debugging.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Configured Ingestion Foundation*
*Context gathered: 2026-06-11*
