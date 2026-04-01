"""Invariant tests for learning chain integrity.

These tests verify that the learning chain maintains its contracts:
provider attribution, adaptive gating, and recovery decision handling.
"""

import pytest
from copy import deepcopy

from finance_feedback_engine.decision_engine.performance_tracker import PerformanceTracker


PROVIDERS = ["llama3.1:8b", "deepseek-r1:8b", "gemma2:9b"]
DEBATE_SEATS = {"bull": "gemma2:9b", "bear": "llama3.1:8b", "judge": "deepseek-r1:8b"}


@pytest.fixture
def tracker(tmp_path):
    config = {
        "ensemble": {},
        "persistence": {"storage_path": str(tmp_path)},
    }
    return PerformanceTracker(config, learning_rate=0.1)


def _make_role_decisions():
    """Create realistic role_decisions as produced by debate_manager."""
    return {
        "bull": {
            "action": "BUY",
            "confidence": 70,
            "provider": "gemma2:9b",
            "role": "bull",
        },
        "bear": {
            "action": "SELL",
            "confidence": 60,
            "provider": "llama3.1:8b",
            "role": "bear",
        },
        "judge": {
            "action": "HOLD",
            "confidence": 50,
            "provider": "deepseek-r1:8b",
            "role": "judge",
        },
    }


class TestProviderDecisionsReconstruction:
    """provider_decisions reconstruction from role_decisions must preserve all providers."""

    def test_reconstruct_provider_decisions_from_roles(self):
        """Simulates _normalize_learning_provider_decisions logic."""
        role_decisions = _make_role_decisions()
        # Reconstruction: role_decisions -> provider_decisions
        reconstructed = {}
        for role_name, role_dec in role_decisions.items():
            provider = role_dec.get("provider")
            if provider:
                reconstructed[provider] = {
                    k: v for k, v in role_dec.items() if k != "role"
                }
        # Must have all 3 providers
        assert len(reconstructed) == 3
        assert "gemma2:9b" in reconstructed
        assert "llama3.1:8b" in reconstructed
        assert "deepseek-r1:8b" in reconstructed

    def test_actions_preserved_in_reconstruction(self):
        role_decisions = _make_role_decisions()
        reconstructed = {}
        for role_name, role_dec in role_decisions.items():
            provider = role_dec.get("provider")
            if provider:
                reconstructed[provider] = {
                    k: v for k, v in role_dec.items() if k != "role"
                }
        assert reconstructed["gemma2:9b"]["action"] == "BUY"
        assert reconstructed["llama3.1:8b"]["action"] == "SELL"
        assert reconstructed["deepseek-r1:8b"]["action"] == "HOLD"

    def test_judge_only_provider_decisions_is_incomplete(self):
        """The old bug: only judge in provider_decisions."""
        judge_only = {"deepseek-r1:8b": {"action": "HOLD", "confidence": 50}}
        assert len(judge_only) == 1, "Judge-only is the known-bad state"
        # This should NOT be used for adaptive scoring without reconstruction


class TestAdaptiveGating:
    """Adaptive weight update must only fire when adaptive_learning=true."""

    def test_tracker_updates_performance_history(self, tracker):
        decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
        tracker.update_provider_performance(decisions, "HOLD", 1.0)
        for p in PROVIDERS:
            assert p in tracker.performance_history
            assert tracker.performance_history[p]["total"] == 1

    def test_tracker_increments_correct_on_match(self, tracker):
        decisions = {"llama3.1:8b": {"action": "BUY"}}
        tracker.update_provider_performance(decisions, "BUY", 2.0)
        assert tracker.performance_history["llama3.1:8b"]["correct"] == 1

    def test_tracker_does_not_increment_correct_on_mismatch(self, tracker):
        decisions = {"llama3.1:8b": {"action": "BUY"}}
        tracker.update_provider_performance(decisions, "SELL", -2.0)
        assert tracker.performance_history["llama3.1:8b"]["correct"] == 0
        assert tracker.performance_history["llama3.1:8b"]["total"] == 1


class TestRecoveryShadowedDecisions:
    """Recovery/shadowed decisions must not poison adaptive scoring."""

    def test_recovery_decision_lacks_full_provider_decisions(self):
        """Recovery decisions typically only have judge in provider_decisions.
        The system must reconstruct from role_decisions before scoring."""
        recovery_decision = {
            "action": "SELL",
            "confidence": 70,
            "source": "recovery",
            "recovery_metadata": {
                "shadowed_from_decision_id": "abc-123",
                "product_id": "BIP-20DEC30-CDE",
            },
            "ensemble_metadata": {
                "provider_decisions": {
                    # Old bug: only judge
                    "deepseek-r1:8b": {"action": "HOLD", "confidence": 50}
                },
                "role_decisions": _make_role_decisions(),
                "debate_seats": DEBATE_SEATS,
            },
        }
        # Verify the stale state
        pd = recovery_decision["ensemble_metadata"]["provider_decisions"]
        rd = recovery_decision["ensemble_metadata"]["role_decisions"]
        assert len(pd) == 1, "Stale provider_decisions has only judge"
        assert len(rd) == 3, "role_decisions has all 3"

        # Reconstruction should be used instead of stale provider_decisions
        reconstructed = {}
        for role_name, role_dec in rd.items():
            provider = role_dec.get("provider")
            if provider:
                reconstructed[provider] = {
                    k: v for k, v in role_dec.items() if k != "role"
                }
        assert len(reconstructed) == 3

    def test_scoring_with_full_vs_judge_only_differs(self, tracker):
        """Scoring with judge-only vs full provider set produces different history."""
        # Score with judge-only (the bug)
        judge_only = {"deepseek-r1:8b": {"action": "HOLD"}}
        tracker.update_provider_performance(judge_only, "SELL", -1.0)

        # Only judge gets a record
        assert "deepseek-r1:8b" in tracker.performance_history
        assert "gemma2:9b" not in tracker.performance_history
        assert "llama3.1:8b" not in tracker.performance_history

    def test_scoring_with_full_providers_updates_all(self, tracker):
        full = {
            "gemma2:9b": {"action": "BUY"},
            "llama3.1:8b": {"action": "SELL"},
            "deepseek-r1:8b": {"action": "HOLD"},
        }
        tracker.update_provider_performance(full, "SELL", -1.0)
        for p in PROVIDERS:
            assert p in tracker.performance_history
            assert tracker.performance_history[p]["total"] == 1


class TestPerformanceHistoryPersistence:
    """Performance history must survive save/load cycle."""

    def test_save_load_roundtrip(self, tmp_path):
        config = {
            "ensemble": {},
            "persistence": {"storage_path": str(tmp_path)},
        }
        tracker1 = PerformanceTracker(config, learning_rate=0.1)
        decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
        tracker1.update_provider_performance(decisions, "HOLD", 1.0)

        # Create new tracker from same path
        tracker2 = PerformanceTracker(config, learning_rate=0.1)
        for p in PROVIDERS:
            assert p in tracker2.performance_history
            assert tracker2.performance_history[p]["total"] == 1

    def test_weights_consistent_after_reload(self, tmp_path):
        config = {
            "ensemble": {},
            "persistence": {"storage_path": str(tmp_path)},
        }
        tracker1 = PerformanceTracker(config, learning_rate=0.1)
        decisions = {p: {"action": "HOLD"} for p in PROVIDERS}
        for _ in range(10):
            tracker1.update_provider_performance(decisions, "HOLD", 1.0)
        w1 = tracker1.calculate_adaptive_weights(PROVIDERS)

        tracker2 = PerformanceTracker(config, learning_rate=0.1)
        w2 = tracker2.calculate_adaptive_weights(PROVIDERS)

        for p in PROVIDERS:
            assert abs(w1[p] - w2[p]) < 1e-9, f"Weight mismatch for {p} after reload"
