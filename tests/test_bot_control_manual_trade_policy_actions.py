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


@pytest.mark.asyncio
async def test_execute_manual_trade_preserves_policy_metadata_and_sends_legacy_action():
    from unittest.mock import AsyncMock, MagicMock

    from finance_feedback_engine.api.bot_control import execute_manual_trade

    platform = MagicMock()
    platform.aexecute_trade = AsyncMock(return_value={"order_id": "abc123", "status": "submitted"})
    engine = MagicMock()
    engine.trading_platform = platform

    request = ManualTradeRequest(asset_pair="BTCUSD", action="OPEN_SMALL_LONG", size=0.25)

    result = await execute_manual_trade(request=request, _api_user="dev", engine=engine)

    platform.aexecute_trade.assert_awaited_once_with(
        {
            "asset_pair": "BTCUSD",
            "action": "BUY",
            "policy_action": "OPEN_SMALL_LONG",
            "legacy_action_compatibility": "BUY",
            "order_type": "MARKET",
            "recommended_position_size": 0.25,
        }
    )
    assert result["status"] == "executed"
    assert result["requested_action"] == "OPEN_SMALL_LONG"
    assert result["policy_action"] == "OPEN_SMALL_LONG"
    assert result["legacy_action_compatibility"] == "BUY"
    assert result["trade"]["order_id"] == "abc123"
