from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SchemaContractError(ValueError):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class SkeletonContract:
    labels: list[str]
    edges: list[list[int]]


def _candidate_specs(points_categories: Any) -> list[dict[str, Any]]:
    if isinstance(points_categories, dict):
        if "labels" in points_categories or "joints" in points_categories:
            return [points_categories]
        candidates: list[dict[str, Any]] = []
        for value in points_categories.values():
            if isinstance(value, dict):
                candidates.append(value)
            elif isinstance(value, list):
                candidates.extend([v for v in value if isinstance(v, dict)])
        return candidates
    if isinstance(points_categories, list):
        return [v for v in points_categories if isinstance(v, dict)]
    return []


def extract_canonical_skeleton_contract(data: dict[str, Any]) -> SkeletonContract:
    categories = data.get("categories") or {}
    points_categories = categories.get("points")
    if points_categories is None:
        raise SchemaContractError("missing_skeleton", "Datumaro categories.points is missing")

    candidates = _candidate_specs(points_categories)
    if not candidates:
        raise SchemaContractError("missing_skeleton", "No usable skeleton spec found in categories.points")
    if len(candidates) > 1:
        raise SchemaContractError("ambiguous_skeleton", "Multiple skeleton specs found in categories.points")

    skeleton = candidates[0]
    labels_raw = skeleton.get("labels")
    if not isinstance(labels_raw, list) or not labels_raw:
        raise SchemaContractError("missing_skeleton", "Skeleton labels must be a non-empty list")
    if not all(isinstance(label, str) and label for label in labels_raw):
        raise SchemaContractError("invalid_skeleton_edges", "Skeleton labels must be non-empty strings")
    labels = list(labels_raw)

    joints_raw = skeleton.get("joints") or []
    if not isinstance(joints_raw, list):
        raise SchemaContractError("invalid_skeleton_edges", "Skeleton joints must be a list")

    edges: list[list[int]] = []
    for joint in joints_raw:
        if not isinstance(joint, list) or len(joint) != 2:
            raise SchemaContractError("invalid_skeleton_edges", "Each skeleton edge must contain exactly two indices")
        a, b = joint
        if not isinstance(a, int) or not isinstance(b, int):
            raise SchemaContractError("invalid_skeleton_edges", "Skeleton edge indices must be integers")
        if a < 0 or b < 0 or a >= len(labels) or b >= len(labels):
            raise SchemaContractError("invalid_skeleton_edges", "Skeleton edge index out of range")
        edges.append([a, b])

    return SkeletonContract(labels=labels, edges=edges)
