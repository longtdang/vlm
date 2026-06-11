# Features Research: FiftyOne + Datumaro Pose Importer

**Date:** 2026-06-11

## Table stakes

- Config-driven import (image folder path + Datumaro JSON path)
- Deterministic image-to-annotation matching with mismatch reporting
- Correct conversion to FiftyOne keypoint labels
- Skeleton metadata setup so connected skeletons render in app
- Visibility/occlusion-preserving mapping
- Clear import summary (counts, warnings, errors)

## Differentiators

- Dry-run mode before writing datasets
- QA report for per-joint missing/hidden distributions
- Incremental re-import with provenance tags
- Auto-generated debug views for problematic samples

## Anti-features (for v1)

- Annotation editing UI (CVAT replacement)
- Generic all-format conversion platform
- Multi-user/cloud orchestration
- End-to-end model training pipeline

## Dependency flow

Config -> Parse Datumaro -> Match images -> Map keypoints -> Apply skeleton/visibility -> Write dataset -> Validate/report
