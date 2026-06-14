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

    if isinstance(result.get("polygon_points"), list):
        result["polygon_points"] = [
            [px - ox, py - oy] for px, py in result["polygon_points"]
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


# Visibility-code → overlay color mapping
_VIS_COLORS: dict[int, tuple[int, int, int]] = {
    2: (0, 230, 0),     # visible → bright green
    1: (255, 165, 0),   # occluded → orange
    0: (140, 140, 140), # unlabeled → gray
}
_VIS_DEFAULT_COLOR = (200, 0, 200)  # magenta for unknown codes
_KEYPOINT_RADIUS = 6                # dot radius in pixels
_BBOX_COLOR = (255, 80, 0)          # orange-red for bbox rectangle
_BBOX_WIDTH = 3                     # outline stroke width
_POLYGON_COLOR = (80, 200, 255)     # cyan-blue for polygon outline


def render_annotation_overlay(
    crop_image_path: Path | str,
    annotation_crop_space: dict[str, Any],
    output_path: Path | str,
) -> Path:
    """Render a copy of the crop image with annotation overlaid for VLM inspection.

    Drawing mode is inferred from the annotation payload:
    - **Polygon** (``polygon_points`` present and non-empty): draws a closed
      polygon outline in cyan-blue. No bbox, no keypoint dots.
    - **Skeleton** (``keypoints`` present and non-empty): draws color-coded
      filled circles per keypoint. No bbox rectangle.
      green  (0,230,0)   — visible (code 2)
      orange (255,165,0) — occluded (code 1)
      gray   (140,140,140) — unlabeled (code 0)
    - **Bbox** (fallback): draws an orange-red rectangle outline.

    Annotation coordinates must already be in crop-space (use
    ``annotation_to_crop_space`` first). Only fields present and non-None
    in ``annotation_crop_space`` are drawn.

    Returns the output path.
    """
    from PIL import ImageDraw

    with Image.open(crop_image_path) as src:
        img = src.convert("RGB").copy()

    draw = ImageDraw.Draw(img)

    polygon_points = annotation_crop_space.get("polygon_points")
    keypoints = annotation_crop_space.get("keypoints")

    if isinstance(polygon_points, list) and len(polygon_points) >= 2:
        # Polygon/segmentation mode: draw closed polygon outline
        flat = [(float(p[0]), float(p[1])) for p in polygon_points if isinstance(p, (list, tuple)) and len(p) >= 2]
        if len(flat) >= 2:
            draw.polygon(flat, outline=_POLYGON_COLOR)
            for _ in range(_BBOX_WIDTH - 1):
                # Thicken by drawing again with a 1-px inset line approximation
                draw.line(flat + [flat[0]], fill=_POLYGON_COLOR, width=_BBOX_WIDTH)

    elif isinstance(keypoints, list) and len(keypoints) > 0:
        # Skeleton mode: draw color-coded keypoint dots, no bbox
        from PIL import ImageFont
        visibility = annotation_crop_space.get("visibility")
        point_names = annotation_crop_space.get("point_names")
        font = ImageFont.load_default()
        for idx, kp in enumerate(keypoints):
            if not isinstance(kp, (list, tuple)) or len(kp) < 2:
                continue
            kx, ky = float(kp[0]), float(kp[1])
            vis_code = visibility[idx] if isinstance(visibility, list) and idx < len(visibility) else 2
            color = _VIS_COLORS.get(int(vis_code) if isinstance(vis_code, (int, float)) else 2, _VIS_DEFAULT_COLOR)
            r = _KEYPOINT_RADIUS
            draw.ellipse([kx - r, ky - r, kx + r, ky + r], fill=color, outline=(0, 0, 0))
            if isinstance(point_names, list) and idx < len(point_names):
                label = str(point_names[idx])
                label_x, label_y = kx - r, ky - r - 11  # 11 px above dot top: 9 px font + 2 px gap
                # Black shadow for contrast on any background
                draw.text((label_x + 1, label_y + 1), label, fill=(0, 0, 0), font=font)
                # White foreground
                draw.text((label_x, label_y), label, fill=(255, 255, 255), font=font)

    else:
        # Bbox mode: draw orange-red rectangle outline
        bbox = annotation_crop_space.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            bx, by, bw, bh = (float(v) for v in bbox)
            x0, y0, x1, y1 = bx, by, bx + bw, by + bh
            for i in range(_BBOX_WIDTH):
                draw.rectangle([x0 - i, y0 - i, x1 + i, y1 + i], outline=_BBOX_COLOR)

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG")
    return dest
