# Research Summary: FiftyOne Datumaro Pose Importer

**Date:** 2026-06-11

## Key findings

- **Stack:** Python 3.11 + FiftyOne + Datumaro + typed config validation is the safest v1 path.
- **Table stakes:** config-driven import, accurate image matching, correct keypoint+skeleton mapping, and explicit visibility handling.
- **Architecture:** staged conversion pipeline with canonical intermediate pose model reduces schema and rendering bugs.
- **Main risks:** visibility semantics, keypoint ordering, and skeleton metadata persistence are the most failure-prone areas.

## Recommendations for roadmap

1. Implement strict config and ingestion validation first.
2. Lock a deterministic keypoint/skeleton contract before visualization logic.
3. Build explicit visibility mapping tests (absent/hidden/visible).
4. Add visual QA and diagnostics as first-class deliverables, not optional polish.
