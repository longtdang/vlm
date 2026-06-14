import json
from pathlib import Path
from typing import Any


def load_datumaro(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "items" not in data or not isinstance(data["items"], list):
        raise ValueError("Datumaro JSON is missing 'items' list")
    return data


def parse_keypoints_and_visibility(
    annotation: dict[str, Any],
) -> tuple[list[list[float]], list[int], list[int], bool]:
    """Parse keypoint coordinates and visibility values from a Datumaro annotation.

    Handles two source formats:
    - ``keypoints`` field: pre-parsed ``[[x, y], ...]`` list (e.g. FiftyOne-exported data)
      with an optional sibling ``visibility`` field.
    - ``points`` flat array: canonical Datumaro format where skeleton annotations
      use ``[x, y, v, ...]`` triplets and points annotations use ``[x, y, ...]``
      pairs with an optional sibling ``visibility`` field.

    Args:
        annotation: a Datumaro annotation dict.

    Returns:
        points: list of ``[x, y]`` float pairs.
        visibility: validated visibility values; each element is 0 (absent),
            1 (hidden), or 2 (visible).
        source_visibility: the raw visibility values as found in the annotation
            before any defaulting (empty list when fully defaulted).
        visibility_defaulted: ``True`` when visibility was not present in the
            annotation and was inferred as ``[2, ...]``.

    Raises:
        ValueError: if point/visibility counts are inconsistent or visibility
            values are outside ``{0, 1, 2}``.
    """
    # --- Try pre-parsed keypoints field first ---
    raw_keypoints = annotation.get("keypoints")
    if isinstance(raw_keypoints, list) and all(
        isinstance(kp, list) and len(kp) == 2 for kp in raw_keypoints
    ):
        points = [[float(kp[0]), float(kp[1])] for kp in raw_keypoints]
        raw_vis = annotation.get("visibility")
        if isinstance(raw_vis, list) and len(raw_vis) == len(points):
            source_visibility = [int(v) for v in raw_vis]
            visibility_defaulted = False
        else:
            source_visibility = []
            visibility_defaulted = True
        visibility = source_visibility if source_visibility else [2] * len(points)
        if len(visibility) != len(points):
            raise ValueError("Visibility length does not match points length")
        if any(v not in (0, 1, 2) for v in visibility):
            raise ValueError("Visibility values must be one of 0, 1, or 2")
        return points, visibility, source_visibility, visibility_defaulted

    # --- Fall back to flat points array (canonical Datumaro format) ---
    ann_type = annotation.get("type")
    raw_points = annotation.get("points") or []
    raw_vis = annotation.get("visibility")

    if ann_type == "skeleton":
        if len(raw_points) % 3 != 0:
            raise ValueError("Invalid skeleton points payload (must be x,y,v triplets)")
        points = [[float(raw_points[i]), float(raw_points[i + 1])] for i in range(0, len(raw_points), 3)]
        source_visibility = [int(raw_points[i + 2]) for i in range(0, len(raw_points), 3)]
        visibility_defaulted = False
        visibility = list(source_visibility)
    else:
        visibility_defaulted = raw_vis is None
        source_visibility = list(raw_vis) if raw_vis is not None else []
        if len(raw_points) % 2 != 0:
            raise ValueError("Invalid points payload (must be x,y pairs)")
        points = [[float(raw_points[i]), float(raw_points[i + 1])] for i in range(0, len(raw_points), 2)]
        visibility = source_visibility if source_visibility else [2] * len(points)

    if len(visibility) != len(points):
        raise ValueError("Visibility length does not match points length")
    if any(v not in (0, 1, 2) for v in visibility):
        raise ValueError("Visibility values must be one of 0, 1, or 2")
    return points, visibility, list(source_visibility), visibility_defaulted

