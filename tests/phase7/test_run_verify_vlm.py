from __future__ import annotations

import json
from pathlib import Path

import yaml
from PIL import Image

from fiftyone_pose_importer.run_verify import run_verify
from fiftyone_pose_importer.verification.vlm_client import MockVlmAdapter


def _write_datumaro_vlm(tmp_path: Path) -> Path:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (200, 64, 32)).save(image_dir / "sample-1.png")

    datumaro_path = tmp_path / "datumaro.json"
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
                        "id": "obj-pass-vlm-scope",
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [10, 10, 30, 20],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[10, 10], [20, 20], [25, 20], [30, 25]],
                        "visibility": [2, 2, 2, 2],
                    },
                    {
                        "id": "obj-pass-no-vlm-scope",
                        "type": "bbox",
                        "label_id": 1,
                        "bbox": [10, 10, 30, 20],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[10, 10], [20, 20], [25, 20], [30, 25]],
                        "visibility": [2, 2, 2, 2],
                    },
                    {
                        "id": "obj-fail-det",
                        "type": "bbox",
                        "label_id": 0,
                        "bbox": [5, 5, 0, 20],
                        "attributes": {"clamp_type": "2-arm"},
                        "keypoints": [[1, 1], [2, 2], [3, 3], [4, 4]],
                        "visibility": [2, 2, 2, 2],
                    },
                ],
            }
        ],
    }
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")
    return datumaro_path


def _write_vlm_config(tmp_path: Path, datumaro_path: Path) -> Path:
    config_path = tmp_path / "verify-vlm.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {
                        "enabled": True,
                        "model_name": "qwen3-vl-2b-instruct-torch",
                        "thresholds": {"pass_below": 0.20, "review_below": 0.60},
                        "generation": {"max_new_tokens": 256},
                        "labels": {
                            "forklift-with-roll": {
                                "enabled": True,
                                "rules": ["bbox_localization", "bbox_coverage"],
                            }
                        },
                    },
                    "image_dir": "images",
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T120000Z",
                    "deterministic": {
                        "padding_px": 8,
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
    return config_path


def test_vlm_pipeline_produces_three_vlm_artifacts(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config = _write_vlm_config(tmp_path, datumaro)
    mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')

    ok, summary = run_verify(str(config), _vlm_adapter=mock)

    assert ok is True
    assert summary["vlm_enabled"] is True
    assert summary["vlm_counts"]["vlm_total"] == 1
    assert Path(summary["vlm_artifacts"]["vlm_csv"]).exists()
    assert Path(summary["vlm_artifacts"]["vlm_json"]).exists()
    assert Path(summary["vlm_artifacts"]["vlm_ndjson"]).exists()


def test_vlm_artifacts_in_same_run_dir_as_deterministic(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config = _write_vlm_config(tmp_path, datumaro)
    mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')

    ok, summary = run_verify(str(config), _vlm_adapter=mock)

    assert ok is True
    det_run_dir = Path(summary["artifacts"]["run_dir"])
    vlm_csv_dir = Path(summary["vlm_artifacts"]["vlm_csv"]).parent
    assert det_run_dir == vlm_csv_dir


def test_deterministic_fail_objects_excluded_from_vlm(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config = _write_vlm_config(tmp_path, datumaro)
    mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')

    ok, summary = run_verify(str(config), _vlm_adapter=mock)

    assert ok is True
    vlm_json = json.loads(Path(summary["vlm_artifacts"]["vlm_json"]).read_text(encoding="utf-8"))
    vlm_object_ids = {obj["object_id"] for obj in vlm_json["objects"]}
    assert "obj-fail-det" not in vlm_object_ids


def test_label_not_in_vlm_scope_excluded(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config = _write_vlm_config(tmp_path, datumaro)
    mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')

    ok, summary = run_verify(str(config), _vlm_adapter=mock)

    assert ok is True
    vlm_json = json.loads(Path(summary["vlm_artifacts"]["vlm_json"]).read_text(encoding="utf-8"))
    vlm_object_ids = {obj["object_id"] for obj in vlm_json["objects"]}
    assert "obj-pass-no-vlm-scope" not in vlm_object_ids


def test_vlm_counts_in_summary(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config = _write_vlm_config(tmp_path, datumaro)
    mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')

    ok, summary = run_verify(str(config), _vlm_adapter=mock)

    assert ok is True
    counts = summary["vlm_counts"]
    assert counts["vlm_total"] == 1
    assert counts["vlm_pass"] == 1
    assert counts["vlm_review"] == 0
    assert counts["vlm_fail"] == 0


def test_vlm_disabled_produces_no_vlm_artifacts(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config_path = tmp_path / "verify-vlm-disabled.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro),
                "verification": {
                    "vlm": {"enabled": False},
                    "image_dir": "images",
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T150000Z",
                    "deterministic": {
                        "padding_px": 8,
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
    assert "vlm_artifacts" not in summary
    assert "vlm_counts" not in summary


def test_vlm_high_ep_produces_fail_verdict(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config_path = tmp_path / "verify-high-ep.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro),
                "verification": {
                    "vlm": {
                        "enabled": True,
                        "model_name": "qwen3-vl-2b-instruct-torch",
                        "thresholds": {"pass_below": 0.20, "review_below": 0.60},
                        "generation": {"max_new_tokens": 256},
                        "labels": {"forklift-with-roll": {"enabled": True, "rules": ["bbox_localization"]}},
                    },
                    "image_dir": "images",
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T130000Z",
                    "deterministic": {
                        "padding_px": 8,
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

    mock = MockVlmAdapter(default_response='{"error_probability": 0.85, "reason": "bad bbox"}')
    ok, summary = run_verify(str(config_path), _vlm_adapter=mock)

    assert ok is True
    assert summary["vlm_counts"]["vlm_fail"] == 1
    assert summary["vlm_counts"]["vlm_pass"] == 0


def test_review_queue_in_vlm_json_is_ordered(tmp_path: Path) -> None:
    datumaro = _write_datumaro_vlm(tmp_path)
    config_path = tmp_path / "verify-review-queue.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro),
                "verification": {
                    "vlm": {
                        "enabled": True,
                        "model_name": "qwen3-vl-2b-instruct-torch",
                        "thresholds": {"pass_below": 0.05, "review_below": 0.50},
                        "generation": {"max_new_tokens": 256},
                        "labels": {"forklift-with-roll": {"enabled": True, "rules": ["bbox_localization"]}},
                    },
                    "image_dir": "images",
                    "output_dir": str(tmp_path / "runs"),
                    "run_timestamp": "20260614T140000Z",
                    "deterministic": {
                        "padding_px": 8,
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

    mock = MockVlmAdapter(default_response='{"error_probability": 0.3, "reason": "uncertain"}')
    ok, summary = run_verify(str(config_path), _vlm_adapter=mock)

    assert ok is True
    vlm_json = json.loads(Path(summary["vlm_artifacts"]["vlm_json"]).read_text(encoding="utf-8"))
    assert isinstance(vlm_json["review_queue"], list)
