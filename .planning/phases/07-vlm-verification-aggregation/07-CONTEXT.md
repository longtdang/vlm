# Phase 7: VLM Verification & Aggregation - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an optional VLM stage on top of deterministic gating: for objects that passed deterministic checks, run FiftyOne model-zoo VLM rules per-label, aggregate per-object risk scores, and export separate VLM artifacts and a prioritized review queue.

</domain>

<decisions>
## Implementation Decisions

### Adapter strategy
- **D-01:** Phase 7 uses only FiftyOne model-zoo models — no external HTTP adapter endpoint.
- **D-02:** Active model is configured by name (one model at a time, e.g., `qwen3-vl-2b`, `qwen3-vl-4b`, `qwen3-vl-8b`).
- **D-03:** If the configured model fails to load or inference throws, mark object as `REVIEW` with failure_reason recorded.
- **D-04:** No fallback chain — single configured model, fail → REVIEW.

### VLM label scope
- **D-05:** VLM verification is opt-in per label — controlled via config (`verification.vlm.labels.<label>.enabled: true`).
- **D-06:** Labels not in the VLM opt-in list remain deterministic-only; their final status is the deterministic verdict.
- **D-07:** Per VLM-enabled label, a per-label explicit rule list specifies which of the six rules to evaluate (`bbox_localization`, `bbox_coverage`, `clamp_type`, `roll_count`, `keypoint_position`, `occlusion_state`).

### VLM execution gate
- **D-08:** Objects that failed deterministic checks skip VLM entirely; their final status remains `FAIL`.
- **D-09:** Only deterministic `PASS` objects in VLM-enabled labels proceed to VLM rules.

### Prompt and response contract
- **D-10:** Per-label per-rule prompt templates are supported; each label/rule pair may define a custom template. A global default template is used as fallback when no per-label template is set.
- **D-11:** Each VLM rule prompt receives: crop image + label name + rule name + relevant annotation fields (bbox, visibility, attribute values as applicable to the rule).
- **D-12:** VLM response must be strict JSON: `{"error_probability": float, "reason": str, "evidence": str (optional)}`.
- **D-13:** If `error_probability` is missing, non-numeric, or outside `[0.0, 1.0]`, the rule result is marked `invalid_output`; the object is marked `REVIEW` with reason.
- **D-14:** VLM generation parameters default to deterministic settings (e.g., temperature=0 equivalent). User may override in config.

### Risk aggregation
- **D-15:** `object_risk = max(error_probability across all VLM rules for the object)`.
- **D-16:** Default thresholds (configurable): PASS ≤ 0.20, REVIEW ≤ 0.60, FAIL > 0.60.
- **D-17:** Thresholds support global defaults with optional per-label overrides in config.
- **D-18:** If VLM produces no valid rule result (adapter fail / all invalid_output), object status is `REVIEW` with failure_reason.

### Artifacts
- **D-19:** Phase 7 emits separate VLM artifacts alongside Phase 6 deterministic artifacts in the same timestamped run directory: `vlm_report.csv`, `vlm_report.json`, `vlm_trace.ndjson`.
- **D-20:** Each VLM artifact row/entry includes: `sample_id`, `object_id`, `label`, `vlm_status` (PASS/REVIEW/FAIL), `object_risk`, per-rule `error_probability` + `reason`, `adapter_model`, `failure_reason`.

### Review queue
- **D-21:** Review queue is embedded in `vlm_report.json` as an ordered list (`review_queue`), sorted by: risk descending → adapter_failure first → sample_id/object_id ascending.

### Testing
- **D-22:** Phase 7 tests use a mock FiftyOne model that returns deterministic JSON responses — no real GPU or model download required for CI.

### the agent's Discretion
No open discretion items; all decisions above are locked.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase contracts
- `.planning/ROADMAP.md` — Phase 7 goal, success criteria, and phase dependencies.
- `.planning/REQUIREMENTS.md` — VLM-01..VLM-05 requirement contract and traceability.
- `.planning/PROJECT.md` — milestone-level constraints.
- `.planning/STATE.md` — active phase cursor and next action contract.

### Upstream phase decisions and implementation baseline
- `.planning/phases/06-deterministic-verification-core-reporting/06-CONTEXT.md` — deterministic policy, crop policy, report schema decisions.
- `.planning/phases/06-deterministic-verification-core-reporting/VERIFICATION.md` — verified behaviors from Phase 6 (crop materialization, VLM-eligibility tagging).
- `src/fiftyone_pose_importer/run_verify.py` — VLM eligibility flag already set; integration point for VLM stage.
- `src/fiftyone_pose_importer/verification/types.py` — `ObjectVerificationResult` type to extend or wrap for VLM outputs.
- `src/fiftyone_pose_importer/verification/config.py` — rule config loading pattern to replicate for VLM config.

### User-referenced context
- `workflow.md` — intended verification flow and rule categories.
- `data/datumaro.json` — label/category source schema for VLM label scope config.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_verify.py` already resolves image paths, materializes crops, and writes report artifacts — the VLM stage extends this pipeline.
- `verification/config.py` pattern (global defaults + per-label overrides) is directly reusable for VLM config loading.
- `verification/report_csv.py` / `report_json.py` / `report_ndjson.py` provide canonical serialization patterns for VLM report writers.
- `tests/phase6/test_run_verify.py` establishes the mock-image testing pattern for integration tests.

### Established Patterns
- Phase 6 config uses global + per-label override blocks — replicate for VLM scope/rules/thresholds/templates.
- `ObjectVerificationResult` captures `verdict`, `rule_results`, `failure_reasons` — extend or create parallel `VlmObjectResult` for VLM-specific fields.
- Deterministic reports write to timestamped run dir — VLM reports write to same run dir under distinct filenames.

### Integration Points
- `run_verify.py`: after deterministic loop completes, VLM-eligible results are identified; VLM stage hooks in here.
- `cli.py` `verify` subcommand: already supports `vlm.enabled` flag; no CLI changes needed unless `--vlm-only` mode is desired.

</code_context>

<specifics>
## Specific Ideas

- Implement `verification/vlm_client.py` as thin FiftyOne model-zoo wrapper; accepts model name + crop path + prompt; returns parsed JSON or raises.
- Implement `verification/vlm_config.py` for VLM scope, per-rule template, and threshold config loading (mirror pattern from `verification/config.py`).
- Implement `verification/vlm_engine.py` for per-object rule execution, `invalid_output` handling, and risk aggregation.
- Implement `verification/report_vlm.py` for VLM CSV/JSON/NDJSON writers and review_queue generation.
- Wrap FiftyOne model with a mock class (duck-type same interface) for CI tests; injected via config or test fixture.

</specifics>

<deferred>
## Deferred Ideas

- External OpenAI-compatible HTTP endpoint — removed from Phase 7 scope per user decision; defer to future milestone if needed.
- Interactive review dashboard (VLM-06) — explicitly deferred in REQUIREMENTS.md.
- Auto-apply VLM correction suggestions (VLM-07) — explicitly deferred in REQUIREMENTS.md.

</deferred>

---

*Phase: 7-VLM Verification & Aggregation*
*Context gathered: 2026-06-13*
