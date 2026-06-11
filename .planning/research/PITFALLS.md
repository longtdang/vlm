# Pitfalls Research: FiftyOne + Datumaro Pose Importer

**Date:** 2026-06-11

## High-risk pitfalls

| Pitfall | Warning signs | Prevention | Phase |
|---|---|---|---|
| Coordinate mismatch (pixel vs normalized) | points render off-image or collapsed | normalize using real image width/height and bounds checks | 1 |
| Wrong visibility mapping | hidden/absent semantics disappear | map 0/1/2 explicitly and keep source visibility metadata | 1 |
| Skeleton index/order mismatch | incorrect bone connections | enforce canonical keypoint order and pad with NaN for missing points | 2 |
| Skeleton metadata missing/not persisted | dots render without skeleton edges | set field skeleton and persist dataset metadata | 2 |
| Image-annotation matching errors | high unmatched counts or wrong overlays | deterministic matching strategy + strict mismatch report | 1 |
| Person-instance grouping loss | wrong person counts per image | preserve group/object identity when building Keypoints | 2 |

## Acceptance risks to test explicitly

- Dataset opens with skeleton connections visible in FiftyOne app.
- Absent points are non-rendered while hidden points remain semantically distinguishable.
- Sample cardinality and keypoint lengths match expected skeleton labels.
