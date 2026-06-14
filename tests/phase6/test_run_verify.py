from __future__ import annotations

import json
from pathlib import Path

import yaml
from PIL import Image

from fiftyone_pose_importer.run_verify import run_verify


def _write_config(tmp_path: Path, datumaro_path: Path) -> Path:
    config_path = tmp_path / "verify.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": "images",
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260613T080000Z",
                    "deterministic": {
                        "padding_px": 8,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [
                                    {"name": "required_attributes", "params": {"required": ["clamp_type"]}}
                                ],
                                "skeleton-count": [
                                    {"name": "keypoint_count", "params": {"expected": 4}}
                                ],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def _write_datumaro(tmp_path: Path) -> Path:
    datumaro_path = tmp_path / "datumaro.json"
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (200, 64, 32)).save(image_dir / "sample-1.png")

    payload = {
        "categories": {
            "label": {
                "labels": [
                    {"name": "forklift-with-roll"},
                    {"name": "forklift-no-roll"},
                ]
            }
        },
        "items": [
            {
                "id": "sample-1",
                "image": {"path": "sample-1.png", "size": [100, 120]},
                "annotations": [
                    {
                        "id": "obj-pass",
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [10, 10, 30, 20],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[10, 10], [20, 20], [25, 20], [30, 25]],
                        "visibility": [2, 2, 2, 2],
                    },
                    {
                        "id": "obj-fail",
                        "type": "bbox",
                        "label_id": 1,
                        "bbox": [5, 5, 0, 20],
                        "attributes": {"clamp_type": "3-arm"},
                        "keypoints": [[1, 1], [2, 2], [3, 3], [4, 4]],
                        "visibility": [2, 2, 2, 2],
                    },
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")
    return datumaro_path


def test_deterministic_only_pipeline_without_vlm(tmp_path: Path) -> None:
    datumaro_path = _write_datumaro(tmp_path)
    config_path = _write_config(tmp_path, datumaro_path)

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["vlm_enabled"] is False
    assert summary["counts"]["objects_total"] == 2
    assert summary["counts"]["deterministic_pass"] == 1
    assert summary["counts"]["deterministic_fail"] == 1

    run_dir = Path(summary["artifacts"]["run_dir"])
    assert run_dir.exists()
    assert Path(summary["artifacts"]["csv"]).exists()
    assert Path(summary["artifacts"]["json"]).exists()
    assert Path(summary["artifacts"]["ndjson"]).exists()

    records = summary["objects"]
    assert {record["object_id"] for record in records} == {"obj-pass", "obj-fail"}
    elig_map = {record["object_id"]: record["vlm_eligible"] for record in records}
    assert elig_map["obj-pass"] is True
    assert elig_map["obj-fail"] is False


def test_cli_exit_code_zero_with_object_failures(tmp_path: Path, capsys) -> None:
    from fiftyone_pose_importer import cli

    datumaro_path = _write_datumaro(tmp_path)
    config_path = _write_config(tmp_path, datumaro_path)

    exit_code = cli.main(["verify", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["counts"]["deterministic_fail"] == 1
    assert Path(payload["artifacts"]["csv"]).exists()


def test_cli_verify_returns_non_zero_for_fatal_errors(capsys) -> None:
    from fiftyone_pose_importer import cli

    exit_code = cli.main(["verify", "--config", "missing-config.yaml"])
    captured = capsys.readouterr()

    assert exit_code != 0
    payload = json.loads(captured.err)
    assert payload["ok"] is False
    assert "error" in payload


def _write_datumaro_with_image_paths(tmp_path: Path) -> Path:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 30), (64, 128, 255)).save(image_dir / "sample-1.png")

    datumaro_path = tmp_path / "datumaro-images.json"
    payload = {
        "categories": {"label": {"labels": [{"name": "forklift-with-roll"}]}},
        "items": [
            {
                "id": "sample-1",
                "image": {"path": "sample-1.png", "size": [30, 40]},
                "annotations": [
                    {
                        "id": "obj-1",
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [3, 4, 12, 10],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[5, 5], [10, 10], [12, 12], [13, 13]],
                        "visibility": [2, 2, 2, 2],
                    }
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")
    return datumaro_path


def test_deterministic_only_pipeline_writes_real_crop_artifacts(tmp_path: Path) -> None:
    datumaro_path = _write_datumaro_with_image_paths(tmp_path)
    config_path = tmp_path / "verify-real-crops.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": "images",
                    "output_dir": "runs",
                    "run_timestamp": "20260613T090000Z",
                    "deterministic": {
                        "padding_px": 6,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    run_dir = Path(summary["artifacts"]["run_dir"])
    crops = sorted((run_dir / "crops").glob("*.png"))
    assert crops
    assert crops[0].parent.name == "crops"


def test_summary_objects_do_not_include_crop_path(tmp_path: Path) -> None:
    datumaro_path = _write_datumaro_with_image_paths(tmp_path)
    config_path = tmp_path / "verify-summary-crops.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": "images",
                    "output_dir": "runs",
                    "run_timestamp": "20260613T091500Z",
                    "deterministic": {
                        "padding_px": 6,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    for record in summary["objects"]:
        assert "crop_path" not in record


def test_missing_annotation_id_uses_ann_index_object_id(tmp_path: Path) -> None:
    datumaro_path = tmp_path / "datumaro-no-id.json"
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 30), (64, 128, 255)).save(image_dir / "sample-1.png")

    payload = {
        "categories": {"label": {"labels": [{"name": "forklift-with-roll"}]}},
        "items": [
            {
                "id": "sample-1",
                "image": {"path": "sample-1.png", "size": [30, 40]},
                "annotations": [
                    {
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [3, 4, 12, 10],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[5, 5], [10, 10], [12, 12], [13, 13]],
                        "visibility": [2, 2, 2, 2],
                    }
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")
    config_path = _write_config(tmp_path, datumaro_path)

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["objects"][0]["object_id"] == "ann-0"


def test_polygon_annotation_derives_bbox_and_passes(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (100, 150, 200)).save(image_dir / "poly-sample.png")

    datumaro_path = tmp_path / "datumaro-polygon.json"
    payload = {
        "categories": {"label": {"labels": [{"name": "forklift-with-roll"}]}},
        "items": [
            {
                "id": "poly-sample",
                "image": {"path": "poly-sample.png", "size": [100, 120]},
                "annotations": [
                    {
                        "id": "poly-obj",
                        "type": "polygon",
                        "label_id": 0,
                        "points": [10.0, 20.0, 40.0, 20.0, 40.0, 50.0, 10.0, 50.0],
                        "attributes": {"clamp_type": "2-arm"},
                        "visibility": [2, 2, 2, 2],
                    }
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")

    config_path = tmp_path / "verify-polygon.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": str(image_dir),
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T090000Z",
                    "deterministic": {
                        "padding_px": 4,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["counts"]["deterministic_pass"] == 1
    assert summary["counts"]["deterministic_fail"] == 0
    crop_dir = Path(summary["artifacts"]["run_dir"]) / "crops"
    assert any(crop_dir.iterdir()), "crop file should be written for polygon annotation"


def test_skeleton_annotation_without_bbox_derives_bbox(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (80, 80, 80)).save(image_dir / "skel-sample.png")

    datumaro_path = tmp_path / "datumaro-skeleton.json"
    payload = {
        "categories": {"label": {"labels": [{"name": "pose-label"}]}},
        "items": [
            {
                "id": "skel-sample",
                "image": {"path": "skel-sample.png", "size": [100, 120]},
                "annotations": [
                    {
                        "id": "skel-obj",
                        "type": "skeleton",
                        "label_id": 0,
                        # skeleton: [x0, y0, v0, x1, y1, v1, ...]
                        "points": [10.0, 15.0, 2, 30.0, 25.0, 2, 50.0, 40.0, 1, 20.0, 50.0, 2],
                        "attributes": {"clamp_type": "2-arm"},
                    }
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")

    config_path = tmp_path / "verify-skeleton.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": str(image_dir),
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T090100Z",
                    "deterministic": {
                        "padding_px": 4,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["counts"]["deterministic_pass"] == 1
    assert summary["counts"]["deterministic_fail"] == 0


def test_points_annotation_without_bbox_derives_bbox(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (60, 60, 60)).save(image_dir / "pts-sample.png")

    datumaro_path = tmp_path / "datumaro-points.json"
    payload = {
        "categories": {"label": {"labels": [{"name": "pose-label"}]}},
        "items": [
            {
                "id": "pts-sample",
                "image": {"path": "pts-sample.png", "size": [100, 120]},
                "annotations": [
                    {
                        "id": "pts-obj",
                        "type": "points",
                        "label_id": 0,
                        "points": [5.0, 10.0, 45.0, 10.0, 45.0, 60.0, 5.0, 60.0],
                        "visibility": [2, 2, 2, 2],
                        "attributes": {"clamp_type": "3-arm"},
                    }
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")

    config_path = tmp_path / "verify-points.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": str(image_dir),
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T090200Z",
                    "deterministic": {
                        "padding_px": 4,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["counts"]["deterministic_pass"] == 1
    assert summary["counts"]["deterministic_fail"] == 0


def test_run_verify_marks_object_fail_when_crop_materialization_fails(tmp_path: Path) -> None:
    datumaro_path = _write_datumaro_with_image_paths(tmp_path)
    config_path = tmp_path / "verify-missing-image.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": "missing-images",
                    "output_dir": "runs",
                    "run_timestamp": "20260613T093000Z",
                    "deterministic": {
                        "padding_px": 6,
                        "rules": {
                            "global": {
                                "detection": ["bbox_non_empty"],
                                "attribute": [{"name": "required_attributes", "params": {"required": ["clamp_type"]}}],
                                "skeleton-count": [{"name": "keypoint_count", "params": {"expected": 4}}],
                                "visibility-format": ["visibility_codes"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    ok, summary = run_verify(str(config_path))

    assert ok is True
    assert summary["counts"]["deterministic_fail"] == 1
    reasons = summary["objects"][0]["failure_reasons"]
    assert "image_path_not_found" in reasons


def test_derive_bbox_from_annotation_polygon() -> None:
    from fiftyone_pose_importer.run_verify import _derive_bbox_from_annotation

    ann = {"type": "polygon", "points": [10.0, 20.0, 40.0, 20.0, 40.0, 50.0, 10.0, 50.0]}
    result = _derive_bbox_from_annotation(ann)
    # AABB: min_x=10, min_y=20, w=30, h=30
    assert result == (10.0, 20.0, 30.0, 30.0)


def test_derive_bbox_from_annotation_skeleton() -> None:
    from fiftyone_pose_importer.run_verify import _derive_bbox_from_annotation

    # skeleton: [x0, y0, v0, x1, y1, v1, ...]
    ann = {"type": "skeleton", "points": [10.0, 15.0, 2, 50.0, 40.0, 1]}
    result = _derive_bbox_from_annotation(ann)
    assert result == (10.0, 15.0, 40.0, 25.0)


def test_derive_bbox_from_annotation_points() -> None:
    from fiftyone_pose_importer.run_verify import _derive_bbox_from_annotation

    ann = {"type": "points", "points": [5.0, 10.0, 45.0, 60.0]}
    result = _derive_bbox_from_annotation(ann)
    assert result == (5.0, 10.0, 40.0, 50.0)


def test_derive_bbox_from_annotation_no_points_returns_none() -> None:
    from fiftyone_pose_importer.run_verify import _derive_bbox_from_annotation

    assert _derive_bbox_from_annotation({"type": "bbox", "bbox": [1, 2, 3, 4]}) is None
    assert _derive_bbox_from_annotation({"type": "polygon"}) is None
    assert _derive_bbox_from_annotation({}) is None


def test_run_verify_skeleton_overlay_includes_point_names(tmp_path: Path) -> None:
    """run_verify injects skeleton point names into the overlay so labels appear on crop images."""
    import json

    import yaml
    from PIL import Image as PILImage

    from fiftyone_pose_importer.run_verify import run_verify

    # Minimal 200x200 white source image
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    img_path = img_dir / "frame_001.jpg"
    PILImage.new("RGB", (200, 200), (255, 255, 255)).save(img_path)

    datumaro_data = {
        "categories": {
            "label": {"labels": [{"name": "person", "attributes": []}]},
            "points": {
                "labels": ["nose", "left_eye"],
                "joints": []
            }
        },
        "items": [
            {
                "id": "frame_001",
                "image": {"path": str(img_path), "size": [200, 200]},
                "annotations": [
                    {
                        "id": "ann-0",
                        "type": "skeleton",
                        "label_id": 0,
                        "bbox": [50.0, 50.0, 80.0, 80.0],
                        "points": [90.0, 90.0, 2, 110.0, 90.0, 2],  # x,y,v triplets
                    }
                ]
            }
        ]
    }

    datumaro_path = tmp_path / "data.json"
    datumaro_path.write_text(json.dumps(datumaro_data))

    config = {
        "datumaro_json": str(datumaro_path),
        "verification": {
            "image_dir": str(img_dir),
            "output_dir": str(tmp_path / "runs"),
            "deterministic": {
                "padding_px": 10,
            },
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))

    result = run_verify(str(config_path))
    assert result is not None

    # Find the crop file written by run_verify
    crops = list((tmp_path / "runs").rglob("*.png"))
    assert len(crops) >= 1, "Expected at least one crop image"
    crop_img = PILImage.open(crops[0])

    # The first keypoint (nose) is at x=90, y=90 in original space.
    # After crop, text labels appear above the dot. Some pixels in the label
    # region must be non-white (text was drawn).
    pixels = list(crop_img.convert("RGB").getdata())
    non_white = [p for p in pixels if p != (255, 255, 255)]
    assert len(non_white) > 0, "Expected text label pixels in crop overlay"
