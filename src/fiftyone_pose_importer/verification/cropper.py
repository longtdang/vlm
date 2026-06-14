from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .types import DeterministicVerdict


@dataclass(frozen=True)
class CropPlan:
    verdict: DeterministicVerdict
    reason: str | None
    policy: str
    padding_px: int
    padded_bounds: tuple[int, int, int, int] | None
    clipped_bounds: tuple[int, int, int, int] | None
    output_size: tuple[int, int] | None
    paste_offset: tuple[int, int] | None
    adjusted_visibility: list[int] | None
    out_of_frame_point_indices: list[int]


def annotation_to_crop_space(
    annotation: dict[str, Any],
    crop_plan: CropPlan,
) -> dict[str, Any]:
    """Translate bbox and keypoint coordinates from original image space to crop image space.

    The VLM receives a crop of the original image. Annotation coordinates must
    be expressed in crop-space so the model can correlate them with what it sees.

    Coordinate origin:
    - skeleton (``skeleton_preserve_canvas``): top-left of the padded canvas
      (``padded_bounds``), which is the full crop canvas including black borders.
    - non-skeleton (``non_skeleton_clip``): top-left of the clipped region
      (``clipped_bounds``), which is the actual crop extent.

    Width/height of ``bbox`` and visibility codes are preserved unchanged.
    """
    if crop_plan.policy == "skeleton_preserve_canvas":
        if crop_plan.padded_bounds is None:
            return annotation
        ox, oy = crop_plan.padded_bounds[0], crop_plan.padded_bounds[1]
    else:
        if crop_plan.clipped_bounds is None:
            return annotation
        ox, oy = crop_plan.clipped_bounds[0], crop_plan.clipped_bounds[1]

    result = dict(annotation)

    if isinstance(result.get("bbox"), (list, tuple)) and len(result["bbox"]) == 4:
        bx, by, bw, bh = result["bbox"]
        result["bbox"] = [bx - ox, by - oy, bw, bh]

    if isinstance(result.get("keypoints"), list):
        result["keypoints"] = [
            [kx - ox, ky - oy] for kx, ky in result["keypoints"]
        ]

    return result

def _bbox_bounds(bbox: tuple[float, float, float, float], padding_px: int) -> tuple[int, int, int, int]:
    x, y, w, h = bbox
    return (
        math.floor(x) - padding_px,
        math.floor(y) - padding_px,
        math.ceil(x + w) + padding_px,
        math.ceil(y + h) + padding_px,
    )


def _clip_bounds(bounds: tuple[int, int, int, int], image_width: int, image_height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bounds
    return (max(0, x0), max(0, y0), min(image_width, x1), min(image_height, y1))


def _mark_out_of_frame_as_occluded(
    *,
    image_width: int,
    image_height: int,
    keypoints: list[tuple[float, float]] | None,
    visibility: list[int] | None,
) -> tuple[list[int] | None, list[int]]:
    if keypoints is None and visibility is None:
        return None, []

    if keypoints is None or visibility is None or len(keypoints) != len(visibility):
        return visibility, []

    adjusted = list(visibility)
    out_of_frame_indices: list[int] = []
    for idx, ((x, y), vis) in enumerate(zip(keypoints, visibility)):
        if x < 0 or y < 0 or x >= image_width or y >= image_height:
            out_of_frame_indices.append(idx)
            if vis != 0:
                adjusted[idx] = 1

    return adjusted, out_of_frame_indices


def plan_crop(
    *,
    image_width: int,
    image_height: int,
    bbox: tuple[float, float, float, float],
    padding_px: int,
    is_skeleton: bool,
    keypoints: list[tuple[float, float]] | None = None,
    visibility: list[int] | None = None,
) -> CropPlan:
    _x, _y, w, h = bbox
    if w <= 0 or h <= 0:
        return CropPlan(
            verdict=DeterministicVerdict.FAIL,
            reason="invalid_bbox",
            policy="invalid_bbox",
            padding_px=padding_px,
            padded_bounds=None,
            clipped_bounds=None,
            output_size=None,
            paste_offset=None,
            adjusted_visibility=visibility,
            out_of_frame_point_indices=[],
        )

    padded_bounds = _bbox_bounds(bbox, padding_px)
    clipped_bounds = _clip_bounds(padded_bounds, image_width, image_height)
    px0, py0, px1, py1 = padded_bounds
    cx0, cy0, cx1, cy1 = clipped_bounds

    adjusted_visibility, out_of_frame_indices = _mark_out_of_frame_as_occluded(
        image_width=image_width,
        image_height=image_height,
        keypoints=keypoints,
        visibility=visibility,
    )

    if is_skeleton:
        output_size = (max(0, px1 - px0), max(0, py1 - py0))
        paste_offset = (max(0, cx0 - px0), max(0, cy0 - py0))
        policy = "skeleton_preserve_canvas"
    else:
        output_size = (max(0, cx1 - cx0), max(0, cy1 - cy0))
        paste_offset = (0, 0)
        policy = "non_skeleton_clip"

    return CropPlan(
        verdict=DeterministicVerdict.PASS,
        reason=None,
        policy=policy,
        padding_px=padding_px,
        padded_bounds=padded_bounds,
        clipped_bounds=clipped_bounds,
        output_size=output_size,
        paste_offset=paste_offset,
        adjusted_visibility=adjusted_visibility,
        out_of_frame_point_indices=out_of_frame_indices,
    )


def materialize_crop(*, source_image_path: Path | str, crop_plan: CropPlan, output_path: Path | str) -> Path:
    if crop_plan.verdict is DeterministicVerdict.FAIL:
        raise ValueError(f"Cannot materialize failed crop plan: {crop_plan.reason or 'crop_failed'}")
    if crop_plan.clipped_bounds is None or crop_plan.output_size is None or crop_plan.paste_offset is None:
        raise ValueError("Crop plan is missing bounds metadata")

    source_path = Path(source_image_path)
    destination = Path(output_path)

    with Image.open(source_path) as opened:
        source = opened.convert("RGB")
        cx0, cy0, cx1, cy1 = crop_plan.clipped_bounds
        clipped = source.crop((cx0, cy0, cx1, cy1))

        if crop_plan.policy == "skeleton_preserve_canvas":
            rendered = Image.new("RGB", crop_plan.output_size, color=(0, 0, 0))
            if clipped.size[0] > 0 and clipped.size[1] > 0:
                rendered.paste(clipped, crop_plan.paste_offset)
        else:
            rendered = clipped

        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered.save(destination, format="PNG")

    return destination
