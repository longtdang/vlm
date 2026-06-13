from __future__ import annotations

import json
from pathlib import Path

import yaml

from fiftyone_pose_importer.run_verify import run_verify


def _write_config(tmp_path: Path, datumaro_path: Path) -> Path:
    config_path = tmp_path / "verify.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "datumaro_json": str(datumaro_path),
                "verification": {
                    "vlm": {"enabled": False},
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
                "image": {"size": [100, 120]},
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
