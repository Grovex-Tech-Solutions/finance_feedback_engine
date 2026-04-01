"""Invariant tests for ensemble weight properties.

These tests verify that ensemble weights maintain mathematical invariants
regardless of the operations performed on them.
"""

import math
import pytest
from unittest.mock import patch, MagicMock

from finance_feedback_engine.decision_engine.performance_tracker import PerformanceTracker


EPSILON = 1e-9
PROVIDERS = ["llama3.1:8b", "deepseek-r1:8b", "gemma2:9b"]


@pytest.fixture
def tracker(tmp_path):
    config = {
        "ensemble": {
            "adaptive_accuracy_weight": 0.75,
            "adaptive_performance_weight": 0.25,
            "adaptive_performance_scale": 5.0,
        },
        "persistence": {"storage_path": str(tmp_path)},
    }
    return PerformanceTracker(config, learning_rate=0.1)


class TestWeightsSumToOne:
    """Weights must ALWAYS sum to 1.0 (within epsilon) after any operation."""

    def test_fresh_tracker_weights_sum_to_one(self, tracker):
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(weights.values()) - 1.0) < EPSILON

    def test_weights_sum_to_one_after_single_update(self, tracker):
        decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
        tracker.update_provider_performance(decisions, "HOLD", 0.05)
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(weights.values()) - 1.0) < EPSILON

    def test_weights_sum_to_one_after_many_updates(self, tracker):
        for i in range(50):
            action = "BUY" if i % 3 == 0 else "HOLD"
            decisions = {p: {"action": action} for p in PROVIDERS}
            metric = (i - 25) * 0.1  # range from -2.5 to +2.5
            tracker.update_provider_performance(decisions, "HOLD", metric)
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(weights.values()) - 1.0) < EPSILON

    def test_weights_sum_to_one_with_asymmetric_performance(self, tracker):
        # One provider always right, others always wrong
        for _ in range(20):
            tracker.update_provider_performance(
                {"llama3.1:8b": {"action": "BUY"}, "deepseek-r1:8b": {"action": "SELL"}, "gemma2:9b": {"action": "HOLD"}},
                "BUY", 5.0,
            )
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(weights.values()) - 1.0) < EPSILON

    def test_weights_sum_to_one_with_extreme_negative_performance(self, tracker):
        for _ in range(20):
            decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
            tracker.update_provider_performance(decisions, "BUY", -100.0)
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(weights.values()) - 1.0) < EPSILON


class TestWeightsNeverNegative:
    """Weights must NEVER go negative."""

    def test_no_negative_weights_fresh(self, tracker):
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        for p, w in weights.items():
            assert w >= 0, f"Provider {p} has negative weight: {w}"

    def test_no_negative_weights_after_catastrophic_loss(self, tracker):
        for _ in range(100):
            decisions = {p: {"action": "BUY"} for p in PROVIDERS}
            tracker.update_provider_performance(decisions, "SELL", -1000.0)
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        for p, w in weights.items():
            assert w >= 0, f"Provider {p} has negative weight {w} after catastrophic loss"

    def test_no_negative_weights_with_zero_accuracy(self, tracker):
        # All providers always wrong
        for _ in range(50):
            decisions = {p: {"action": "BUY"} for p in PROVIDERS}
            tracker.update_provider_performance(decisions, "SELL", -5.0)
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        for p, w in weights.items():
            assert w >= 0, f"Provider {p} has negative weight {w} with zero accuracy"


class TestWeightsNeverExceedOne:
    """No single provider weight must exceed 1.0."""

    def test_no_weight_exceeds_one_fresh(self, tracker):
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        for p, w in weights.items():
            assert w <= 1.0 + EPSILON, f"Provider {p} weight {w} exceeds 1.0"

    def test_no_weight_exceeds_one_dominant_provider(self, tracker):
        # One provider perfect, others terrible
        for _ in range(100):
            tracker.update_provider_performance(
                {"llama3.1:8b": {"action": "BUY"}, "deepseek-r1:8b": {"action": "SELL"}, "gemma2:9b": {"action": "SELL"}},
                "BUY", 10.0,
            )
        weights = tracker.calculate_adaptive_weights(PROVIDERS)
        for p, w in weights.items():
            assert w <= 1.0 + EPSILON, f"Provider {p} weight {w} exceeds 1.0"


class TestNoPhantomProviders:
    """Only enabled_providers should have weights."""

    def test_only_enabled_providers_get_weights(self, tracker):
        subset = ["llama3.1:8b", "gemma2:9b"]
        weights = tracker.calculate_adaptive_weights(subset)
        assert set(weights.keys()) == set(subset)

    def test_removed_provider_not_in_weights(self, tracker):
        # Train with 3 providers
        decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
        tracker.update_provider_performance(decisions, "HOLD", 1.0)
        # Calculate with only 2
        subset = ["llama3.1:8b", "deepseek-r1:8b"]
        weights = tracker.calculate_adaptive_weights(subset)
        assert "gemma2:9b" not in weights

    def test_history_for_removed_provider_doesnt_leak(self, tracker):
        # Build history for all 3
        for _ in range(10):
            decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
            tracker.update_provider_performance(decisions, "HOLD", 1.0)
        # Now only 2 enabled
        weights = tracker.calculate_adaptive_weights(["llama3.1:8b", "deepseek-r1:8b"])
        assert len(weights) == 2
        assert abs(sum(weights.values()) - 1.0) < EPSILON


class TestRedistributionOnProviderChange:
    """Adding/removing a provider must redistribute, not corrupt."""

    def test_adding_provider_redistributes(self, tracker):
        w2 = tracker.calculate_adaptive_weights(["llama3.1:8b", "deepseek-r1:8b"])
        w3 = tracker.calculate_adaptive_weights(PROVIDERS)
        assert abs(sum(w2.values()) - 1.0) < EPSILON
        assert abs(sum(w3.values()) - 1.0) < EPSILON
        assert len(w3) == 3

    def test_removing_provider_redistributes(self, tracker):
        for _ in range(10):
            decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
            tracker.update_provider_performance(decisions, "HOLD", 1.0)
        w3 = tracker.calculate_adaptive_weights(PROVIDERS)
        w2 = tracker.calculate_adaptive_weights(["llama3.1:8b", "deepseek-r1:8b"])
        assert abs(sum(w3.values()) - 1.0) < EPSILON
        assert abs(sum(w2.values()) - 1.0) < EPSILON


class TestBaseWeightsFallback:
    """Base weights used when no history exists for a provider."""

    def test_base_weights_used_for_unknown_provider(self, tracker):
        base = {"llama3.1:8b": 0.5, "newmodel:7b": 0.5}
        weights = tracker.calculate_adaptive_weights(
            ["llama3.1:8b", "newmodel:7b"], base_weights=base
        )
        assert abs(sum(weights.values()) - 1.0) < EPSILON
        assert "newmodel:7b" in weights

    def test_empty_base_weights_still_normalizes(self, tracker):
        weights = tracker.calculate_adaptive_weights(PROVIDERS, base_weights={})
        assert abs(sum(weights.values()) - 1.0) < EPSILON
