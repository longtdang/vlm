from pathlib import Path
from typing import Any

from .image_index import normalize_stem


def annotation_match_key(item: dict[str, Any]) -> str:
    image = item.get("image") or {}
    image_path = image.get("path")
    if image_path:
        return normalize_stem(image_path)
    item_id = str(item.get("id", "")).strip()
    return normalize_stem(item_id)


def build_matches(
    image_index: dict[str, Path], items: list[dict[str, Any]]
) -> tuple[list[tuple[Path, dict[str, Any]]], list[str], list[str], list[str]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    unmatched: list[str] = []
    duplicate_annotation_keys: list[str] = []
    seen_annotation_keys: set[str] = set()
    matched_image_keys: set[str] = set()

    for item in items:
        key = annotation_match_key(item)
        if key in seen_annotation_keys:
            duplicate_annotation_keys.append(key)
            continue
        seen_annotation_keys.add(key)
        image_path = image_index.get(key)
        if image_path is None:
            unmatched.append(key)
            continue
        matches.append((image_path, item))
        matched_image_keys.add(key)

    unmatched_image_keys = sorted(set(image_index.keys()) - matched_image_keys)
    return matches, unmatched, sorted(set(duplicate_annotation_keys)), unmatched_image_keys
