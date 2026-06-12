# FiftyOne Datumaro Pose Importer

## What This Is

A local utility project to load an image folder and a Datumaro JSON export (from CVAT frame export) into FiftyOne. It creates a dataset that correctly renders pose/keypoint skeletons with proper keypoint visibility handling. It is designed for single-user, config-driven usage in a local workflow.

## Core Value

Given only config paths, the project reliably imports and visualizes CVAT/Datumaro pose annotations in FiftyOne with correct skeleton visibility behavior.

## Requirements

### Validated

- CONF-01/02/03/04, ING-01/02/03, POSE-01/02/03, VIS-01/02/03, OUT-01/02/03 (v1.0 shipped)

### Active

- [ ] Load images from a configured image folder path into a FiftyOne dataset
- [ ] Load Datumaro annotations from a configured Datumaro JSON path
- [ ] Map Datumaro keypoint/pose annotations to FiftyOne label structures
- [ ] Configure and apply skeleton metadata so keypoints render as connected skeletons
- [ ] Correctly preserve and render visibility/occlusion semantics for skeleton keypoints
- [ ] Provide a config file that accepts image-folder link/path and Datumaro-JSON link/path

### Out of Scope

- Multi-user auth, permissions, and hosted service deployment — v1 is local single-user
- Full annotation editing UI/workflow replacement for CVAT — v1 focuses on import + visualization

## Context

- Primary stack target is FiftyOne with Python-based data loading.
- Source annotations come from Datumaro JSON exported from CVAT frame workflows.
- A known risk area is keypoint visibility semantics (visible/occluded/not-labeled) and how those map to FiftyOne rendering behavior.
- Configuration-first operation is required so users can quickly swap datasets by changing paths.

## Constraints

- **Runtime**: Must work in local environment — single-user development flow
- **Data Input**: Must support Datumaro JSON from CVAT exports — this is the required source format
- **Usability**: Config-first setup — no hardcoded paths in import logic
- **Visualization Correctness**: Skeleton visibility semantics must be preserved — incorrect visibility undermines dataset trust

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build a config-driven importer as the v1 scope | User needs repeatable local imports by changing paths only | — Pending |
| Prioritize skeleton visibility correctness as a core requirement | Rendering correctness is explicitly critical for this workflow | — Pending |
| Focus on CVAT-exported Datumaro JSON first | This is the concrete data source already in use | — Pending |

## Current State

- **Shipped milestone:** v1.0
- **Archive roadmap:** `.planning/milestones/v1.0-ROADMAP.md`
- **Archive requirements:** `.planning/milestones/v1.0-REQUIREMENTS.md`
- **Milestone audit:** `.planning/v1.0-v1.0-MILESTONE-AUDIT.md` (`complete_with_warnings`)

## Next Milestone Goals

- Define new scope and requirements with `/gsd-new-milestone`.
- Carry forward operational warning: keep a canonicalized known-good dataset fixture for manual visibility UAT.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-12 after v1.0 completion*
