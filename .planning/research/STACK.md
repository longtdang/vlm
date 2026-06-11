# Stack Research: FiftyOne + Datumaro Pose Importer

**Date:** 2026-06-11

## Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | Python 3.11 | Best compatibility for FiftyOne/Datumaro ecosystem |
| Dataset + Visualization | `fiftyone` | Native keypoint and skeleton rendering in app |
| Annotation parsing | `datumaro` | Reliable handling of CVAT-exported Datumaro schema |
| Config validation | `pydantic` + `pyyaml` | Typed config for image/datumaro paths and import options |
| CLI | `typer` | Simple command entrypoint for local workflows |
| Tests | `pytest` | Regression coverage for mapping/visibility semantics |

## Critical mapping contract

1. Datumaro visibility states: `0=absent`, `1=hidden`, `2=visible`.
2. For FiftyOne rendering, absent points should map to `NaN` coordinates.
3. Preserve original visibility values as per-point metadata (do not overload confidence as visibility).
4. Apply explicit `KeypointSkeleton` labels/edges from source categories to ensure stable rendering.

## Avoid

- Ad-hoc JSON-only parsing without Datumaro model checks.
- Treating hidden and absent as identical states.
- Dropping missing joints instead of preserving index alignment.
