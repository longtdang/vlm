from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import fiftyone as fo

from .config_loader import load_config
from .datumaro_reader import load_datumaro
from .image_index import build_image_index
from .matching import build_matches
from .preflight import PreflightReport
from .summary import write_summary


def _extract_points_and_visibility(annotation: dict[str, Any]) -> tuple[list[list[float]], list[int]]:
    raw_points = annotation.get("points") or []
    visibility = annotation.get("visibility") or []
    if len(raw_points) % 2 != 0:
        raise ValueError("Invalid points payload (must be x,y pairs)")
    points = [[raw_points[i], raw_points[i + 1]] for i in range(0, len(raw_points), 2)]
    if not visibility:
        visibility = [2] * len(points)
    if len(visibility) != len(points):
        raise ValueError("Visibility length does not match points length")
    return points, visibility


def _normalize_points(points: list[list[float]], width: float, height: float, visibility: list[int]) -> list[list[float]]:
    normalized: list[list[float]] = []
    for (x, y), vis in zip(points, visibility):
        if vis == 0:
            normalized.append([math.nan, math.nan])
            continue
        normalized.append([x / width, y / height])
    return normalized


def _build_skeleton_from_datumaro(data: dict[str, Any], label_field: str) -> fo.KeypointSkeleton | None:
    categories = data.get("categories") or {}
    points_categories = categories.get("points")
    if not points_categories:
        return None

    first = None
    if isinstance(points_categories, list) and points_categories:
        first = points_categories[0]
    elif isinstance(points_categories, dict):
        first = next(iter(points_categories.values()), None)
    if not first:
        return None

    labels = first.get("labels") or []
    joints = first.get("joints") or []
    edges: list[list[int]] = []
    for joint in joints:
        if isinstance(joint, list) and len(joint) == 2:
            edges.append([int(joint[0]), int(joint[1])])
    if not labels:
        return None
    return fo.KeypointSkeleton(labels=labels, edges=edges)


def run_import(config_path: str, launch_app: bool = False) -> tuple[bool, dict[str, Any]]:
    cfg = load_config(config_path)
    data = load_datumaro(cfg.datumaro_json)
    items: list[dict[str, Any]] = data["items"]

    image_index, duplicate_keys = build_image_index(cfg.image_dir)
    matches, unmatched_keys = build_matches(image_index, items)
    malformed: list[str] = []

    report = PreflightReport(
        duplicate_image_keys=sorted(set(duplicate_keys)),
        unmatched_annotation_keys=sorted(set(unmatched_keys)),
        malformed_annotations=malformed,
    )

    summary: dict[str, Any] = {
        "dataset_name": cfg.dataset_name,
        "label_field": cfg.label_field,
        "image_count": len(image_index),
        "annotation_item_count": len(items),
        "matched_count": len(matches),
        "preflight": report.to_dict(),
        "written_samples": 0,
    }

    if report.has_errors():
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    dataset = fo.Dataset(cfg.dataset_name)
    skeleton = _build_skeleton_from_datumaro(data, cfg.label_field)
    if skeleton is not None:
        dataset.default_skeleton = skeleton

    samples: list[fo.Sample] = []
    for image_path, item in matches:
        image_meta = (item.get("image") or {}).get("size") or []
        width = float(image_meta[1]) if len(image_meta) >= 2 else None
        height = float(image_meta[0]) if len(image_meta) >= 2 else None

        sample = fo.Sample(filepath=str(image_path))
        keypoints: list[fo.Keypoint] = []

        for ann in item.get("annotations") or []:
            if ann.get("type") != "points":
                continue
            try:
                points, visibility = _extract_points_and_visibility(ann)
                if width is None or height is None or width <= 0 or height <= 0:
                    raise ValueError("Missing valid image size metadata")
                norm = _normalize_points(points, width, height, visibility)
                kp = fo.Keypoint(points=norm)
                kp["visibility"] = visibility
                keypoints.append(kp)
            except Exception:
                malformed.append(str(item.get("id", "unknown")))

        sample[cfg.label_field] = fo.Keypoints(keypoints=keypoints)
        samples.append(sample)

    if malformed:
        summary["preflight"] = PreflightReport(
            duplicate_image_keys=sorted(set(duplicate_keys)),
            unmatched_annotation_keys=sorted(set(unmatched_keys)),
            malformed_annotations=sorted(set(malformed)),
        ).to_dict()
        summary_path = write_summary(cfg.config_path, summary)
        summary["summary_path"] = str(summary_path)
        return False, summary

    dataset.add_samples(samples)
    dataset.save()
    summary["written_samples"] = len(samples)
    summary_path = write_summary(cfg.config_path, summary)
    summary["summary_path"] = str(summary_path)

    if launch_app:
        fo.launch_app(dataset)

    return True, summary

