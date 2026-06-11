# Architecture Research: FiftyOne + Datumaro Pose Importer

**Date:** 2026-06-11

## Recommended architecture

Use a staged pipeline with a canonical intermediate model:

`Config Loader -> Image Indexer -> Datumaro Adapter -> Canonical Pose Model -> Visibility Policy -> FiftyOne Writer -> Validation`

## Component boundaries

- **Config Loader**: validates file paths and runtime options.
- **Image Indexer**: maps image IDs/paths and dimensions.
- **Datumaro Adapter**: parses Datumaro annotations and categories.
- **Canonical Pose Model**: normalizes per-instance points/visibility/attributes.
- **Visibility Policy**: applies absent/hidden/visible mapping contract.
- **FiftyOne Writer**: writes samples/labels and applies skeleton metadata.
- **Validation**: checks cardinality, mismatches, and rendering readiness.

## Build order

1. Config + error model
2. Parsing + image matching
3. Canonical keypoint/skeleton contracts
4. Visibility mapping logic
5. FiftyOne writer integration
6. QA and diagnostics hardening
