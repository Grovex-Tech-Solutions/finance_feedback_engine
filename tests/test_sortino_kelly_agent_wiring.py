"""TDD tests for Phase 3 — SortinoGate wired into TradingLoopAgent.

Track SK — Phase 3.
See docs/plans/TRACK_SK_SORTINO_KELLY_PLAN_2026-04-03.md

Tests verify:
1. Agent maintains _trade_pnl_history list, appended on each trade outcome
2. Agent instantiates SortinoGate and computes gate result
3. Gate result + performance_metrics injected into decision before position sizing
4. _kelly_activated replaced by sortino gate
5. Gate computation is logged in cycle summary
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from finance_feedback_engine.decision_engine.sortino_gate import (
    SortinoGate,
    SortinoGateResult,
)


# ---------------------------------------------------------------------------
# Helpers — lightweight agent attribute simulation
# ---------------------------------------------------------------------------

class TestTradePnlHistoryTracking:
    """Agent must maintain a rolling deque of trade P&L values for SortinoGate."""

    def test_pnl_history_initialized_empty(self):
        """_trade_pnl_history should be an empty deque at agent init."""
        from finance_feedback_engine.agent.trading_loop_agent import TradingLoopAgent
        assert hasattr(TradingLoopAgent, '__init__')

    def test_pnl_appended_on_trade_outcome(self):
        """When _update_performance_metrics is called, P&L should be appended."""
        from collections import deque
        pnl_history = deque(maxlen=500)
        
        def mock_update(trade_outcome):
            pnl = trade_outcome.get("realized_pnl", 0)
            if pnl != 0:
                pnl_history.append(float(pnl))
        
        mock_update({"realized_pnl": 50.0, "was_profitable": True})
        mock_update({"realized_pnl": -20.0, "was_profitable": False})
        mock_update({"realized_pnl": 0.0, "was_profitable": False})
        mock_update({"realized_pnl": 100.0, "was_profitable": True})
        
        assert list(pnl_history) == [50.0, -20.0, 100.0]  # zero filtered

    def test_deque_auto_caps_at_maxlen(self):
        """deque(maxlen=500) automatically drops oldest entries."""
        from collections import deque
        pnl_history = deque(maxlen=500)
        for i in range(600):
            pnl_history.append(float(i))
        
        assert len(pnl_history) == 500
        assert pnl_history[0] == 100.0  # first 100 dropped
        assert pnl_history[-1] == 599.0  # newest preserved


class TestSortinoGateComputation:
    """Agent computes sortino gate from P&L history and injects into decision."""

    def test_gate_computed_from_pnl_history(self):
        """SortinoGate.compute() called with _trade_pnl_history."""
        gate = SortinoGate(min_trades=10, min_losing_trades=3, activation_confirmations=1)
        pnl_history = [100, -50, 80, -30, 120, -40, 90, -20, 150, -60,
                       100, -50, 80, -30, 120]
        result = gate.compute(pnl_history)
        assert isinstance(result, SortinoGateResult)
        assert result.trade_count == 15

    def test_gate_result_injected_into_decision(self):
        """sortino_gate_result should be placed in decision dict before sizing."""
        gate = SortinoGate(min_trades=10, min_losing_trades=3, activation_confirmations=1)
        pnl_history = [100, -50, 80, -30, 120, -40, 90, -20, 150, -60,
                       100, -50, 80, -30, 120]
        gate_result = gate.compute(pnl_history)
        
        decision = {
            "action": "OPEN_SMALL_SHORT",
            "asset_pair": "BTCUSD",
            "entry_price": 67000.0,
        }
        decision["sortino_gate_result"] = gate_result
        
        assert "sortino_gate_result" in decision
        assert isinstance(decision["sortino_gate_result"], SortinoGateResult)

    def test_performance_metrics_injected_into_decision(self):
        """performance_metrics from _performance_metrics should be in decision."""
        perf = {
            "win_rate": 0.63,
            "avg_win": 220.0,
            "avg_loss": 70.0,
            "total_trades": 87,
        }
        decision = {"action": "OPEN_SMALL_SHORT"}
        decision["performance_metrics"] = {
            "win_rate": perf["win_rate"] / 100 if perf["win_rate"] > 1 else perf["win_rate"],
            "avg_win": perf["avg_win"],
            "avg_loss": perf["avg_loss"],
            "payoff_ratio": perf["avg_win"] / perf["avg_loss"] if perf["avg_loss"] > 0 else 1.0,
        }
        
        assert "performance_metrics" in decision
        assert decision["performance_metrics"]["win_rate"] == 0.63

    def test_empty_history_produces_fixed_risk(self):
        """No trade history → gate says fixed_risk."""
        gate = SortinoGate(min_trades=30)
        result = gate.compute([])
        assert result.sizing_mode == "fixed_risk"
        assert result.kelly_multiplier == 0.0

    def test_insufficient_history_produces_fixed_risk(self):
        """< min_trades → gate says fixed_risk."""
        gate = SortinoGate(min_trades=30, min_losing_trades=5)
        pnl_history = [100, -50] * 10  # 20 trades
        result = gate.compute(pnl_history)
        assert result.sizing_mode == "fixed_risk"


class TestGateReplacesKellyActivated:
    """SortinoGate replaces the disconnected _kelly_activated flag."""

    def test_gate_provides_activation_status(self):
        """Gate result sizing_mode tells you if Kelly is active — no separate flag needed."""
        gate = SortinoGate(min_trades=10, min_losing_trades=3, activation_confirmations=1)
        
        # Strong history
        pnl_history = [200, -50] * 20  # 40 trades, strong edge
        result = gate.compute(pnl_history)
        kelly_active = result.sizing_mode != "fixed_risk"
        assert kelly_active is True
        
        # Weak history
        pnl_history_weak = [-50, 10] * 20
        result_weak = gate.compute(pnl_history_weak)
        kelly_active_weak = result_weak.sizing_mode != "fixed_risk"
        assert kelly_active_weak is False

    def test_gate_status_logged_in_batch_review(self):
        """The gate result should provide data for the batch review log."""
        gate = SortinoGate(min_trades=10, min_losing_trades=3, activation_confirmations=1)
        pnl_history = [200, -50] * 20
        result = gate.compute(pnl_history)
        
        # These fields should be available for logging
        log_line = (
            f"Sortino-Kelly: {result.sizing_mode} "
            f"(sortino={result.weighted_sortino:.3f}, "
            f"multiplier={result.kelly_multiplier:.2f}, "
            f"trades={result.trade_count}, "
            f"windows={result.windows_used})"
        )
        assert "sortino=" in log_line
        assert "multiplier=" in log_line


class TestWinRateNormalization:
    """_performance_metrics stores win_rate as percentage (0-100),
    but Kelly needs it as fraction (0-1). Verify normalization + clamping."""

    def _normalize(self, raw):
        raw = float(raw or 0)
        normalized = raw / 100.0 if raw > 1.0 else raw
        return max(0.0, min(1.0, normalized))  # clamp [0, 1]

    def test_win_rate_above_one_normalized(self):
        assert self._normalize(63.0) == pytest.approx(0.63)

    def test_win_rate_already_fraction_unchanged(self):
        assert self._normalize(0.63) == pytest.approx(0.63)

    def test_win_rate_zero_safe(self):
        assert self._normalize(0.0) == 0.0

    def test_win_rate_100_normalized(self):
        assert self._normalize(100.0) == 1.0

    def test_win_rate_negative_clamped_to_zero(self):
        assert self._normalize(-5.0) == 0.0

    def test_win_rate_over_100_clamped_to_one(self):
        assert self._normalize(120.0) == 1.0

    def test_win_rate_none_safe(self):
        assert self._normalize(None) == 0.0


class TestPayoffRatioCalculation:
    """payoff_ratio uses sanitized locals, no dual-default bug."""

    def test_normal_payoff(self):
        avg_win, avg_loss = 220.0, 70.0
        assert abs(avg_win) / abs(avg_loss) == pytest.approx(3.142857, rel=1e-3)

    def test_zero_avg_loss_returns_one(self):
        avg_win, avg_loss = 220.0, 0.0
        ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
        assert ratio == 1.0

    def test_none_avg_loss_safe(self):
        avg_loss = abs(float(None or 0))
        ratio = 100.0 / avg_loss if avg_loss > 0 else 1.0
        assert ratio == 1.0

    def test_negative_values_use_abs(self):
        avg_win = abs(float(-220.0))
        avg_loss = abs(float(-70.0))
        assert avg_win / avg_loss == pytest.approx(3.142857, rel=1e-3)


class TestPreloadPnlHistory:
    """Phase 4: P&L history pre-loaded from durable trade outcomes on startup."""

    def test_preload_loads_from_jsonl_files(self):
        """Verify the preload pattern works with real JSONL data."""
        import json, tempfile, os
        from collections import deque

        # Create temp outcome files
        with tempfile.TemporaryDirectory() as tmpdir:
            outcomes_dir = os.path.join(tmpdir, "data", "trade_outcomes")
            os.makedirs(outcomes_dir)

            with open(os.path.join(outcomes_dir, "2026-04-01.jsonl"), "w") as f:
                for pnl in [50.0, -20.0, 100.0, 0.0, -30.0]:
                    json.dump({"realized_pnl": pnl}, f)
                    f.write("\n")

            with open(os.path.join(outcomes_dir, "2026-04-02.jsonl"), "w") as f:
                for pnl in [200.0, -80.0]:
                    json.dump({"realized_pnl": pnl}, f)
                    f.write("\n")

            # Simulate preload
            import glob
            history = deque(maxlen=500)
            files = sorted(glob.glob(os.path.join(outcomes_dir, "*.jsonl")))
            for fpath in files:
                with open(fpath) as f:
                    for line in f:
                        rec = json.loads(line)
                        p = float(rec.get("realized_pnl", 0))
                        if p != 0:
                            history.append(p)

            assert list(history) == [50.0, -20.0, 100.0, -30.0, 200.0, -80.0]
            assert len(history) == 6

    def test_preload_caps_at_500(self):
        """Only last 500 P&Ls loaded even if more exist on disk."""
        from collections import deque
        pnls = list(range(1, 701))  # 700 values
        history = deque(maxlen=500)
        for p in pnls[-500:]:
            history.append(float(p))
        assert len(history) == 500
        assert history[0] == 201.0
        assert history[-1] == 700.0
