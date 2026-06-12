from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace


def _install_fake_fiftyone() -> types.ModuleType:
    module = types.ModuleType("fiftyone")

    class KeypointSkeleton:
        def __init__(self, labels: list[str], edges: list[list[int]]):
            self.labels = labels
            self.edges = edges

    class Keypoint(dict):
        def __init__(self, points: list[list[float]]):
            super().__init__()
            self.points = points

    class Keypoints:
        def __init__(self, keypoints: list[Keypoint]):
            self.keypoints = keypoints

    class Sample(dict):
        def __init__(self, filepath: str):
            super().__init__()
            self.filepath = filepath

    class Dataset:
        last_created: "Dataset | None" = None

        def __init__(self, name: str):
            self.name = name
            self.default_skeleton = None
            self.samples: list[Sample] = []
            Dataset.last_created = self

        def add_samples(self, samples: list[Sample]) -> None:
            self.samples.extend(samples)

        def save(self) -> None:
            return None

    module.KeypointSkeleton = KeypointSkeleton
    module.Keypoint = Keypoint
    module.Keypoints = Keypoints
    module.Sample = Sample
    module.Dataset = Dataset
    module.launch_app = lambda dataset: None
    return module


def _load_run_import_module():
    sys.modules["fiftyone"] = _install_fake_fiftyone()
    if "fiftyone_pose_importer.run_import" in sys.modules:
        return importlib.reload(sys.modules["fiftyone_pose_importer.run_import"])
    return importlib.import_module("fiftyone_pose_importer.run_import")


def _base_data() -> dict:
    return {
        "categories": {"points": {"labels": ["nose", "left_eye", "right_eye"], "joints": [[0, 1], [0, 2]]}},
        "items": [],
    }


def _configure(module, data: dict, item: dict, image_name: str = "img.jpg") -> None:
    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path(image_name), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("config.summary.json")


def test_summary_additive_schema() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-1",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 20, 30, 40, 50, 60], "visibility": [2, 1, 0]}],
    }
    data = _base_data()
    data["items"] = [item]
    _configure(module, data, item)

    ok, summary = module.run_import("config.yaml")
    assert ok is True
    assert "preflight" in summary
    assert "visibility" in summary
    assert summary["label_counts"]["keypoint_annotations"] == 1
    assert summary["label_counts"]["keypoint_positions_total"] == 3
    assert "warnings" in summary
    assert "failures" in summary


def test_warning_failure_rollups() -> None:
    module = _load_run_import_module()
    bad_item = {
        "id": "sample-2",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [1, 1, 2, 2, 3, 3, 4, 4], "visibility": [2, 2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [bad_item]
    _configure(module, data, bad_item, image_name="img2.jpg")

    ok, summary = module.run_import("config.yaml")
    assert ok is False
    assert summary["failures"]["counts"]["schema_mismatches_total"] == 1
    assert summary["failures"]["details"]["schema_mismatch_counts"]["point_count_mismatch"] == 1
    assert "point_count_mismatch" in summary["failures"]["details"]["schema_mismatches"]


def test_summary_path_contract_success_and_failure() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-3",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 10], "visibility": [2]}],
    }
    data = _base_data()
    data["items"] = [item]
    _configure(module, data, item, image_name="img3.jpg")

    ok_success, summary_success = module.run_import("config.yaml")
    assert ok_success is True
    assert summary_success["summary_path"].endswith("config.summary.json")

    # failure case
    bad_item = {
        "id": "sample-4",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [1, 1, 2, 2, 3, 3, 4, 4], "visibility": [2, 2, 2, 2]}],
    }
    data["items"] = [bad_item]
    _configure(module, data, bad_item, image_name="img4.jpg")

    ok_failure, summary_failure = module.run_import("config.yaml")
    assert ok_failure is False
    assert summary_failure["summary_path"].endswith("config.summary.json")
