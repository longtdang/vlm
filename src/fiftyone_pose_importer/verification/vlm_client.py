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

    Model loading uses ``fiftyone.zoo.load_zoo_model`` which downloads and
    caches the Qwen3-VL weights from HuggingFace. Inference is performed via
    the underlying HuggingFace ``model.generate()`` API directly rather than
    any private FiftyOne method, making it stable against fiftyone internals
    changes (dependency pinned to ``<2.0.0`` in pyproject.toml).
    """

    def __init__(self, model_name: str, max_new_tokens: int = 256) -> None:
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._zoo_model = None

    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        if self._zoo_model is None:
            import fiftyone.zoo as foz

            self._zoo_model = foz.load_zoo_model(
                self._model_name,
                max_new_tokens=self._max_new_tokens,
            )

        # Access the underlying HuggingFace model and processor that
        # foz.load_zoo_model loads and stores on the zoo model object.
        # This uses the stable HuggingFace generate() API rather than any
        # private fiftyone method (_generate_detections etc.).
        hf_model = self._zoo_model._model
        processor = self._zoo_model._processor

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        # Move tensor values to the model's device; non-tensors (strings etc.)
        # are passed through unchanged via the hasattr guard.
        inputs = {
            k: v.to(hf_model.device) if hasattr(v, "to") else v
            for k, v in inputs.items()
        }

        generated_ids = hf_model.generate(
            **inputs,
            max_new_tokens=self._max_new_tokens,
            do_sample=False,
        )
        generated_ids_trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
        ]
        return processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]


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
