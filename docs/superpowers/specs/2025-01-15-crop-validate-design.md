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
      - Derives bbox from polygon/skeleton/points when bbox field absent
        (reuse _derive_bbox_from_annotation logic from run_verify.py)
      - annotation_type derived from Datumaro type field:
          "bbox"              → "detection"
          "polygon"           → "segmentation"
          "skeleton"/"points" → "skeleton"
        ↓
  [2] Crop each annotation
      - Reuse: cropper.plan_crop + materialize_crop + render_annotation_overlay
      - Detection/segmentation: clipped crop with padding (non_skeleton_clip policy)
      - Skeleton: black-canvas crop preserving spatial context (skeleton_preserve_canvas policy)
      - Output image is the ANNOTATED OVERLAY (bbox/keypoints/polygon drawn on crop)
        — this is the image the VLM will see
        ↓
  [3] Build FiftyOne crop dataset
      - One fo.Sample per annotation crop (filepath = annotated overlay image)
      - Back-reference fields: source_image, source_ann_id, annotation_label, annotation_type
      - Annotation fields in crop-space, coordinates NORMALIZED by crop dimensions [0,1]:
          "detections"           → fo.Detections  (for bbox/detection labels)
          "segmentations"        → fo.Polylines    (for polygon/mask labels)
          "keypoints_label_<id>" → fo.Keypoints    (per skeleton label_id)
      - Dataset skeleton metadata set per keypoints_label_<id> field
      - Dataset name gets a timestamp suffix to avoid collision on repeated runs
        (unless --overwrite-dataset flag is given)
        ↓
  [4] Apply Qwen2.5-VL plugin (VQA mode, grouped by annotation_type)
      - Register plugin once: foz.register_zoo_model_source(PLUGIN_URL)
      - Load model: foz.load_zoo_model(model_name)
      - Set model.operation = "vqa"
      - Run apply_model 3× (one per annotation type), each with a type-specific prompt,
        writing raw VLM text to intermediate "vlm_raw_response" string field
      - Parse vlm_raw_response per sample: extract JSON error_probability + reason
        (re-use JSON-fence regex from vlm_engine.py; fall back to REVIEW on parse failure)
      - Write fo.Classification to "vlm_verdict" field:
          label      = "PASS" / "REVIEW" / "FAIL"
          confidence = error_probability (float 0–1; higher = more likely an error)
      - Risk thresholds: PASS < 0.20 · REVIEW 0.20–0.60 · FAIL ≥ 0.60
      - Delete intermediate "vlm_raw_response" field after parsing
        ↓
  [5] Export Markdown report
      - Output: <output_dir>/report.md
      - Sections: FAIL → REVIEW → PASS (sorted by risk descending within each)
      - Per-row: crop filename, source image, ann ID, label type, risk score, VLM reason
```

---

## FiftyOne Sample Schema

```python
fo.Sample(
    filepath="<output_dir>/crops/<orig_stem>__ann_<id>__<label>.png",  # annotated overlay

    # Back-reference to original source
    source_image     = "frame_001.jpg",       # original image filename
    source_ann_id    = "42",                  # annotation ID from Datumaro (str)
    annotation_label = "forklift-with-roll",  # Datumaro label name
    annotation_type  = "detection",           # "detection" | "segmentation" | "skeleton"

    # Annotation in crop-space — ALL COORDINATES NORMALIZED by crop width/height to [0,1]:
    # (exactly one of these fields populated per sample, depending on annotation_type)
    detections    = fo.Detections([fo.Detection(
        label="forklift-with-roll",
        bounding_box=[x/W, y/H, w/W, h/H],  # FiftyOne format: [x_tl, y_tl, w, h] normalized
    )]),
    # OR
    segmentations = fo.Polylines([fo.Polyline(
        label="roll-mask",
        points=[[[px/W, py/H], ...]],        # FiftyOne format: list of rings, each normalized
        filled=True, closed=True,
    )]),
    # OR
    keypoints_label_2 = fo.Keypoints([fo.Keypoint(
        points=[[kx/W, ky/H], ...],          # normalized; NaN for absent (vis=0) points
    )]),  # field name = "keypoints_label_<datumaro_label_id>"

    # VLM output (written manually after parsing vlm_raw_response):
    vlm_verdict   = fo.Classification(label="PASS", confidence=0.05),
    # confidence = error_probability; higher confidence = higher annotation error risk
)
```

**Skeleton field naming:** Each skeleton `label_id` from Datumaro gets its own `keypoints_label_<id>` field — the same convention as `run_import.py`. Since each crop sample represents exactly one annotation, only one keypoints field is populated per sample. The dataset-level `skeletons` dict maps each field name to its `fo.KeypointSkeleton`.

**Coordinate normalization:** `fo.Detection.bounding_box` and `fo.Polyline.points` require normalized `[0, 1]` coordinates relative to the image dimensions. Since samples are crop images, coordinates are divided by crop width/height (from `crop_plan.output_size`). `fo.Keypoint.points` follows the same normalization (consistent with `run_import.py`).

---

## VLM Prompt Design

Prompts are type-based, with a `LABEL_PROMPTS` dict ready for per-label customization:

```python
DEFAULT_PROMPTS: dict[str, str] = {
    "detection": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with an orange-red bounding box drawn on it.\n"
        "Judge whether the bounding box correctly localizes and covers the '{label}' object.\n"
        "Return ONLY JSON: {\"error_probability\": <float 0-1>, \"reason\": \"<brief reason>\"}"
    ),
    "skeleton": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with colored keypoint dots: green=visible, orange=occluded, gray=unlabeled.\n"
        "Judge whether the keypoints are correctly placed on the '{label}' structure and "
        "whether their visibility codes match the actual occlusion state.\n"
        "Return ONLY JSON: {\"error_probability\": <float 0-1>, \"reason\": \"<brief reason>\"}"
    ),
    "segmentation": (
        "You are validating annotation quality for the '{label}' region.\n"
        "The image shows a crop with a cyan polygon outline drawn on it.\n"
        "Judge whether the polygon correctly outlines the '{label}' region.\n"
        "Return ONLY JSON: {\"error_probability\": <float 0-1>, \"reason\": \"<brief reason>\"}"
    ),
}

# Per-label overrides — add entries here to customize per label (easy to extend):
LABEL_PROMPTS: dict[str, str] = {
    # "forklift-with-roll": "...",
    # "clamp-2-arm": "...",
}
```

At runtime: `LABEL_PROMPTS.get(label) or DEFAULT_PROMPTS[annotation_type]`, with `{label}` substituted.

**VQA grouping strategy:** Since `model.prompt` is a global property (not per-sample) in the plugin API, samples are grouped by annotation type for the `apply_model` calls:

```python
model.operation = "vqa"
for ann_type in ("detection", "segmentation", "skeleton"):
    view = dataset.match(F("annotation_type") == ann_type)
    if len(view) == 0:
        continue
    model.prompt = DEFAULT_PROMPTS[ann_type]   # generic per-type prompt
    view.apply_model(model, label_field="vlm_raw_response")
```

> **Per-label extensibility:** To add per-label prompts in the future, group by `annotation_label` instead of `annotation_type` and set `model.prompt = LABEL_PROMPTS.get(label) or DEFAULT_PROMPTS[ann_type]` per group. No structural change required.

---

## VQA Response Parsing

The plugin's VQA mode returns a raw string. The script parses it:

1. Strip markdown fences (`` ```json ... ``` ``) using the regex from `vlm_engine.py`
2. `json.loads()` the cleaned string
3. Extract `error_probability` (float 0–1) and `reason` (str)
4. On any parse failure → default to `error_probability=None`, verdict=REVIEW, reason="parse_failed"

Verdicts:
| error_probability | vlm_verdict.label |
|---|---|
| < 0.20 | PASS |
| 0.20 – 0.60 | REVIEW |
| ≥ 0.60 | FAIL |
| None (parse fail) | REVIEW |

---

## Markdown Report Structure

```markdown
# Crop Annotation Validation Report
Generated: YYYY-MM-DD HH:MM:SS
Dataset: <dataset_name>
Total crops: N

## Summary
| Verdict | Count |   % |
|---------|------:|----:|
| FAIL    |    12 |  8% |
| REVIEW  |    34 | 23% |
| PASS    |   102 | 69% |

## ❌ FAIL (12)
| # | Crop File | Source Image | Ann ID | Label | Risk | VLM Reason |
|---|-----------|--------------|--------|-------|-----:|------------|
| 1 | frame_001__ann_5__forklift-with-roll.png | frame_001.jpg | 5 | forklift-with-roll | 0.92 | bbox clips left side |

## ⚠️ REVIEW (34)
| # | Crop File | Source Image | Ann ID | Label | Risk | VLM Reason |
...

## ✅ PASS (102)
| # | Crop File | Source Image | Ann ID | Label | Risk | VLM Reason |
...
```

Within each section, rows are sorted by risk descending (worst first).

---

## Output Directory Layout

```
<output_dir>/              # configurable, e.g. ./crop-validate-output/
  crops/
    <orig_stem>__ann_<id>__<label>.png   # annotated overlay crop images
  report.md                              # human-readable Markdown report
```

---

## Configuration (CLI flags)

```
python scripts/crop_validate.py \
  --datumaro-json     ./data/datumaro.json \
  --image-dir         ./data/images \
  --output-dir        ./crop-validate-output \
  --dataset-name      crop_validate_run \
  --model             Qwen/Qwen2.5-VL-7B-Instruct \
  --plugin-source     https://github.com/harpreetsahota204/qwen2_5_vl \
  --padding-px        16 \
  [--persist-dataset]      # keep FiftyOne dataset after run (default: delete)
  [--overwrite-dataset]    # overwrite existing dataset with same name (default: add timestamp suffix)
  [--pass-threshold   0.20]
  [--review-threshold 0.60]
  [--no-vlm]               # skip VLM stage; only crop + build FiftyOne dataset (useful for testing)
```

---

## Key Design Decisions

1. **Reuse `cropper.py` infrastructure** — crop geometry (padding, skeleton canvas) is identical to `run_verify.py`. No duplication.
2. **Annotated overlay as the sample image** — VLM sees drawn annotations (bbox/keypoints/polygon), consistent with the current pipeline.
3. **VQA mode grouped by annotation type** — `model.prompt` is global; grouping by type gives type-specific prompts without iterating samples manually. Per-label extension only requires grouping by label instead.
4. **Intermediate `vlm_raw_response` field** — VQA returns raw text; parsed into `fo.Classification` after the run, then deleted to keep the dataset clean.
5. **Per-label_id skeleton fields** — matches `run_import.py` naming convention; only one field populated per crop sample.
6. **Dataset name timestamp suffix** — avoids collision on repeated runs without requiring `--overwrite-dataset`.
7. **`--no-vlm` flag** — allows testing the crop + FiftyOne dataset build step in isolation without GPU.
8. **Markdown report** — human-readable, easy to read in editor or GitHub. Sorted by risk so worst offenders appear first.

---

## Dependencies

- Python packages: `fiftyone`, `Pillow`, `pyyaml`, `transformers<=4.49.0` (required by Qwen2.5-VL plugin)
- FiftyOne plugin: `https://github.com/harpreetsahota204/qwen2_5_vl` (registered/downloaded on first run)
- Existing modules reused: `datumaro_reader`, `pose_contract`, `image_index`, `matching`, `cropper`, `vlm_engine` (JSON fence regex)

> ⚠️ **transformers version:** The Qwen2.5-VL plugin requires `transformers<=4.49.0` due to a breaking change in 4.50.0. Verify your environment before running.
