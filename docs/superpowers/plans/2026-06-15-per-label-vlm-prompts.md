# Per-Label VLM Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route each annotation crop to a label-specific merged VLM prompt (instead of the current annotation-type-level default), injecting attribute values per-sample for `forklift-with-roll`.

**Architecture:** Three changes to `scripts/crop_validate.py`: (1) store annotation attributes on FiftyOne samples so `_apply_vlm` can read them; (2) populate `LABEL_PROMPTS` with five merged prompts covering all applicable checks per label; (3) refactor `_apply_vlm` to route by `annotation_label` first, with per-sample attribute injection for labels that need it, falling back to `DEFAULT_PROMPTS` for unrecognized labels.

**Tech Stack:** Python 3.11, FiftyOne, pytest (`uv run pytest`), existing `scripts/crop_validate.py` helpers.

**Spec:** `docs/superpowers/specs/2026-06-15-per-label-vlm-prompts-design.md`

---

## File Map

| File | Change |
|---|---|
| `scripts/crop_validate.py` | Add `attributes` param to `_to_fo_sample`; populate `LABEL_PROMPTS`; refactor `_apply_vlm` |
| `tests/crop_validate/test_fo_sample.py` | Add `TestAnnotationAttributes` class |
| `tests/crop_validate/test_integration.py` | Add `annotation_attributes` assertions; add `clamp-type`/`roll-count` to forklift fixture |

---

### Task 1: Store `annotation_attributes` on FiftyOne samples

**Files:**
- Modify: `scripts/crop_validate.py` — `_to_fo_sample` signature + body; `_build_dataset` call site
- Test: `tests/crop_validate/test_fo_sample.py` — add `TestAnnotationAttributes`

- [ ] **Step 1: Write the failing test**

Add this class to `tests/crop_validate/test_fo_sample.py` (after the existing `TestSkeletonSample` class):

```python
class TestAnnotationAttributes:
    def test_attributes_stored_on_sample(self) -> None:
        crop_plan = _make_crop_plan(output_size=(100, 100))
        attrs = {"clamp-type": "3-arm", "roll-count": 2.0, "occluded": False}
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann={"bbox": [0.0, 0.0, 50.0, 50.0]},
            label="forklift-with-roll",
            ann_type="detection",
            source_image="img.jpg",
            ann_id="1",
            label_id=None,
            contract=None,
            attributes=attrs,
        )
        assert sample["annotation_attributes"] == attrs

    def test_attributes_defaults_to_empty_dict_when_omitted(self) -> None:
        crop_plan = _make_crop_plan(output_size=(100, 100))
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann={"bbox": [0.0, 0.0, 50.0, 50.0]},
            label="forklift-no-roll",
            ann_type="detection",
            source_image="img.jpg",
            ann_id="2",
            label_id=None,
            contract=None,
        )
        assert sample["annotation_attributes"] == {}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/crop_validate/test_fo_sample.py::TestAnnotationAttributes -v
```

Expected: FAIL — `_to_fo_sample() got an unexpected keyword argument 'attributes'`

- [ ] **Step 3: Add `attributes` parameter to `_to_fo_sample`**

In `scripts/crop_validate.py`, update the `_to_fo_sample` signature and body. Locate the function starting at line 196 and replace it:

```python
def _to_fo_sample(
    *,
    crop_overlay_path: Path,
    crop_plan: CropPlan,
    crop_space_ann: dict[str, Any],
    label: str,
    ann_type: str,
    source_image: str,
    ann_id: str,
    label_id: int | None,
    contract: SkeletonContract | None,
    attributes: dict[str, Any] | None = None,
) -> fo.Sample:
    """Build a FiftyOne Sample for one annotation crop.

    All annotation coordinates are normalized by crop dimensions (output_size).
    The sample filepath is the annotated overlay image.
    """
    sample = fo.Sample(filepath=str(crop_overlay_path))
    sample["source_image"] = source_image
    sample["source_ann_id"] = ann_id
    sample["annotation_label"] = label
    sample["annotation_type"] = ann_type
    sample["annotation_attributes"] = attributes if attributes is not None else {}
```

(The rest of the function body — detection/segmentation/skeleton branches and `return sample` — is unchanged.)

- [ ] **Step 4: Pass attributes from `_build_dataset`**

In `scripts/crop_validate.py`, locate the `_to_fo_sample(...)` call inside `_build_dataset` (around line 406) and add the `attributes` keyword argument:

```python
            sample = _to_fo_sample(
                crop_overlay_path=overlay_path,
                crop_plan=crop,
                crop_space_ann=crop_space_ann,
                label=label,
                ann_type=ann_type,
                source_image=source_image,
                ann_id=ann_id,
                label_id=label_id if isinstance(label_id, int) else None,
                contract=contract,
                attributes=annotation.get("attributes") or {},
            )
```

- [ ] **Step 5: Run the new tests to verify they pass**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/crop_validate/test_fo_sample.py -v
```

Expected: all tests PASS (including the 5 existing ones and the 2 new ones)

- [ ] **Step 6: Run the full suite to check nothing regressed**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/ -v --tb=short
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
cd /home/longtdang/KMS/vlm && git add scripts/crop_validate.py tests/crop_validate/test_fo_sample.py
git commit -m "feat: store annotation_attributes on FiftyOne samples

Adds attributes dict (clamp-type, roll-count, occluded, etc.) from the
Datumaro annotation payload to each crop sample as annotation_attributes.
Needed for per-label VLM prompt attribute injection.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Populate `LABEL_PROMPTS` with five merged per-label prompts

**Files:**
- Modify: `scripts/crop_validate.py` — replace the placeholder `LABEL_PROMPTS` dict

No new tests needed — these are string constants exercised by Task 3's integration test.

- [ ] **Step 1: Replace the placeholder `LABEL_PROMPTS` constant**

In `scripts/crop_validate.py`, find this block (around line 67):

```python
# Per-label prompt overrides (future use — not yet consulted by _apply_vlm):
LABEL_PROMPTS: dict[str, str] = {
    # "forklift-with-roll": "...",
}
```

Replace it with:

```python
# Per-label merged prompts — one prompt per label covering all applicable checks.
# Prompts may contain {label} and {annotation_fields_json} placeholders.
# {annotation_fields_json} triggers per-sample attribute injection in _apply_vlm.
LABEL_PROMPTS: dict[str, str] = {
    "forklift-with-roll": (
        "You are validating annotation quality for label '{label}'.\n"
        "The image shows a crop with an orange-red bounding box drawn on it"
        " — focus ONLY on that annotated object.\n"
        "Annotation fields:\n"
        "{annotation_fields_json}\n"
        "Evaluate ALL of the following checks and return ONE overall error probability:\n"
        "1. Bbox localization — does the bounding box tightly localize the forklift?\n"
        "2. Bbox coverage — the bounding box must cover the forklift body, the clamp assembly,"
        " AND all paper rolls currently being carried by the clamp."
        " Penalize if any of these are clipped.\n"
        "3. Clamp type — does the clamp-type attribute value match the clamp visually"
        " present in the crop?\n"
        "4. Roll count — does the roll-count attribute value match the number of rolls"
        " visible in the crop?\n"
        "Return ONLY JSON:\n"
        '{"error_probability": <float 0..1>, "reason": "<brief summary of any issues found>"}'
    ),
    "forklift-no-roll": (
        "You are validating annotation quality for label '{label}'.\n"
        "The image shows a crop with an orange-red bounding box drawn on it"
        " — focus ONLY on that annotated object.\n"
        "Evaluate ALL of the following checks and return ONE overall error probability:\n"
        "1. Bbox localization — does the bounding box tightly localize the forklift?\n"
        "2. Bbox coverage — the bounding box must cover the forklift body and clamp assembly"
        " only (no rolls are being carried for this label)."
        " Penalize major clipping or excess background.\n"
        "3. Label correctness — if the forklift is visibly carrying paper rolls,"
        " the label is likely wrong; assign high error probability in that case.\n"
        "Return ONLY JSON:\n"
        '{"error_probability": <float 0..1>, "reason": "<brief summary of any issues found>"}'
    ),
    "clamp-2-arm": (
        "You are validating annotation quality for label '{label}'.\n"
        "The image shows a crop with colored keypoint dots marking structural points"
        " on the '{label}' clamp.\n"
        "Focus ONLY on those dots — ignore any text, stickers, or labels visible in the scene.\n"
        "The keypoint coordinates themselves are assumed to be correct."
        " Do NOT evaluate keypoint position.\n"
        "Only evaluate whether the visibility state (visible, occluded, unlabeled) matches the image.\n"
        "Dot color meaning:\n"
        "  green  = this part of the clamp structure is directly visible in the image\n"
        "  orange = this part of the clamp structure is hidden behind another object (e.g. a roll);"
        " the dot marks where that surface is, even though it is blocked\n"
        "  gray   = this keypoint is unlabeled\n"
        "Important: an orange dot overlapping a roll or another object is CORRECT"
        " — it marks a hidden surface of the '{label}'.\n"
        "Judge whether each dot color matches the actual occlusion state of the"
        " '{label}' structure at that position.\n"
        "Return ONLY JSON:\n"
        '{"error_probability": <float 0..1>, "reason": "<brief reason>"}'
    ),
    "clamp-3-arm": (
        "You are validating annotation quality for label '{label}'.\n"
        "The image shows a crop with colored keypoint dots marking structural points"
        " on the '{label}' clamp.\n"
        "Focus ONLY on those dots — ignore any text, stickers, or labels visible in the scene.\n"
        "The keypoint coordinates themselves are assumed to be correct."
        " Do NOT evaluate keypoint position.\n"
        "Only evaluate whether the visibility state (visible, occluded, unlabeled) matches the image.\n"
        "Dot color meaning:\n"
        "  green  = this part of the clamp structure is directly visible in the image\n"
        "  orange = this part of the clamp structure is hidden behind another object (e.g. a roll);"
        " the dot marks where that surface is, even though it is blocked\n"
        "  gray   = this keypoint is unlabeled\n"
        "Important: an orange dot overlapping a roll or another object is CORRECT"
        " — it marks a hidden surface of the '{label}'.\n"
        "Judge whether each dot color matches the actual occlusion state of the"
        " '{label}' structure at that position.\n"
        "Return ONLY JSON:\n"
        '{"error_probability": <float 0..1>, "reason": "<brief reason>"}'
    ),
    "roll-keypoints": (
        "You are validating annotation quality for label '{label}'.\n"
        "The image shows a crop with colored keypoint dots marking structural points on the roll.\n"
        "Focus ONLY on those dots.\n"
        "The keypoint coordinates themselves are assumed to be correct."
        " Do NOT evaluate keypoint position.\n"
        "Only evaluate whether the visibility state (visible, occluded, unlabeled) matches the image.\n"
        "Dot color meaning:\n"
        "  green  = this part of the roll structure is directly visible in the image\n"
        "  orange = this part of the roll structure is hidden behind another object;"
        " the dot marks where that surface is, even though it is blocked\n"
        "  gray   = this keypoint is unlabeled\n"
        "Important: an orange dot overlapping another object is CORRECT"
        " — it marks a hidden surface of the '{label}'.\n"
        "Judge whether each dot color matches the actual visibility of the"
        " roll structure at that position.\n"
        "Return ONLY JSON:\n"
        '{"error_probability": <float 0..1>, "reason": "<brief reason>"}'
    ),
}
```

- [ ] **Step 2: Verify the constant is importable and contains all 5 labels**

```bash
cd /home/longtdang/KMS/vlm && python -c "
from scripts.crop_validate import LABEL_PROMPTS
assert set(LABEL_PROMPTS.keys()) == {'forklift-with-roll','forklift-no-roll','clamp-2-arm','clamp-3-arm','roll-keypoints'}
assert '{annotation_fields_json}' in LABEL_PROMPTS['forklift-with-roll']
assert '{annotation_fields_json}' not in LABEL_PROMPTS['forklift-no-roll']
assert 'Do NOT evaluate keypoint position' in LABEL_PROMPTS['clamp-2-arm']
assert 'Do NOT evaluate keypoint position' in LABEL_PROMPTS['roll-keypoints']
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd /home/longtdang/KMS/vlm && git add scripts/crop_validate.py
git commit -m "feat: populate LABEL_PROMPTS with five per-label merged prompts

Each prompt covers all applicable checks for that label in a single VLM
call. forklift-with-roll uses {annotation_fields_json} for attribute
injection. Skeleton prompts explicitly exclude keypoint position evaluation.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Refactor `_apply_vlm` to route by label

**Files:**
- Modify: `scripts/crop_validate.py` — `_apply_vlm` function body

- [ ] **Step 1: Replace the type-routing loop in `_apply_vlm`**

In `scripts/crop_validate.py`, locate this block inside `_apply_vlm` (around line 450):

```python
    # Group samples by annotation_type and run apply_model once per type.
    # model.prompt is a global property — we set one prompt per type group.
    # Prompts use "{label}" as a placeholder; at type-level we fill it with
    # the type name (e.g. "detection"). For per-label prompts, group by
    # annotation_label instead and use LABEL_PROMPTS.get(label) overrides.
    for ann_type in ("detection", "segmentation", "skeleton"):
        view = dataset.match(F("annotation_type") == ann_type)
        if len(view) == 0:
            continue
        prompt_template = DEFAULT_PROMPTS[ann_type]
        model.prompt = prompt_template.replace("{label}", ann_type)
        print(f"[crop_validate] Running VQA for {len(view)} '{ann_type}' samples…")
        view.apply_model(model, label_field="vlm_raw_response")
```

Replace it with:

```python
    # Route by annotation_label using LABEL_PROMPTS.
    # Labels with {annotation_fields_json} in their prompt get per-sample
    # attribute injection (each annotation has different attribute values).
    # All other known labels are batched in a single apply_model call.
    # Any label not in LABEL_PROMPTS falls back to DEFAULT_PROMPTS[ann_type].
    processed_labels: set[str] = set()
    for label, prompt_template in LABEL_PROMPTS.items():
        view = dataset.match(F("annotation_label") == label)
        if len(view) == 0:
            continue
        processed_labels.add(label)
        if "{annotation_fields_json}" in prompt_template:
            print(f"[crop_validate] Running per-sample VQA for {len(view)} '{label}' samples…")
            for sample in view.iter_samples(progress=True):
                attrs = sample.get_field("annotation_attributes") or {}
                fields_json = json.dumps({"attributes": attrs}, indent=2)
                model.prompt = (
                    prompt_template
                    .replace("{label}", label)
                    .replace("{annotation_fields_json}", fields_json)
                )
                dataset.select([sample.id]).apply_model(model, label_field="vlm_raw_response")
                sample.reload()
        else:
            model.prompt = prompt_template.replace("{label}", label)
            print(f"[crop_validate] Running VQA for {len(view)} '{label}' samples…")
            view.apply_model(model, label_field="vlm_raw_response")

    # Fallback: labels not covered by LABEL_PROMPTS use DEFAULT_PROMPTS[ann_type]
    if processed_labels:
        remaining = dataset.match(~F("annotation_label").is_in(list(processed_labels)))
    else:
        remaining = dataset
    for ann_type in ("detection", "segmentation", "skeleton"):
        type_view = remaining.match(F("annotation_type") == ann_type)
        if len(type_view) == 0:
            continue
        model.prompt = DEFAULT_PROMPTS[ann_type].replace("{label}", ann_type)
        print(f"[crop_validate] Running VQA for {len(type_view)} '{ann_type}' fallback samples…")
        type_view.apply_model(model, label_field="vlm_raw_response")
```

- [ ] **Step 2: Verify the full test suite still passes**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/ -v --tb=short
```

Expected: all tests PASS (the VLM path is not exercised by tests since `--skip-vlm` is used)

- [ ] **Step 3: Commit**

```bash
cd /home/longtdang/KMS/vlm && git add scripts/crop_validate.py
git commit -m "feat: refactor _apply_vlm to route by annotation label

Samples are now grouped by annotation_label and routed to LABEL_PROMPTS
rather than the generic DEFAULT_PROMPTS[ann_type]. For forklift-with-roll,
attribute values are injected per-sample. Labels not in LABEL_PROMPTS fall
back to DEFAULT_PROMPTS[ann_type] as before.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Update integration tests and verify `annotation_attributes` end-to-end

**Files:**
- Modify: `tests/crop_validate/test_integration.py` — add `annotation_attributes` assertions; enrich forklift fixture with real attributes

- [ ] **Step 1: Update the datumaro fixture with real attributes**

In `tests/crop_validate/test_integration.py`, find the `datumaro_fixture` bbox annotation (the one with `"type": "bbox"`) and update its `attributes` field:

```python
                    {
                        "id": 1,
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [20.0, 15.0, 80.0, 60.0],
                        "attributes": {"clamp-type": "2-arm", "roll-count": 1.0},
                    },
```

- [ ] **Step 2: Add `annotation_attributes` assertions to the first integration test**

In `test_no_vlm_builds_crops_and_report`, find the loop that checks back-reference fields:

```python
        for sample in dataset.iter_samples():
            assert sample.get_field("source_image") == "frame_001.jpg"
            assert sample.get_field("annotation_label") is not None
            assert sample.get_field("annotation_type") in ("detection", "segmentation", "skeleton")
```

Replace it with:

```python
        for sample in dataset.iter_samples():
            assert sample.get_field("source_image") == "frame_001.jpg"
            assert sample.get_field("annotation_label") is not None
            assert sample.get_field("annotation_type") in ("detection", "segmentation", "skeleton")
            # annotation_attributes must always be a dict (may be empty for non-bbox types)
            attrs = sample.get_field("annotation_attributes")
            assert isinstance(attrs, dict)

        # Detection sample carries the clamp-type and roll-count attributes
        for s in dataset.match(fo.ViewField("annotation_label") == "forklift-with-roll").iter_samples():
            attrs = s.get_field("annotation_attributes")
            assert attrs.get("clamp-type") == "2-arm"
            assert attrs.get("roll-count") == 1.0
```

- [ ] **Step 3: Run the integration tests to verify they pass**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/crop_validate/test_integration.py -v --tb=short
```

Expected: both integration tests PASS

- [ ] **Step 4: Run the full suite**

```bash
cd /home/longtdang/KMS/vlm && uv run pytest tests/ -v --tb=short
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/longtdang/KMS/vlm && git add tests/crop_validate/test_integration.py
git commit -m "test: assert annotation_attributes stored correctly end-to-end

Enriches fixture with clamp-type and roll-count attributes.
Asserts annotation_attributes is a dict on every sample, and that
forklift-with-roll samples carry the correct attribute values.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review

**Spec coverage check:**
- [x] `annotation_attributes` stored on samples → Task 1
- [x] `LABEL_PROMPTS` populated with 5 prompts → Task 2
- [x] `_apply_vlm` routes by label → Task 3
- [x] `{annotation_fields_json}` per-sample injection for `forklift-with-roll` → Task 3
- [x] Static batch `apply_model` for non-attribute labels → Task 3
- [x] Fallback to `DEFAULT_PROMPTS` for unknown labels → Task 3
- [x] Skeleton prompts exclude `keypoint_position` evaluation → Task 2 (in prompt text)
- [x] Tests for `annotation_attributes` field → Tasks 1 + 4
- [x] All existing tests continue to pass → verified in each task

**Placeholder scan:** No TBDs, no "implement later", all code blocks complete.

**Type consistency:**
- `_to_fo_sample(..., attributes: dict[str, Any] | None = None)` — default allows existing test calls without `attributes` to still pass
- `sample["annotation_attributes"]` — stored as dict; read back in `_apply_vlm` via `sample.get_field("annotation_attributes") or {}`
- `LABEL_PROMPTS: dict[str, str]` — unchanged type annotation; now populated
- `processed_labels: set[str]` — used in fallback `~F("annotation_label").is_in(list(processed_labels))`
