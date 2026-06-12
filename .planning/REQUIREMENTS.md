# Requirements: FiftyOne Datumaro Pose Importer

**Defined:** 2026-06-11  
**Core Value:** Given only config paths, reliably import and visualize CVAT/Datumaro pose annotations in FiftyOne with correct skeleton visibility behavior.

## v1 Requirements

### Configuration

- [x] **CONF-01**: User can provide image-folder path in a config file
- [x] **CONF-02**: User can provide Datumaro JSON path in a config file
- [x] **CONF-03**: User can provide dataset name and label field settings in config
- [x] **CONF-04**: Import run fails with clear errors when configured paths are invalid

### Ingestion

- [x] **ING-01**: User can load all images from configured image folder into FiftyOne samples
- [x] **ING-02**: User can load Datumaro annotations from configured JSON file
- [x] **ING-03**: Import process reports unmatched images/annotations explicitly

### Pose Mapping

- [x] **POSE-01**: User gets keypoints converted from Datumaro to FiftyOne keypoint labels
- [x] **POSE-02**: User gets skeleton labels/edges applied from source or config contract
- [x] **POSE-03**: User gets stable keypoint ordering aligned with skeleton definition

### Visibility Semantics

- [x] **VIS-01**: Absent keypoints are represented as non-rendered points in FiftyOne-compatible form
- [x] **VIS-02**: Hidden vs visible keypoints remain distinguishable after import
- [x] **VIS-03**: Source visibility values are preserved as metadata for auditability

### Dataset Output and Validation

- [x] **OUT-01**: User can open imported dataset in FiftyOne and see connected skeleton rendering
- [x] **OUT-02**: Import outputs a summary of samples, labels, warnings, and failures
- [x] **OUT-03**: Import fails fast on schema mismatches that would corrupt rendering semantics

## v2 Requirements

### Enhanced Workflow

- **ENH-01**: User can run dry-run mode without persisting dataset writes
- **ENH-02**: User can generate per-joint QA statistics and anomaly summaries
- **ENH-03**: User can perform incremental re-import/merge with provenance tracking
- **ENH-04**: User can auto-generate debug views in FiftyOne for problematic samples

## Out of Scope

| Feature | Reason |
|---------|--------|
| CVAT-like annotation editing interface | Not required for v1 import/render objective |
| Cloud/multi-user orchestration | v1 is explicitly local single-user |
| Generic all-format conversion platform | v1 is scoped to Datumaro JSON from CVAT |
| Model training/serving pipeline integration | Not needed to validate import/render core value |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| CONF-04 | Phase 1 | Complete |
| ING-01 | Phase 1 | Complete |
| ING-02 | Phase 1 | Complete |
| ING-03 | Phase 1 | Complete |
| POSE-01 | Phase 2 | Complete |
| POSE-02 | Phase 2 | Complete |
| POSE-03 | Phase 2 | Complete |
| VIS-01 | Phase 3 | Complete |
| VIS-02 | Phase 3 | Complete (manual flow data-blockable) |
| VIS-03 | Phase 3 | Complete |
| OUT-01 | Phase 4 | Complete |
| OUT-02 | Phase 4 | Complete |
| OUT-03 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✅

---
*Requirements defined: 2026-06-11*  
*Last updated: 2026-06-12 after milestone traceability verification*
