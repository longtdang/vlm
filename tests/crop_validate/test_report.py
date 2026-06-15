from __future__ import annotations

from pathlib import Path

import fiftyone as fo
import pytest

from scripts.crop_validate import _write_report


def _make_dataset_with_verdicts(tmp_path: Path) -> fo.Dataset:
    """Build a minimal in-memory FiftyOne dataset with vlm_verdict fields.

    Two frames so we can test frame-based grouping:
      frame_001.jpg → FAIL 0.92, REVIEW 0.45
      frame_002.jpg → FAIL 0.75, PASS 0.05, PASS 0.10
    """
    import uuid
    dataset = fo.Dataset(f"test_report_{uuid.uuid4().hex[:8]}")

    rows = [
        ("frame_001.jpg", "FAIL",   0.92, "bbox clips edge",   "forklift-with-roll"),
        ("frame_001.jpg", "REVIEW", 0.45, "partially correct", "clamp-2-arm"),
        ("frame_002.jpg", "FAIL",   0.75, "wrong placement",   "clamp-2-arm"),
        ("frame_002.jpg", "PASS",   0.05, "looks good",        "clamp-3-arm"),
        ("frame_002.jpg", "PASS",   0.10, "well placed",       "forklift-with-roll"),
    ]
    for i, (source_image, verdict, confidence, reason, label) in enumerate(rows):
        img_path = tmp_path / f"crop_{i}.png"
        from PIL import Image
        Image.new("RGB", (10, 10), color=(0, 0, 0)).save(img_path)

        sample = fo.Sample(filepath=str(img_path))
        sample["source_image"] = source_image
        sample["source_ann_id"] = str(i + 100)
        sample["annotation_label"] = label
        sample["annotation_type"] = "detection"
        sample["vlm_verdict"] = fo.Classification(label=verdict, confidence=confidence)
        sample["vlm_reason"] = reason
        dataset.add_sample(sample)

    dataset.save()
    return dataset


class TestWriteReport:
    def test_report_file_created(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        assert report_path.exists()
        dataset.delete()

    def test_report_contains_summary_table(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        assert "## Summary" in content
        assert "FAIL" in content
        assert "REVIEW" in content
        assert "PASS" in content
        dataset.delete()

    def test_frame_sections_are_present(self, tmp_path: Path) -> None:
        """Report has one section per source frame, not per verdict."""
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        assert "## frame_001.jpg" in content
        assert "## frame_002.jpg" in content
        # Must NOT have old-style verdict section headers
        assert "## ❌ FAIL" not in content
        assert "## ⚠️ REVIEW" not in content
        assert "## ✅ PASS" not in content
        dataset.delete()

    def test_frames_sorted_alphabetically(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        pos_001 = content.index("## frame_001.jpg")
        pos_002 = content.index("## frame_002.jpg")
        assert pos_001 < pos_002
        dataset.delete()

    def test_rows_contain_source_image_and_reason(self, tmp_path: Path) -> None:
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        assert "frame_001.jpg" in content
        assert "bbox clips edge" in content
        dataset.delete()

    def test_rows_within_frame_sorted_by_risk_descending(self, tmp_path: Path) -> None:
        """Within frame_002.jpg, FAIL 0.75 must appear before PASS 0.10."""
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        frame_002_start = content.index("## frame_002.jpg")
        frame_002_section = content[frame_002_start:]
        idx_75 = frame_002_section.index("0.75")
        idx_10 = frame_002_section.index("0.10")
        assert idx_75 < idx_10
        dataset.delete()

    def test_verdict_inline_in_row(self, tmp_path: Path) -> None:
        """Verdict and risk appear as columns within each frame's table, not section headers."""
        dataset = _make_dataset_with_verdicts(tmp_path)
        report_path = tmp_path / "report.md"
        _write_report(dataset, report_path, dataset.name)
        content = report_path.read_text()
        # Each row shows the verdict inline
        assert "❌ FAIL" in content
        assert "⚠️ REVIEW" in content
        assert "✅ PASS" in content
        dataset.delete()
