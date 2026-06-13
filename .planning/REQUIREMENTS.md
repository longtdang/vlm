# Milestone Requirements: v1.1

**Milestone:** v1.1  
**Name:** Skeleton Field Rendering + Configurable VLM Verification  
**Status:** Approved

## v1.1 Requirements

### Skeleton Rendering Foundation

- [x] **SKEL-01**: User can import multi-skeleton annotations into separate label-specific keypoint fields so each skeleton type renders connected edges correctly in FiftyOne.
- [x] **SKEL-02**: User can run the importer without collapsing all skeleton types into one shared keypoint field.
- [x] **SKEL-03**: User can verify from run output/metadata which keypoint field each skeleton type was mapped to.

### Deterministic Verification Core

- [ ] **VER-01**: User can run annotation verification that crops each annotation region using a configurable fixed-padding policy.
- [ ] **VER-02**: User can configure deterministic verification rules per label/class and get pass/fail/review results per annotation. Required rule categories include detection rules, attribute rules (e.g., clamp_type), skeleton-count rules, and visibility-format rules.
- [ ] **VER-03**: User can export verification results to CSV and JSON summaries for downstream triage, and the artifacts include per-sample traces (NDJSON/JSONL).
- [ ] **VER-04**: User can run deterministic verification without requiring any VLM service; deterministic FAILs must be recorded and surfaced in reports (no VLM dependency required).

### VLM Verification

- [ ] **VLM-01**: User can configure which labels/classes are VLM-verified and which remain deterministic-only.
- [ ] **VLM-02**: User can configure prompt templates and rule-linked prompt parameters per verified label; per-rule prompt mapping covers rules: bbox_localization, bbox_coverage, clamp_type, roll_count, keypoint_position, occlusion_state.
- [ ] **VLM-03**: User can run VLM verification only as an optional stage after deterministic checks; each VLM rule returns an error_probability and per-object aggregation computes a risk score (object_risk = max(rule error_probability)).
- [ ] **VLM-04**: User can receive safe fallback `REVIEW` outcomes when VLM checks fail, timeout, or return invalid outputs; all failures recorded with reason.
- [ ] **VLM-05**: User can configure an external OpenAI-compatible adapter endpoint to use Qwen2.5-VL-7B-Instruct (not present in FiftyOne 1.17 model zoo). System defaults to using installed model-zoo Qwen3-VL models (qwen3-vl-2b, qwen3-vl-4b, qwen3-vl-8b). Adapter selection and fallback behavior must be configurable and recorded in run provenance.

## Future Requirements (Deferred)

- [ ] **VLM-06**: User can use an interactive QA dashboard for verification review.
- [ ] **VLM-07**: User can auto-apply VLM correction suggestions back to annotations with rollback controls.

## Out of Scope (v1.1)

- Multi-user hosted verification service and permissions — keep local workflow focus.
- Always-on VLM evaluation for every annotation — use deterministic-first gating.
- Automatic mutation of canonical skeleton contract using VLM output — keep canonical import deterministic.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKEL-01 | Phase 5 | complete (05-01) |
| SKEL-02 | Phase 5 | complete (05-01) |
| SKEL-03 | Phase 5 | complete (05-01) |
| VER-01 | Phase 6 | pending |
| VER-02 | Phase 6 | pending |
| VER-03 | Phase 6 | pending |
| VER-04 | Phase 6 | pending |
| VLM-01 | Phase 7 | pending |
| VLM-02 | Phase 7 | pending |
| VLM-03 | Phase 7 | pending |
| VLM-04 | Phase 7 | pending |
| VLM-05 | Phase 7 | pending |
