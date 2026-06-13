from __future__ import annotations

from typing import Protocol, runtime_checkable

from PIL import Image as PILImage


@runtime_checkable
class VlmAdapter(Protocol):
    def generate_text(self, image: PILImage.Image, prompt: str) -> str: ...


class FiftyOneZooAdapter:
    """Thin wrapper around FiftyOne zoo Qwen3-VL model for raw text generation.

    Loads the model lazily on first call. Not thread-safe — single sequential
    pipeline use only. Per D-01: FiftyOne model-zoo only.
    """

    def __init__(self, model_name: str, max_new_tokens: int = 256) -> None:
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._model = None

    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        if self._model is None:
            import fiftyone.zoo as foz

            self._model = foz.load_zoo_model(
                self._model_name,
                max_new_tokens=self._max_new_tokens,
            )
        self._model.config.prompt = prompt
        raw_texts: list[str] = self._model._generate_detections([image])
        return raw_texts[0]


class MockVlmAdapter:
    """Deterministic mock for CI tests.

    Returns a configured response when key substring appears in the prompt,
    otherwise returns default_response.
    """

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = '{"error_probability": 0.1, "reason": "mock-ok"}',
    ) -> None:
        self._responses: dict[str, str] = responses or {}
        self._default = default_response

    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        for key, resp in self._responses.items():
            if key in prompt:
                return resp
        return self._default
