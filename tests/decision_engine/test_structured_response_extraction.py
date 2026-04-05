"""Tests for structured response extraction and judge path robustness.

Covers the fix for the malformed structured-response fallback bug where
the judge path consistently fell back to HOLD/50 instead of parsing
valid LLM responses.
"""
import json

import pytest

from finance_feedback_engine.decision_engine.decision_validation import (
    extract_json_from_text,
    try_parse_decision_json,
)


class TestExtractJsonFromText:
    """Tests for extract_json_from_text helper."""

    def test_plain_json(self):
        text = '{"action": "HOLD", "confidence": 50}'
        assert extract_json_from_text(text) == text.strip()

    def test_json_with_think_tags(self):
        text = '<think>\nLet me analyze this...\n</think>\n{"action": "HOLD", "confidence": 50}'
        result = extract_json_from_text(text)
        assert '"action": "HOLD"' in result
        assert "<think>" not in result

    def test_json_with_markdown_fences(self):
        text = '```json\n{"action": "HOLD", "confidence": 50}\n```'
        result = extract_json_from_text(text)
        assert '"action": "HOLD"' in result
        assert "```" not in result

    def test_json_with_preamble(self):
        text = 'Here is my analysis:\n{"action": "HOLD", "confidence": 50, "reasoning": "test", "amount": 0.1}'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert parsed["action"] == "HOLD"

    def test_empty_text(self):
        assert extract_json_from_text("") == ""
        assert extract_json_from_text("   ") == "   "

    def test_no_json(self):
        text = "Just a plain text response with no JSON"
        assert extract_json_from_text(text) == text

    def test_nested_json(self):
        text = '{"action": "HOLD", "reasoning": {"thesis": "neither", "basis": "test"}}'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert parsed["reasoning"]["thesis"] == "neither"

    def test_truncated_json(self):
        """Truncated JSON without closing brace returns original text."""
        text = '{"action": "HOLD", "confidence": 50'
        result = extract_json_from_text(text)
        # No matching close brace, returns original
        assert result == text

    def test_json_with_strings_containing_braces(self):
        text = '{"action": "HOLD", "reasoning": "price is in range {82000-84000}"}'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert "82000-84000" in parsed["reasoning"]


class TestTryParseDecisionJsonRobust:
    """Tests for try_parse_decision_json with edge cases from judge path."""

    def test_valid_json_string_reasoning(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 50,
            "reasoning": "Market is ranging",
            "amount": 0.1,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["action"] == "HOLD"

    def test_valid_json_dict_reasoning(self):
        """Judge path: deepseek-r1 often returns reasoning as dict."""
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 50,
            "reasoning": {
                "Winning Thesis": "neither",
                "Decision Basis": "RSI neutral",
            },
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert "Winning Thesis: neither" in result["reasoning"]

    def test_empty_dict_reasoning_gets_fallback(self):
        """Empty dict reasoning normalizes to empty string; fix adds fallback."""
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 50,
            "reasoning": {},
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["reasoning"]  # non-empty after fallback

    def test_string_confidence_coerced_to_int(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": "75",
            "reasoning": "test",
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 75
        assert isinstance(result["confidence"], int)

    def test_word_confidence_defaults_to_50(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": "medium",
            "reasoning": "test",
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 50

    def test_float_confidence_coerced(self):
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 72.5,
            "reasoning": "test",
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["confidence"] == 72

    def test_think_tags_stripped(self):
        """deepseek-r1 may include <think> blocks before JSON."""
        payload = "<think>\nLet me think about this...\n</think>\n" + json.dumps({
            "action": "HOLD",
            "confidence": 60,
            "reasoning": "Market analysis complete",
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["action"] == "HOLD"
        assert result["confidence"] == 60

    def test_markdown_fenced_json(self):
        payload = "```json\n" + json.dumps({
            "action": "HOLD",
            "confidence": 55,
            "reasoning": "Ranging market",
            "amount": 0,
        }) + "\n```"
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["action"] == "HOLD"

    def test_missing_reasoning_gets_synthetic_fallback(self):
        """Missing reasoning gets a synthetic fallback string."""
        payload = json.dumps({
            "action": "HOLD",
            "confidence": 50,
            "amount": 0,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert "reasoning not provided" in result["reasoning"]

    def test_policy_actions_preserved(self):
        payload = json.dumps({
            "action": "CLOSE_LONG",
            "confidence": 85,
            "reasoning": "Strong bearish signal",
            "amount": 0.5,
        })
        result = try_parse_decision_json(payload)
        assert result is not None
        assert result["action"] == "CLOSE_LONG"
