from pathlib import Path

import yaml
from pydantic import ValidationError

from .config_model import ImportConfig, ResolvedConfig


class ConfigLoadError(ValueError):
    pass


def load_config(config_path: str) -> ResolvedConfig:
    cfg_path = Path(config_path).resolve()
    if not cfg_path.exists():
        raise ConfigLoadError(f"Config file does not exist: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    try:
        parsed = ImportConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"Config validation failed: {exc}") from exc

    resolved = parsed.resolve_paths(cfg_path)

    if not resolved.image_dir.exists() or not resolved.image_dir.is_dir():
        raise ConfigLoadError(f"Invalid image_dir path: {resolved.image_dir}")
    if not resolved.datumaro_json.exists() or not resolved.datumaro_json.is_file():
        raise ConfigLoadError(f"Invalid datumaro_json path: {resolved.datumaro_json}")

    return resolved

