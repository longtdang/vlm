from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import fiftyone as fo
import pytest
from PIL import Image

from scripts.crop_validate import LABEL_PROMPTS, _apply_vlm


def _make_minimal_dataset(tmp_path: Path, samples_info: list[dict]) -> fo.Dataset:
    """Build a throw-away FiftyOne dataset with dummy crop images."""
    dataset_name = f"test_apply_vlm_{id(samples_info)}"
    if fo.dataset_exists(dataset_name):
        fo.delete_dataset(dataset_name)
    dataset = fo.Dataset(dataset_name)
    samples = []
    for i, info in enumerate(samples_info):
        img_path = tmp_path / f"crop_{i}.png"
        Image.new("RGB", (64, 64), color=(100, 100, 100)).save(img_path)
        sample = fo.Sample(filepath=str(img_path))
        sample["annotation_label"] = info["label"]
        sample["annotation_type"] = info["ann_type"]
        sample["annotation_attributes"] = info.get("attributes", {})
        samples.append(sample)
    dataset.add_samples(samples)
    # Pre-register vlm_raw_response so get_field works after mocked apply_model
    dataset.add_sample_field("vlm_raw_response", fo.StringField)
    return dataset


class TestApplyVlmAttributeInjection:
    """Tests for _apply_vlm prompt routing and attribute injection."""

    def test_per_sample_attribute_injection_for_forklift_with_roll(
        self, tmp_path: Path
    ) -> None:
        """forklift-with-roll prompt gets per-sample attribute values injected."""
        attrs_a = {"clamp-type": "2-arm", "roll-count": 1.0}
        attrs_b = {"clamp-type": "3-arm", "roll-count": 3.0}
        dataset = _make_minimal_dataset(
            tmp_path,
            [
                {"label": "forklift-with-roll", "ann_type": "detection", "attributes": attrs_a},
                {"label": "forklift-with-roll", "ann_type": "detection", "attributes": attrs_b},
            ],
        )
        try:
            mock_model = MagicMock()
            mock_model.prompt = None
            # Capture each prompt value set before apply_model is called
            prompts_seen: list[str] = []

            def fake_apply_model(model_arg, label_field):
                prompts_seen.append(mock_model.prompt)

            # apply_model is called on a dataset view — mock it via the dataset's method
            with patch("fiftyone.zoo.register_zoo_model_source"), \
                 patch("fiftyone.zoo.load_zoo_model", return_value=mock_model):
                # Patch apply_model on the dataset class so view calls are intercepted
                with patch.object(fo.DatasetView, "apply_model", side_effect=fake_apply_model):
                    _apply_vlm(
                        dataset=dataset,
                        model_name="test-model",
                        plugin_source="https://example.com",
                        pass_threshold=0.20,
                        review_threshold=0.60,
                    )

            assert len(prompts_seen) == 2, f"Expected 2 prompts, got {len(prompts_seen)}"

            # Each prompt should contain the per-sample attribute JSON
            expected_json_a = json.dumps({"attributes": attrs_a}, indent=2)
            expected_json_b = json.dumps({"attributes": attrs_b}, indent=2)
            # Both attrs should appear somewhere in the prompts (order may vary)
            all_prompts = "\n".join(prompts_seen)
            assert '"clamp-type": "2-arm"' in all_prompts
            assert '"clamp-type": "3-arm"' in all_prompts
            assert '"roll-count": 1.0' in all_prompts
            assert '"roll-count": 3.0' in all_prompts
            # Each prompt should contain 'forklift-with-roll' (label substituted)
            for p in prompts_seen:
                assert "forklift-with-roll" in p
        finally:
            if fo.dataset_exists(dataset.name):
                dataset.delete()

    def test_static_prompt_for_forklift_no_roll(self, tmp_path: Path) -> None:
        """forklift-no-roll uses a single static prompt (no attribute injection)."""
        dataset = _make_minimal_dataset(
            tmp_path,
            [
                {"label": "forklift-no-roll", "ann_type": "detection", "attributes": {}},
            ],
        )
        try:
            mock_model = MagicMock()
            mock_model.prompt = None
            prompts_seen: list[str] = []

            def fake_apply_model(model_arg, label_field):
                prompts_seen.append(mock_model.prompt)

            with patch("fiftyone.zoo.register_zoo_model_source"), \
                 patch("fiftyone.zoo.load_zoo_model", return_value=mock_model):
                with patch.object(fo.DatasetView, "apply_model", side_effect=fake_apply_model):
                    _apply_vlm(
                        dataset=dataset,
                        model_name="test-model",
                        plugin_source="https://example.com",
                        pass_threshold=0.20,
                        review_threshold=0.60,
                    )

            # One apply_model call for the batch (not per-sample)
            assert len(prompts_seen) == 1
            prompt = prompts_seen[0]
            assert "forklift-no-roll" in prompt
            assert "{annotation_fields_json}" not in prompt
            assert "error_probability" in prompt
        finally:
            if fo.dataset_exists(dataset.name):
                dataset.delete()

    def test_fallback_to_default_prompts_for_unknown_label(self, tmp_path: Path) -> None:
        """Labels not in LABEL_PROMPTS fall back to DEFAULT_PROMPTS[ann_type]."""
        dataset = _make_minimal_dataset(
            tmp_path,
            [
                {"label": "unknown-label", "ann_type": "detection", "attributes": {}},
            ],
        )
        try:
            mock_model = MagicMock()
            mock_model.prompt = None
            prompts_seen: list[str] = []

            def fake_apply_model(model_arg, label_field):
                prompts_seen.append(mock_model.prompt)

            with patch("fiftyone.zoo.register_zoo_model_source"), \
                 patch("fiftyone.zoo.load_zoo_model", return_value=mock_model):
                with patch.object(fo.DatasetView, "apply_model", side_effect=fake_apply_model):
                    _apply_vlm(
                        dataset=dataset,
                        model_name="test-model",
                        plugin_source="https://example.com",
                        pass_threshold=0.20,
                        review_threshold=0.60,
                    )

            assert len(prompts_seen) == 1
            prompt = prompts_seen[0]
            # Fallback uses DEFAULT_PROMPTS["detection"] with label="detection"
            assert "detection" in prompt
            assert "error_probability" in prompt
        finally:
            if fo.dataset_exists(dataset.name):
                dataset.delete()
