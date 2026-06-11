from dataclasses import dataclass, asdict


@dataclass
class PreflightReport:
    duplicate_image_keys: list[str]
    duplicate_annotation_keys: list[str]
    unmatched_annotation_keys: list[str]
    unmatched_image_keys: list[str]
    malformed_annotations: list[str]

    def has_errors(self) -> bool:
        return bool(
            self.duplicate_image_keys
            or self.duplicate_annotation_keys
            or self.unmatched_annotation_keys
            or self.unmatched_image_keys
            or self.malformed_annotations
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        result["ok"] = not self.has_errors()
        return result
