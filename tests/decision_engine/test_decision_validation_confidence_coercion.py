"""Tests for word-based confidence coercion in decision validation.

Covers the fix for: deepseek-r1:8b returning "medium"/"low"/"high" instead
of integer confidence values, causing malformed-response fallback on the judge path.
"""

import json

import pytest

from finance_feedback_engine.decision_engine.decision_validation import (
    _coerce_confidence_value,
    try_parse_decision_json,
    is_valid_decision,
    normalize_decision_action_payload,
)


class TestCoerceConfidenceValue:
    """Unit tests for _coerce_confidence_value."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            (50, 50),
            (0, 0),
            (100, 100),
            (75.5, 75),
            (-10, 0),
            (200, 100),
        ],
    )
    def test_numeric_values(self, raw, expected):
        assert _coerce_confidence_value(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("50", 50),
            ("75.5", 75),
            ("0", 0),
            ("100", 100),
        ],
    )
    def test_numeric_strings(self, raw, expected):
        assert _coerce_confidence_value(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("medium", 50),
            ("Medium", 50),
            ("MEDIUM", 50),
            ("low", 25),
            ("Low", 25),
            ("high", 75),
            ("HIGH", 75),
            ("moderate", 50),
            ("very low", 15),
            ("very high", 90),
            ("medium-low", 35),
            ("medium-high", 65),
        ],
    )
    def test_word_strings(self, raw, expected):
        assert _coerce_confidence_value(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "garbage", "??", [], {}])
    def test_fallback_to_50(self, raw):
        assert _coerce_confidence_value(raw) == 50


class TestTryParseDecisionJsonWithWordConfidence:
    """Integration: JSON payloads with word confidence should now parse successfully."""

    def test_medium_confidence_parses(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": "medium",
            "reasoning": "Market ranging",
            "amount": 0.1,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 50
        assert result["action"] == "HOLD"

    def test_low_confidence_parses(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": "low",
            "reasoning": "Uncertain",
            "amount": 0.05,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 25

    def test_high_confidence_parses(self):
        payload = json.dumps({
            "action": "CLOSE_SHORT",
            "confidence": "high",
            "reasoning": "Strong reversal",
            "amount": 0.2,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 75

    def test_numeric_confidence_still_works(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 65,
            "reasoning": "Normal",
            "amount": 0.1,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 65


class TestNormalizeDecisionWithWordConfidence:
    """Ensure normalization coerces confidence before downstream validation."""

    def test_word_confidence_normalized(self):
        decision = {"action": "HOLD", "confidence": "medium", "reasoning": "test"}
        result = normalize_decision_action_payload(decision)
        assert result["confidence"] == 50
        assert is_valid_decision(result)

    def test_word_confidence_low_normalized(self):
        decision = {"action": "HOLD", "confidence": "low", "reasoning": "test"}
        result = normalize_decision_action_payload(decision)
        assert result["confidence"] == 25
        assert is_valid_decision(result)
