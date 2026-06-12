# Milestone Requirements: v1.1

**Milestone:** v1.1  
**Name:** Skeleton Field Rendering + Configurable VLM Verification  
**Status:** Approved

## v1.1 Requirements

### Skeleton Rendering Foundation

- [ ] **SKEL-01**: User can import multi-skeleton annotations into separate label-specific keypoint fields so each skeleton type renders connected edges correctly in FiftyOne.
- [ ] **SKEL-02**: User can run the importer without collapsing all skeleton types into one shared keypoint field.
- [ ] **SKEL-03**: User can verify from run output/metadata which keypoint field each skeleton type was mapped to.

### Deterministic Verification Core

- [ ] **VER-01**: User can run annotation verification that crops each annotation region using a configurable fixed-padding policy.
- [ ] **VER-02**: User can configure deterministic verification rules per label/class and get pass/fail/review results per annotation.
- [ ] **VER-03**: User can export verification results to CSV and JSON summaries for downstream triage.
- [ ] **VER-04**: User can run verification without requiring any VLM service.

### Optional VLM Verification

- [ ] **VLM-01**: User can configure which labels/classes are VLM-verified and which remain deterministic-only.
- [ ] **VLM-02**: User can configure prompt templates and rule-linked prompt parameters per verified label.
- [ ] **VLM-03**: User can run VLM verification only as an optional stage after deterministic checks.
- [ ] **VLM-04**: User can receive safe fallback `REVIEW` outcomes when VLM checks fail, timeout, or return invalid outputs.

## Future Requirements (Deferred)

- [ ] **VLM-05**: User can use an interactive QA dashboard for verification review.
- [ ] **VLM-06**: User can auto-apply VLM correction suggestions back to annotations with rollback controls.

## Out of Scope (v1.1)

- Multi-user hosted verification service and permissions — keep local workflow focus.
- Always-on VLM evaluation for every annotation — use deterministic-first gating.
- Automatic mutation of canonical skeleton contract using VLM output — keep canonical import deterministic.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKEL-01 | — | pending |
| SKEL-02 | — | pending |
| SKEL-03 | — | pending |
| VER-01 | — | pending |
| VER-02 | — | pending |
| VER-03 | — | pending |
| VER-04 | — | pending |
| VLM-01 | — | pending |
| VLM-02 | — | pending |
| VLM-03 | — | pending |
| VLM-04 | — | pending |
