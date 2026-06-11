import json
from pathlib import Path
from typing import Any


def write_summary(config_path: Path, summary: dict[str, Any]) -> Path:
    output_path = config_path.parent / f"{config_path.stem}.summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return output_path
