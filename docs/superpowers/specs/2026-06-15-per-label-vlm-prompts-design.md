# Per-Label VLM Prompts for crop_validate

**Date:** 2026-06-15
**Status:** Approved

## Problem

`_apply_vlm` in `scripts/crop_validate.py` currently routes all annotations of the same type (detection / skeleton) through a single generic `DEFAULT_PROMPTS[ann_type]` prompt. This ignores:
- Label-specific annotation semantics (e.g., a `forklift-with-roll` box also needs clamp-type and roll-count verification)
- Attribute values stored in the Datumaro JSON (e.g., `{"clamp-type": "3-arm", "roll-count": 1.0}`)
- The distinction between `keypoint_position` (deferred) and `occlusion_state` checks for skeleton labels

## Goal

Route each annotation crop to a merged, label-specific VLM prompt derived from `config.import-vlm.example.yaml`, injecting annotation attribute values where needed, so the VLM evaluates the right checks for each label type.

---

## Labels and Checks

| Label | Annotation Type | Checks Included | Attribute Injection |
|---|---|---|---|
| `forklift-with-roll` | detection | bbox localization, bbox coverage, clamp-type, roll-count | Yes — `clamp-type`, `roll-count` |
| `forklift-no-roll` | detection | bbox localization, bbox coverage | No |
| `clamp-2-arm` | skeleton | occlusion_state | No |
| `clamp-3-arm` | skeleton | occlusion_state | No |
| `roll-keypoints` | skeleton | occlusion_state | No |
| `clamp-mask` | segmentation | — (disabled) | — |
| `roll-mask` | segmentation | — (disabled) | — |

`keypoint_position` is intentionally deferred for all skeleton labels — to be defined by the user later.

---

## Architecture

### 1. `LABEL_PROMPTS` constant

Replace the placeholder `LABEL_PROMPTS: dict[str, str] = {}` with five populated entries.

Each prompt is a single string covering all applicable checks for that label. Prompts may contain:
- `{label}` — substituted at runtime with the annotation label name
- `{annotation_fields_json}` — substituted with a JSON string of annotation attributes (only for labels that need it)

Prompts that do NOT use `{annotation_fields_json}` are "static" — the same text is sent for every sample of that label.

### 2. `annotation_attributes` field on FiftyOne samples

`_build_dataset` passes `annotation.get("attributes", {})` through `_to_fo_sample` and stores it as a FiftyOne field (`sample["annotation_attributes"]`). This makes attributes available to `_apply_vlm` without re-reading the Datumaro JSON.

Type: `fo.DictField` (dict stored as-is on the sample).

### 3. `_apply_vlm` refactor

New routing logic:

```
for label, prompt_template in LABEL_PROMPTS.items():
    view = dataset.match(F("annotation_label") == label)
    if empty: skip

    if "{annotation_fields_json}" in prompt_template:
        # Per-sample loop — each annotation has different attribute values
        for sample in view.iter_samples():
            attrs = sample["annotation_attributes"] or {}
            fields_json = json.dumps({"attributes": attrs}, indent=2)
            model.prompt = prompt_template
                .replace("{label}", label)
                .replace("{annotation_fields_json}", fields_json)
            dataset.select([sample.id]).apply_model(model, label_field="vlm_raw_response")
    else:
        # Static prompt — batch the full label view in one apply_model call
        model.prompt = prompt_template.replace("{label}", label)
        view.apply_model(model, label_field="vlm_raw_response")

# Fallback for any label not in LABEL_PROMPTS
remaining = dataset.match(~F("annotation_label").is_in(list(LABEL_PROMPTS.keys())))
for ann_type in ("detection", "segmentation", "skeleton"):
    type_view = remaining.match(F("annotation_type") == ann_type)
    if empty: skip
    model.prompt = DEFAULT_PROMPTS[ann_type].replace("{label}", ann_type)
    type_view.apply_model(model, label_field="vlm_raw_response")
```

The remainder of `_apply_vlm` (parsing raw responses, writing `vlm_verdict`, cleanup) is unchanged.

---

## Prompt Specifications

### `forklift-with-roll`

```
You are validating annotation quality for label '{label}'.
The image shows a crop with an orange-red bounding box drawn on it — focus ONLY on that annotated object.
Annotation fields:
{annotation_fields_json}
Evaluate ALL of the following checks and return ONE overall error probability:
1. Bbox localization — does the bounding box tightly localize the forklift?
2. Bbox coverage — the bounding box must cover the forklift body, the clamp assembly, AND all
   paper rolls currently being carried by the clamp. Penalize if any of these are clipped.
3. Clamp type — does the clamp-type attribute value match the clamp visually present in the crop?
4. Roll count — does the roll-count attribute value match the number of rolls visible in the crop?
Return ONLY JSON:
{"error_probability": <float 0..1>, "reason": "<brief summary of any issues found>"}
```

### `forklift-no-roll`

```
You are validating annotation quality for label '{label}'.
The image shows a crop with an orange-red bounding box drawn on it — focus ONLY on that annotated object.
Evaluate ALL of the following checks and return ONE overall error probability:
1. Bbox localization — does the bounding box tightly localize the forklift?
2. Bbox coverage — the bounding box must cover the forklift body and clamp assembly only (no rolls
   are being carried for this label). Penalize major clipping or excess background.
3. Label correctness — if the forklift is visibly carrying paper rolls, the label is likely wrong;
   assign high error probability in that case.
Return ONLY JSON:
{"error_probability": <float 0..1>, "reason": "<brief summary of any issues found>"}
```

### `clamp-2-arm`

```
You are validating annotation quality for label '{label}'.
The image shows a crop with colored keypoint dots marking structural points on the '{label}' clamp.
Focus ONLY on those dots — ignore any text, stickers, or labels visible in the scene.
The keypoint coordinates themselves are assumed to be correct. Do NOT evaluate keypoint position.
Only evaluate whether the visibility state (visible, occluded, unlabeled) matches the image.
Dot color meaning:
  green  = this part of the clamp structure is directly visible in the image
  orange = this part of the clamp structure is hidden behind another object (e.g. a roll);
           the dot marks where that surface is, even though it is blocked
  gray   = this keypoint is unlabeled
Important: an orange dot overlapping a roll or another object is CORRECT — it marks a hidden surface of the '{label}'.
Judge whether each dot color matches the actual occlusion state of the '{label}' structure at that position.
Return ONLY JSON:
{"error_probability": <float 0..1>, "reason": "<brief reason>"}
```

### `clamp-3-arm`

Same structure as `clamp-2-arm` (identical prompt text — `{label}` fills in the difference).

### `roll-keypoints`

```
You are validating annotation quality for label '{label}'.
The image shows a crop with colored keypoint dots marking structural points on the roll.
Focus ONLY on those dots.
The keypoint coordinates themselves are assumed to be correct. Do NOT evaluate keypoint position.
Only evaluate whether the visibility state (visible, occluded, unlabeled) matches the image.
Dot color meaning:
  green  = this part of the roll structure is directly visible in the image
  orange = this part of the roll structure is hidden behind another object;
           the dot marks where that surface is, even though it is blocked
  gray   = this keypoint is unlabeled
Important: an orange dot overlapping another object is CORRECT — it marks a hidden surface of the '{label}'.
Judge whether each dot color matches the actual visibility of the roll structure at that position.
Return ONLY JSON:
{"error_probability": <float 0..1>, "reason": "<brief reason>"}
```

---

## Data Flow

```
Datumaro JSON
    │
    ▼
_build_dataset
    ├── annotation.get("attributes") ──► sample["annotation_attributes"]  (new)
    └── existing fields (annotation_label, annotation_type, …)
    │
    ▼
_apply_vlm
    ├── route by annotation_label → LABEL_PROMPTS[label]
    │     ├── forklift-with-roll → per-sample loop (inject attributes)
    │     ├── forklift-no-roll   → batch apply_model (static prompt)
    │     ├── clamp-2-arm        → batch apply_model (static prompt)
    │     ├── clamp-3-arm        → batch apply_model (static prompt)
    │     └── roll-keypoints     → batch apply_model (static prompt)
    └── remaining labels → DEFAULT_PROMPTS[ann_type] (unchanged fallback)
    │
    ▼
Parse vlm_raw_response → vlm_verdict (fo.Classification) + vlm_reason
    │
    ▼
_write_report (unchanged)
```

---

## Testing

1. **`test_helpers.py`** — no changes needed
2. **`test_vlm_parse.py`** — no changes needed
3. **`test_fo_sample.py`** — add: `annotation_attributes` field is populated correctly
4. **`test_integration.py`** — add: with `--skip-vlm`, `annotation_attributes` present on samples
5. **New assertion in integration test**: forklift-with-roll prompt renders `{annotation_fields_json}` with attribute dict from the sample

All existing 68 tests must continue to pass.

---

## Affected Files

| File | Change |
|---|---|
| `scripts/crop_validate.py` | Populate `LABEL_PROMPTS`, add `annotation_attributes` to `_to_fo_sample` + `_build_dataset`, refactor `_apply_vlm` |
| `tests/crop_validate/test_fo_sample.py` | Add assertion for `annotation_attributes` field |
| `tests/crop_validate/test_integration.py` | Add assertion for `annotation_attributes` on dataset samples |
