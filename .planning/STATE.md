---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
status: planning
last_updated: "2026-06-13T05:21:15.025Z"
last_activity: 2026-06-13 — Roadmap revised for explicit import flow and VLM adapter constraints.
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

---
gsd_state_version: 1.1
milestone: v1.1
milestone_name: Skeleton Field Rendering + Configurable VLM Verification
status: in_progress
last_updated: "2026-06-13T06:05:00Z"
last_activity: 2026-06-13
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 67

# Project State

## Project Reference

See: .planning/PROJECT.md

**Core value:** Given only config paths, reliably import and visualize CVAT/Datumaro pose annotations in FiftyOne with correct skeleton visibility behavior.
**Current focus:** Phase 5 — implement Datumaro -> Importer -> FiftyOne flow and validate skeleton contracts, visibility mapping, and per-skeleton field mapping.

## Current Position

Phase: 5 (Contracts & Preflight)
Plan: 03 (pending)
Status: In progress
Last activity: 2026-06-13 — Completed plan 05-02 importer routing, per-field skeleton assignment, and visibility strictness.

## Accumulated Context

- v1.0 shipped core importer. v1.1 focuses on field-preserving imports and verification pipeline (deterministic-first, VLM opt-in).
- Key decisions: VLM opt-in default = false; do not mutate canonical dataset with VLM outputs in v1.1.
- Phase 7 must support Qwen2.5-VL-7B-Instruct via a configurable external OpenAI-compatible adapter endpoint; fallback to installed FiftyOne 1.17 model-zoo Qwen3-VL models must be supported.

## Next Actions

1. Phase 5: complete plan 05-03 additive summary schema validation and finalize preflight artifact checks.
2. Phase 6: implement deterministic cropper, rules engine (detection, attribute, skeleton-count, visibility-format rules), and report exports with PASS/FAIL/REVIEW gating.
3. Phase 7: implement VLM adapter interface with external-adapter option for Qwen2.5, fallback to model-zoo Qwen3-VL models, per-rule prompt templates, aggregation, and report + review queue export.
