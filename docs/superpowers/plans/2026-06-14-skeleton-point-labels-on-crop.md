# Skeleton Point Name Labels on Crop Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw skeleton point names (e.g. "nose", "left_eye") as text labels above each keypoint dot when rendering annotation overlays on cropped images.

**Architecture:** Add `point_names: list[str] | None` to the `annotation_payload` dict in `run_verify.py` by extracting it from the Datumaro skeleton contract. `render_annotation_overlay` in `cropper.py` reads this optional field and draws white text with a black shadow above each dot — no change to function signatures.

**Tech Stack:** Python, Pillow (PIL) — `ImageDraw.text()` for label rendering.

---

## File Map

| File | Change |
|---|---|
| `src/fiftyone_pose_importer/verification/cropper.py` | Add text label rendering in skeleton branch of `render_annotation_overlay` |
| `src/fiftyone_pose_importer/run_verify.py` | Import `extract_skeleton_contract_bundle`, extract labels, add `point_names` to `annotation_payload` |
| `tests/phase6/test_cropper.py` | Add 3 tests for label rendering |
| `tests/phase6/test_run_verify.py` | Add / extend test verifying `point_names` flows into `annotation_payload` |

---

### Task 1: Add label rendering to `render_annotation_overlay`

**Files:**
- Modify: `src/fiftyone_pose_importer/verification/cropper.py` (skeleton branch, lines 252–262)
- Test: `tests/phase6/test_cropper.py`

- [ ] **Step 1.1: Write the failing test — labels appear above dots when `point_names` provided**

Add to `tests/phase6/test_cropper.py`:

```python
def test_render_annotation_overlay_keypoints_with_point_names(tmp_path: Path) -> None:
    """Point names are rendered as text labels above each keypoint dot."""
    source = tmp_path / "crop.png"
    # White canvas so any non-white pixel == something was drawn
    Image.new("RGB", (200, 200), (255, 255, 255)).save(source)

    annotation = {
        "keypoints": [[50.0, 100.0], [150.0, 100.0]],
        "visibility": [2, 2],
        "point_names": ["nose", "left_eye"],
        "polygon_points": None,
        "bbox": None,
    }
    out = tmp_path / "labeled.png"
    render_annotation_overlay(source, annotation, out)

    img = Image.open(out)
    # Pixels directly above the first dot (kx=50, ky=100 - radius - label height)
    # must differ from the white background — text was drawn there.
    label_area_pixels = [img.getpixel((x, y)) for x in range(40, 70) for y in range(75, 95)]
    non_white = [p for p in label_area_pixels if p != (255, 255, 255)]
    assert len(non_white) > 0, "Expected text pixels above the first keypoint dot"
```

- [ ] **Step 1.2: Run to confirm the test fails**

```bash
cd /home/longtdang/KMS/vlm
.venv/bin/pytest tests/phase6/test_cropper.py::test_render_annotation_overlay_keypoints_with_point_names -v
```

Expected: FAIL — the current implementation does not draw any text labels.

- [ ] **Step 1.3: Implement label rendering in `cropper.py`**

In `render_annotation_overlay`, replace the skeleton `elif` block (currently lines ~252–262):

```python
elif isinstance(keypoints, list) and len(keypoints) > 0:
    # Skeleton mode: draw color-coded keypoint dots, no bbox
    from PIL import ImageFont
    visibility = annotation_crop_space.get("visibility")
    point_names = annotation_crop_space.get("point_names")
    font = ImageFont.load_default()
    for idx, kp in enumerate(keypoints):
        if not isinstance(kp, (list, tuple)) or len(kp) < 2:
            continue
        kx, ky = float(kp[0]), float(kp[1])
        vis_code = visibility[idx] if isinstance(visibility, list) and idx < len(visibility) else 2
        color = _VIS_COLORS.get(int(vis_code) if isinstance(vis_code, (int, float)) else 2, _VIS_DEFAULT_COLOR)
        r = _KEYPOINT_RADIUS
        draw.ellipse([kx - r, ky - r, kx + r, ky + r], fill=color, outline=(0, 0, 0))
        if isinstance(point_names, list) and idx < len(point_names):
            label = str(point_names[idx])
            label_x, label_y = kx - r, ky - r - 11  # 11 px above dot top: 9 px font + 2 px gap
            # Black shadow for contrast on any background
            draw.text((label_x + 1, label_y + 1), label, fill=(0, 0, 0), font=font)
            # White foreground
            draw.text((label_x, label_y), label, fill=(255, 255, 255), font=font)
```

- [ ] **Step 1.4: Run test to confirm it passes**

```bash
.venv/bin/pytest tests/phase6/test_cropper.py::test_render_annotation_overlay_keypoints_with_point_names -v
```

Expected: PASS

- [ ] **Step 1.5: Write test — `point_names` absent → dots only, no crash**

Add to `tests/phase6/test_cropper.py`:

```python
def test_render_annotation_overlay_keypoints_no_point_names(tmp_path: Path) -> None:
    """Omitting point_names produces dots only — no crash, no regression."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(source)

    annotation = {
        "keypoints": [[30.0, 50.0]],
        "visibility": [2],
        # point_names intentionally absent
        "polygon_points": None,
        "bbox": None,
    }
    out = tmp_path / "no_names.png"
    render_annotation_overlay(source, annotation, out)

    assert out.exists()
    img = Image.open(out)
    # Dot at (30, 50) should be green (visible)
    assert img.getpixel((30, 50))[1] > 100, "dot should still be drawn green"
```

- [ ] **Step 1.6: Write test — `point_names` shorter than `keypoints` → partial labels, no crash**

Add to `tests/phase6/test_cropper.py`:

```python
def test_render_annotation_overlay_point_names_shorter_than_keypoints(tmp_path: Path) -> None:
    """If point_names has fewer entries than keypoints, label only the first N dots."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (200, 200), (255, 255, 255)).save(source)

    annotation = {
        "keypoints": [[50.0, 100.0], [150.0, 100.0]],
        "visibility": [2, 2],
        "point_names": ["nose"],   # only one name for two keypoints
        "polygon_points": None,
        "bbox": None,
    }
    out = tmp_path / "partial.png"
    render_annotation_overlay(source, annotation, out)   # must not raise

    assert out.exists()
    img = Image.open(out)
    # Both dots drawn
    assert img.getpixel((50, 100))[1] > 100
    assert img.getpixel((150, 100))[1] > 100
```

- [ ] **Step 1.7: Run all three new tests**

```bash
.venv/bin/pytest tests/phase6/test_cropper.py::test_render_annotation_overlay_keypoints_with_point_names \
  tests/phase6/test_cropper.py::test_render_annotation_overlay_keypoints_no_point_names \
  tests/phase6/test_cropper.py::test_render_annotation_overlay_point_names_shorter_than_keypoints -v
```

Expected: All 3 PASS

- [ ] **Step 1.8: Run the full phase6 cropper tests to confirm no regressions**

```bash
.venv/bin/pytest tests/phase6/test_cropper.py -v
```

Expected: All existing tests still PASS

- [ ] **Step 1.9: Commit**

```bash
git add src/fiftyone_pose_importer/verification/cropper.py tests/phase6/test_cropper.py
git commit -m "feat: render skeleton point name labels above keypoint dots in crop overlay"
```

---

### Task 2: Inject `point_names` into `annotation_payload` in `run_verify.py`

**Files:**
- Modify: `src/fiftyone_pose_importer/run_verify.py`
- Test: `tests/phase6/test_run_verify.py`

- [ ] **Step 2.1: Write the failing test**

First, check the existing test file to find a suitable integration test or fixture to extend:

```bash
grep -n "annotation_payload\|point_names\|skeleton_contract\|render_annotation_overlay" \
  tests/phase6/test_run_verify.py | head -30
```

Then add a new test. The test calls `run_verify` with a minimal datumaro fixture that has a `categories.points` skeleton spec, and checks that the resulting overlay crop image has non-white pixels in the label area above the first keypoint:

```python
# At top of tests/phase6/test_run_verify.py (if not already imported):
# from PIL import Image

def test_run_verify_skeleton_overlay_includes_point_names(tmp_path: Path) -> None:
    """run_verify injects skeleton point names into the overlay so labels appear on crop images."""
    from PIL import Image as PILImage
    from fiftyone_pose_importer.run_verify import run_verify

    # Minimal 200x200 white source image
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    img_path = img_dir / "frame_001.jpg"
    PILImage.new("RGB", (200, 200), (255, 255, 255)).save(img_path)

    datumaro_data = {
        "categories": {
            "label": {"labels": [{"name": "person", "attributes": []}]},
            "points": {
                "labels": ["nose", "left_eye"],
                "joints": []
            }
        },
        "items": [
            {
                "id": "frame_001",
                "image": {"path": str(img_path), "size": [200, 200]},
                "annotations": [
                    {
                        "id": "ann-0",
                        "type": "skeleton",
                        "label_id": 0,
                        "bbox": [50.0, 50.0, 80.0, 80.0],
                        "points": [90.0, 90.0, 2, 110.0, 90.0, 2],  # x,y,v triplets
                    }
                ]
            }
        ]
    }

    datumaro_path = tmp_path / "data.json"
    import json
    datumaro_path.write_text(json.dumps(datumaro_data))

    config = {
        "verification": {
            "datumaro_path": str(datumaro_path),
            "images_root": str(img_dir),
            "run_root": str(tmp_path / "runs"),
            "padding_px": 10,
        }
    }
    config_path = tmp_path / "config.yaml"
    import yaml
    config_path.write_text(yaml.dump(config))

    result = run_verify(config_path=config_path)
    assert result is not None

    # Find the crop file written by run_verify
    crops = list((tmp_path / "runs").rglob("*.png"))
    assert len(crops) >= 1, "Expected at least one crop image"
    crop_img = PILImage.open(crops[0])

    # The first keypoint (nose) is at x=90, y=90 in original space.
    # After crop, text labels appear above the dot. Some pixels in the label
    # region must be non-white (text was drawn).
    pixels = [crop_img.getpixel((x, y)) for x in range(0, crop_img.width) for y in range(0, min(30, crop_img.height))]
    non_white = [p for p in pixels if p != (255, 255, 255)]
    assert len(non_white) > 0, "Expected text label pixels in crop overlay"
```

- [ ] **Step 2.2: Run to confirm the test fails**

```bash
.venv/bin/pytest tests/phase6/test_run_verify.py::test_run_verify_skeleton_overlay_includes_point_names -v
```

Expected: FAIL — `point_names` is not yet in `annotation_payload`.

- [ ] **Step 2.3: Add import for `extract_skeleton_contract_bundle` in `run_verify.py`**

In `src/fiftyone_pose_importer/run_verify.py`, update the import block at the top:

```python
from .datumaro_reader import load_datumaro, parse_keypoints_and_visibility
from .pose_contract import SchemaContractError, extract_skeleton_contract_bundle
```

- [ ] **Step 2.4: Extract skeleton labels before the annotation loop in `run_verify.py`**

Locate the line `label_names = _label_lookup(data)` (around line 202) and add the skeleton bundle extraction immediately after it:

```python
label_names = _label_lookup(data)

# Extract skeleton point-name labels so they can be drawn on crop overlays.
try:
    _skeleton_bundle = extract_skeleton_contract_bundle(data)
except (SchemaContractError, Exception):
    _skeleton_bundle = None
```

- [ ] **Step 2.5: Resolve per-annotation skeleton labels and inject into `annotation_payload`**

Locate the `annotation_payload` dict construction (around line 360) and add `point_names`:

```python
# Resolve skeleton point names for this annotation
_skeleton_labels: list[str] | None = None
if is_skeleton and _skeleton_bundle is not None:
    _contract = _skeleton_bundle.by_label_id.get(label_id) if isinstance(label_id, int) else None
    if _contract is None:
        _contract = _skeleton_bundle.default
    if _contract is not None:
        _skeleton_labels = _contract.labels

annotation_payload = {
    "bbox": list(bbox),
    "attributes": annotation.get("attributes") if isinstance(annotation.get("attributes"), dict) else {},
    "keypoints": keypoints,
    "visibility": crop.adjusted_visibility if crop.adjusted_visibility is not None else visibility,
    "polygon_points": polygon_points,
    "out_of_frame_indices": crop.out_of_frame_point_indices,
    "point_names": _skeleton_labels,
}
```

- [ ] **Step 2.6: Run the failing test to confirm it now passes**

```bash
.venv/bin/pytest tests/phase6/test_run_verify.py::test_run_verify_skeleton_overlay_includes_point_names -v
```

Expected: PASS

- [ ] **Step 2.7: Run the full test suite to confirm no regressions**

```bash
.venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -40
```

Expected: All previously passing tests still PASS.

- [ ] **Step 2.8: Commit**

```bash
git add src/fiftyone_pose_importer/run_verify.py tests/phase6/test_run_verify.py
git commit -m "feat: inject skeleton point_names into annotation_payload for crop label rendering"
```
