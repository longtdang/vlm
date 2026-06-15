from __future__ import annotations

import pytest
from scripts.crop_validate import _ep_to_verdict, _parse_vlm_response


class TestParseVlmResponse:
    def test_plain_json(self) -> None:
        raw = '{"error_probability": 0.1, "reason": "looks good"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.1)
        assert reason == "looks good"

    def test_json_in_markdown_fence(self) -> None:
        raw = '```json\n{"error_probability": 0.8, "reason": "bad box"}\n```'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.8)
        assert reason == "bad box"

    def test_json_in_plain_fence(self) -> None:
        raw = '```\n{"error_probability": 0.5, "reason": "uncertain"}\n```'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.5)

    def test_invalid_json_returns_none(self) -> None:
        ep, reason = _parse_vlm_response("not json at all")
        assert ep is None
        assert reason == "parse_failed"

    def test_missing_error_probability_returns_none(self) -> None:
        raw = '{"reason": "forgot probability"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep is None
        assert reason == "parse_failed"

    def test_out_of_range_ep_returns_none(self) -> None:
        raw = '{"error_probability": 1.5, "reason": "out of range"}'
        ep, reason = _parse_vlm_response(raw)
        assert ep is None
        assert reason == "parse_failed"

    def test_missing_reason_uses_empty_string(self) -> None:
        raw = '{"error_probability": 0.3}'
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.3)
        assert reason == ""

    def test_whitespace_padded(self) -> None:
        raw = '  {"error_probability": 0.0, "reason": "perfect"}  '
        ep, reason = _parse_vlm_response(raw)
        assert ep == pytest.approx(0.0)


class TestEpToVerdict:
    def test_below_pass_threshold(self) -> None:
        assert _ep_to_verdict(0.10, 0.20, 0.60) == "PASS"

    def test_at_pass_threshold_boundary(self) -> None:
        assert _ep_to_verdict(0.19, 0.20, 0.60) == "PASS"

    def test_at_pass_threshold_exact(self) -> None:
        assert _ep_to_verdict(0.20, 0.20, 0.60) == "REVIEW"

    def test_in_review_range(self) -> None:
        assert _ep_to_verdict(0.45, 0.20, 0.60) == "REVIEW"

    def test_at_fail_threshold_exact(self) -> None:
        assert _ep_to_verdict(0.60, 0.20, 0.60) == "FAIL"

    def test_above_fail_threshold(self) -> None:
        assert _ep_to_verdict(0.95, 0.20, 0.60) == "FAIL"

    def test_none_ep_returns_review(self) -> None:
        assert _ep_to_verdict(None, 0.20, 0.60) == "REVIEW"
