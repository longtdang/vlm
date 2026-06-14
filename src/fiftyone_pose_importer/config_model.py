from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class ImportConfigError(ValueError):
    pass


_KNOWN_IMPORT_KEYS: frozenset[str] = frozenset(
    {"image_dir", "datumaro_json", "dataset_name", "label_field"}
)


@dataclass(frozen=True)
class ImportConfig:
    image_dir: str
    datumaro_json: str
    dataset_name: str
    label_field: str = "ground_truth"

    @classmethod
    def from_dict(cls, raw: object) -> ImportConfig:
        if not isinstance(raw, dict):
            raise ImportConfigError("Config must be a mapping")

        unknown = set(raw.keys()) - _KNOWN_IMPORT_KEYS
        if unknown:
            raise ImportConfigError(f"Unknown config keys: {sorted(unknown)}")

        image_dir = raw.get("image_dir")
        datumaro_json = raw.get("datumaro_json")
        dataset_name = raw.get("dataset_name")
        label_field = raw.get("label_field", "ground_truth")

        if not isinstance(image_dir, str) or not image_dir:
            raise ImportConfigError("image_dir is required and must be a non-empty string")
        if not isinstance(datumaro_json, str) or not datumaro_json:
            raise ImportConfigError("datumaro_json is required and must be a non-empty string")
        if not isinstance(dataset_name, str) or not dataset_name:
            raise ImportConfigError("dataset_name is required and must be a non-empty string")
        if not isinstance(label_field, str) or not label_field:
            raise ImportConfigError("label_field must be a non-empty string")
        for fname, fval in (("image_dir", image_dir), ("datumaro_json", datumaro_json)):
            if "://" in fval:
                raise ImportConfigError(f"{fname}: only local filesystem paths are supported")

        return cls(
            image_dir=image_dir,
            datumaro_json=datumaro_json,
            dataset_name=dataset_name,
            label_field=label_field,
        )

    def resolve_paths(self, config_path: Path) -> ResolvedConfig:
        base_dir = config_path.parent.resolve()
        image_dir = (base_dir / self.image_dir).resolve() if not Path(self.image_dir).is_absolute() else Path(self.image_dir).resolve()
        datumaro_json = (base_dir / self.datumaro_json).resolve() if not Path(self.datumaro_json).is_absolute() else Path(self.datumaro_json).resolve()
        return ResolvedConfig(
            image_dir=image_dir,
            datumaro_json=datumaro_json,
            dataset_name=self.dataset_name,
            label_field=self.label_field,
            config_path=config_path.resolve(),
        )


@dataclass(frozen=True)
class ResolvedConfig:
    image_dir: Path
    datumaro_json: Path
    dataset_name: str
    label_field: str
    config_path: Path

