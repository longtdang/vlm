from __future__ import annotations

from fiftyone_pose_importer.verification.config import load_verification_config
from PIL import Image

from fiftyone_pose_importer.verification.cropper import annotation_to_crop_space, materialize_crop, plan_crop
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
