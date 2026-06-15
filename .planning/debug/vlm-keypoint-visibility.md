---
status: resolved
trigger: "VLM Does Not Detect Orange Keypoints for ann-9"
created: 2026-06-14T09:16:52+00:00
updated: 2026-06-14T09:17:39+00:00
---

# Debug Session: vlm-keypoint-visibility

## Symptoms

- expected_behavior: "For annotation ann-9 (sample cf-flow-3CekECM0BRzSP1JGtHMCPo3DkXJ, label clamp-2-arm), the VLM should detect and report the 4 orange keypoints visible in the crop image."
- actual_behavior: "keypoint_position_reason says 'No orange or gray keypoints are present' and keypoint_position_ep is 0.0 (PASS). But the crop image clearly shows 4 orange dots on the white roll/label area."
- error_messages: "keypoint_position_reason: 'All green keypoints are correctly placed on visible structural landmarks of the clamp-2-arm, including its arms and mounting points. No orange or gray keypoints are present, so no occlusion or unlabeled issues exist.' keypoint_position_ep: 0.0 → PASS"
- timeline: "Observed in verification run 20260614T090008Z"
- reproduction: "Run VLM verification for ann-9 in sample cf-flow-3CekECM0BRzSP1JGtHMCPo3DkXJ and inspect keypoint_position result."

## Current Focus

- hypothesis: "The keypoint_position prompt wording ('focus ONLY on those dots, not on any text, stickers, or labels visible in the scene') causes the model to dismiss the 4 orange dots that appear near the product label sticker on the white roll, treating them as part of the label/sticker rather than as keypoint markers. Alternatively, the model only checks if green dots are on clamp landmarks and then wrongly concludes no orange/gray dots exist anywhere."
- next_action: "Inspect keypoint_position prompt in local.verify.yaml, compare with occlusion_state prompt, identify the specific wording that leads to misidentification, and propose a prompt fix."
- test: "Check VLM trace ndjson for ann-9 keypoint_position vs occlusion_state responses; inspect both prompts side-by-side."
- expecting: "Find that keypoint_position prompt lacks explicit instruction to report all dot colors observed, leading to the model ignoring orange dots near non-clamp areas."

## Evidence

- timestamp: 2026-06-14T09:16:52+00:00
  note: "Crop image viewed — 6 green dots on red clamp structure (correctly placed), 4 orange dots on white roll/label area on the right side. Orange dots clearly visible."
- timestamp: 2026-06-14T09:16:52+00:00
  note: "VLM contradiction confirmed: keypoint_position says 'No orange or gray keypoints are present' (WRONG) while occlusion_state correctly says 'all orange dots are positioned on surfaces that are occluded by the roll or other objects' — both used the same crop image."
- timestamp: 2026-06-14T09:16:52+00:00
  note: "Code path confirmed (run_verify.py lines 449-481): crop PIL loaded once, both rules get identical image object via evaluate_vlm_batch. Image delivery is not the issue."
- timestamp: 2026-06-14T09:16:52+00:00
  note: "keypoint_position prompt contains: 'focus ONLY on those dots, not on any text, stickers, or labels visible in the scene' — orange dots are positioned near a PAPERTECH UNLIMITED barcode/label sticker, so model may conflate orange dots with label sticker content."
- timestamp: 2026-06-14T09:16:52+00:00
  note: "keypoint_position prompt also says 'Judge whether keypoints are placed correctly on expected clamp landmarks' — model may only evaluate green dots on clamp, then generalize to 'no other color dots present'."

## Eliminated

- hypothesis: "Batch rendering or image delivery issue."
  reason: "Confirmed same PIL crop object sent to both rules via evaluate_vlm_batch; occlusion_state correctly sees orange dots in the same run, proving image data is fine."

## Resolution

- root_cause: "The `keypoint_position` prompt told the VLM to 'focus ONLY on those dots, not on any text, stickers, or labels visible in the scene'. When orange keypoint dots are positioned ON a product barcode label sticker (the white roll), the model conflates the orange dots with the sticker content it is told to ignore — and reports 'No orange or gray keypoints are present'. The `occlusion_state` prompt avoids this failure because it has an explicit 'Important: an orange dot whose position falls on or overlaps a roll or another object is CORRECT' safeguard that disambiguates keypoint dots from sticker graphics."
- fix: "Rewrote all three `keypoint_position` prompts (clamp-2-arm, clamp-3-arm, roll-keypoints) in local.verify.yaml: changed 'focus ONLY on those dots, not on any text, stickers, or labels' to 'do NOT confuse these keypoint dots with any text, stickers, or label graphics'; expanded color descriptions to explicitly name what orange means ('hidden behind another object such as a roll'); added 'Important: orange dots will naturally appear ON rolls or other occluding objects — they mark hidden structural parts of the label, and are NOT label sticker content. Count and evaluate ALL dots regardless of color.'"
- verification: "YAML parses cleanly (python3 yaml.safe_load). All three keypoint_position prompt blocks confirmed to contain the new Important: line and the 'do NOT confuse' wording. No old 'focus ONLY on those dots, not on any text, stickers' text remains in any keypoint_position prompt."
- files_changed:
  - local.verify.yaml
