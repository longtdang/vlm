# Design: Crop-Based Annotation Validation with Qwen2.5-VL Plugin

**Date:** 2025-01-15  
**Status:** Approved  
**Script:** `scripts/crop_validate.py`

---

## Problem Statement

The existing `run_import.py` loads full images with all annotations into FiftyOne. The existing `run_verify.py` crops each annotation and runs a custom VLM adapter for validation. However, there is no workflow where **each annotation crop becomes its own FiftyOne sample** that can be browsed visually and validated using the **official Qwen2.5-VL FiftyOne model zoo plugin**.

This script fills that gap: it creates a crop-first FiftyOne dataset, applies the Qwen2.5-VL plugin to each crop, and exports a human-readable Markdown report for manual annotation review.

---

## Pipeline Architecture

```
Datumaro JSON + Images
        ↓
  [1] Parse annotations
      - Reuse: datumaro_reader, pose_contract, image_index, matching
      - Derives bbox from polygon/skeleton when bbox field absent
        ↓
  [2] Crop each annotation
      - Reuse: cropper.plan_crop + materialize_crop + render_annotation_overlay
      - Detection/segmentation: clipped crop with padding
      - Skeleton: black-canvas crop preserving spatial context
      - Overlay drawn on crop (bbox=orange-red rect, keypoints=colored dots, polygon=cyan)
        ↓
  [3] Build FiftyOne crop dataset
      - One fo.Sample per annotation crop
      - Back-reference fields: source_image, source_ann_id, annotation_label, annotation_type
      - Annotation fields in crop-space coordinates:
          detections field       → fo.Detections  (for forklift-* labels)
          segmentations field    → fo.Polylines    (for mask labels)
          keypoints_label_<id>   → fo.Keypoints    (per skeleton label_id, matching run_import.py convention)
      - Dataset skeleton metadata set per keypoints_label_<id> field
        ↓
  [4] Apply Qwen2.5-VL plugin
      - foz.load_zoo_model("Qwen/Qwen2.5-VL-7B-Instruct", source=PLUGIN_URL)
      - Per-crop prompt built from annotation_type and annotation_label
      - VLM output parsed into fo.Classification on "vlm_verdict" field:
          label      = "PASS" / "REVIEW" / "FAIL"
          confidence = risk score (float 0–1)
      - Risk thresholds: PASS < 0.20, REVIEW < 0.60, FAIL >= 0.60
        ↓
  [5] Export Markdown report
      - Output: <output_dir>/report.md
      - Sections: FAIL → REVIEW → PASS (sorted by risk descending within each)
      - Per-row: crop filename, source image, ann ID, label, risk score, VLM reason
```

---

## FiftyOne Sample Schema

```python
fo.Sample(
    filepath="<output_dir>/crops/<orig_stem>__ann_<id>__<label>.png",

    # Back-reference to original source
    source_image     = "frame_001.jpg",       # original image filename
    source_ann_id    = "42",                  # annotation ID from Datumaro
    annotation_label = "forklift-with-roll",  # Datumaro label name
    annotation_type  = "detection",           # "detection" | "segmentation" | "skeleton"

    # Annotation in crop-space (one of these, depending on type):
    detections       = fo.Detections([fo.Detection(label="forklift-with-roll", bounding_box=[...])]),
    # OR
    segmentations    = fo.Polylines([fo.Polyline(label="roll-mask", points=[[...]])]),
    # OR
    keypoints_label_2 = fo.Keypoints([fo.Keypoint(points=[...])]),  # field name varies by label_id

    # VLM output (written by apply_model):
    vlm_verdict      = fo.Classification(label="PASS", confidence=0.05),
)
```

**Skeleton field naming:** Each skeleton label_id gets its own `keypoints_label_<id>` field — the same convention used by `run_import.py`. Since each crop sample contains exactly one annotation, only one keypoints field is populated per sample. The dataset-level `skeletons` metadata dict maps each field name to its `fo.KeypointSkeleton`.

---

## VLM Prompt Design

Prompts are type-based with easy per-label extensibility. The script contains a `PROMPTS` dict:

```python
DEFAULT_PROMPTS = {
    "detection": "...",
    "segmentation": "...",
    "skeleton": "...",
}

# Future per-label overrides (easy to add):
LABEL_PROMPTS = {
    # "forklift-with-roll": "...",
}
```

At runtime: if `LABEL_PROMPTS.get(label)` exists, use it; else fall back to `DEFAULT_PROMPTS[annotation_type]`.

Default templates (VLM sees the annotated overlay image):
- **detection**: "Is the orange-red bounding box correctly placed and sized around the `{label}` object in this crop? Return JSON: {\"error_probability\": <0..1>, \"reason\": \"<brief>\"}"
- **skeleton**: "Are the colored keypoint dots correctly placed on the `{label}` structure? Green=visible, orange=occluded, gray=unlabeled. Return JSON: {\"error_probability\": <0..1>, \"reason\": \"<brief>\"}"
- **segmentation**: "Does the cyan polygon correctly outline the `{label}` region in this crop? Return JSON: {\"error_probability\": <0..1>, \"reason\": \"<brief>\"}"

VLM response is parsed for `error_probability` (float 0–1). Risk thresholds map to verdict:
- `< 0.20` → PASS
- `0.20–0.60` → REVIEW
- `> 0.60` → FAIL

---

## Markdown Report Structure

```markdown
# Crop Annotation Validation Report
Generated: YYYY-MM-DD HH:MM:SS
Dataset: <dataset_name>
Total crops: N

## Summary
| Verdict | Count | % |
...

## ❌ FAIL (N)
| # | Crop File | Source Image | Ann ID | Label | Risk | VLM Reason |
...

## ⚠️ REVIEW (N)
...

## ✅ PASS (N)
...
```

Within each section, rows sorted by risk descending (highest risk first for FAIL/REVIEW).

---

## Output Directory Layout

```
<output_dir>/              # configurable, e.g. ./crop-validate-output/
  crops/
    <stem>__ann_<id>__<label>.png   # annotated crop images (overlay drawn)
  report.md                         # human-readable Markdown report
```

---

## Configuration (CLI flags)

```
python scripts/crop_validate.py \
  --datumaro-json ./data/datumaro.json \
  --image-dir     ./data/images \
  --output-dir    ./crop-validate-output \
  --dataset-name  crop_validate_run \
  --model         Qwen/Qwen2.5-VL-7B-Instruct \
  --plugin-source https://github.com/harpreetsahota204/qwen2_5_vl \
  --padding-px    16 \
  [--persist-dataset]   # keep FiftyOne dataset after run (default: delete)
  [--pass-threshold  0.20]
  [--review-threshold 0.60]
```

---

## Key Design Decisions

1. **Reuse `cropper.py` infrastructure** — ensures crop geometry (padding, skeleton canvas) is identical to `run_verify.py`. No duplication.
2. **Annotated overlay as the crop image** — VLM sees drawn annotations, same as current VLM pipeline.
3. **Per-label_id skeleton fields** — matches `run_import.py` naming convention, enabling cross-comparison if needed.
4. **Simple prompt dict now, extensible later** — `DEFAULT_PROMPTS` + `LABEL_PROMPTS` dict. Adding per-label prompts requires changing one dict.
5. **FiftyOne ephemeral by default** — avoids dataset accumulation; `--persist-dataset` flag retains for app browsing.
6. **Markdown report over CSV** — human-readable, easy to read in editor or GitHub. Sorted by risk so worst offenders are at the top.

---

## Dependencies

- Python packages: `fiftyone`, `Pillow` (already used), `pyyaml` (already used)
- FiftyOne plugin: `https://github.com/harpreetsahota204/qwen2_5_vl` (auto-downloaded on first run)
- Existing modules: `datumaro_reader`, `pose_contract`, `image_index`, `matching`, `cropper`
