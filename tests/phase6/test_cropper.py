from __future__ import annotations

from pathlib import Path

import pytest
from fiftyone_pose_importer.verification.config import load_verification_config
from PIL import Image

from fiftyone_pose_importer.verification.cropper import (
    annotation_to_crop_space,
    materialize_crop,
    plan_crop,
    render_annotation_overlay,
)
from fiftyone_pose_importer.verification.types import DeterministicVerdict


def test_annotation_to_crop_space_skeleton() -> None:
    plan = plan_crop(
        image_width=1000,
        image_height=1000,
        bbox=(100.0, 200.0, 50.0, 60.0),
        padding_px=10,
        is_skeleton=True,
    )
    # padded_bounds = (90, 190, 160, 270) → origin = (90, 190)
    ann = {
        "bbox": [100.0, 200.0, 50.0, 60.0],
        "keypoints": [[120.0, 220.0], [140.0, 250.0]],
        "attributes": {"clamp-type": "2-arm"},
    }
    result = annotation_to_crop_space(ann, plan)
    assert result["bbox"] == [10.0, 10.0, 50.0, 60.0]  # origin translated, w/h unchanged
    assert result["keypoints"] == [[30.0, 30.0], [50.0, 60.0]]
    assert result["attributes"] == {"clamp-type": "2-arm"}  # unchanged


def test_annotation_to_crop_space_non_skeleton() -> None:
    plan = plan_crop(
        image_width=1000,
        image_height=1000,
        bbox=(100.0, 200.0, 50.0, 60.0),
        padding_px=10,
        is_skeleton=False,
    )
    # clipped_bounds = (90, 190, 160, 270) → origin = (90, 190)
    ann = {
        "bbox": [100.0, 200.0, 50.0, 60.0],
        "keypoints": None,
        "attributes": {},
    }
    result = annotation_to_crop_space(ann, plan)
    assert result["bbox"] == [10.0, 10.0, 50.0, 60.0]
    assert result["keypoints"] is None  # None keypoints pass through unchanged


def test_annotation_to_crop_space_failed_plan_returns_unchanged() -> None:
    plan = plan_crop(
        image_width=100,
        image_height=100,
        bbox=(10.0, 10.0, 0.0, 0.0),  # invalid — zero size
        padding_px=5,
        is_skeleton=False,
    )
    assert plan.verdict is DeterministicVerdict.FAIL
    ann = {"bbox": [10.0, 10.0, 0.0, 0.0], "keypoints": None, "attributes": {}}
    result = annotation_to_crop_space(ann, plan)
    # No bounds on a failed plan — returns annotation unchanged
    assert result == ann


def test_annotation_to_crop_space_polygon_points() -> None:
    plan = plan_crop(
        image_width=1000,
        image_height=1000,
        bbox=(100.0, 200.0, 50.0, 60.0),
        padding_px=10,
        is_skeleton=False,
    )
    # clipped_bounds origin = (90, 190)
    ann = {
        "bbox": [100.0, 200.0, 50.0, 60.0],
        "polygon_points": [[100.0, 200.0], [150.0, 200.0], [150.0, 260.0], [100.0, 260.0]],
    }
    result = annotation_to_crop_space(ann, plan)
    assert result["polygon_points"] == [[10.0, 10.0], [60.0, 10.0], [60.0, 70.0], [10.0, 70.0]]


def test_skeleton_preserves_padded_canvas_with_out_of_image_fill() -> None:
    plan = plan_crop(
        image_width=100,
        image_height=80,
        bbox=(10.0, 5.0, 20.0, 10.0),
        padding_px=16,
        is_skeleton=True,
    )

    assert plan.verdict is DeterministicVerdict.PASS
    assert plan.policy == "skeleton_preserve_canvas"
    assert plan.padded_bounds == (-6, -11, 46, 31)
    assert plan.clipped_bounds == (0, 0, 46, 31)
    assert plan.output_size == (52, 42)
    assert plan.paste_offset == (6, 11)


def test_non_skeleton_clips_crop_to_image_bounds() -> None:
    plan = plan_crop(
        image_width=100,
        image_height=80,
        bbox=(10.0, 5.0, 20.0, 10.0),
        padding_px=16,
        is_skeleton=False,
    )

    assert plan.verdict is DeterministicVerdict.PASS
    assert plan.policy == "non_skeleton_clip"
    assert plan.padded_bounds == (-6, -11, 46, 31)
    assert plan.clipped_bounds == (0, 0, 46, 31)
    assert plan.output_size == (46, 31)
    assert plan.paste_offset == (0, 0)


def test_invalid_bbox_is_deterministic_fail() -> None:
    plan = plan_crop(
        image_width=100,
        image_height=80,
        bbox=(10.0, 5.0, 0.0, 10.0),
        padding_px=8,
        is_skeleton=True,
    )

    assert plan.verdict is DeterministicVerdict.FAIL
    assert plan.reason == "invalid_bbox"


def test_padding_px_is_consumed_from_config() -> None:
    config, _warnings = load_verification_config({"padding_px": 24})
    plan = plan_crop(
        image_width=100,
        image_height=80,
        bbox=(20.0, 10.0, 30.0, 20.0),
        padding_px=config.padding_px,
        is_skeleton=False,
    )

    assert plan.padding_px == 24
    assert plan.padded_bounds == (-4, -14, 74, 54)


def test_out_of_frame_skeleton_points_are_marked_occluded() -> None:
    plan = plan_crop(
        image_width=100,
        image_height=100,
        bbox=(20.0, 20.0, 40.0, 40.0),
        padding_px=8,
        is_skeleton=True,
        keypoints=[(-5.0, 50.0), (10.0, 10.0), (120.0, 2.0)],
        visibility=[2, 2, 2],
    )

    assert plan.adjusted_visibility == [1, 2, 1]
    assert plan.out_of_frame_point_indices == [0, 2]


def test_materialize_crop_skeleton_padded_canvas(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10), (255, 0, 0)).save(source)

    plan = plan_crop(
        image_width=10,
        image_height=10,
        bbox=(2.0, 2.0, 4.0, 4.0),
        padding_px=4,
        is_skeleton=True,
    )
    out_path = tmp_path / "skeleton.png"

    written = materialize_crop(source_image_path=source, crop_plan=plan, output_path=out_path)

    assert written == out_path
    saved = Image.open(out_path)
    assert saved.size == plan.output_size
    assert saved.getpixel((0, 0)) == (0, 0, 0)
    assert saved.getpixel((2, 2)) == (255, 0, 0)


def test_materialize_crop_non_skeleton_clipped(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10), (255, 0, 0)).save(source)

    plan = plan_crop(
        image_width=10,
        image_height=10,
        bbox=(2.0, 2.0, 4.0, 4.0),
        padding_px=4,
        is_skeleton=False,
    )
    out_path = tmp_path / "bbox.png"

    written = materialize_crop(source_image_path=source, crop_plan=plan, output_path=out_path)

    assert written == out_path
    saved = Image.open(out_path)
    assert saved.size == plan.output_size
    assert saved.size == (10, 10)
    assert saved.getpixel((0, 0)) == (255, 0, 0)


def test_render_annotation_overlay_bbox_only(tmp_path: Path) -> None:
    """Bbox-only annotation renders orange-red rectangle outline."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (100, 100), (200, 200, 200)).save(source)

    annotation = {"bbox": [10.0, 10.0, 50.0, 40.0], "keypoints": None, "visibility": None, "polygon_points": None}
    out = tmp_path / "overlay.png"
    result = render_annotation_overlay(source, annotation, out)

    assert result == out
    assert out.exists()
    img = Image.open(out)
    assert img.size == (100, 100)


def test_render_annotation_overlay_keypoints_color_coded(tmp_path: Path) -> None:
    """Skeleton annotation draws color-coded keypoint dots, no bbox."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(source)

    annotation = {
        "bbox": [0.0, 0.0, 100.0, 100.0],  # bbox present but should NOT be drawn
        "keypoints": [[20.0, 20.0], [50.0, 50.0], [80.0, 80.0]],
        "visibility": [2, 1, 0],  # visible, occluded, unlabeled
        "polygon_points": None,
    }
    out = tmp_path / "kp_overlay.png"
    render_annotation_overlay(source, annotation, out)

    img = Image.open(out)
    r_vis = img.getpixel((20, 20))   # visible → green
    r_occ = img.getpixel((50, 50))   # occluded → orange
    r_unl = img.getpixel((80, 80))   # unlabeled → gray

    assert r_vis[1] > r_vis[0] and r_vis[1] > r_vis[2], "visible dot should be greenish"
    assert r_occ[0] > r_occ[2], "occluded dot should be reddish/orange"
    assert abs(int(r_unl[0]) - int(r_unl[1])) < 30, "unlabeled dot should be grayish"


def test_render_annotation_overlay_polygon(tmp_path: Path) -> None:
    """Polygon annotation draws cyan-blue outline, no keypoint dots."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(source)

    annotation = {
        "bbox": None,
        "keypoints": None,
        "visibility": None,
        "polygon_points": [[10.0, 10.0], [90.0, 10.0], [90.0, 90.0], [10.0, 90.0]],
    }
    out = tmp_path / "poly_overlay.png"
    render_annotation_overlay(source, annotation, out)

    assert out.exists()
    img = Image.open(out)
    # Polygon top edge pixel should have blue channel elevated (cyan-blue color)
    edge_pixel = img.getpixel((50, 10))
    assert edge_pixel[2] > 100, "polygon edge should have blue component"


def test_render_annotation_overlay_no_annotations(tmp_path: Path) -> None:
    """Empty annotation dict produces a copy of the source with no crash."""
    source = tmp_path / "crop.png"
    Image.new("RGB", (60, 60), (128, 128, 128)).save(source)

    annotation: dict = {}
    out = tmp_path / "empty_overlay.png"
    render_annotation_overlay(source, annotation, out)

    assert out.exists()
    img = Image.open(out)
    assert img.size == (60, 60)


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
