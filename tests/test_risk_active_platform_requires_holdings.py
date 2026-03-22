from finance_feedback_engine.risk.correlation_analyzer import CorrelationAnalyzer
from finance_feedback_engine.risk.var_calculator import VaRCalculator


def _history(start, step, days=40):
    return [
        {"date": f"2024-01-{i+1:02d}", "price": start + i * step}
        for i in range(days)
    ]


def test_var_ignores_platform_with_history_but_no_holdings():
    calc = VaRCalculator()
    result = calc.calculate_dual_portfolio_var(
        {"BTCUSD": {"quantity": 1.0, "current_price": 50000.0}},
        {"BTCUSD": _history(40000, 100)},
        {},
        {"EUR_USD": _history(1.05, 0.001)},
        confidence_level=0.95,
    )
    assert result["active_platforms"] == ["coinbase"]
    assert "oanda_var" not in result


def test_correlation_ignores_platform_with_history_but_no_holdings():
    analyzer = CorrelationAnalyzer()
    result = analyzer.analyze_dual_platform_correlations(
        {"BTCUSD": {"quantity": 1.0}},
        {"BTCUSD": _history(40000, 100)},
        {},
        {"EUR_USD": _history(1.05, 0.001)},
    )
    assert result["active_platforms"] == ["coinbase"]
    assert "oanda" not in result
    assert "cross_platform" not in result
