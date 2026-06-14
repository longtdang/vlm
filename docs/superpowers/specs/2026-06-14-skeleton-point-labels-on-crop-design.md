# Design: Skeleton Point Name Labels on Crop Images

**Date:** 2026-06-14  
**Status:** Approved  
**Scope:** `cropper.py` (rendering) + `run_verify.py` (data flow)

---

## Problem

When the VLM verification pipeline crops images with skeleton annotations, it draws
color-coded dots for each keypoint but provides no visual indication of which anatomical
point each dot represents. This makes it hard to inspect crops and debug labeling issues.

## Goal

Render the skeleton point names (e.g. "nose", "left_eye", "right_shoulder") as text
labels directly above each keypoint dot in the crop overlay image.

---

## Architecture

The change touches two files:

### 1. `src/fiftyone_pose_importer/run_verify.py`

**Extract skeleton labels** from the loaded Datumaro JSON (`data`) using the existing
`extract_skeleton_contract_bundle` helper. For multi-skeleton datasets, select the
contract matching the annotation's `label_id`; fall back to the bundle's `default`
contract if no per-label contract exists.

**Inject `point_names`** into the `annotation_payload` dict before it is passed to
`render_annotation_overlay`. If no contract is available (e.g., non-skeleton annotation
type), `point_names` is omitted or set to `None` — the renderer handles absence gracefully.

```python
annotation_payload = {
    "bbox": ...,
    "keypoints": keypoints,
    "visibility": ...,
    "polygon_points": ...,
    "out_of_frame_indices": ...,
    "point_names": skeleton_labels,   # list[str] | None
}
```

### 2. `src/fiftyone_pose_importer/verification/cropper.py`

**`render_annotation_overlay`** — in the skeleton branch (where `keypoints` is drawn),
after drawing each dot, draw the corresponding point name label:

- Read `point_names = annotation_crop_space.get("point_names")` (list or None)
- For each keypoint at index `idx`: if `point_names` is a list and `idx < len(point_names)`,
  draw the label text above the dot
- Position: `(kx, ky - radius - 2)` — 2 px gap above the dot top edge
- Render a 1 px black shadow offset (+1, +1) then white foreground text
- Font: PIL default bitmap font (no external file dependency)
- If `point_names` is absent, `None`, or empty, rendering proceeds unchanged (dots only)

---

## Data Flow

```
data (Datumaro JSON)
  └── extract_skeleton_contract_bundle(data)
        └── SkeletonContractBundle
              ├── .default: SkeletonContract | None
              └── .by_label_id: dict[int, SkeletonContract]

For each annotation:
  label_id → SkeletonContract → .labels: list[str]
  → annotation_payload["point_names"] = labels
  → annotation_to_crop_space(annotation_payload, crop)
  → render_annotation_overlay(..., annotation_crop_space)
       → draw dots + text labels
```

---

## Error Handling

- If `extract_skeleton_contract_bundle` raises (malformed or missing categories), catch
  the exception in `run_verify.py` and set `skeleton_labels = None`. The crop still
  renders without labels.
- If label count doesn't match keypoint count (truncated list), draw labels only for
  the indices that exist — never raise on mismatch.
- Non-skeleton annotation types (polygon, bbox) are unaffected.

---

## Testing

- Add test to `tests/phase6/test_cropper.py`: `render_annotation_overlay` with
  `point_names` in the annotation renders text above each keypoint. Verify pixel
  changes occur at expected label positions (pixel count increases vs no-label baseline).
- Add test: missing/`None` `point_names` → dots drawn, no error.
- Add test: `point_names` shorter than `keypoints` → labels only for matching indices.

---

## Non-Goals

- No font size configurability (use PIL default for now).
- No label color configurability.
- No label position configurability beyond "above the dot".
- No changes to VLM prompt text or JSON payloads sent to the model.
