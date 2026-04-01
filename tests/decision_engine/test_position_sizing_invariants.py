"""Invariant tests for position sizing properties.

These tests verify that position sizing maintains safety invariants
regardless of market conditions or decision inputs.
"""

import pytest
from finance_feedback_engine.decision_engine.position_sizing import PositionSizingCalculator


@pytest.fixture
def calculator():
    config = {
        "decision_engine": {
            "default_position_size": 0.03,
            "risk_per_trade": 0.01,
            "stop_loss_percentage": 0.02,
        },
        "position_sizing": {
            "dev_cap_usd": 500,
            "prod_cap_usd": 500,
        },
    }
    return PositionSizingCalculator(config)


class TestPositionSizeNeverNegative:
    """Position size must ALWAYS be >= 0."""

    def test_positive_balance_positive_size(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.02
        )
        assert size >= 0

    def test_zero_balance_returns_zero(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=0, entry_price=50000, stop_loss_percentage=0.02
        )
        assert size == 0.0

    def test_negative_balance_returns_zero(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=-100, entry_price=50000, stop_loss_percentage=0.02
        )
        assert size == 0.0

    def test_zero_entry_price_returns_zero(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=0, stop_loss_percentage=0.02
        )
        assert size == 0.0

    def test_negative_entry_price_returns_zero(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=-100, stop_loss_percentage=0.02
        )
        assert size == 0.0


class TestStopLossMinimumEnforced:
    """Stop loss must be at least 0.5% to prevent excessive leverage."""

    def test_tiny_stop_loss_clamped(self, calculator):
        # 0.001 (0.1%) should be clamped to 0.5%
        size_tiny = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.001
        )
        size_min = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.005
        )
        assert size_tiny == size_min, "Tiny stop loss should be clamped to minimum"

    def test_zero_stop_loss_clamped(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.0
        )
        # Should use minimum 0.5%, not divide by zero
        assert size > 0
        assert size == calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.005
        )


class TestRiskPercentageBounds:
    """Risk percentage must be bounded 0-10%."""

    def test_excessive_risk_clamped_to_default(self, calculator):
        # risk > 10% should be clamped to 1% default
        size_high = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=0.50, entry_price=50000
        )
        size_default = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=0.01, entry_price=50000
        )
        assert size_high == size_default

    def test_negative_risk_clamped_to_default(self, calculator):
        size = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=-0.05, entry_price=50000
        )
        size_default = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=0.01, entry_price=50000
        )
        assert size == size_default


class TestPositionSizeMonotonic:
    """Larger balance should produce larger or equal position size."""

    def test_larger_balance_larger_size(self, calculator):
        size_small = calculator.calculate_position_size(
            account_balance=100, entry_price=50000, stop_loss_percentage=0.02
        )
        size_large = calculator.calculate_position_size(
            account_balance=10000, entry_price=50000, stop_loss_percentage=0.02
        )
        assert size_large >= size_small

    def test_larger_risk_larger_size(self, calculator):
        size_conservative = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=0.005, entry_price=50000, stop_loss_percentage=0.02
        )
        size_aggressive = calculator.calculate_position_size(
            account_balance=1000, risk_percentage=0.02, entry_price=50000, stop_loss_percentage=0.02
        )
        assert size_aggressive >= size_conservative


class TestPositionSizeFinite:
    """Position size must always be a finite number (no NaN/Inf)."""

    def test_no_nan(self, calculator):
        import math
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.02
        )
        assert not math.isnan(size)
        assert not math.isinf(size)

    def test_very_small_stop_loss_no_inf(self, calculator):
        import math
        # Even with minimum clamp, should not be inf
        size = calculator.calculate_position_size(
            account_balance=1000, entry_price=50000, stop_loss_percentage=0.0001
        )
        assert not math.isinf(size)
        assert not math.isnan(size)

    def test_very_large_balance_no_overflow(self, calculator):
        import math
        size = calculator.calculate_position_size(
            account_balance=1e12, entry_price=50000, stop_loss_percentage=0.02
        )
        assert not math.isinf(size)
        assert not math.isnan(size)
        assert size > 0
