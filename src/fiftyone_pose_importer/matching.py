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
) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    unmatched: list[str] = []

    for item in items:
        key = annotation_match_key(item)
        image_path = image_index.get(key)
        if image_path is None:
            unmatched.append(key)
            continue
        matches.append((image_path, item))

    return matches, unmatched

