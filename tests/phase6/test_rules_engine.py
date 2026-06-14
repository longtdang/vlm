from __future__ import annotations

from fiftyone_pose_importer.verification.config import load_verification_config
from fiftyone_pose_importer.verification.engine import evaluate_object
from fiftyone_pose_importer.verification.types import DeterministicVerdict


def _valid_annotation() -> dict[str, object]:
    return {
        "bbox": [10.0, 20.0, 40.0, 50.0],
        "attributes": {"clamp_type": "2-arm", "roll_count": 2},
        "keypoints": [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]],
        "visibility": [2, 1, 2, 2],
    }


def test_any_failed_rule_forces_object_fail() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [
                        {"name": "required_attributes", "params": {"required": ["clamp_type"]}},
                        {"name": "roll_count_positive"},
                    ],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    bad = _valid_annotation()
    bad["attributes"] = {"clamp_type": "2-arm", "roll_count": 0}

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=bad,
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert "roll_count_non_positive" in outcome.result.failure_reasons
    assert {r.verdict.value for r in outcome.result.rule_results} <= {"PASS", "FAIL"}


def test_unevaluable_rule_is_converted_to_explicit_fail_reason() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    bad = _valid_annotation()
    bad["bbox"] = "not-a-bbox"

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=bad,
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert any(reason.startswith("unevaluable:") for reason in outcome.result.failure_reasons)


def test_unknown_rule_names_are_warning_only_and_skipped() -> None:
    config, warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty", "made_up_rule"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                }
            }
        }
    )

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-with-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=_valid_annotation(),
        config=config,
    )

    assert any("made_up_rule" in warning for warning in warnings)
    assert all(result.rule_name != "made_up_rule" for result in outcome.result.rule_results)
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_per_label_override_rules_are_applied() -> None:
    config, _warnings = load_verification_config(
        {
            "rules": {
                "global": {
                    "detection": ["bbox_non_empty"],
                    "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                    "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                    "visibility-format": ["visibility_codes"],
                },
                "overrides": {
                    "forklift-no-roll": {
                        "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type", "serial"]}}]
                    }
                },
            }
        }
    )

    outcome = evaluate_object(
        sample_id="sample-1",
        object_id="obj-1",
        label="forklift-no-roll",
        crop_path="runs/001/crops/sample-1_obj-1.png",
        annotation=_valid_annotation(),
        config=config,
    )

    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert "missing_required_attribute:serial" in outcome.result.failure_reasons


def _skeleton_annotation_with_out_of_frame(out_of_frame_indices: list[int], visibility: list[int]) -> dict[str, object]:
    keypoints = [[float(i), float(i)] for i in range(len(visibility))]
    return {
        "bbox": [10.0, 10.0, 40.0, 40.0],
        "attributes": {},
        "keypoints": keypoints,
        "visibility": visibility,
        "out_of_frame_indices": out_of_frame_indices,
    }


def test_out_of_frame_points_visible_fails() -> None:
    """A keypoint outside the frame marked v=2 (visible) must fail."""
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = _skeleton_annotation_with_out_of_frame(out_of_frame_indices=[0], visibility=[2, 1, 1])
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert any("out_of_frame_points_visible" in (r or "") for r in outcome.result.failure_reasons)


def test_out_of_frame_points_occluded_passes() -> None:
    """A keypoint outside the frame correctly marked v=1 (occluded) should pass."""
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = _skeleton_annotation_with_out_of_frame(out_of_frame_indices=[0, 2], visibility=[1, 2, 1])
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_out_of_frame_unlabeled_passes() -> None:
    """A keypoint outside the frame marked v=0 (unlabeled) is not a visible violation."""
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = _skeleton_annotation_with_out_of_frame(out_of_frame_indices=[1], visibility=[2, 0, 2])
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_no_out_of_frame_points_passes() -> None:
    """When no out-of-frame indices are present the rule is a no-op."""
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = _skeleton_annotation_with_out_of_frame(out_of_frame_indices=[], visibility=[2, 2, 1])
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_out_of_frame_indices_missing_passes() -> None:
    """Annotations without out_of_frame_indices (bbox/polygon types) skip silently."""
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = {"bbox": [0.0, 0.0, 50.0, 50.0], "attributes": {}, "keypoints": None, "visibility": []}
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.PASS


def test_out_of_frame_visible_in_original_fails_after_adjustment() -> None:
    """Rule must detect the original annotator violation even after plan_crop adjusts visibility.

    run_verify.py stores crop.adjusted_visibility in annotation_payload["visibility"], which
    silently changes out-of-frame points from 2→1 before the rule runs.  The rule must read
    annotation["original_visibility"] (the pre-adjustment copy) to see that the annotator
    originally marked those points as visible (=2).

    Before fix: rule reads visibility[0]==1  → no violation → PASS  (false pass)
    After fix:  rule reads original_visibility[0]==2 → violation → FAIL (correct)
    """
    config, _ = load_verification_config(
        {"rules": {"global": {"visibility-format": ["out_of_frame_occluded"], "skeleton-count": []}}}
    )
    ann = {
        "bbox": [10.0, 10.0, 40.0, 40.0],
        "attributes": {},
        "keypoints": [[-5.0, -5.0], [20.0, 20.0], [30.0, 30.0]],
        # adjusted_visibility: out-of-frame point at idx=0 already auto-corrected to 1
        "visibility": [1, 2, 1],
        # original_visibility: what the annotator actually submitted (idx=0 was visible=2)
        "original_visibility": [2, 2, 1],
        "out_of_frame_indices": [0],
    }
    outcome = evaluate_object(
        sample_id="s", object_id="o", label="x", crop_path="x.png",
        annotation=ann, config=config,
    )
    assert outcome.result.verdict is DeterministicVerdict.FAIL
    assert any("out_of_frame_points_visible" in (r or "") for r in outcome.result.failure_reasons)
