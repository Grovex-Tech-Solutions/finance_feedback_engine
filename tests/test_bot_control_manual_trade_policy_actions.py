import pytest

from finance_feedback_engine.api.bot_control import ManualTradeRequest


def test_manual_trade_request_accepts_policy_action_and_derives_compatibility():
    req = ManualTradeRequest(asset_pair="BTCUSD", action="OPEN_SMALL_LONG", size=0.1)

    assert req.action == "OPEN_SMALL_LONG"
    assert req.policy_action == "OPEN_SMALL_LONG"
    assert req.legacy_action_compatibility == "BUY"


def test_manual_trade_request_preserves_legacy_direction_without_policy_action():
    req = ManualTradeRequest(asset_pair="BTCUSD", action="SELL", size=0.1)

    assert req.action == "SELL"
    assert req.policy_action is None
    assert req.legacy_action_compatibility == "SELL"


def test_manual_trade_request_rejects_unknown_action():
    with pytest.raises(ValueError):
        ManualTradeRequest(asset_pair="BTCUSD", action="PANIC", size=0.1)
