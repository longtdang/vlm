from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace


class _Dataset:
    last_created: "_Dataset | None" = None

    def __init__(self, name: str):
        self.name = name
        self.default_skeleton = None
        self.skeletons: dict[str, object] = {}
        self.samples: list[_Sample] = []
        _Dataset.last_created = self

    def add_samples(self, samples: list["_Sample"]) -> None:
        self.samples.extend(samples)

    def save(self) -> None:
        return None


class _Sample(dict):
    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath


class _Keypoint(dict):
    def __init__(self, points: list[list[float]]):
        super().__init__()
        self.points = points


class _Keypoints:
    def __init__(self, keypoints: list[_Keypoint]):
        self.keypoints = keypoints


class _KeypointSkeleton:
    def __init__(self, labels: list[str], edges: list[list[int]]):
        self.labels = labels
        self.edges = edges


def _install_fake_fiftyone() -> types.ModuleType:
    module = types.ModuleType("fiftyone")
    module.Dataset = _Dataset
    module.Sample = _Sample
    module.Keypoint = _Keypoint
    module.Keypoints = _Keypoints
    module.KeypointSkeleton = _KeypointSkeleton
    module.launch_app = lambda _dataset: None
    return module


def _load_run_import_module():
    sys.modules["fiftyone"] = _install_fake_fiftyone()
    if "fiftyone_pose_importer.run_import" in sys.modules:
        return importlib.reload(sys.modules["fiftyone_pose_importer.run_import"])
    return importlib.import_module("fiftyone_pose_importer.run_import")


def _run_import_with_payload(payload: dict, item: dict, *, label_field: str = "ground_truth"):
    module = _load_run_import_module()
    module.load_config = lambda _path: SimpleNamespace(
        datumaro_json=Path("datumaro.json"),
        image_dir=Path("images"),
        dataset_name="phase5-contracts",
        label_field=label_field,
        config_path=Path("config.yaml"),
    )
    module.load_datumaro = lambda _path: payload
    module.build_image_index = lambda _image_dir: ({}, [])
    module.build_matches = lambda _index, _items: ([(Path("image.jpg"), item)], [], [], [])
    module.write_summary = lambda _cfg_path, summary: Path(summary.get("dataset_name", "summary") + ".summary.json")
    ok, summary = module.run_import("config.yaml")
    dataset = _Dataset.last_created
    return ok, summary, dataset


def _multi_skeleton_payload(*, label_names_a: list[str] | None = None) -> tuple[dict, dict]:
    labels_a = label_names_a or ["a-1", "a-2"]
    item = {
        "id": "sample-05",
        "image": {"size": [100, 100]},
        "annotations": [
            {"id": 2, "type": "skeleton", "label_id": 11, "points": [30, 30, 2, 40, 40, 2, 50, 50, 1]},
            {"id": 1, "type": "skeleton", "label_id": 10, "points": [10, 10, 2, 20, 20, 2]},
        ],
    }
    payload = {
        "categories": {
            "points": {
                "items": [
                    {"label_id": 10, "label": "Arm Clamp", "labels": labels_a, "joints": [[1, 2]]},
                    {"label_id": 11, "label": "Main Roll", "labels": ["b-1", "b-2", "b-3"], "joints": [[1, 2], [2, 3]]},
                ]
            }
        },
        "items": [item],
    }
    return payload, item


def test_per_label_id_field_mapping() -> None:
    payload, item = _multi_skeleton_payload()
    ok, summary, dataset = _run_import_with_payload(payload, item)

    assert ok is True
    assert summary["written_samples"] == 1
    sample = dataset.samples[0]

    # Contract (D-01/D-02): route by stable label_id identity to keypoints_label_<id>
    assert "keypoints_label_10" in sample
    assert "keypoints_label_11" in sample
    assert len(sample["keypoints_label_10"].keypoints) == 1
    assert len(sample["keypoints_label_11"].keypoints) == 1


def test_no_single_field_collapse() -> None:
    payload, item = _multi_skeleton_payload()
    ok, _summary, dataset = _run_import_with_payload(payload, item, label_field="ground_truth")

    assert ok is True
    sample = dataset.samples[0]

    # Contract (SKEL-02/D-03): no fallback collapse into one shared field
    assert "ground_truth" not in sample
    assert set(sample.keys()) == {"keypoints_label_10", "keypoints_label_11"}


def test_label_text_changes_keep_field_identity() -> None:
    payload_v1, item_v1 = _multi_skeleton_payload(label_names_a=["joint-a", "joint-b"])
    payload_v2, item_v2 = _multi_skeleton_payload(label_names_a=["renamed-a", "renamed-b"])

    ok1, _summary1, dataset_v1 = _run_import_with_payload(payload_v1, item_v1)
    ok2, _summary2, dataset_v2 = _run_import_with_payload(payload_v2, item_v2)

    assert ok1 is True
    assert ok2 is True

    # Contract (D-04): mutable text metadata must not alter canonical field identity.
    assert "keypoints_label_10" in dataset_v1.samples[0]
    assert "keypoints_label_10" in dataset_v2.samples[0]



def test_visibility_invalid_values_fail_preflight() -> None:
    bad_item = {
        "id": "sample-bad-vis",
        "image": {"size": [100, 100]},
        "annotations": [
            {"type": "points", "label_id": 10, "points": [1, 1, 2, 2], "visibility": [2, 5]},
            {"type": "points", "label_id": 10, "points": [1, 1, 2, 2], "visibility": [2]},
        ],
    }
    payload = {
        "categories": {"points": {"items": [{"label_id": 10, "label": "Arm Clamp", "labels": ["a", "b"], "joints": [[1, 2]]}]}},
        "items": [bad_item],
    }

    ok, summary, _dataset = _run_import_with_payload(payload, bad_item)

    # Contract (D-05): invalid values and length mismatch both block import at preflight.
    assert ok is False
    mismatch_counts = summary["preflight"]["schema_mismatch_counts"]
    assert "invalid_visibility_values" in mismatch_counts
    assert "visibility_length_mismatch" in mismatch_counts


def test_missing_visibility_defaults_to_two() -> None:
    item = {
        "id": "sample-default-vis",
        "image": {"size": [100, 100]},
        "annotations": [
            {"type": "skeleton", "label_id": 10, "points": [10, 10, 2, 20, 20, 2]},
            {"type": "points", "label_id": 10, "points": [30, 30, 40, 40]},
        ],
    }
    payload = {
        "categories": {"points": {"items": [{"label_id": 10, "label": "Arm Clamp", "labels": ["a", "b"], "joints": [[1, 2]]}]}},
        "items": [item],
    }

    ok, summary, dataset = _run_import_with_payload(payload, item)

    assert ok is True
    assert summary["warnings"]["counts"]["defaulted_visibility_annotations"] == 1
    assert summary["visibility"]["defaulted_annotations"] == 1

    # Contract carries routed field expectation alongside defaulting semantics.
    sample = dataset.samples[0]
    assert "keypoints_label_10" in sample
    defaulted_pose = sample["keypoints_label_10"].keypoints[1]
    assert defaulted_pose["visibility"] == [2, 2]



def test_mapping_metadata_emitted_with_required_keys() -> None:
    payload, item = _multi_skeleton_payload()
    ok, summary, _dataset = _run_import_with_payload(payload, item)

    assert ok is True

    # Contract (D-07): mapping metadata must exist in run summary.
    assert "mapping" in summary
    mapping = summary["mapping"]
    assert isinstance(mapping, list)
    assert len(mapping) == 2

    required_keys = {
        "label_id",
        "source_label_name",
        "target_field",
        "skeleton_labels",
        "skeleton_edges",
        "visibility_policy",
    }

    for entry in mapping:
        assert required_keys.issubset(entry.keys())
        assert entry["target_field"] == f"keypoints_label_{entry['label_id']}"
