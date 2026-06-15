---
status: resolved
trigger: "out-of-frame points auto-changed to orange (occluded) before deterministic rule runs — rule always PASSes, never detects bad visibility"
created: 2026-06-14T14:31:10+00:00
updated: 2026-06-14T14:39:38+00:00
---

# Debug Session: out-of-frame-occluded-false-pass

## Symptoms

- expected_behavior: "evaluate_out_of_frame_occluded should FAIL when any out-of-frame keypoint has original visibility=2 (marked visible by annotator). Bad annotations should be caught."
- actual_behavior: "Rule always PASSes. In run_verify.py line 364, annotation_payload['visibility'] is set to crop.adjusted_visibility, which already auto-corrected out-of-frame points from visibility=2 to 1. When evaluate_out_of_frame_occluded checks visibility[idx] == 2, it always finds 1 — the violation is invisible to the rule."
- error_messages: "No runtime error. Silently produces a false PASS for annotations where out-of-frame points are wrongly marked visible."
- timeline: "Always had this behavior — rule was never working correctly since it was introduced."
- reproduction: "Create a skeleton annotation where one or more keypoints have coordinates outside the original image bounds (x<0 or x>=w or y<0 or y>=h) AND original visibility=2. Run run_verify. evaluate_out_of_frame_occluded returns PASS instead of FAIL."

## Current Focus

- hypothesis: "The annotation_payload in run_verify.py uses adjusted_visibility (which pre-corrects out-of-frame visibility to 1) before passing to the rules engine. evaluate_out_of_frame_occluded reads annotation['visibility'] and checks == 2, but adjusted_visibility already replaced 2→1, so the check can never fire. The fix is to store the original visibility separately and have the rule check against original, OR pass original_visibility alongside adjusted_visibility."
- next_action: "Confirm hypothesis by tracing run_verify.py annotation_payload construction (line 364) and rules.py evaluate_out_of_frame_occluded. Then determine the correct fix: store original_visibility in annotation_payload and have the rule check original_visibility[idx] == 2 instead of visibility[idx] == 2."
- test: "Write a test: skeleton annotation with keypoint at (-10, -10) and visibility=2. After plan_crop, adjusted_visibility should have 1 at that index. Verify evaluate_out_of_frame_occluded FAILS (not PASSes) because original visibility was 2."
- expecting: "Confirmed in code — adjusted_visibility in annotation_payload masks the original violation. Rule needs access to pre-adjustment visibility values."

## Evidence

- timestamp: 2026-06-14T14:31:10+00:00
  note: "run_verify.py line 364: annotation_payload['visibility'] = crop.adjusted_visibility if crop.adjusted_visibility is not None else visibility. This uses adjusted (post-correction) values."
- timestamp: 2026-06-14T14:31:10+00:00
  note: "_mark_out_of_frame_as_occluded in cropper.py lines 86-107: for each out-of-frame keypoint (x<0 or y<0 or x>=w or y>=h), if vis != 0, adjusted[idx] = 1. So original visibility=2 becomes 1 in adjusted."
- timestamp: 2026-06-14T14:31:10+00:00
  note: "evaluate_out_of_frame_occluded in rules.py lines 140-143: violations = [idx for idx in out_of_frame if visibility[idx] == 2]. Since visibility is adjusted_visibility from annotation_payload, out-of-frame points always have visibility=1 here — violations is always empty."
- timestamp: 2026-06-14T14:31:10+00:00
  note: "Issue has always existed — rule was designed to catch bad annotations but the pre-processing step removes the evidence before the rule can see it."

## Resolution

root_cause: >
  plan_crop() calls _mark_out_of_frame_as_occluded() which changes out-of-frame point
  visibility from 2→1 in adjusted_visibility. run_verify.py line 364 set
  annotation_payload["visibility"] = crop.adjusted_visibility — so
  evaluate_out_of_frame_occluded always read 1 at out-of-frame indices and could
  never detect violations. Rule always PASSed (false pass).

fix: >
  1. Added original_visibility field to CropPlan dataclass (copy of visibility BEFORE
     _mark_out_of_frame_as_occluded mutates it).
  2. run_verify.py annotation_payload gains "original_visibility": crop.original_visibility.
  3. evaluate_out_of_frame_occluded reads original_visibility when present, falls back
     to visibility for backward compatibility. Now correctly detects out-of-frame points
     that the annotator originally marked as visible (=2).

verification: >
  - New regression test test_out_of_frame_visible_in_original_fails_after_adjustment
    was RED before fix (PASS instead of FAIL) and is GREEN after fix.
  - All 10 rules_engine tests pass. All 49 unaffected phase6 tests pass.
  - 3 pre-existing failures (fiftyone import, rendering font) unchanged.

files_changed:
  - src/fiftyone_pose_importer/verification/cropper.py
  - src/fiftyone_pose_importer/verification/rules.py
  - src/fiftyone_pose_importer/run_verify.py
  - tests/phase6/test_rules_engine.py

commit: 962e029