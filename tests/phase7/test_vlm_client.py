from __future__ import annotations

from unittest.mock import MagicMock

from PIL import Image
import importlib
import pytest

vlm_client = importlib.import_module("fiftyone_pose_importer.verification.vlm_client")
FiftyOneZooAdapter = vlm_client.FiftyOneZooAdapter
MockVlmAdapter = vlm_client.MockVlmAdapter


def _img() -> Image.Image:
    return Image.new("RGB", (1, 1), (128, 64, 32))


def _make_fake_zoo_model(generate_return: str = "raw text from fake model", raises: Exception | None = None):
    """Build a fake zoo model with the same interface as Qwen3VLModel post-load.

    Uses pure MagicMock objects so torch is not required in the test environment.
    fake_input_ids is a list to mirror the [in_ids, ...] zip-slicing in generate_text.
    """
    fake_input_ids = MagicMock()
    fake_input_ids.__len__ = lambda self: 3

    fake_out_ids = MagicMock()
    fake_out_ids.__getitem__ = lambda self, key: MagicMock()

    processor = MagicMock()
    # apply_chat_template returns a dict; input_ids must be iterable for zip
    processor.apply_chat_template.return_value = {"input_ids": [fake_input_ids]}
    processor.batch_decode.return_value = [generate_return]

    hf_model = MagicMock()
    if raises is not None:
        hf_model.generate.side_effect = raises
    else:
        hf_model.generate.return_value = [fake_out_ids]

    zoo_model = MagicMock()
    zoo_model._model = hf_model
    zoo_model._processor = processor
    return zoo_model, hf_model, processor


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
    zoo_model, hf_model, processor = _make_fake_zoo_model("raw text from fake model")

    adapter = FiftyOneZooAdapter(model_name="qwen3-vl-2b-instruct-torch")
    adapter._zoo_model = zoo_model

    result = adapter.generate_text(_img(), "my prompt")

    assert result == "raw text from fake model"
    processor.apply_chat_template.assert_called_once()
    # Verify prompt was forwarded in the messages content
    # apply_chat_template now receives a list of conversations (batch format)
    call_messages = processor.apply_chat_template.call_args.args[0]
    prompt_parts = [
        part.get("text")
        for conversation in call_messages
        for msg in conversation
        for part in msg.get("content", [])
        if isinstance(part, dict) and "text" in part
    ]
    assert "my prompt" in prompt_parts
    hf_model.generate.assert_called_once()
    processor.batch_decode.assert_called_once()


def test_fiftyone_zoo_adapter_propagates_model_exception() -> None:
    zoo_model, _, _ = _make_fake_zoo_model(raises=RuntimeError("inference failed"))

    adapter = FiftyOneZooAdapter(model_name="qwen3-vl-2b-instruct-torch")
    adapter._zoo_model = zoo_model

    with pytest.raises(RuntimeError, match="inference failed"):
        adapter.generate_text(_img(), "prompt")
