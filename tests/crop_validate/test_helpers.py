from __future__ import annotations

import pytest
from scripts.crop_validate import (
    _annotation_type,
    _derive_bbox,
    _is_skeleton_type,
    _label_lookup,
    _safe_token,
    _to_field_name,
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

    def test_dash_becomes_underscore(self) -> None:
        assert _safe_token("frame-001") == "frame_001"

    def test_empty_becomes_unknown(self) -> None:
        assert _safe_token("") == "unknown"


class TestToFieldName:
    def test_roll_keypoints(self) -> None:
        assert _to_field_name("roll-keypoints") == "keypoints_roll_keypoints"

    def test_clamp_2_arm(self) -> None:
        assert _to_field_name("clamp-2-arm") == "keypoints_clamp_2_arm"

    def test_clamp_3_arm(self) -> None:
        assert _to_field_name("clamp-3-arm") == "keypoints_clamp_3_arm"

    def test_uppercase_lowercased(self) -> None:
        assert _to_field_name("MyLabel") == "keypoints_mylabel"

    def test_spaces_normalized(self) -> None:
        assert _to_field_name("my label") == "keypoints_my_label"

    def test_empty_becomes_unknown(self) -> None:
        assert _to_field_name("") == "keypoints_unknown"

    def test_leading_trailing_separators_stripped(self) -> None:
        assert _to_field_name("-arm-") == "keypoints_arm"
