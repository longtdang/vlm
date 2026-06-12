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


def test_canonical_mapping_contract_padding() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-1",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 20], "visibility": [2]}],
    }
    data = _base_data()
    data["items"] = [item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img1.jpg"), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, summary = module.run_import("config.yaml")
    assert ok is True
    assert summary["written_samples"] == 1

    dataset = sys.modules["fiftyone"].Dataset.last_created
    keypoints_obj = dataset.samples[0]["ground_truth"]
    first_pose = keypoints_obj.keypoints[0]
    assert len(first_pose.points) == 3
    assert first_pose.points[1][0] != first_pose.points[1][0]  # NaN
    assert first_pose["visibility"] == [2, 0, 0]


def test_preflight_failfast_and_deterministic_pose_order() -> None:
    module = _load_run_import_module()
    bad_item = {
        "id": "sample-2",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [1, 1, 2, 2, 3, 3, 4, 4], "visibility": [2, 2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [bad_item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img2.jpg"), bad_item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, summary = module.run_import("config.yaml")
    assert ok is False
    assert summary["preflight"]["schema_mismatch_counts"]["point_count_mismatch"] == 1


def test_skeleton_labels_edges_applied() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-3",
        "image": {"size": [100, 100]},
        "annotations": [
            {"id": 2, "type": "points", "points": [20, 20, 30, 30, 40, 40], "visibility": [2, 2, 2]},
            {"id": 1, "type": "points", "points": [10, 10, 15, 15, 25, 25], "visibility": [2, 2, 2]},
        ],
    }
    data = _base_data()
    data["items"] = [item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img3.jpg"), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, _summary = module.run_import("config.yaml")
    assert ok is True
    dataset = sys.modules["fiftyone"].Dataset.last_created
    assert dataset.default_skeleton.labels == ["nose", "left_eye", "right_eye"]
    assert dataset.default_skeleton.edges == [[0, 1], [0, 2]]
    mapped = dataset.samples[0]["ground_truth"].keypoints
    assert len(mapped) == 2
    # id=1 should come first after deterministic sort by annotation id
    assert mapped[0].points[0] == [0.1, 0.1]


def test_visibility_fidelity_mapping() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-4",
        "image": {"size": [100, 100]},
        "annotations": [
            {
                "type": "points",
                "points": [10, 10, 20, 20, 30, 30],
                "visibility": [0, 1, 2],
            }
        ],
    }
    data = _base_data()
    data["items"] = [item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img4.jpg"), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, _summary = module.run_import("config.yaml")
    assert ok is True
    dataset = sys.modules["fiftyone"].Dataset.last_created
    pose = dataset.samples[0]["ground_truth"].keypoints[0]
    assert pose["visibility"] == [0, 1, 2]
    assert pose.points[0][0] != pose.points[0][0]  # NaN for absent
    assert pose.points[1] == [0.2, 0.2]
    assert pose.points[2] == [0.3, 0.3]


def test_visibility_metadata_preserved() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-5",
        "image": {"size": [100, 100]},
        "annotations": [
            {"id": 2, "type": "points", "points": [20, 20, 30, 30], "visibility": [1, 2]},
            {"id": 1, "type": "points", "points": [10, 10, 15, 15]},
        ],
    }
    data = _base_data()
    data["items"] = [item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img5.jpg"), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, _summary = module.run_import("config.yaml")
    assert ok is True
    dataset = sys.modules["fiftyone"].Dataset.last_created
    keypoints = dataset.samples[0]["ground_truth"].keypoints
    assert len(keypoints) == 2
    assert keypoints[0]["source_visibility"] == []
    assert keypoints[0]["visibility_defaulted"] is True
    assert keypoints[1]["source_visibility"] == [1, 2]
    assert keypoints[1]["visibility_defaulted"] is False


def test_visibility_summary_counts_and_defaults() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-6",
        "image": {"size": [100, 100]},
        "annotations": [
            {"type": "points", "points": [10, 10, 20, 20, 30, 30], "visibility": [0, 1, 2]},
            {"type": "points", "points": [40, 40, 50, 50, 60, 60]},
        ],
    }
    data = _base_data()
    data["items"] = [item]

    module.load_config = lambda _: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="ds",
        label_field="ground_truth",
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _: data
    module.build_image_index = lambda _: ({}, [])
    module.build_matches = lambda _a, _b: ([(Path("img6.jpg"), item)], [], [], [])
    module.write_summary = lambda _config, _summary: Path("summary.json")

    ok, summary = module.run_import("config.yaml")
    assert ok is True
    assert summary["visibility"] == {
        "absent": 1,
        "hidden": 1,
        "visible": 4,
        "defaulted_annotations": 1,
    }
