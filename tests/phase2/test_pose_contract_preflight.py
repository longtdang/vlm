from fiftyone_pose_importer.pose_contract import (
    SchemaContractError,
    extract_canonical_skeleton_contract,
    extract_skeleton_contract_bundle,
)
from fiftyone_pose_importer.preflight import PreflightReport


def test_extract_canonical_skeleton_contract_rejects_missing_points() -> None:
    try:
        extract_canonical_skeleton_contract({"categories": {}})
        assert False, "Expected SchemaContractError"
    except SchemaContractError as exc:
        assert exc.category == "missing_skeleton"


def test_extract_canonical_skeleton_contract_rejects_ambiguous_specs() -> None:
    data = {
        "categories": {
            "points": {
                "person": {"labels": ["a"], "joints": []},
                "animal": {"labels": ["b"], "joints": []},
            }
        }
    }
    try:
        extract_canonical_skeleton_contract(data)
        assert False, "Expected SchemaContractError"
    except SchemaContractError as exc:
        assert exc.category == "ambiguous_skeleton"


def test_extract_canonical_skeleton_contract_rejects_invalid_edges() -> None:
    data = {"categories": {"points": {"labels": ["a"], "joints": [[0, 1]]}}}
    try:
        extract_canonical_skeleton_contract(data)
        assert False, "Expected SchemaContractError"
    except SchemaContractError as exc:
        assert exc.category == "invalid_skeleton_edges"


def test_preflight_schema_mismatch_aggregation_counts() -> None:
    report = PreflightReport(
        duplicate_image_keys=[],
        duplicate_annotation_keys=[],
        unmatched_annotation_keys=[],
        unmatched_image_keys=[],
        malformed_annotations=[],
    )
    report.add_schema_mismatch("point_count_mismatch", "sample-1")
    report.add_schema_mismatch("point_count_mismatch", "sample-2")
    report.add_schema_mismatch("invalid_annotation", "sample-3")

    data = report.to_dict()
    assert data["ok"] is False
    assert data["schema_mismatch_counts"]["point_count_mismatch"] == 2
    assert data["schema_mismatch_counts"]["invalid_annotation"] == 1


def test_extract_skeleton_contract_bundle_from_points_items() -> None:
    data = {
        "categories": {
            "points": {
                "items": [
                    {"label_id": 10, "labels": ["a", "b"], "joints": [[1, 2]]},
                    {"label_id": 11, "labels": ["x", "y", "z"], "joints": [[1, 2], [2, 3]]},
                ]
            }
        }
    }
    bundle = extract_skeleton_contract_bundle(data)
    assert bundle.default is None
    assert sorted(bundle.by_label_id.keys()) == [10, 11]
    assert bundle.by_label_id[10].edges == [[0, 1]]
    assert bundle.by_label_id[11].edges == [[0, 1], [1, 2]]
