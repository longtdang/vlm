# SUMMARY — v1.1 research synthesis

## Executive Summary

This project is a local-first FiftyOne Datumaro pose importer extended with a verification pipeline that combines deterministic checks with an optional Visual Language Model (VLM) escalation. The recommended approach is conservative: preserve deterministic import semantics and skeleton contracts, deliver a robust deterministic verification core (cropper, rules, reporting), then add an optional, pluggable VLM adapter behind strict config and privacy guardrails.

For v1.1 ship a deterministic, auditable verification pipeline that: (a) does not change canonical dataset content as a side effect of VLM, (b) emits a machine-readable verification artifact (JSON/NDJSON + CSV summary), and (c) implements VLM as opt-in, rate-limited, and privacy-conscious. This minimizes risk, keeps the milestone scoped, and provides the telemetry needed to expand VLM usage safely later.

## Key Findings

### From STACK.md
- Python >=3.10 (prefer 3.11): aligns with project constraints and ecosystem. 
- fiftyone >=1.0,<2.0: required for dataset and per-field skeleton rendering. 
- pydantic >=2: typed config validation for strict contracts. 
- PyYAML >=6: config loading. 
- Additions (v1.1): Pillow (10+ for cropping), httpx (VLM client), tenacity (retries/backoff). 
- Explicit do-not-add in v1.1: web service layer, job queues, DB-backed results, LangChain-like frameworks, plugin system for rules.

Critical version constraints: pydantic v2+, fiftyone 1.x, Pillow >=10 per recommendations in STACK.md.

### From FEATURES.md
- Table-stakes: preserve per-skeleton-type field mapping; configurable label targeting; deterministic rule checks; reusable crop generation; unified verification schema; JSON + CSV exports.
- Differentiators (v1.1): optional VLM escalation gated by deterministic checks; configurable prompt templates; merged verdict with provenance metadata.
- Anti-features (defer): running VLM on every annotation, auto-correction, a full interactive QA UI, multi-provider orchestration engine.
- MVP priority: 1) skeleton preservation + deterministic rules; 2) label targeting + config schema; 3) optional VLM escalation + reporting.

### From ARCHITECTURE.md
- Verification must be a post-import pipeline under src/fiftyone_pose_importer/verification/, isolated from parsing. Key modules: config_model.py updates, runner.py, cropper.py, rules.py, vlm_client.py (adapter), report.py, and CLI hooks in run_import.py.
- Data flow: import -> verification.runner -> crop -> deterministic checks -> optional VLM -> report JSON -> summary link.
- Patterns: Facade + pipeline stages; provider interface for optional VLM; do not mix verification into import parsing loops; keep src/main.py for manual inspection only.
- Build order: define contracts -> deterministic core -> orchestrator integration -> add VLM adapter last -> CLI/docs/tests.

### From PITFALLS.md
Top critical pitfalls and mitigations:
1. Non-determinism leaking into canonical import — mitigation: VLM opt-in, never mutate source annotations in-place, produce separate verification artifacts, and provide replay/apply tooling. 
2. Applying VLM to change skeleton contracts at write-time — mitigation: retain deterministic contract selection and surface VLM suggestions as warnings or migration plans only. 
3. Visibility semantics mismatch and silent overwrites — mitigation: preserve source_visibility, add vlm suggestion fields, do not overwrite without explicit reconcile policy.
Other notable risks: missing image size metadata, rate limits/latency for VLM (don't block writes), privacy/exfiltration (cfg guardrails), prompt-template drift and brittle parsers, and poor error visibility without a report artifact.

Minimum safeguards checklist (v1.1): VLM opt-in default off; NDJSON/JSONL per-sample traces; preserve source visibility; deterministic contract selection; rate-limits + local fallback; unit and snapshot tests; include verification summary in run summary.

## Implications for Roadmap (phased suggestions)

Suggested phases (3 phases to deliver v1.1 safely):

1) Phase 1 — Contracts & Preflight (Rationale: foundation)
- Rationale: correct contracts, image metadata, and preflight validation are prerequisites for reliable verification and VLM reasoning. Fixing these first prevents systematic errors down the line.
- Delivers: extended config_model with verification schema, preflight checks for image sizes and ambiguous skeletons, tests/fixtures for visibility states, and summary contract extension (verification metadata placeholder).
- Features: per-skeleton-type field preservation enforcement, preflight validation, image size normalization fallback.
- Pitfalls to avoid: do not allow VLM to influence canonical contract selection; add preflight fail-fast for ambiguous skeletons.
- Research flags: none major — pattern is well-documented.

2) Phase 2 — Deterministic Verification Core + Reporting (Rationale: low-risk, high-value)
- Rationale: deterministic checks provide immediate value (fast, auditable) and gate VLM use. They can be implemented and tested without external dependencies.
- Delivers: verification/cropper.py, verification/rules.py, verification/report.py (JSON/CSV), runner.py skeleton, CLI flag (--verify or config-driven), NDJSON per-sample traces, unit & snapshot tests.
- Features: deterministic rule checks, reusable crop generation, unified verification schema, label allowlist/denylist targeting, report export.
- Pitfalls to avoid: running rules inline during import parsing; do not block dataset write on verification failures; ensure normalization of coordinates and bounding for crops.
- Research flags: none critical; requires fleshing out rule list/thresholds (local domain experts) but implementable with existing info.

3) Phase 3 — Optional VLM Adapter, Ops & Safety (Rationale: highest-risk features last)
- Rationale: VLM integration introduces non-determinism, privacy, and rate-limit concerns. Implement it last, behind a clear adapter with config, guards, and replayability.
- Delivers: verification/vlm_client.py (VLMClient protocol + httpx adapter), tenacity-wrapped retries, concurrency/rate-limit settings, privacy guardrails (cfg.verify.vlm.send_images=false default), prompt templating with version/hash recording, replay/apply tooling and CLI flags (--apply-verification/--replay-verification), and docs.
- Features: optional VLM escalation for flagged items, prompt templates per-label, merged verdicts with provenance fields in reports.
- Pitfalls to avoid: do not mutate dataset in-place with VLM outputs; do not send images to cloud by default; provide local/mock adapter and CI canned responses; avoid blocking import on VLM latency or failing on rate limits.
- Research flags: choose default VLM provider(s) and clarify legal/privacy acceptance (requires product/legal input). Consider whether auto-apply migration mode is needed — if so, a separate research phase is required.

Optional Phase 4 — UX & Scale (defer v1.1)
- Rationale: interactive QA UI, auto-correction, and distributed processing add substantial scope. Defer to v2 once verification artifacts and VLM patterns are stable.

## Research Flags (need deeper planning)
- VLM provider selection and default adapters (cloud vs local): impacts privacy, cost, and reproducibility — Research Phase required. (affects Phase 3)
- Auto-apply migration tooling for contract rewrites: safety model and rollback — Research Phase required if product wants automated migration. (affects Phase 1/3)
- Legal/privacy review for sending image crops to third-party providers — operational/legal sign-off required. (Phase 3)

## Confidence Assessment
- Stack: HIGH — Stack recommendations align with project pyproject and proven ecosystem packages; version constraints are explicit in STACK.md.
- Features: HIGH-MEDIUM — Table-stakes and MVP priorities are well-supported by codebase references; some rule thresholds need domain input.
- Architecture: HIGH — Clear componentization and build order are documented; patterns and anti-patterns are concrete and actionable.
- Pitfalls: HIGH — Pitfalls are detailed with code pointers and explicit mitigations; VLM-related open questions remain.

Gaps / Open Questions
- Default VLM provider(s) to support (local vs cloud). 
- Whether product requires an auto-apply migration path for contract changes. 
- Any legal constraints on sending data off-host (country-specific). 

## Actionable Recommendations (short)
- Implement Phase 1+2 immediately for v1.1: contracts, preflight, deterministic verification, reporting, and CLI hooks. Keep VLM disabled by default. 
- Add Phase 3 (VLM) only after Phase 2 is shipping and after provider/privacy decisions are made; require opt-in and replay/apply tooling. 
- Ensure test coverage: unit tests for normalization/visibility, snapshot tests for VLM adapter responses (mocked), UAT dataset for visual inspection.

## Sources
- .planning/research/STACK.md
- .planning/research/FEATURES.md
- .planning/research/ARCHITECTURE.md
- .planning/research/PITFALLS.md


<!-- GENERATED by gsd research synthesizer -->
