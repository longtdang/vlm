# ROADMAP: Milestone v1.1 — Skeleton Field Rendering + Configurable VLM Verification

Granularity: standard  
Milestone: v1.1

## Phases

- [ ] **Phase 5: Contracts & Preflight** - Datumaro -> Importer -> FiftyOne dataset flow: validate skeleton contracts, field mapping, and visibility semantics so skeletons render correctly in FiftyOne.
- [ ] **Phase 6: Deterministic Verification Core & Reporting** - Cropper + deterministic rule engine (detection rules, attribute rules, skeleton count rules, visibility format rules); deterministic FAIL -> report; deterministic PASS -> continue.
- [ ] **Phase 7: VLM Verification & Aggregation** - Per-rule VLM checks (bbox_localization, bbox_coverage, clamp_type, roll_count, keypoint_position, occlusion_state) producing error_probability; per-object aggregation -> CSV/JSON + Review Queue. Support Qwen2.5 via an external adapter endpoint with fallback to installed model-zoo Qwen3-VL models.

## Phase Details

### Phase 5: Contracts & Preflight
**Goal**: Given a Datumaro JSON export, the importer reliably produces a FiftyOne dataset where each skeleton type is mapped to its own keypoint field and visibility semantics (visible/occluded/not-labeled) are preserved and auditable.

**Depends on**: none (phase 5 is the milestone entry)

**Requirements**: SKEL-01, SKEL-02, SKEL-03

**Success Criteria** (what must be TRUE):
  1. Running the importer with a Datumaro JSON path and an image-folder path produces a FiftyOne dataset (verify dataset exists in FiftyOne) — explicit Datumaro -> Importer -> FiftyOne flow is observable (CLI output and dataset listing).
  2. Each skeleton type from the Datumaro source maps to a distinct target keypoint field in the FiftyOne dataset (inspect dataset schema; each skeleton type corresponds to its own field and edges render correctly).
  3. Visibility semantics are preserved: for keypoints, source visibility codes (visible/occluded/not-labeled) are represented in the dataset and render consistently in the FiftyOne viewer (manual visual check and metadata spot-check).
  4. Import metadata (CLI output or run artifact) documents the mapping for every skeleton type: source identifier -> target field name -> visibility mapping rules (inspectable metadata file in run artifact).

**Plans**: Implement Datumaro parsing -> mapping layer; add explicit mapping metadata emission in import artifacts; add preflight checks for ambiguous visibility or missing image size metadata; include canonical UAT fixture for visual verification.

### Phase 6: Deterministic Verification Core & Reporting
**Goal**: Users can run a deterministic, auditable verification pipeline that crops annotated objects (fixed-padding policy), applies per-label deterministic rules (including detection, attribute, skeleton-count, visibility-format rules), and exports deterministic PASS/FAIL/REVIEW results to machine-readable reports.

**Depends on**: Phase 5

**Requirements**: VER-01, VER-02, VER-03, VER-04

**Success Criteria** (what must be TRUE):
  1. For each annotation, the pipeline generates a crop according to the configured fixed-padding policy and records crop paths or in-memory references in the verification artifact (inspect crop files/paths).
  2. Deterministic rules are available and applied per label/class; the engine produces a deterministic verdict for each rule (PASS/FAIL only, no deterministic REVIEW state). Deterministic rules must include at minimum: detection rules (e.g., bbox localization format), attribute rules (e.g., clamp_type attribute consistency), skeleton count rules (expected keypoint count per skeleton type), and visibility format rules (valid v codes and semantics).
  3. Deterministic FAIL results are surfaced immediately in the report artifact (CSV/JSON) with rule name and deterministic reason; deterministic PASS results allow that object to proceed to the optional VLM stage or be marked PASS at pipeline end if VLM is disabled (observable via run outputs).
  4. Pipeline produces NDJSON/JSON per-sample traces and a CSV summary consumable by downstream triage tools (open CSV/JSON to inspect expected columns).
  5. The deterministic verification stage can run with VLM disabled and still produce complete reports (run with VLM disabled and inspect artifacts).

**Plans**: Implement verification/cropper.py, verification/rules.py (rule types enumerated above), deterministic runner with gating logic, report exporter (CSV/JSON), and unit/snapshot tests for rule logic and reproducibility.

### Phase 7: VLM Verification & Aggregation
**Goal**: For objects that pass through deterministic gating, run a pluggable VLM stage that evaluates specific rules (bbox_localization, bbox_coverage, clamp_type, roll_count, keypoint_position, occlusion_state). Each VLM rule returns an error_probability; aggregate per-object risk (max) and export CSV/JSON and a prioritized review queue.

**Depends on**: Phase 6

**Requirements**: VLM-01, VLM-02, VLM-03, VLM-04, VLM-05

**Success Criteria** (what must be TRUE):
  1. For each object selected for VLM verification, the pipeline performs: generate object crop -> run VLM per configured rule list [bbox_localization, bbox_coverage, clamp_type, roll_count, keypoint_position, occlusion_state] -> produce per-rule error_probability values that are recorded in the per-sample trace (inspect rule entries in JSON).
  2. Per-object aggregation computes object_risk = max(error_probability across rules) and assigns a status (PASS/REVIEW/FAIL) per configured thresholds; the CSV/JSON artifacts contain object-level risk_score and status (open artifact and verify fields).
  3. System supports configurable VLM adapter selection: default adapter uses installed FiftyOne 1.17 model zoo (qwen3-vl-{2b,4b,8b}); Qwen2.5-VL-7B-Instruct is supported only via a configurable external OpenAI-compatible adapter endpoint (local server or remote) — configuration and adapter selection are recorded in run provenance (inspect run config recorded).
  4. If the configured external adapter is unreachable, times out, or returns invalid responses, the system falls back to the configured fallback model-zoo adapter (if allowed by config) or marks the object as REVIEW and records the failure reason (observe failure entries in trace).
  5. The pipeline emits CSV and JSON reports and a Review Queue ordering by risk descending that can be consumed by triage tooling (open CSV/JSON and ensure review queue ordering exists).

**Plans**: Implement verification/vlm_client.py (adapter interface + httpx/OpenAI-compatible adapter), model selection and fallback logic, rule-to-prompt mapping for the six rules, per-rule result parsing into error_probability, object aggregation, and report + review queue exporter. Include tests and a mock adapter for CI.

## Traceability (summary)

| Requirement | Phase |
|-------------|-------|
| SKEL-01 | Phase 5 |
| SKEL-02 | Phase 5 |
| SKEL-03 | Phase 5 |
| VER-01 | Phase 6 |
| VER-02 | Phase 6 |
| VER-03 | Phase 6 |
| VER-04 | Phase 6 |
| VLM-01 | Phase 7 |
| VLM-02 | Phase 7 |
| VLM-03 | Phase 7 |
| VLM-04 | Phase 7 |
| VLM-05 | Phase 7 |

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 5 - Contracts & Preflight | 3/3 | Complete | 2026-06-13 (05-01, 05-02, 05-03) |
| 6 - Deterministic Verification Core & Reporting | 4/4 | Complete | 2026-06-13 (06-01, 06-02, 06-03, 06-04) |
| 7 - VLM Verification & Aggregation | 0/5 | Not started | - |

## Notes

- Phase 7 includes explicit support for Qwen2.5-VL-7B-Instruct only via external adapter endpoint with fallback to model zoo Qwen3-VL models (qwen3-vl-2b, qwen3-vl-4b, qwen3-vl-8b).
