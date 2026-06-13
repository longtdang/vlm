from __future__ import annotations

from PIL import Image
import importlib
import pytest

vlm_client = importlib.import_module("fiftyone_pose_importer.verification.vlm_client")
FiftyOneZooAdapter = vlm_client.FiftyOneZooAdapter
MockVlmAdapter = vlm_client.MockVlmAdapter


def _img() -> Image.Image:
    return Image.new("RGB", (1, 1), (128, 64, 32))


def test_mock_vlm_adapter_default_response() -> None:
    adapter = MockVlmAdapter()
    assert adapter.generate_text(_img(), "any prompt") == '{"error_probability": 0.1, "reason": "mock-ok"}'


def test_mock_vlm_adapter_key_match() -> None:
    adapter = MockVlmAdapter(
        responses={"bbox_localization": '{"error_probability": 0.5, "reason": "off"}'},
    )
    assert (
        adapter.generate_text(_img(), "evaluate rule bbox_localization for this crop")
        == '{"error_probability": 0.5, "reason": "off"}'
    )


def test_mock_vlm_adapter_no_key_match_uses_default() -> None:
    adapter = MockVlmAdapter(responses={"clamp_type": "x"}, default_response="fallback")
    assert adapter.generate_text(_img(), "roll_count rule") == "fallback"


def test_mock_vlm_adapter_custom_default() -> None:
    adapter = MockVlmAdapter(default_response='{"error_probability": 0.0, "reason": "fine"}')
    assert adapter.generate_text(_img(), "anything") == '{"error_probability": 0.0, "reason": "fine"}'


def test_fiftyone_zoo_adapter_uses_injected_model_not_foz() -> None:
    class _Config:
        prompt = ""

    class FakeModel:
        def __init__(self) -> None:
            self.config = _Config()

        def _generate_detections(self, images: list[Image.Image]) -> list[str]:
            assert len(images) == 1
            return ["raw text from fake model"]

    fake_model = FakeModel()
    adapter = FiftyOneZooAdapter(model_name="qwen3-vl-2b-instruct-torch")
    adapter._model = fake_model

    assert adapter.generate_text(_img(), "my prompt") == "raw text from fake model"
    assert fake_model.config.prompt == "my prompt"


def test_fiftyone_zoo_adapter_propagates_model_exception() -> None:
    class _Config:
        prompt = ""

    class FakeModel:
        def __init__(self) -> None:
            self.config = _Config()

        def _generate_detections(self, images: list[Image.Image]) -> list[str]:
            raise RuntimeError("inference failed")

    adapter = FiftyOneZooAdapter(model_name="qwen3-vl-2b-instruct-torch")
    adapter._model = FakeModel()

    with pytest.raises(RuntimeError, match="inference failed"):
        adapter.generate_text(_img(), "prompt")
