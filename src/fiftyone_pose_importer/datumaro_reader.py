import json
from pathlib import Path
from typing import Any


def load_datumaro(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "items" not in data or not isinstance(data["items"], list):
        raise ValueError("Datumaro JSON is missing 'items' list")
    return data

