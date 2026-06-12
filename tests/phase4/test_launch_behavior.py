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
    module.launch_calls = []

    def _launch(dataset):
        module.launch_calls.append(dataset)
        return None

    module.launch_app = _launch
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


def test_launch_status_reporting() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-1",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 10, 20, 20, 30, 30], "visibility": [2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [item]
    _configure(module, data, item)

    ok, summary = module.run_import("config.yaml", launch_app=True)
    assert ok is True
    assert summary["launch"] == {"requested": True, "attempted": True, "ok": True, "error": None}


def test_launch_preflight_guard() -> None:
    module = _load_run_import_module()
    bad_item = {
        "id": "sample-2",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [1, 1, 2, 2, 3, 3, 4, 4], "visibility": [2, 2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [bad_item]
    _configure(module, data, bad_item)

    ok, summary = module.run_import("config.yaml", launch_app=True)
    assert ok is False
    assert summary["launch"]["requested"] is True
    assert summary["launch"]["attempted"] is False


def test_launch_preserves_connected_skeleton_contract() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-3",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 10, 20, 20, 30, 30], "visibility": [2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [item]
    _configure(module, data, item)

    ok, _summary = module.run_import("config.yaml", launch_app=True)
    assert ok is True
    launch_dataset = sys.modules["fiftyone"].launch_calls[0]
    assert launch_dataset.default_skeleton.labels == ["nose", "left_eye", "right_eye"]
    assert launch_dataset.default_skeleton.edges == [[0, 1], [0, 2]]


def test_launch_uses_fo_launch_app() -> None:
    module = _load_run_import_module()
    item = {
        "id": "sample-4",
        "image": {"size": [100, 100]},
        "annotations": [{"type": "points", "points": [10, 10, 20, 20, 30, 30], "visibility": [2, 2, 2]}],
    }
    data = _base_data()
    data["items"] = [item]
    _configure(module, data, item)

    ok, _summary = module.run_import("config.yaml", launch_app=True)
    assert ok is True
    assert len(sys.modules["fiftyone"].launch_calls) == 1


def test_cli_launch_wiring() -> None:
    sys.modules["fiftyone"] = _install_fake_fiftyone()
    if "fiftyone_pose_importer.cli" in sys.modules:
        cli = importlib.reload(sys.modules["fiftyone_pose_importer.cli"])
    else:
        cli = importlib.import_module("fiftyone_pose_importer.cli")

    called = {}

    def fake_run_import(config_path: str, launch_app: bool = False):
        called["config_path"] = config_path
        called["launch_app"] = launch_app
        return True, {"ok": True}

    cli.run_import = fake_run_import
    cli.write_summary = lambda *_args, **_kwargs: Path("summary.json")
    original_argv = sys.argv
    sys.argv = ["prog", "--config", "config.yaml", "--launch"]
    try:
        code = cli.main()
    finally:
        sys.argv = original_argv
    assert code == 0
    assert called == {"config_path": "config.yaml", "launch_app": True}
