from fiftyone_pose_importer.verification.vlm_types import VlmVerdict
from fiftyone_pose_importer.verification.vlm_config import load_vlm_config, VlmConfigError


def test_vlm_verdict_members_exist():
    assert VlmVerdict("PASS").value == "PASS"


def test_load_vlm_config_requires_model_name():
    try:
        load_vlm_config({})
    except VlmConfigError:
        return
    raise AssertionError("expected VlmConfigError")
