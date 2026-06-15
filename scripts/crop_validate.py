# scripts/crop_validate.py
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import fiftyone as fo
import fiftyone.zoo as foz
from fiftyone import ViewField as F

# ── project-local imports ────────────────────────────────────────────────────
# Add the repo src/ to path so this script can be run from anywhere
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from fiftyone_pose_importer.datumaro_reader import load_datumaro, parse_keypoints_and_visibility
from fiftyone_pose_importer.image_index import build_image_index
from fiftyone_pose_importer.matching import build_matches
from fiftyone_pose_importer.pose_contract import (
    SkeletonContract,
    SkeletonContractBundle,
    extract_skeleton_contract_bundle,
)
from fiftyone_pose_importer.verification.cropper import (
    CropPlan,
    annotation_to_crop_space,
    materialize_crop,
    plan_crop,
    render_annotation_overlay,
)
from fiftyone_pose_importer.verification.types import DeterministicVerdict

# ── constants ────────────────────────────────────────────────────────────────
PLUGIN_URL = "https://github.com/harpreetsahota204/qwen2_5_vl"
DEFAULT_PADDING_PX = 16
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)

DEFAULT_PROMPTS: dict[str, str] = {
    "detection": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with an orange-red bounding box drawn on it.\n"
        "Judge whether the bounding box correctly localizes and covers the '{label}' object.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
    "skeleton": (
        "You are validating annotation quality for the '{label}' object.\n"
        "The image shows a crop with colored keypoint dots: green=visible, orange=occluded, gray=unlabeled.\n"
        "Judge whether the keypoints are correctly placed on the '{label}' structure and "
        "whether their visibility codes match the actual occlusion state.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
    "segmentation": (
        "You are validating annotation quality for the '{label}' region.\n"
        "The image shows a crop with a cyan polygon outline drawn on it.\n"
        "Judge whether the polygon correctly outlines the '{label}' region.\n"
        'Return ONLY JSON: {"error_probability": <float 0-1>, "reason": "<brief reason>"}'
    ),
}

# Per-label overrides — add entries here to customize prompts per label:
LABEL_PROMPTS: dict[str, str] = {
    # "forklift-with-roll": "...",
}

_SKELETON_ANN_TYPES = {"points", "skeleton"}
_NON_SKELETON_ANN_TYPES = {"polygon", "bbox", "mask", "ellipse", "polyline"}


def _annotation_type(datumaro_type: str | None) -> str:
    """Map Datumaro annotation type string to our three-way type: detection/segmentation/skeleton."""
    if datumaro_type in {"polygon", "polyline", "mask"}:
        return "segmentation"
    if datumaro_type in _SKELETON_ANN_TYPES:
        return "skeleton"
    return "detection"  # bbox, ellipse, unknown, None


def _is_skeleton_type(datumaro_type: str | None) -> bool:
    return datumaro_type in _SKELETON_ANN_TYPES


def _derive_bbox(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return (x, y, w, h) bbox — from bbox field if present, else derived from points."""
    raw = annotation.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        try:
            return float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
        except (TypeError, ValueError):
            pass

    ann_type = annotation.get("type")
    points_raw = annotation.get("points")
    if not isinstance(points_raw, list) or not points_raw:
        return None
    try:
        if ann_type == "skeleton" and len(points_raw) >= 3 and len(points_raw) % 3 == 0:
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 3)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 3)]
        elif len(points_raw) >= 2 and len(points_raw) % 2 == 0:
            xs = [float(points_raw[i]) for i in range(0, len(points_raw), 2)]
            ys = [float(points_raw[i + 1]) for i in range(0, len(points_raw), 2)]
        else:
            return None
    except (TypeError, ValueError):
        return None
    if not xs:
        return None
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _label_lookup(data: dict[str, Any]) -> dict[int, str]:
    labels_raw = ((data.get("categories") or {}).get("label") or {}).get("labels") or []
    lookup: dict[int, str] = {}
    for index, raw in enumerate(labels_raw):
        if isinstance(raw, dict):
            lookup[index] = str(raw.get("name") or f"label-{index}")
        else:
            lookup[index] = f"label-{index}"
    return lookup


def _safe_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._]+", "_", value).strip("._")
    return cleaned or "unknown"


def _to_field_name(label_name: str) -> str:
    """Convert a label name to a FiftyOne keypoints field name.

    Each distinct skeleton label maps to its own field so FiftyOne can
    enforce a consistent keypoint schema (fixed point count) per field.
    e.g. "clamp-2-arm" → "keypoints_clamp_2_arm"
         "roll-keypoints" → "keypoints_roll_keypoints"
    """
    slug = re.sub(r"[^a-z0-9]+", "_", label_name.lower()).strip("_")
    return f"keypoints_{slug}" if slug else "keypoints_unknown"


def _get_polygon_points(annotation: dict[str, Any]) -> list[list[float]] | None:
    """Extract polygon/polyline/mask points as [[x, y], ...] pairs."""
    ann_type = annotation.get("type")
    if ann_type not in {"polygon", "polyline", "mask"}:
        return None
    raw_pts = annotation.get("points")
    if not isinstance(raw_pts, list) or len(raw_pts) < 4:
        return None
    try:
        return [
            [float(raw_pts[i]), float(raw_pts[i + 1])]
            for i in range(0, len(raw_pts) - 1, 2)
        ]
    except (TypeError, ValueError):
        return None


def _parse_vlm_response(raw: str) -> tuple[float | None, str]:
    """Parse VLM text output into (error_probability, reason).

    Returns (None, "parse_failed") on any parse failure.
    """
    stripped = raw.strip()
    match = _FENCE_RE.search(stripped)
    if match:
        stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None, "parse_failed"

    ep = parsed.get("error_probability")
    if not isinstance(ep, (int, float)) or not (0.0 <= float(ep) <= 1.0):
        return None, "parse_failed"

    reason = str(parsed.get("reason", ""))
    return float(ep), reason


def _ep_to_verdict(ep: float | None, pass_threshold: float, review_threshold: float) -> str:
    """Map error_probability to PASS/REVIEW/FAIL verdict string."""
    if ep is None:
        return "REVIEW"
    if ep < pass_threshold:
        return "PASS"
    if ep < review_threshold:
        return "REVIEW"
    return "FAIL"


def _to_fo_sample(
    *,
    crop_overlay_path: Path,
    crop_plan: CropPlan,
    crop_space_ann: dict[str, Any],
    label: str,
    ann_type: str,
    source_image: str,
    ann_id: str,
    label_id: int | None,
    contract: SkeletonContract | None,
) -> fo.Sample:
    """Build a FiftyOne Sample for one annotation crop.

    All annotation coordinates are normalized by crop dimensions (output_size).
    The sample filepath is the annotated overlay image.
    """
    sample = fo.Sample(filepath=str(crop_overlay_path))
    sample["source_image"] = source_image
    sample["source_ann_id"] = ann_id
    sample["annotation_label"] = label
    sample["annotation_type"] = ann_type

    W, H = crop_plan.output_size  # crop pixel dimensions

    if ann_type == "detection":
        bbox = crop_space_ann.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            bx, by, bw, bh = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            fo_bbox = [bx / W, by / H, bw / W, bh / H]
            sample["detections"] = fo.Detections(
                detections=[fo.Detection(label=label, bounding_box=fo_bbox)]
            )

    elif ann_type == "segmentation":
        polygon_points = crop_space_ann.get("polygon_points")
        if isinstance(polygon_points, list) and len(polygon_points) >= 2:
            fo_pts = [[[px / W, py / H] for px, py in polygon_points]]
            sample["segmentations"] = fo.Polylines(
                polylines=[
                    fo.Polyline(label=label, points=fo_pts, filled=True, closed=True)
                ]
            )

    elif ann_type == "skeleton":
        keypoints = crop_space_ann.get("keypoints") or []
        visibility = crop_space_ann.get("visibility") or []
        # Use the label name (slugified) as the field name so each skeleton type
        # (roll-keypoints, clamp-2-arm, clamp-3-arm) gets its own field with a
        # consistent keypoint count — required by FiftyOne's schema enforcement.
        field_name = _to_field_name(label)
        fo_points = []
        for idx, (kx, ky) in enumerate(keypoints):
            vis = visibility[idx] if idx < len(visibility) else 2
            if vis == 0:
                fo_points.append([math.nan, math.nan])
            else:
                fo_points.append([kx / W, ky / H])
        kp = fo.Keypoint(points=fo_points)
        if isinstance(visibility, list):
            kp["visibility"] = list(visibility)
        if contract is not None:
            kp["skeleton_labels"] = contract.labels
            kp["skeleton_edges"] = contract.edges
        sample[field_name] = fo.Keypoints(keypoints=[kp])

    return sample


def _build_dataset(args: argparse.Namespace) -> fo.Dataset:
    """Parse Datumaro JSON, crop each annotation, build FiftyOne dataset."""
    datumaro_path = Path(args.datumaro_json).resolve()
    image_dir = Path(args.image_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    crops_dir = output_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    data = load_datumaro(datumaro_path)
    items: list[dict[str, Any]] = data["items"]
    label_names = _label_lookup(data)

    image_index, _ = build_image_index(image_dir)
    matches, _, _, _ = build_matches(image_index, items)

    try:
        skeleton_bundle: SkeletonContractBundle | None = extract_skeleton_contract_bundle(data)
    except Exception:
        skeleton_bundle = None

    # Resolve dataset name (avoid collision with timestamp suffix)
    dataset_name = args.dataset_name
    if not args.overwrite_dataset:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{args.dataset_name}_{timestamp}"
    elif fo.dataset_exists(dataset_name):
        fo.delete_dataset(dataset_name)

    dataset = fo.Dataset(dataset_name)
    routed_contracts: dict[str, SkeletonContract] = {}
    samples: list[fo.Sample] = []
    skipped = 0

    for image_path, item in matches:
        image_meta = (item.get("image") or {}).get("size") or []
        width = int(image_meta[1]) if len(image_meta) >= 2 else None
        height = int(image_meta[0]) if len(image_meta) >= 2 else None
        if width is None or height is None or width <= 0 or height <= 0:
            skipped += 1
            continue

        source_image = Path(image_path).name
        annotations = item.get("annotations") or []

        for ann_idx, annotation in enumerate(annotations):
            if not isinstance(annotation, dict):
                skipped += 1
                continue

            ann_id = str(annotation.get("id") or f"ann-{ann_idx}")
            label_id = annotation.get("label_id")
            label = (
                label_names.get(label_id, str(annotation.get("label") or "unknown"))
                if isinstance(label_id, int)
                else str(annotation.get("label") or "unknown")
            )
            ann_type_raw = annotation.get("type")
            ann_type = _annotation_type(ann_type_raw)
            is_skeleton = _is_skeleton_type(ann_type_raw)

            # Derive bbox
            bbox = _derive_bbox(annotation)
            if bbox is None:
                print(f"[crop_validate] skip ann_id={ann_id}: no bbox", file=sys.stderr)
                skipped += 1
                continue

            # Parse keypoints/visibility for skeleton types
            keypoints: list[list[float]] = []
            visibility: list[int] = []
            if is_skeleton:
                try:
                    keypoints, visibility, _, _ = parse_keypoints_and_visibility(annotation)
                except ValueError as exc:
                    print(f"[crop_validate] skip ann_id={ann_id}: {exc}", file=sys.stderr)
                    skipped += 1
                    continue

            crop = plan_crop(
                image_width=width,
                image_height=height,
                bbox=bbox,
                padding_px=args.padding_px,
                is_skeleton=is_skeleton,
                keypoints=[(p[0], p[1]) for p in keypoints] if keypoints else None,
                visibility=visibility if visibility else None,
            )
            if crop.verdict is DeterministicVerdict.FAIL:
                print(f"[crop_validate] skip ann_id={ann_id}: {crop.reason}", file=sys.stderr)
                skipped += 1
                continue

            # Resolve polygon points for segmentation
            polygon_points = _get_polygon_points(annotation)

            # Resolve skeleton point names
            skeleton_labels: list[str] | None = None
            contract: SkeletonContract | None = None
            if is_skeleton and skeleton_bundle is not None:
                if isinstance(label_id, int):
                    contract = skeleton_bundle.by_label_id.get(label_id)
                if contract is None:
                    contract = skeleton_bundle.default
                if contract is not None:
                    skeleton_labels = contract.labels

            annotation_payload: dict[str, Any] = {
                "bbox": list(bbox),
                "attributes": annotation.get("attributes") if isinstance(annotation.get("attributes"), dict) else {},
                "keypoints": keypoints or None,
                "visibility": crop.adjusted_visibility,
                "original_visibility": crop.original_visibility,
                "point_names": skeleton_labels,
                "polygon_points": polygon_points,
            }
            crop_space_ann = annotation_to_crop_space(annotation_payload, crop)

            # Filename: <orig_stem>__ann_<id>__<label>.png
            orig_stem = _safe_token(Path(image_path).stem)
            safe_label = _safe_token(label)
            safe_ann_id = _safe_token(ann_id)
            crop_filename = f"{orig_stem}__ann_{safe_ann_id}__{safe_label}.png"
            overlay_path = crops_dir / crop_filename

            try:
                materialize_crop(source_image_path=image_path, crop_plan=crop, output_path=overlay_path)
                render_annotation_overlay(
                    crop_image_path=overlay_path,
                    annotation_crop_space=crop_space_ann,
                    output_path=overlay_path,
                )
            except Exception as exc:
                print(f"[crop_validate] skip ann_id={ann_id}: crop error {exc}", file=sys.stderr)
                skipped += 1
                continue

            if is_skeleton and contract is not None:
                field_name = _to_field_name(label)
                routed_contracts[field_name] = contract

            sample = _to_fo_sample(
                crop_overlay_path=overlay_path,
                crop_plan=crop,
                crop_space_ann=crop_space_ann,
                label=label,
                ann_type=ann_type,
                source_image=source_image,
                ann_id=ann_id,
                label_id=label_id if isinstance(label_id, int) else None,
                contract=contract,
            )
            samples.append(sample)

    # Set skeleton metadata on dataset
    if routed_contracts:
        dataset.skeletons = {
            field_name: fo.KeypointSkeleton(labels=c.labels, edges=c.edges)
            for field_name, c in routed_contracts.items()
        }

    dataset.add_samples(samples)
    dataset.save()
    print(f"[crop_validate] Built dataset '{dataset_name}': {len(samples)} crops, {skipped} skipped")
    return dataset


def _apply_vlm(
    dataset: fo.Dataset,
    model_name: str,
    plugin_source: str,
    pass_threshold: float,
    review_threshold: float,
) -> None:
    pass  # implemented in Task 6


def _write_report(dataset: fo.Dataset, output_path: Path, dataset_name: str) -> None:
    pass  # implemented in Task 7


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = _build_dataset(args)

    if not args.no_vlm:
        _apply_vlm(dataset, args.model, args.plugin_source, args.pass_threshold, args.review_threshold)

    report_path = output_dir / "report.md"
    _write_report(dataset, report_path, dataset.name)
    print(f"[crop_validate] Report written: {report_path}")

    if not args.persist_dataset:
        dataset.delete()
        print(f"[crop_validate] Dataset '{dataset.name}' deleted (use --persist-dataset to keep)")
    else:
        print(f"[crop_validate] Dataset '{dataset.name}' persisted in FiftyOne")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop annotations into FiftyOne samples and validate with Qwen2.5-VL"
    )
    parser.add_argument("--datumaro-json", required=True, help="Path to Datumaro JSON file")
    parser.add_argument("--image-dir", required=True, help="Directory containing source images")
    parser.add_argument("--output-dir", required=True, help="Output directory for crops and report")
    parser.add_argument("--dataset-name", default="crop_validate", help="FiftyOne dataset base name")
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-3B-Instruct", help="Qwen2.5-VL model checkpoint")
    parser.add_argument("--plugin-source", default=PLUGIN_URL, help="FiftyOne zoo plugin URL")
    parser.add_argument("--padding-px", type=int, default=DEFAULT_PADDING_PX, help="Crop padding in pixels")
    parser.add_argument("--pass-threshold", type=float, default=0.20, help="Risk below this → PASS")
    parser.add_argument("--review-threshold", type=float, default=0.60, help="Risk below this → REVIEW, else FAIL")
    parser.add_argument("--persist-dataset", action="store_true", help="Keep FiftyOne dataset after run")
    parser.add_argument("--overwrite-dataset", action="store_true", help="Overwrite existing dataset instead of using timestamp suffix")
    parser.add_argument("--no-vlm", action="store_true", help="Skip VLM stage (build crops and dataset only)")
    return parser.parse_args()


if __name__ == "__main__":
    main()
