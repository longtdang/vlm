---
slug: vlm-occlusion-contradiction
status: investigating
trigger: "VLM occlusion_state: reason says 'no occluded parts' (ep=0.0) but orange dots ARE on occluded keypoints"
created: 2026-06-14
updated: 2026-06-14T07:20:00Z
---

## Symptoms

- **VLM trace line 6**: `sample_id=cf-flow-3CekECM0BRzSP1JGtHMCPo3DkXJ`, `object_id=ann-9`, `label=clamp-2-arm`
- `occlusion_state_ep=0.0` (PASS) but reason: "All green dots are on the visible parts of the clamp and label, and all orange dots are on the label, which is fully visible. There are no occluded parts of the label or clamp that would require orange dots to be on the occluded parts."
- **User observation**: The orange points ARE on invisible/occluded parts (behind the paper roll)
- `keypoint_position_ep=0.0` reason correctly identifies green dots on the clamp structure

## Known Facts

### Annotation (index 9, skeleton, label_id=4 = clamp-2-arm)
Points format: [x, y, visibility, ...]
- Point 0: (1406.2, 601.47, v=1) — occluded
- Point 1: (1635.46, 602.32, v=1) — occluded
- Point 2: (1416.53, 847.78, v=1) — occluded
- Point 3: (1632.26, 849.25, v=1) — occluded
- Points 4-11: all v=2 (visible)

### Crop image
- Shows clamp-2-arm grasping a paper roll
- Green dots correctly placed on outer visible clamp arm surfaces
- Orange dots placed where inner clamp surfaces meet the roll (CORRECTLY occluded — hidden behind roll)
- Large PAPERTECH sticker visible on the white roll surface

### VLM contradiction
- Reason says "orange dots on the label, which is fully visible"
- But orange dots are NOT on the PAPERTECH sticker — they're on inner clamp positions
- ep=0.0 (correct verdict) contradicts the wrong reasoning

## Current Focus
hypothesis: CONFIRMED — Two prompt defects cause the VLM misidentification, with no code bug in the rendering pipeline.

reasoning_checkpoint:
  hypothesis: "The VLM misidentifies orange dots as being on the PAPERTECH sticker due to (1) the word 'label' in the prompt colliding with the visible product label sticker, and (2) the prompt failing to explain that occluded keypoints project to positions ON the occluding object. No code bug exists."
  confirming_evidence:
    - "Orange dots in crop-space: KP0=(361,51), KP1=(590,52), KP2=(372,298), KP3=(587,299). KP2 and KP3 fall inside the PAPERTECH sticker bounding region (~x=285-640, y=90-415). KP0 and KP1 are above the sticker but in the white roll surface area (right half of image, x=361/590)."
    - "Crop is exactly 642x466px (padded_bounds=(1045,550,1687,1016), padding=16px). Coordinates verified against actual image output size — exact match, no translation error."
    - "VLM reasoning uses 'label' to mean the PAPERTECH sticker: 'orange dots are on the label, which is fully visible.' The prompt says 'You are validating label clamp-2-arm' — the word 'label' appears in the prompt and a label sticker appears in the image."
    - "RULE_ANNOTATION_FIELDS for occlusion_state = [] — no annotation data injected. The VLM only sees the image and the prompt. No coordinate data available to help it resolve spatial ambiguity."
    - "annotation_to_crop_space correctly uses padded_bounds origin for skeleton policy. render_annotation_overlay correctly maps v=1→orange, v=2→green. No rendering bug."
  falsification_test: "If we change the prompt to use 'annotation class' instead of 'label' and explain that orange dots on the roll surface are correct, the VLM reasoning should stop referencing the PAPERTECH sticker. If the orange dots were drawn at wrong positions, they would not match the computed crop-space coordinates — but they do match exactly."
  fix_rationale: "Prompt word 'label' and absent positional semantics explanation are the root causes. Fixing both in the prompt resolves the VLM's confusion."
  blind_spots: "Model capability ceiling (2b): even with a better prompt, a small model may still fail on complex spatial occlusion reasoning. Not tested with improved prompt."

next_action: Return Root Cause Report (diagnosis-only mode)
