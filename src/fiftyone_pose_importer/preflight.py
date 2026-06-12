from dataclasses import dataclass, asdict, field


@dataclass
class PreflightReport:
    duplicate_image_keys: list[str]
    duplicate_annotation_keys: list[str]
    unmatched_annotation_keys: list[str]
    unmatched_image_keys: list[str]
    malformed_annotations: list[str]
    schema_mismatches: dict[str, list[str]] = field(default_factory=dict)

    def add_schema_mismatch(self, category: str, sample_id: str, max_ids: int = 10) -> None:
        bucket = self.schema_mismatches.setdefault(category, [])
        if sample_id not in bucket and len(bucket) < max_ids:
            bucket.append(sample_id)

    def has_errors(self) -> bool:
        return bool(
            self.duplicate_image_keys
            or self.duplicate_annotation_keys
            or self.unmatched_annotation_keys
            or self.unmatched_image_keys
            or self.malformed_annotations
            or any(self.schema_mismatches.values())
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        result["schema_mismatch_counts"] = {key: len(value) for key, value in self.schema_mismatches.items()}
        result["ok"] = not self.has_errors()
        return result
