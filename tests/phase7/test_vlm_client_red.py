from PIL import Image

from fiftyone_pose_importer.verification.vlm_client import MockVlmAdapter


def test_mock_adapter_default_response():
    img = Image.new("RGB", (1, 1), (0, 0, 0))
    adapter = MockVlmAdapter()
    assert adapter.generate_text(img, "any") == '{"error_probability": 0.1, "reason": "mock-ok"}'
