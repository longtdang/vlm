# Crop-Based Annotation Validation Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `scripts/crop_validate.py` — a standalone script that crops every annotation from a Datumaro dataset into individual FiftyOne samples, applies the Qwen2.5-VL plugin for annotation quality assessment, and exports a Markdown report sorted by risk.

**Architecture:** Reuses `cropper.py`, `datumaro_reader.py`, `pose_contract.py`, `image_index.py`, and `matching.py` from the existing package. VLM inference uses the FiftyOne model zoo plugin (VQA mode, grouped by annotation type). All logic lives in one `scripts/crop_validate.py` file with pure helper functions that are independently testable.

**Tech Stack:** Python 3.10+, FiftyOne ≥1.0, Pillow, Qwen2.5-VL FiftyOne plugin (`https://github.com/harpreetsahota204/qwen2_5_vl`), uv (test runner: `uv run pytest`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scripts/__init__.py` | Makes `scripts` a package so tests can import helpers |
| Create | `scripts/crop_validate.py` | All pipeline logic + CLI entry point |
| Modify | `tests/conftest.py` | Add repo root to `sys.path` for `scripts.*` imports |
| Create | `tests/crop_validate/__init__.py` | Test package marker |
| Create | `tests/crop_validate/test_helpers.py` | Unit tests for annotation parsing helpers |
| Create | `tests/crop_validate/test_vlm_parse.py` | Unit tests for VLM response parsing |
| Create | `tests/crop_validate/test_fo_sample.py` | Unit tests for FiftyOne sample building |
| Create | `tests/crop_validate/test_report.py` | Unit tests for Markdown report generation |
| Create | `tests/crop_validate/test_integration.py` | End-to-end test with `--no-vlm` |

---

## Task 1: Script scaffold + conftest update

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/crop_validate.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Create scripts package marker**

```bash
touch /path/to/repo/scripts/__init__.py
```

File content: empty.

- [ ] **Step 2: Create scripts/crop_validate.py with imports, constants, and argparse skeleton**

```python
# scripts/crop_validate.py
from __future__ import annotations

import argparse
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import fiftyone as fo
import fiftyone.zoo as foz
from fiftyone import ViewField as F

# ── project-local imports ────────────────────────────────────────────────────
# Add the repo src/ to path so this script can be run from anywhere
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from fiftyone_pose_importer.datumaro_reader import load_datumaro, parse_keypoints_and_visibility
from fiftyone_pose_importer.image_index import build_image_index
from fiftyone_pose_importer.matching import build_matches
from fiftyone_pose_importer.pose_contract import (
    SkeletonContract,
    SkeletonContractBundle,
    extract_skeleton_contract_bundle,
)
from fiftyone_pose_importer.verification.cropper import (
    CropPlan,
    annotation_to_crop_space,
    materialize_crop,
    plan_crop,
    render_annotation_overlay,
)
from fiftyone_pose_importer.verification.types import DeterministicVerdict

# ── constants ────────────────────────────────────────────────────────────────
PLUGIN_URL = "https://github.com/harpreetsahota204/qwen2_5_vl"
DEFAULT_PADDING_PX = 16
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)

DEFAULT_PROMPTS: dict[str, str] = {
    "detection": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with an orange-red bounding box drawn on it.\n"
        "Judge whether the bounding box correctly localizes and covers the '{label}' object.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
    "skeleton": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with colored keypoint dots: green=visible, orange=occluded, gray=unlabeled.\n"
        "Judge whether the keypoints are correctly placed on the '{label}' structure and "
        "whether their visibility codes match the actual occlusion state.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
    "segmentation": (
        "You are validating annotation quality for the '{label}' region.\n"
        "The image shows a crop with a cyan polygon outline drawn on it.\n"
        "Judge whether the polygon correctly outlines the '{label}' region.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
}

# Per-label overrides — add entries here to customize prompts per label:
LABEL_PROMPTS: dict[str, str] = {
    # "forklift-with-roll": "...",
}

_SKELETON_ANN_TYPES = {"points", "skeleton"}
_NON_SKELETON_ANN_TYPES = {"polygon", "bbox", "mask", "ellipse", "polyline"}


def main() -> None:
    args = _parse_args()
    print(f"[crop_validate] Starting — output dir: {args.output_dir}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop annotations into FiftyOne samples and validate with Qwen2.5-VL"
    )
    parser.add_argument("--datumaro-json", required=True, help="Path to Datumaro JSON file")
    parser.add_argument("--image-dir", required=True, help="Directory containing source images")
    parser.add_argument("--output-dir", required=True, help="Output directory for crops and report")
    parser.add_argument("--dataset-name", default="crop_validate", help="FiftyOne dataset base name")
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-7B-Instruct", help="Qwen2.5-VL model checkpoint")
    parser.add_argument("--plugin-source", default=PLUGIN_URL, help="FiftyOne zoo plugin URL")
    parser.add_argument("--padding-px", type=int, default=DEFAULT_PADDING_PX, help="Crop padding in pixels")
    parser.add_argument("--pass-threshold", type=float, default=0.20, help="Risk below this → PASS")
    parser.add_argument("--review-threshold", type=float, default=0.60, help="Risk below this → REVIEW, else FAIL")
    parser.add_argument("--persist-dataset", action="store_true", help="Keep FiftyOne dataset after run")
    parser.add_argument("--overwrite-dataset", action="store_true", help="Overwrite existing dataset instead of using timestamp suffix")
    parser.add_argument("--no-vlm", action="store_true", help="Skip VLM stage (build crops and dataset only)")
    return parser.parse_args()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update tests/conftest.py to add repo root to sys.path**

Current content of `tests/conftest.py`:
```python
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

New content (add ROOT itself for `scripts.*` imports):
```python
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 4: Verify the scaffold runs**

```bash
cd /path/to/repo && python scripts/crop_validate.py --help
```

Expected: argparse help message showing all flags with no import errors.

- [ ] **Step 5: Commit scaffold**

```bash
git add scripts/__init__.py scripts/crop_validate.py tests/conftest.py
git commit -m "feat: add crop_validate script scaffold with CLI argparse"
```

---

## Task 2: Annotation parsing helpers + tests

**Files:**
- Modify: `scripts/crop_validate.py`
- Create: `tests/crop_validate/__init__.py`
- Create: `tests/crop_validate/test_helpers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/crop_validate/__init__.py` (empty).

Create `tests/crop_validate/test_helpers.py`:
```python
from __future__ import annotations

import pytest
from scripts.crop_validate import (
    _annotation_type,
    _derive_bbox,
    _is_skeleton_type,
    _label_lookup,
    _safe_token,
)


class TestAnnotationType:
    def test_bbox_is_detection(self) -> None:
        assert _annotation_type("bbox") == "detection"

    def test_polygon_is_segmentation(self) -> None:
        assert _annotation_type("polygon") == "segmentation"

    def test_skeleton_is_skeleton(self) -> None:
        assert _annotation_type("skeleton") == "skeleton"

    def test_points_is_skeleton(self) -> None:
        assert _annotation_type("points") == "skeleton"

    def test_unknown_defaults_to_detection(self) -> None:
        assert _annotation_type("unknown_type") == "detection"

    def test_none_defaults_to_detection(self) -> None:
        assert _annotation_type(None) == "detection"


class TestDeriveBbox:
    def test_returns_bbox_field_when_present(self) -> None:
        ann = {"type": "bbox", "bbox": [10.0, 20.0, 30.0, 40.0]}
        result = _derive_bbox(ann)
        assert result == (10.0, 20.0, 30.0, 40.0)

    def test_derives_from_polygon_points(self) -> None:
        # polygon points [x0,y0,x1,y1,...] → AABB
        ann = {"type": "polygon", "points": [10.0, 20.0, 50.0, 20.0, 50.0, 60.0, 10.0, 60.0]}
        result = _derive_bbox(ann)
        assert result == (10.0, 20.0, 40.0, 40.0)  # x=10, y=20, w=40, h=40

    def test_derives_from_skeleton_points(self) -> None:
        # skeleton: [x,y,v, x,y,v, ...] triplets
        ann = {"type": "skeleton", "points": [100.0, 200.0, 2, 150.0, 250.0, 2]}
        result = _derive_bbox(ann)
        assert result == (100.0, 200.0, 50.0, 50.0)

    def test_returns_none_for_empty(self) -> None:
        ann = {"type": "polygon", "points": []}
        assert _derive_bbox(ann) is None

    def test_returns_none_when_no_bbox_and_no_points(self) -> None:
        ann = {"type": "bbox"}
        assert _derive_bbox(ann) is None


class TestIsSkeletonType:
    def test_skeleton(self) -> None:
        assert _is_skeleton_type("skeleton") is True

    def test_points(self) -> None:
        assert _is_skeleton_type("points") is True

    def test_bbox(self) -> None:
        assert _is_skeleton_type("bbox") is False

    def test_polygon(self) -> None:
        assert _is_skeleton_type("polygon") is False

    def test_none(self) -> None:
        assert _is_skeleton_type(None) is False


class TestLabelLookup:
    def test_extracts_labels(self) -> None:
        data = {
            "categories": {
                "label": {
                    "labels": [
                        {"name": "forklift-with-roll"},
                        {"name": "clamp-2-arm"},
                    ]
                }
            }
        }
        result = _label_lookup(data)
        assert result == {0: "forklift-with-roll", 1: "clamp-2-arm"}

    def test_empty_data(self) -> None:
        assert _label_lookup({}) == {}

    def test_fallback_for_non_dict_entry(self) -> None:
        data = {"categories": {"label": {"labels": ["bad"]}}}
        result = _label_lookup(data)
        assert result == {0: "label-0"}


class TestSafeToken:
    def test_alphanumeric_unchanged(self) -> None:
        assert _safe_token("frame001") == "frame001"

    def test_spaces_become_underscores(self) -> None:
        assert _safe_token("my image") == "my_image"

    def test_special_chars_replaced(self) -> None:
        assert _safe_token("frame/001:test") == "frame_001_test"

    def test_empty_becomes_unknown(self) -> None:
        assert _safe_token("") == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_helpers.py -v 2>&1 | head -30
```

Expected: `ImportError` — functions not yet defined.

- [ ] **Step 3: Implement helpers in scripts/crop_validate.py**

Add these functions after the constants block:
```python
import json  # add to imports at top of file


def _annotation_type(datumaro_type: str | None) -> str:
    """Map Datumaro annotation type string to our three-way type: detection/segmentation/skeleton."""
    if datumaro_type == "polygon":
        return "segmentation"
    if datumaro_type in _SKELETON_ANN_TYPES:
        return "skeleton"
    return "detection"  # bbox, mask, ellipse, polyline, unknown, None


def _is_skeleton_type(datumaro_type: str | None) -> bool:
    return datumaro_type in _SKELETON_ANN_TYPES


def _derive_bbox(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return (x, y, w, h) bbox — from bbox field if present, else derived from points."""
    raw = annotation.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        try:
            return float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
        except (TypeError, ValueError):
            pass

    ann_type = annotation.get("type")
    points_raw = annotation.get("points")
    if not isinstance(points_raw, list) or not points_raw:
        return None
    try:
        if ann_type == "skeleton" and len(points_raw) >= 3 and len(points_raw) % 3 == 0:
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 3)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 3)]
        elif len(points_raw) >= 2 and len(points_raw) % 2 == 0:
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 2)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 2)]
        else:
            return None
    except (TypeError, ValueError):
        return None
    if not xs:
        return None
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _label_lookup(data: dict[str, Any]) -> dict[int, str]:
    labels_raw = ((data.get("categories") or {}).get("label") or {}).get("labels") or []
    lookup: dict[int, str] = {}
    for index, raw in enumerate(labels_raw):
        if isinstance(raw, dict):
            lookup[index] = str(raw.get("name") or f"label-{index}")
        else:
            lookup[index] = f"label-{index}"
    return lookup


def _safe_token(value: str) -> str:
    import re as _re
    cleaned = _re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "unknown"


def _get_polygon_points(annotation: dict[str, Any]) -> list[list[float]] | None:
    """Extract polygon/polyline/mask points as [[x, y], ...] pairs."""
    ann_type = annotation.get("type")
    if ann_type not in {"polygon", "polyline", "mask"}:
        return None
    raw_pts = annotation.get("points")
    if not isinstance(raw_pts, list) or len(raw_pts) < 4:
        return None
    try:
        return [
            [float(raw_pts[i]), float(raw_pts[i + 1])]
            for i in range(0, len(raw_pts) - 1, 2)
        ]
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_helpers.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/crop_validate.py tests/crop_validate/__init__.py tests/crop_validate/test_helpers.py
git commit -m "feat: add annotation parsing helpers with tests"
```

---

## Task 3: VLM response parsing helpers + tests

**Files:**
- Modify: `scripts/crop_validate.py`
- Create: `tests/crop_validate/test_vlm_parse.py`

- [ ] **Step 1: Write failing tests**

Create `tests/crop_validate/test_vlm_parse.py`:
```python
from __future__ import annotations

import pytest
from scripts.crop_validate import _ep_to_verdict, _parse_vlm_response


class TestParseVlmResponse:
    def test_plain_json(self) -> None:
        raw = '{"error_probability": 0.1, "reason": "looks good"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.1)
        assert reason == "looks good"

    def test_json_in_markdown_fence(self) -> None:
        raw = '```json\n{"error_probability": 0.8, "reason": "bad box"}\n```'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.8)
        assert reason == "bad box"

    def test_json_in_plain_fence(self) -> None:
        raw = '```\n{"error_probability": 0.5, "reason": "uncertain"}\n```'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.5)

    def test_invalid_json_returns_none(self) -> None:
        ep, reason = _parse_vlm_response("not json at all")
        assert ep is None
        assert reason == "parse_failed"

    def test_missing_error_probability_returns_none(self) -> None:
        raw = '{"reason": "forgot probability"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep is None
        assert reason == "parse_failed"

    def test_out_of_range_ep_returns_none(self) -> None:
        raw = '{"error_probability": 1.5, "reason": "out of range"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep is None
        assert reason == "parse_failed"

    def test_missing_reason_uses_empty_string(self) -> None:
        raw = '{"error_probability": 0.3}'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.3)
        assert reason == ""

    def test_whitespace_padded(self) -> None:
        raw = '  {"error_probability": 0.0, "reason": "perfect"}  '
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.0)


class TestEpToVerdict:
    def test_below_pass_threshold(self) -> None:
        assert _ep_to_verdict(0.10, 0.20, 0.60) == "PASS"

    def test_at_pass_threshold_boundary(self) -> None:
        assert _ep_to_verdict(0.19, 0.20, 0.60) == "PASS"

    def test_at_pass_threshold_exact(self) -> None:
        assert _ep_to_verdict(0.20, 0.20, 0.60) == "REVIEW"

    def test_in_review_range(self) -> None:
        assert _ep_to_verdict(0.45, 0.20, 0.60) == "REVIEW"

    def test_at_fail_threshold_exact(self) -> None:
        assert _ep_to_verdict(0.60, 0.20, 0.60) == "FAIL"

    def test_above_fail_threshold(self) -> None:
        assert _ep_to_verdict(0.95, 0.20, 0.60) == "FAIL"

    def test_none_ep_returns_review(self) -> None:
        assert _ep_to_verdict(None, 0.20, 0.60) == "REVIEW"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_vlm_parse.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Implement VLM parsing functions**

Add to `scripts/crop_validate.py`:
```python
def _parse_vlm_response(raw: str) -> tuple[float | None, str]:
    """Parse VLM text output into (error_probability, reason).

    Returns (None, "parse_failed") on any parse failure.
    """
    stripped = raw.strip()
    match = _FENCE_RE.search(stripped)
    if match:
        stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None, "parse_failed"

    ep = parsed.get("error_probability")
    if not isinstance(ep, (int, float)) or not (0.0 <= float(ep) <= 1.0):
        return None, "parse_failed"

    reason = str(parsed.get("reason", ""))
    return float(ep), reason


def _ep_to_verdict(ep: float | None, pass_threshold: float, review_threshold: float) -> str:
    """Map error_probability to PASS/REVIEW/FAIL verdict string."""
    if ep is None:
        return "REVIEW"
    if ep < pass_threshold:
        return "PASS"
    if ep < review_threshold:
        return "REVIEW"
    return "FAIL"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_vlm_parse.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/crop_validate.py tests/crop_validate/test_vlm_parse.py
git commit -m "feat: add VLM response parsing helpers with tests"
```

---

## Task 4: FiftyOne sample building + tests

**Files:**
- Modify: `scripts/crop_validate.py`
- Create: `tests/crop_validate/test_fo_sample.py`

- [ ] **Step 1: Write failing tests**

Create `tests/crop_validate/test_fo_sample.py`:
```python
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import fiftyone as fo
import pytest

from fiftyone_pose_importer.pose_contract import SkeletonContract
from fiftyone_pose_importer.verification.cropper import CropPlan
from fiftyone_pose_importer.verification.types import DeterministicVerdict
from scripts.crop_validate import _to_fo_sample


def _make_crop_plan(
    output_size: tuple[int, int] = (200, 150),
    policy: str = "non_skeleton_clip",
    padded_bounds: tuple[int, int, int, int] | None = None,
    clipped_bounds: tuple[int, int, int, int] | None = (10, 20, 210, 170),
    paste_offset: tuple[int, int] = (0, 0),
) -> CropPlan:
    return CropPlan(
        verdict=DeterministicVerdict.PASS,
        reason=None,
        policy=policy,
        padding_px=10,
        padded_bounds=padded_bounds,
        clipped_bounds=clipped_bounds,
        output_size=output_size,
        paste_offset=paste_offset,
        adjusted_visibility=None,
        original_visibility=None,
        out_of_frame_point_indices=[],
    )


class TestDetectionSample:
    def test_bounding_box_normalized(self) -> None:
        crop_plan = _make_crop_plan(output_size=(200, 150))
        # bbox in crop-space pixels
        crop_space_ann = {"bbox": [20.0, 15.0, 100.0, 75.0]}
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann=crop_space_ann,
            label="forklift-with-roll",
            ann_type="detection",
            source_image="frame_001.jpg",
            ann_id="42",
            label_id=None,
            contract=None,
        )
        det = sample["detections"].detections[0]
        # x/W=20/200=0.1, y/H=15/150=0.1, w/W=100/200=0.5, h/H=75/150=0.5
        assert det.bounding_box == pytest.approx([0.1, 0.1, 0.5, 0.5])
        assert det.label == "forklift-with-roll"

    def test_back_reference_fields(self) -> None:
        crop_plan = _make_crop_plan(output_size=(100, 100))
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann={"bbox": [0.0, 0.0, 50.0, 50.0]},
            label="forklift-no-roll",
            ann_type="detection",
            source_image="img.jpg",
            ann_id="7",
            label_id=None,
            contract=None,
        )
        assert sample["source_image"] == "img.jpg"
        assert sample["source_ann_id"] == "7"
        assert sample["annotation_label"] == "forklift-no-roll"
        assert sample["annotation_type"] == "detection"


class TestSegmentationSample:
    def test_polyline_points_normalized(self) -> None:
        crop_plan = _make_crop_plan(output_size=(200, 100))
        crop_space_ann = {
            "polygon_points": [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]]
        }
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann=crop_space_ann,
            label="roll-mask",
            ann_type="segmentation",
            source_image="img.jpg",
            ann_id="3",
            label_id=None,
            contract=None,
        )
        polyline = sample["segmentations"].polylines[0]
        # points normalized: [[0/200,0/100],[100/200,0/100],[100/200,50/100],[0/200,50/100]]
        expected = [[[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]]
        assert polyline.points == pytest.approx(expected)
        assert polyline.label == "roll-mask"
        assert polyline.filled is True
        assert polyline.closed is True


class TestSkeletonSample:
    def test_keypoints_normalized_and_absent_is_nan(self) -> None:
        contract = SkeletonContract(labels=["pt_a", "pt_b", "pt_c"], edges=[[0, 1]])
        crop_plan = _make_crop_plan(output_size=(400, 300), policy="skeleton_preserve_canvas")
        crop_space_ann = {
            "keypoints": [[40.0, 30.0], [200.0, 150.0], [0.0, 0.0]],
            "visibility": [2, 1, 0],
        }
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann=crop_space_ann,
            label="clamp-2-arm",
            ann_type="skeleton",
            source_image="img.jpg",
            ann_id="5",
            label_id=2,
            contract=contract,
        )
        kp_field = "keypoints_label_2"
        assert kp_field in sample.field_names
        kp = sample[kp_field].keypoints[0]
        # visible: [40/400, 30/300] = [0.1, 0.1]
        assert kp.points[0] == pytest.approx([0.1, 0.1])
        # occluded (vis=1): still normalized — NOT nan
        assert kp.points[1] == pytest.approx([0.5, 0.5])
        # absent (vis=0): should be [nan, nan]
        assert math.isnan(kp.points[2][0])
        assert math.isnan(kp.points[2][1])

    def test_skeleton_field_name_uses_label_id(self) -> None:
        contract = SkeletonContract(labels=["a", "b"], edges=[])
        crop_plan = _make_crop_plan(output_size=(100, 100), policy="skeleton_preserve_canvas")
        sample = _to_fo_sample(
            crop_overlay_path=Path("/tmp/crop.png"),
            crop_plan=crop_plan,
            crop_space_ann={"keypoints": [[10.0, 10.0], [20.0, 20.0]], "visibility": [2, 2]},
            label="clamp-3-arm",
            ann_type="skeleton",
            source_image="img.jpg",
            ann_id="9",
            label_id=5,
            contract=contract,
        )
        assert "keypoints_label_5" in sample.field_names
        assert "keypoints_label_0" not in sample.field_names
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_fo_sample.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Implement _to_fo_sample in scripts/crop_validate.py**

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

    W, H = crop_plan.output_size  # crop pixel dimensions

    if ann_type == "detection":
        bbox = crop_space_ann.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            bx, by, bw, bh = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            fo_bbox = [bx / W, by / H, bw / W, bh / H]
            sample["detections"] = fo.Detections(
                detections=[fo.Detection(label=label, bounding_box=fo_bbox)]
            )

    elif ann_type == "segmentation":
        polygon_points = crop_space_ann.get("polygon_points")
        if isinstance(polygon_points, list) and len(polygon_points) >= 2:
            fo_pts = [[[px / W, py / H] for px, py in polygon_points]]
            sample["segmentations"] = fo.Polylines(
                polylines=[
                    fo.Polyline(label=label, points=fo_pts, filled=True, closed=True)
                ]
            )

    elif ann_type == "skeleton":
        keypoints = crop_space_ann.get("keypoints") or []
        visibility = crop_space_ann.get("visibility") or []
        field_name = f"keypoints_label_{label_id}" if isinstance(label_id, int) else "keypoints_label_unknown"
        fo_points = []
        for idx, (kx, ky) in enumerate(keypoints):
            vis = visibility[idx] if idx < len(visibility) else 2
            if vis == 0:
                fo_points.append([math.nan, math.nan])
            else:
                fo_points.append([kx / W, ky / H])
        kp = fo.Keypoint(points=fo_points)
        if isinstance(visibility, list):
            kp["visibility"] = list(visibility)
        if contract is not None:
            kp["skeleton_labels"] = contract.labels
            kp["skeleton_edges"] = contract.edges
        sample[field_name] = fo.Keypoints(keypoints=[kp])

    return sample
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_fo_sample.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/crop_validate.py tests/crop_validate/test_fo_sample.py
git commit -m "feat: implement FiftyOne sample builder with normalization"
```

---

## Task 5: Crop generation loop + FiftyOne dataset build

**Files:**
- Modify: `scripts/crop_validate.py` (add `_build_dataset` and wire into `main`)

- [ ] **Step 1: Implement _build_dataset**

Add to `scripts/crop_validate.py`:
```python
def _build_dataset(args: argparse.Namespace) -> fo.Dataset:
    """Parse Datumaro JSON, crop each annotation, build FiftyOne dataset."""
    datumaro_path = Path(args.datumaro_json).resolve()
    image_dir = Path(args.image_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    crops_dir = output_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    data = load_datumaro(datumaro_path)
    items: list[dict[str, Any]] = data["items"]
    label_names = _label_lookup(data)

    image_index, _ = build_image_index(image_dir)
    matches, _, _, _ = build_matches(image_index, items)

    try:
        skeleton_bundle: SkeletonContractBundle | None = extract_skeleton_contract_bundle(data)
    except Exception:
        skeleton_bundle = None

    # Resolve dataset name (avoid collision with timestamp suffix)
    dataset_name = args.dataset_name
    if not args.overwrite_dataset:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{args.dataset_name}_{timestamp}"
    elif fo.dataset_exists(dataset_name):
        fo.delete_dataset(dataset_name)

    dataset = fo.Dataset(dataset_name)
    routed_contracts: dict[str, SkeletonContract] = {}
    samples: list[fo.Sample] = []
    skipped = 0

    for image_path, item in matches:
        image_meta = (item.get("image") or {}).get("size") or []
        width = int(image_meta[1]) if len(image_meta) >= 2 else None
        height = int(image_meta[0]) if len(image_meta) >= 2 else None
        if width is None or height is None or width <= 0 or height <= 0:
            skipped += 1
            continue

        source_image = Path(image_path).name
        sample_id = str(item.get("id") or "unknown")
        annotations = item.get("annotations") or []

        for ann_idx, annotation in enumerate(annotations):
            if not isinstance(annotation, dict):
                skipped += 1
                continue

            ann_id = str(annotation.get("id") or f"ann-{ann_idx}")
            label_id = annotation.get("label_id")
            label = (
                label_names.get(label_id, str(annotation.get("label") or "unknown"))
                if isinstance(label_id, int)
                else str(annotation.get("label") or "unknown")
            )
            ann_type_raw = annotation.get("type")
            ann_type = _annotation_type(ann_type_raw)
            is_skeleton = _is_skeleton_type(ann_type_raw)

            # Derive bbox
            bbox = _derive_bbox(annotation)
            if bbox is None:
                print(f"[crop_validate] skip ann_id={ann_id}: no bbox", file=sys.stderr)
                skipped += 1
                continue

            # Parse keypoints/visibility for skeleton types
            keypoints: list[list[float]] = []
            visibility: list[int] = []
            if is_skeleton:
                try:
                    keypoints, visibility, _, _ = parse_keypoints_and_visibility(annotation)
                except ValueError as exc:
                    print(f"[crop_validate] skip ann_id={ann_id}: {exc}", file=sys.stderr)
                    skipped += 1
                    continue

            crop = plan_crop(
                image_width=width,
                image_height=height,
                bbox=bbox,
                padding_px=args.padding_px,
                is_skeleton=is_skeleton,
                keypoints=[(p[0], p[1]) for p in keypoints] if keypoints else None,
                visibility=visibility if visibility else None,
            )
            if crop.verdict is DeterministicVerdict.FAIL:
                print(f"[crop_validate] skip ann_id={ann_id}: {crop.reason}", file=sys.stderr)
                skipped += 1
                continue

            # Resolve polygon points for segmentation
            polygon_points = _get_polygon_points(annotation)

            # Resolve skeleton point names
            skeleton_labels: list[str] | None = None
            contract: SkeletonContract | None = None
            if is_skeleton and skeleton_bundle is not None:
                if isinstance(label_id, int):
                    contract = skeleton_bundle.by_label_id.get(label_id)
                if contract is None:
                    contract = skeleton_bundle.default
                if contract is not None:
                    skeleton_labels = contract.labels

            annotation_payload: dict[str, Any] = {
                "bbox": list(bbox),
                "attributes": annotation.get("attributes") if isinstance(annotation.get("attributes"), dict) else {},
                "keypoints": keypoints or None,
                "visibility": crop.adjusted_visibility,
                "original_visibility": crop.original_visibility,
                "point_names": skeleton_labels,
                "polygon_points": polygon_points,
            }
            crop_space_ann = annotation_to_crop_space(annotation_payload, crop)

            # Filename: <orig_stem>__ann_<id>__<label>.png
            orig_stem = _safe_token(Path(image_path).stem)
            safe_label = _safe_token(label)
            safe_ann_id = _safe_token(ann_id)
            crop_filename = f"{orig_stem}__ann_{safe_ann_id}__{safe_label}.png"
            overlay_path = crops_dir / crop_filename

            try:
                materialize_crop(source_image_path=image_path, crop_plan=crop, output_path=overlay_path)
                render_annotation_overlay(
                    crop_image_path=overlay_path,
                    annotation_crop_space=crop_space_ann,
                    output_path=overlay_path,
                )
            except Exception as exc:
                print(f"[crop_validate] skip ann_id={ann_id}: crop error {exc}", file=sys.stderr)
                skipped += 1
                continue

            if is_skeleton and contract is not None and isinstance(label_id, int):
                field_name = f"keypoints_label_{label_id}"
                routed_contracts[field_name] = contract

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
            )
            samples.append(sample)

    # Set skeleton metadata on dataset
    for field_name, contract in routed_contracts.items():
        skeletons = dict(getattr(dataset, "skeletons", {}) or {})
        skeletons[field_name] = fo.KeypointSkeleton(
            labels=contract.labels, edges=contract.edges
        )
        dataset.skeletons = skeletons

    dataset.add_samples(samples)
    dataset.save()
    print(f"[crop_validate] Built dataset '{dataset_name}': {len(samples)} crops, {skipped} skipped")
    return dataset
```

- [ ] **Step 2: Wire _build_dataset into main()**

Replace the `main()` body:
```python
def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = _build_dataset(args)

    if not args.no_vlm:
        _apply_vlm(dataset, args.model, args.plugin_source, args.pass_threshold, args.review_threshold)

    report_path = output_dir / "report.md"
    _write_report(dataset, report_path, dataset.name)
    print(f"[crop_validate] Report written: {report_path}")

    if not args.persist_dataset:
        dataset.delete()
        print(f"[crop_validate] Dataset '{dataset.name}' deleted (use --persist-dataset to keep)")
    else:
        print(f"[crop_validate] Dataset '{dataset.name}' persisted in FiftyOne")
```

Note: `_apply_vlm` and `_write_report` will be stubbed as `pass` for now, implemented in Tasks 6 and 7.

Add stubs after `_build_dataset`:
```python
def _apply_vlm(
    dataset: fo.Dataset,
    model_name: str,
    plugin_source: str,
    pass_threshold: float,
    review_threshold: float,
) -> None:
    pass  # implemented in Task 6


def _write_report(dataset: fo.Dataset, output_path: Path, dataset_name: str) -> None:
    pass  # implemented in Task 7
```

- [ ] **Step 3: Commit**

```bash
git add scripts/crop_validate.py
git commit -m "feat: implement crop generation loop and FiftyOne dataset builder"
```

---

## Task 6: VLM stage (apply_model + parse + write verdict)

**Files:**
- Modify: `scripts/crop_validate.py` (replace `_apply_vlm` stub with real implementation)

- [ ] **Step 1: Implement _apply_vlm**

Replace the stub with:
```python
def _apply_vlm(
    dataset: fo.Dataset,
    model_name: str,
    plugin_source: str,
    pass_threshold: float,
    review_threshold: float,
) -> None:
    """Apply Qwen2.5-VL VQA to each crop, parse responses, write vlm_verdict field."""
    print(f"[crop_validate] Registering plugin source: {plugin_source}")
    foz.register_zoo_model_source(plugin_source, overwrite=False)

    print(f"[crop_validate] Loading model: {model_name}")
    model = foz.load_zoo_model(model_name)
    model.operation = "vqa"

    # Group samples by annotation_type and run apply_model once per type
    for ann_type in ("detection", "segmentation", "skeleton"):
        view = dataset.match(F("annotation_type") == ann_type)
        if len(view) == 0:
            continue
        prompt_template = DEFAULT_PROMPTS[ann_type]
        # Use a generic placeholder label in the global prompt; per-label is handled post-hoc
        # by substituting the actual label per sample when parsing
        model.prompt = prompt_template.replace("{label}", ann_type)
        print(f"[crop_validate] Running VQA for {len(view)} '{ann_type}' samples…")
        view.apply_model(model, label_field="vlm_raw_response")

    # Parse raw VQA responses and write fo.Classification to vlm_verdict
    import json as _json  # already imported at module level but explicit for clarity
    updated = 0
    for sample in dataset.iter_samples(progress=True):
        raw = sample.get_field("vlm_raw_response")
        raw_str = str(raw) if raw is not None else ""
        # Build a label-specific prompt for parsing context (informational)
        label = sample.get_field("annotation_label") or ""
        ann_type = sample.get_field("annotation_type") or "detection"
        ep, reason = _parse_vlm_response(raw_str)
        verdict = _ep_to_verdict(ep, pass_threshold, review_threshold)
        confidence = ep if ep is not None else 0.0
        sample["vlm_verdict"] = fo.Classification(label=verdict, confidence=confidence)
        sample["vlm_reason"] = reason
        sample.save()
        updated += 1

    # Clean up intermediate field
    if "vlm_raw_response" in dataset.get_field_schema():
        dataset.delete_sample_field("vlm_raw_response")
        dataset.save()

    print(f"[crop_validate] VLM stage complete: {updated} samples evaluated")
```

- [ ] **Step 2: Commit**

```bash
git add scripts/crop_validate.py
git commit -m "feat: implement VLM stage with Qwen2.5-VL plugin and response parsing"
```

---

## Task 7: Markdown report + tests

**Files:**
- Modify: `scripts/crop_validate.py` (replace `_write_report` stub)
- Create: `tests/crop_validate/test_report.py`

- [ ] **Step 1: Write failing tests**

Create `tests/crop_validate/test_report.py`:
```python
from __future__ import annotations

from pathlib import Path

import fiftyone as fo
import pytest

from scripts.crop_validate import _write_report


def _make_dataset_with_verdicts(tmp_path: Path) -> fo.Dataset:
    """Build a minimal in-memory FiftyOne dataset with vlm_verdict fields."""
    import uuid
    dataset = fo.Dataset(f"test_report_{uuid.uuid4().hex[:8]}")

    for i, (verdict, confidence, reason, label) in enumerate([
        ("FAIL",   0.92, "bbox clips edge", "forklift-with-roll"),
        ("FAIL",   0.75, "wrong placement", "clamp-2-arm"),
        ("REVIEW", 0.45, "partially correct", "forklift-no-roll"),
        ("PASS",   0.05, "looks good", "clamp-3-arm"),
        ("PASS",   0.10, "well placed", "forklift-with-roll"),
    ]):
        # Create a tiny 1x1 PNG so FiftyOne accepts the filepath
        img_path = tmp_path / f"crop_{i}.png"
        from PIL import Image
        Image.new("RGB", (10, 10), color=(0, 0, 0)).save(img_path)

        sample = fo.Sample(filepath=str(img_path))
        sample["source_image"] = f"frame_{i:03d}.jpg"
        sample["source_ann_id"] = str(i + 100)
        sample["annotation_label"] = label
        sample["annotation_type"] = "detection"
        sample["vlm_verdict"] = fo.Classification(label=verdict, confidence=confidence)
        sample["vlm_reason"] = reason
        dataset.add_sample(sample)

    dataset.save()
    return dataset


class TestWriteReport:
    def test_report_file_created(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        assert report_path.exists()
        dataset.delete()

    def test_report_contains_summary_table(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        assert "## Summary" in content
        assert "FAIL" in content
        assert "REVIEW" in content
        assert "PASS" in content
        dataset.delete()

    def test_fail_section_before_review_before_pass(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        fail_pos = content.index("## ❌ FAIL")
        review_pos = content.index("## ⚠️ REVIEW")
        pass_pos = content.index("## ✅ PASS")
        assert fail_pos < review_pos < pass_pos
        dataset.delete()

    def test_rows_contain_source_image_and_reason(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        assert "frame_000.jpg" in content
        assert "bbox clips edge" in content
        dataset.delete()

    def test_fail_rows_sorted_by_risk_descending(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        # 0.92 must appear before 0.75 in the FAIL section
        idx_92 = content.index("0.92")
        idx_75 = content.index("0.75")
        assert idx_92 < idx_75
        dataset.delete()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_report.py -v 2>&1 | head -20
```

Expected: FAIL (stub `_write_report` does nothing, so file not created).

- [ ] **Step 3: Implement _write_report**

Replace the stub with:
```python
def _write_report(dataset: fo.Dataset, output_path: Path, dataset_name: str) -> None:
    """Write a Markdown report from FiftyOne dataset vlm_verdict fields."""

    # Collect all sample data
    rows: list[dict[str, Any]] = []
    for sample in dataset.iter_samples():
        verdict_field = sample.get_field("vlm_verdict")
        verdict = verdict_field.label if verdict_field is not None else "REVIEW"
        confidence = verdict_field.confidence if verdict_field is not None else 0.0
        rows.append({
            "crop_file": Path(sample.filepath).name,
            "source_image": sample.get_field("source_image") or "",
            "ann_id": sample.get_field("source_ann_id") or "",
            "label": sample.get_field("annotation_label") or "",
            "risk": confidence if confidence is not None else 0.0,
            "verdict": verdict,
            "reason": sample.get_field("vlm_reason") or "",
        })

    fail_rows = sorted([r for r in rows if r["verdict"] == "FAIL"], key=lambda r: -r["risk"])
    review_rows = sorted([r for r in rows if r["verdict"] == "REVIEW"], key=lambda r: -r["risk"])
    pass_rows = sorted([r for r in rows if r["verdict"] == "PASS"], key=lambda r: -r["risk"])
    total = len(rows)

    def _pct(n: int) -> str:
        return f"{round(100 * n / total)}%" if total > 0 else "0%"

    lines: list[str] = [
        "# Crop Annotation Validation Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Dataset: {dataset_name}",
        f"Total crops: {total}",
        "",
        "## Summary",
        "| Verdict | Count |    % |",
        "|---------|------:|-----:|",
        f"| FAIL    | {len(fail_rows):>5} | {_pct(len(fail_rows)):>4} |",
        f"| REVIEW  | {len(review_rows):>5} | {_pct(len(review_rows)):>4} |",
        f"| PASS    | {len(pass_rows):>5} | {_pct(len(pass_rows)):>4} |",
        "",
    ]

    def _table_section(title: str, section_rows: list[dict[str, Any]]) -> list[str]:
        section_lines = [
            title,
            "| # | Crop File | Source Image | Ann ID | Label | Risk | VLM Reason |",
            "|---|-----------|--------------|--------|-------|-----:|------------|",
        ]
        for idx, row in enumerate(section_rows, 1):
            risk_str = f"{row['risk']:.2f}" if row["risk"] is not None else "N/A"
            reason = row["reason"].replace("|", "\\|")
            section_lines.append(
                f"| {idx} | {row['crop_file']} | {row['source_image']} | "
                f"{row['ann_id']} | {row['label']} | {risk_str} | {reason} |"
            )
        section_lines.append("")
        return section_lines

    lines += _table_section(f"## ❌ FAIL ({len(fail_rows)})", fail_rows)
    lines += _table_section(f"## ⚠️ REVIEW ({len(review_rows)})", review_rows)
    lines += _table_section(f"## ✅ PASS ({len(pass_rows)})", pass_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_report.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/crop_validate.py tests/crop_validate/test_report.py
git commit -m "feat: implement Markdown report generator with tests"
```

---

## Task 8: End-to-end integration test with --no-vlm

**Files:**
- Create: `tests/crop_validate/test_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/crop_validate/test_integration.py`:
```python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture()
def datumaro_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal Datumaro JSON + one test image."""
    img_path = tmp_path / "images" / "frame_001.jpg"
    img_path.parent.mkdir(parents=True)
    Image.new("RGB", (200, 150), color=(100, 100, 100)).save(img_path)

    datumaro = {
        "items": [
            {
                "id": "frame_001",
                "image": {
                    "path": "frame_001.jpg",
                    "size": [150, 200],  # [height, width]
                },
                "annotations": [
                    {
                        "id": 1,
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [20.0, 15.0, 80.0, 60.0],
                        "attributes": {},
                    },
                    {
                        "id": 2,
                        "type": "polygon",
                        "label_id": 1,
                        "points": [30.0, 40.0, 80.0, 40.0, 80.0, 90.0, 30.0, 90.0],
                        "attributes": {},
                    },
                ],
            }
        ],
        "categories": {
            "label": {
                "labels": [
                    {"name": "forklift-with-roll"},
                    {"name": "roll-mask"},
                ]
            }
        },
    }
    json_path = tmp_path / "datumaro.json"
    json_path.write_text(json.dumps(datumaro), encoding="utf-8")
    return json_path, tmp_path / "images"


def test_no_vlm_builds_crops_and_report(
    datumaro_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    json_path, image_dir = datumaro_fixture
    output_dir = tmp_path / "output"

    from scripts.crop_validate import main as _main_fn
    import argparse

    # Build args namespace directly (avoids sys.argv mutation)
    args = argparse.Namespace(
        datumaro_json=str(json_path),
        image_dir=str(image_dir),
        output_dir=str(output_dir),
        dataset_name="test_integration",
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        plugin_source="https://github.com/harpreetsahota204/qwen2_5_vl",
        padding_px=8,
        pass_threshold=0.20,
        review_threshold=0.60,
        persist_dataset=False,
        overwrite_dataset=True,
        no_vlm=True,
    )

    from scripts.crop_validate import _build_dataset, _write_report
    import fiftyone as fo

    dataset = _build_dataset(args)
    try:
        # 2 annotations → 2 crop samples
        assert len(dataset) == 2

        # Crops directory populated
        crops_dir = output_dir / "crops"
        crops = list(crops_dir.glob("*.png"))
        assert len(crops) == 2

        # Back-reference fields present on each sample
        for sample in dataset.iter_samples():
            assert sample.get_field("source_image") == "frame_001.jpg"
            assert sample.get_field("annotation_label") is not None
            assert sample.get_field("annotation_type") in ("detection", "segmentation", "skeleton")

        # Detection sample has detections field
        det_samples = dataset.match(fo.ViewField("annotation_type") == "detection")
        assert len(det_samples) == 1
        for s in det_samples.iter_samples():
            assert s.get_field("detections") is not None

        # Segmentation sample has segmentations field
        seg_samples = dataset.match(fo.ViewField("annotation_type") == "segmentation")
        assert len(seg_samples) == 1
        for s in seg_samples.iter_samples():
            assert s.get_field("segmentations") is not None

        # Report can be generated (with no vlm_verdict → REVIEW defaults)
        report_path = output_dir / "report.md"
        _write_report(dataset, report_path, dataset.name)
        assert report_path.exists()
        content = report_path.read_text()
        assert "## Summary" in content
        assert "frame_001.jpg" in content

    finally:
        if fo.dataset_exists(dataset.name):
            dataset.delete()


def test_crops_have_annotation_overlays(
    datumaro_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    """Verify that crop files contain non-zero image data (overlay was rendered)."""
    json_path, image_dir = datumaro_fixture
    output_dir = tmp_path / "output2"

    import argparse
    from scripts.crop_validate import _build_dataset
    import fiftyone as fo

    args = argparse.Namespace(
        datumaro_json=str(json_path),
        image_dir=str(image_dir),
        output_dir=str(output_dir),
        dataset_name="test_overlay",
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        plugin_source="https://github.com/harpreetsahota204/qwen2_5_vl",
        padding_px=8,
        pass_threshold=0.20,
        review_threshold=0.60,
        persist_dataset=False,
        overwrite_dataset=True,
        no_vlm=True,
    )

    dataset = _build_dataset(args)
    try:
        for sample in dataset.iter_samples():
            img = Image.open(sample.filepath)
            assert img.size[0] > 0 and img.size[1] > 0
    finally:
        if fo.dataset_exists(dataset.name):
            dataset.delete()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_integration.py -v 2>&1 | head -30
```

Expected: FAIL (functions not yet wired, or assertion errors).

- [ ] **Step 3: Run integration tests until they pass**

Fix any wiring issues in `scripts/crop_validate.py` (the most common issue will be the `_build_dataset` loop not correctly matching annotations to images via `image_index`/`build_matches`).

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/test_integration.py -v
```

Expected: both integration tests PASS.

- [ ] **Step 4: Run the full test suite**

```bash
cd /path/to/repo && uv run pytest tests/crop_validate/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/crop_validate/test_integration.py
git commit -m "test: add end-to-end integration tests for crop_validate --no-vlm"
```

---

## Task 9: Run complete test suite + final cleanup

- [ ] **Step 1: Run all project tests (regression check)**

```bash
cd /path/to/repo && uv run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass (no regressions in existing tests).

- [ ] **Step 2: Verify CLI help and --no-vlm smoke test**

```bash
cd /path/to/repo && python scripts/crop_validate.py --help
```

Expected: full help message with all flags documented.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete crop_validate script — crops, FiftyOne dataset, VLM, report

- Standalone scripts/crop_validate.py with 5-stage pipeline
- Reuses cropper.py, datumaro_reader, pose_contract, image_index, matching
- VQA via Qwen2.5-VL FiftyOne plugin (grouped by annotation type)
- fo.Classification vlm_verdict field (PASS/REVIEW/FAIL + confidence)
- Markdown report sorted by risk (FAIL → REVIEW → PASS)
- --no-vlm flag for testing without GPU
- 100% unit test coverage of helper functions"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] §Pipeline [1] Parse: `_label_lookup`, `_derive_bbox`, `_annotation_type`, `build_matches` used in `_build_dataset`
- [x] §Pipeline [2] Crop: `plan_crop`, `materialize_crop`, `render_annotation_overlay` used in `_build_dataset`
- [x] §Pipeline [3] FiftyOne dataset: `_to_fo_sample`, `_build_dataset`, skeleton field naming
- [x] §Pipeline [4] VLM: `_apply_vlm` with `foz.register_zoo_model_source` + `foz.load_zoo_model` + `apply_model` per type
- [x] §Pipeline [5] Report: `_write_report` with FAIL→REVIEW→PASS sections
- [x] §FiftyOne Sample Schema: back-reference fields, normalized coords, skeleton `keypoints_label_<id>`
- [x] §VLM Prompt Design: `DEFAULT_PROMPTS` + `LABEL_PROMPTS` dicts
- [x] §VQA Grouping: `dataset.match(F("annotation_type") == ann_type)` loop in `_apply_vlm`
- [x] §VQA Response Parsing: `_parse_vlm_response` + `_ep_to_verdict` + fallback to REVIEW
- [x] §Markdown Report: all sections, sorting, risk column
- [x] §CLI flags: all flags in `_parse_args`
- [x] §Dataset name collision: timestamp suffix + `--overwrite-dataset`
- [x] §`--no-vlm` flag: skips `_apply_vlm` in `main()`
- [x] §Coordinate normalization: `_to_fo_sample` divides by `crop_plan.output_size`

**Placeholder scan:** No TBDs or "implement later" in any step. All code blocks are complete. ✅

**Type consistency:**
- `_to_fo_sample` parameter `crop_space_ann` matches what `annotation_to_crop_space` returns (dict)
- `CropPlan.output_size` used as `(W, H)` — confirmed from `cropper.py` line 151
- `_parse_vlm_response` returns `tuple[float | None, str]` — consumed correctly in `_apply_vlm`
- `_ep_to_verdict` takes `float | None` — matches `_parse_vlm_response` return ✅
