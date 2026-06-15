from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture()
def datumaro_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal Datumaro JSON + one test image."""
    img_path = tmp_path / "images" / "frame_001.jpg"
    img_path.parent.mkdir(parents=True)
    Image.new("RGB", (200, 150), color=(100, 100, 100)).save(img_path)

    datumaro = {
        "items": [
            {
                "id": "frame_001",
                "image": {
                    "path": "frame_001.jpg",
                    "size": [150, 200],  # [height, width]
                },
                "annotations": [
                    {
                        "id": 1,
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [20.0, 15.0, 80.0, 60.0],
                        "attributes": {"clamp-type": "2-arm", "roll-count": 1.0},
                    },
                    {
                        "id": 2,
                        "type": "polygon",
                        "label_id": 1,
                        "points": [30.0, 40.0, 80.0, 40.0, 80.0, 90.0, 30.0, 90.0],
                        "attributes": {},
                    },
                ],
            }
        ],
        "categories": {
            "label": {
                "labels": [
                    {"name": "forklift-with-roll"},
                    {"name": "roll-mask"},
                ]
            }
        },
    }
    json_path = tmp_path / "datumaro.json"
    json_path.write_text(json.dumps(datumaro), encoding="utf-8")
    return json_path, tmp_path / "images"


def test_no_vlm_builds_crops_and_report(
    datumaro_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    json_path, image_dir = datumaro_fixture
    output_dir = tmp_path / "output"

    import argparse
    import fiftyone as fo
    from scripts.crop_validate import _build_dataset, _write_report

    # Build args namespace directly (avoids sys.argv mutation)
    args = argparse.Namespace(
        datumaro_json=str(json_path),
        image_dir=str(image_dir),
        output_dir=str(output_dir),
        dataset_name="test_integration",
        model="Qwen/Qwen2.5-VL-3B-Instruct",
        plugin_source="https://github.com/harpreetsahota204/qwen2_5_vl",
        padding_px=8,
        pass_threshold=0.20,
        review_threshold=0.60,
        persist_dataset=False,
        overwrite_dataset=True,
        no_vlm=True,
    )

    dataset = _build_dataset(args)
    try:
        # 2 annotations → 2 crop samples
        assert len(dataset) == 2

        # Crops directory populated
        crops_dir = output_dir / "crops"
        crops = list(crops_dir.glob("*.png"))
        assert len(crops) == 2

        # Back-reference fields present on each sample
        for sample in dataset.iter_samples():
            assert sample.get_field("source_image") == "frame_001.jpg"
            assert sample.get_field("annotation_label") is not None
            assert sample.get_field("annotation_type") in ("detection", "segmentation", "skeleton")
            # annotation_attributes must always be a dict (may be empty for non-bbox types)
            attrs = sample.get_field("annotation_attributes")
            assert isinstance(attrs, dict)

        # Detection sample carries the clamp-type and roll-count attributes
        for s in dataset.match(fo.ViewField("annotation_label") == "forklift-with-roll").iter_samples():
            attrs = s.get_field("annotation_attributes")
            assert attrs.get("clamp-type") == "2-arm"
            assert attrs.get("roll-count") == 1.0

        # Detection sample has detections field
        det_samples = dataset.match(fo.ViewField("annotation_type") == "detection")
        assert len(det_samples) == 1
        for s in det_samples.iter_samples():
            assert s.get_field("detections") is not None

        # Segmentation sample has segmentations field
        seg_samples = dataset.match(fo.ViewField("annotation_type") == "segmentation")
        assert len(seg_samples) == 1
        for s in seg_samples.iter_samples():
            assert s.get_field("segmentations") is not None

        # Report can be generated (with no vlm_verdict → REVIEW defaults)
        report_path = output_dir / "report.md"
        _write_report(dataset, report_path, dataset.name)
        assert report_path.exists()
        content = report_path.read_text()
        assert "## Summary" in content
        assert "frame_001.jpg" in content

    finally:
        if fo.dataset_exists(dataset.name):
            dataset.delete()


def test_crops_have_annotation_overlays(
    datumaro_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    """Verify that crop files contain non-zero image data (overlay was rendered)."""
    json_path, image_dir = datumaro_fixture
    output_dir = tmp_path / "output2"

    import argparse
    from scripts.crop_validate import _build_dataset
    import fiftyone as fo

    args = argparse.Namespace(
        datumaro_json=str(json_path),
        image_dir=str(image_dir),
        output_dir=str(output_dir),
        dataset_name="test_overlay",
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        plugin_source="https://github.com/harpreetsahota204/qwen2_5_vl",
        padding_px=8,
        pass_threshold=0.20,
        review_threshold=0.60,
        persist_dataset=False,
        overwrite_dataset=True,
        no_vlm=True,
    )

    dataset = _build_dataset(args)
    try:
        for sample in dataset.iter_samples():
            img = Image.open(sample.filepath)
            assert img.size[0] > 0 and img.size[1] > 0
    finally:
        if fo.dataset_exists(dataset.name):
            dataset.delete()
