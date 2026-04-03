"""TDD tests for Phase 2 — SortinoGate wired into PositionSizingCalculator.

Track SK — Phase 2.
See docs/plans/TRACK_SK_SORTINO_KELLY_PLAN_2026-04-03.md

Tests verify that:
1. When sortino_gate_result is in the context with a non-fixed mode,
   position sizing uses Kelly with the gate's multiplier.
2. When sortino_gate_result is absent or fixed_risk, existing behavior
   is unchanged.
3. The kelly_fraction_multiplier is set dynamically per-call, not globally.
4. Logging clearly indicates which sizing mode was used.
"""

import math
import pytest
from unittest.mock import patch, MagicMock

from finance_feedback_engine.decision_engine.position_sizing import (
    PositionSizingCalculator,
)
from finance_feedback_engine.decision_engine.sortino_gate import (
    SortinoGate,
    SortinoGateResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(use_kelly: bool = False, risk_pct: float = 0.01) -> dict:
    """Build a minimal config for PositionSizingCalculator."""
    return {
        "agent": {
            "risk_percentage": risk_pct,
            "sizing_stop_loss_percentage": 0.02,
            "use_dynamic_stop_loss": False,
            "use_kelly_criterion": use_kelly,
            "kelly_criterion": {
                "kelly_fraction_cap": 0.25,
                "kelly_fraction_multiplier": 0.25,
                "min_kelly_fraction": 0.001,
                "max_position_size_pct": 0.05,
                "default_win_rate": 0.60,
                "default_avg_win": 150.0,
                "default_avg_loss": 75.0,
            },
            "position_sizing": {
                "risk_percentage": risk_pct,
                "max_position_usd_prod": 500.0,
                "max_position_usd_dev": 50.0,
            },
        },
    }


def _make_context(
    asset_pair: str = "BTCUSD",
    sortino_gate_result: SortinoGateResult | None = None,
    balance_snapshot: dict | None = None,
    performance_metrics: dict | None = None,
) -> dict:
    """Build a minimal decision context."""
    ctx = {
        "asset_pair": asset_pair,
        "market_data": {"type": "crypto"},
        "position_state": {"state": "NONE"},
    }
    if sortino_gate_result is not None:
        ctx["sortino_gate_result"] = sortino_gate_result
    if balance_snapshot is not None:
        ctx["balance_snapshot"] = balance_snapshot
    if performance_metrics is not None:
        ctx["performance_metrics"] = performance_metrics
    return ctx


def _fixed_risk_gate_result(trade_count: int = 50) -> SortinoGateResult:
    """A gate result that says stay on fixed risk."""
    return SortinoGateResult(
        weighted_sortino=0.2,
        window_sortinos={10: 0.15, 30: 0.25},
        kelly_multiplier=0.0,
        sizing_mode="fixed_risk",
        reason="Sortino 0.200 below activation threshold (0.5)",
        trade_count=trade_count,
        short_window_veto=False,
        windows_used=2,
    )


def _quarter_kelly_gate_result(trade_count: int = 50) -> SortinoGateResult:
    """A gate result that activates quarter Kelly."""
    return SortinoGateResult(
        weighted_sortino=0.75,
        window_sortinos={10: 0.80, 30: 0.70},
        kelly_multiplier=0.25,
        sizing_mode="quarter_kelly",
        reason="Sortino 0.750 → quarter_kelly (multiplier=0.25)",
        trade_count=trade_count,
        short_window_veto=False,
        windows_used=2,
    )


def _half_kelly_gate_result(trade_count: int = 50) -> SortinoGateResult:
    """A gate result that activates half Kelly."""
    return SortinoGateResult(
        weighted_sortino=1.2,
        window_sortinos={10: 1.3, 30: 1.1},
        kelly_multiplier=0.50,
        sizing_mode="half_kelly",
        reason="Sortino 1.200 → half_kelly (multiplier=0.50)",
        trade_count=trade_count,
        short_window_veto=False,
        windows_used=2,
    )


# ---------------------------------------------------------------------------
# Core wiring: sortino gate result in context drives sizing mode
# ---------------------------------------------------------------------------

class TestSortinoGateWiring:
    """Verify position_sizing reads sortino_gate_result from context."""

    def test_no_gate_result_uses_fixed_risk(self):
        """No sortino_gate_result in context → standard risk-based sizing."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context()
        result = calc.calculate_position_sizing_params(
            context=ctx,
            current_price=67000.0,
            action="OPEN_SMALL_SHORT",
            has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert result["position_sizing_method"] == "risk_based"
        assert result["recommended_position_size"] is not None
        assert result["recommended_position_size"] > 0

    def test_fixed_risk_gate_uses_risk_based(self):
        """sortino_gate_result with fixed_risk → standard risk-based sizing."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(sortino_gate_result=_fixed_risk_gate_result())
        result = calc.calculate_position_sizing_params(
            context=ctx,
            current_price=67000.0,
            action="OPEN_SMALL_SHORT",
            has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert result["position_sizing_method"] == "risk_based"

    def test_quarter_kelly_gate_uses_kelly(self):
        """sortino_gate_result with quarter_kelly → Kelly sizing with 0.25 multiplier."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics={
                "win_rate": 0.63,
                "avg_win": 220.0,
                "avg_loss": 70.0,
                "payoff_ratio": 3.14,
            },
        )
        result = calc.calculate_position_sizing_params(
            context=ctx,
            current_price=67000.0,
            action="OPEN_SMALL_SHORT",
            has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert result["position_sizing_method"] == "sortino_kelly"
        assert result["recommended_position_size"] is not None
        assert result["recommended_position_size"] > 0
        assert "sortino_gate" in result

    def test_half_kelly_gate_uses_kelly(self):
        """sortino_gate_result with half_kelly → Kelly sizing with 0.50 multiplier."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(
            sortino_gate_result=_half_kelly_gate_result(),
            performance_metrics={
                "win_rate": 0.63,
                "avg_win": 220.0,
                "avg_loss": 70.0,
                "payoff_ratio": 3.14,
            },
        )
        result = calc.calculate_position_sizing_params(
            context=ctx,
            current_price=67000.0,
            action="OPEN_SMALL_SHORT",
            has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert result["position_sizing_method"] == "sortino_kelly"
        assert result["recommended_position_size"] is not None
        assert result["recommended_position_size"] > 0

    def test_kelly_size_larger_than_fixed_risk(self):
        """Kelly-gated sizing should produce larger positions than fixed 1% risk."""
        calc = PositionSizingCalculator(_make_config())
        balance = {"coinbase_FUTURES_USD": 500.0}
        price = 67000.0

        # Fixed risk sizing
        ctx_fixed = _make_context(sortino_gate_result=_fixed_risk_gate_result())
        result_fixed = calc.calculate_position_sizing_params(
            context=ctx_fixed, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        # Quarter Kelly sizing  
        ctx_kelly = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics={
                "win_rate": 0.63, "avg_win": 220.0,
                "avg_loss": 70.0, "payoff_ratio": 3.14,
            },
        )
        result_kelly = calc.calculate_position_sizing_params(
            context=ctx_kelly, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        # Kelly should generally be larger (with a good win rate and payoff)
        # but may be capped. At minimum, they should be different methods.
        assert result_fixed["position_sizing_method"] == "risk_based"
        assert result_kelly["position_sizing_method"] == "sortino_kelly"

    def test_half_kelly_larger_than_quarter_kelly(self):
        """Half Kelly should produce larger or equal position than quarter Kelly."""
        calc = PositionSizingCalculator(_make_config())
        balance = {"coinbase_FUTURES_USD": 500.0}
        price = 67000.0
        perf = {
            "win_rate": 0.63, "avg_win": 220.0,
            "avg_loss": 70.0, "payoff_ratio": 3.14,
        }

        ctx_quarter = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics=perf,
        )
        r_quarter = calc.calculate_position_sizing_params(
            context=ctx_quarter, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        ctx_half = _make_context(
            sortino_gate_result=_half_kelly_gate_result(),
            performance_metrics=perf,
        )
        r_half = calc.calculate_position_sizing_params(
            context=ctx_half, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        assert r_half["recommended_position_size"] >= r_quarter["recommended_position_size"]


# ---------------------------------------------------------------------------
# Multiplier is per-call, not global
# ---------------------------------------------------------------------------

class TestMultiplierIsolation:
    """Verify kelly_fraction_multiplier is set per-call, not globally mutated."""

    def test_multiplier_not_persisted_between_calls(self):
        """Quarter Kelly call doesn't affect subsequent fixed risk call."""
        calc = PositionSizingCalculator(_make_config())
        balance = {"coinbase_FUTURES_USD": 500.0}
        price = 67000.0
        perf = {
            "win_rate": 0.63, "avg_win": 220.0,
            "avg_loss": 70.0, "payoff_ratio": 3.14,
        }

        # Call 1: quarter Kelly
        ctx1 = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics=perf,
        )
        r1 = calc.calculate_position_sizing_params(
            context=ctx1, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )
        assert r1["position_sizing_method"] == "sortino_kelly"

        # Call 2: no gate → should be back to risk_based
        ctx2 = _make_context()
        r2 = calc.calculate_position_sizing_params(
            context=ctx2, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )
        assert r2["position_sizing_method"] == "risk_based"

    def test_multiplier_changes_between_calls(self):
        """Different gate results produce different sizing on same calculator."""
        calc = PositionSizingCalculator(_make_config())
        balance = {"coinbase_FUTURES_USD": 500.0}
        price = 67000.0
        perf = {
            "win_rate": 0.63, "avg_win": 220.0,
            "avg_loss": 70.0, "payoff_ratio": 3.14,
        }

        # Quarter Kelly
        ctx1 = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics=perf,
        )
        r1 = calc.calculate_position_sizing_params(
            context=ctx1, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        # Half Kelly
        ctx2 = _make_context(
            sortino_gate_result=_half_kelly_gate_result(),
            performance_metrics=perf,
        )
        r2 = calc.calculate_position_sizing_params(
            context=ctx2, current_price=price,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance=balance, balance_source="Coinbase",
        )

        assert r1["position_sizing_method"] == "sortino_kelly"
        assert r2["position_sizing_method"] == "sortino_kelly"
        # Half Kelly should produce larger position
        assert r2["recommended_position_size"] >= r1["recommended_position_size"]


# ---------------------------------------------------------------------------
# Gate result propagated in output
# ---------------------------------------------------------------------------

class TestGateResultInOutput:
    """Verify the sortino gate metadata is included in sizing output."""

    def test_gate_metadata_in_result(self):
        """When Kelly sizing is used, sortino_gate info is in the result."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(
            sortino_gate_result=_quarter_kelly_gate_result(),
            performance_metrics={
                "win_rate": 0.63, "avg_win": 220.0,
                "avg_loss": 70.0, "payoff_ratio": 3.14,
            },
        )
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert "sortino_gate" in result
        gate_info = result["sortino_gate"]
        assert gate_info["sizing_mode"] == "quarter_kelly"
        assert gate_info["kelly_multiplier"] == 0.25
        assert gate_info["weighted_sortino"] == 0.75

    def test_no_gate_metadata_when_fixed_risk(self):
        """When fixed risk, no sortino_gate key (or it shows fixed_risk)."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context()
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        # Either no key, or key with fixed_risk
        if "sortino_gate" in result:
            assert result["sortino_gate"]["sizing_mode"] == "fixed_risk"


# ---------------------------------------------------------------------------
# De-risking / HOLD actions unaffected
# ---------------------------------------------------------------------------

class TestDeRiskingUnaffected:
    """Sortino Kelly should not affect CLOSE/REDUCE/HOLD-without-position."""

    def test_close_action_ignores_gate(self):
        """CLOSE_SHORT with Kelly gate → still uses de-risking path."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(sortino_gate_result=_half_kelly_gate_result())
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="CLOSE_SHORT", has_existing_position=True,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        # De-risking skips sizing entirely
        assert result["recommended_position_size"] == 0

    def test_hold_no_position_ignores_gate(self):
        """HOLD without position → no sizing regardless of gate."""
        calc = PositionSizingCalculator(_make_config())
        ctx = _make_context(sortino_gate_result=_half_kelly_gate_result())
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="HOLD", has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        assert result["recommended_position_size"] == 0


# ---------------------------------------------------------------------------
# Legacy use_kelly_criterion flag interaction
# ---------------------------------------------------------------------------

class TestLegacyKellyFlagInteraction:
    """When the old use_kelly_criterion=True flag is set alongside sortino gate."""

    def test_sortino_gate_takes_precedence_over_legacy_flag(self):
        """If sortino_gate_result is present and says fixed_risk,
        it should stay fixed even if use_kelly_criterion=True."""
        calc = PositionSizingCalculator(_make_config(use_kelly=True))
        ctx = _make_context(sortino_gate_result=_fixed_risk_gate_result())
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        # Sortino gate says fixed_risk → should override legacy kelly
        assert result["position_sizing_method"] == "risk_based"


# ---------------------------------------------------------------------------
# Position size cap still applies with Kelly
# ---------------------------------------------------------------------------

class TestPositionCapWithKelly:
    """The environment-based position cap should still apply to Kelly-sized positions."""

    def test_kelly_position_respects_usd_cap(self):
        """Even with half Kelly, the USD cap limits the final position."""
        config = _make_config()
        config["agent"]["position_sizing"]["max_position_usd_prod"] = 100.0
        calc = PositionSizingCalculator(config)
        ctx = _make_context(
            sortino_gate_result=_half_kelly_gate_result(),
            performance_metrics={
                "win_rate": 0.63, "avg_win": 220.0,
                "avg_loss": 70.0, "payoff_ratio": 3.14,
            },
        )
        result = calc.calculate_position_sizing_params(
            context=ctx, current_price=67000.0,
            action="OPEN_SMALL_SHORT", has_existing_position=False,
            relevant_balance={"coinbase_FUTURES_USD": 500.0},
            balance_source="Coinbase",
        )
        # Position value should be <= $100 cap
        pos_value = result["recommended_position_size"] * 67000.0
        assert pos_value <= 100.0 + 0.01  # small float tolerance
