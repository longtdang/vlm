# Roadmap: FiftyOne Datumaro Pose Importer

## Overview

Deliver a config-driven local importer that loads images and Datumaro JSON into FiftyOne, preserves pose and visibility semantics, and enables reliable skeleton rendering with clear diagnostics.

## Phases

- [ ] **Phase 1: Configured Ingestion Foundation** - Users can run import from config paths with explicit input validation and matching diagnostics.
- [x] **Phase 2: Pose Contract Mapping** - Users get deterministic keypoint and skeleton conversion with schema safety. (completed 2026-06-12)
- [x] **Phase 3: Visibility Fidelity** - Users retain absent/hidden/visible semantics and audit metadata after import. (completed 2026-06-12)
- [ ] **Phase 4: FiftyOne Viewing and Run Reporting** - Users can view connected skeletons in FiftyOne and review import outcomes.

## Phase Details

### Phase 1: Configured Ingestion Foundation

**Goal**: Users can start imports from config-only inputs and reliably load source images/annotations with clear failures when inputs are invalid.  
**Depends on**: Nothing (first phase)  
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, ING-01, ING-02, ING-03  
**Success Criteria**:

1. User can run importer by setting image-folder and Datumaro-JSON paths in config only.
2. User can set dataset name and label field in config and see these reflected in import output.
3. User gets immediate, clear errors when configured paths are invalid.
4. User sees explicit reporting of unmatched images and annotations.

**Plans**: TBD

### Phase 2: Pose Contract Mapping

**Goal**: Users receive stable and correct keypoint/skeleton mapping from Datumaro into FiftyOne labels.  
**Depends on**: Phase 1  
**Requirements**: POSE-01, POSE-02, POSE-03, OUT-03  
**Success Criteria**:

1. User can inspect imported samples and confirm keypoints are present as FiftyOne labels.
2. User can confirm skeleton edges/structure are applied consistently from source/config contract.
3. User sees stable keypoint ordering aligned with skeleton definitions.
4. User sees import fail fast on schema mismatches before corrupted data is written.

**Plans**: TBD

### Phase 3: Visibility Fidelity

**Goal**: Users can trust visibility semantics from source annotations remain intact and auditable after import.  
**Depends on**: Phase 2  
**Requirements**: VIS-01, VIS-02, VIS-03  
**Success Criteria**:

1. User observes absent keypoints as non-rendered points in FiftyOne-compatible output.
2. User can distinguish hidden vs visible keypoints after import.
3. User can inspect preserved source visibility metadata.

**Plans**: `03-01-PLAN.md`, `03-02-PLAN.md`, `03-03-PLAN.md`

### Phase 4: FiftyOne Viewing and Run Reporting

**Goal**: Users can open the dataset in FiftyOne, view connected skeleton rendering, and review import quality summaries.  
**Depends on**: Phase 3  
**Requirements**: OUT-01, OUT-02  
**Success Criteria**:

1. User can open imported dataset in FiftyOne and view connected skeleton rendering.
2. User receives run summary including sample counts, label counts, warnings, and failures.

**Plans**: `04-01-PLAN.md`, `04-02-PLAN.md`  
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Configured Ingestion Foundation | 0/TBD | Not started | - |
| 2. Pose Contract Mapping | 2/2 | Complete   | 2026-06-12 |
| 3. Visibility Fidelity | 3/3 | Complete | 2026-06-12 |
| 4. FiftyOne Viewing and Run Reporting | 2/2 | Planned | - |
