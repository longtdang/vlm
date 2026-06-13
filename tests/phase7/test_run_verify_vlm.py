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
                    }
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
