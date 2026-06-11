from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class ImportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_dir: str
    datumaro_json: str
    dataset_name: str
    label_field: str = "ground_truth"

    @field_validator("image_dir", "datumaro_json")
    @classmethod
    def reject_urls(cls, value: str) -> str:
        if "://" in value:
            raise ValueError("Only local filesystem paths are supported")
        return value

    def resolve_paths(self, config_path: Path) -> "ResolvedConfig":
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


class ResolvedConfig(BaseModel):
    image_dir: Path
    datumaro_json: Path
    dataset_name: str
    label_field: str
    config_path: Path

