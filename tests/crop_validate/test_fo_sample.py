from __future__ import annotations

import math
from pathlib import Path

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
        expected = [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]
        for actual, exp in zip(polyline.points[0], expected):
            assert actual == pytest.approx(exp)
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
        kp_field = "keypoints_clamp_2_arm"
        assert kp_field in sample.field_names
        kp = sample[kp_field].keypoints[0]
        # visible: [40/400, 30/300] = [0.1, 0.1]
        assert kp.points[0] == pytest.approx([0.1, 0.1])
        # occluded (vis=1): still normalized — NOT nan
        assert kp.points[1] == pytest.approx([0.5, 0.5])
        # absent (vis=0): should be [nan, nan]
        assert math.isnan(kp.points[2][0])
        assert math.isnan(kp.points[2][1])

    def test_skeleton_field_name_uses_label_name(self) -> None:
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
        assert "keypoints_clamp_3_arm" in sample.field_names
        assert "keypoints_clamp_2_arm" not in sample.field_names
