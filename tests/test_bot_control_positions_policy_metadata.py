import pytest
from unittest.mock import AsyncMock, MagicMock

from finance_feedback_engine.api.bot_control import get_open_positions


@pytest.mark.asyncio
async def test_get_open_positions_includes_close_policy_metadata_for_long():
    platform = MagicMock()
    platform.get_active_positions = True
    platform.aget_active_positions = AsyncMock(return_value={
        "positions": [
            {
                "id": "pos-long",
                "instrument": "BTCUSD",
                "side": "LONG",
                "units": 0.5,
                "entry_price": 70000,
                "current_price": 70500,
                "unrealized_pnl": 250,
            }
        ]
    })
    platform.get_portfolio_breakdown = True
    platform.aget_portfolio_breakdown = AsyncMock(return_value={"total_value_usd": 1000.0})
    engine = MagicMock()
    engine.trading_platform = platform

    result = await get_open_positions(_api_user="dev", engine=engine)

    assert result["positions"][0]["close_policy_action"] == "REDUCE_LONG"
    assert result["positions"][0]["close_legacy_action_compatibility"] == "SELL"


@pytest.mark.asyncio
async def test_get_open_positions_includes_close_policy_metadata_for_short():
    platform = MagicMock()
    platform.get_active_positions = True
    platform.aget_active_positions = AsyncMock(return_value={
        "positions": [
            {
                "id": "pos-short",
                "product_id": "ETP-20DEC30-CDE",
                "side": "SHORT",
                "number_of_contracts": "5",
                "entry_price": 2052.6,
                "current_price": 2127.5,
                "unrealized_pnl": -36.2,
            }
        ]
    })
    platform.get_portfolio_breakdown = True
    platform.aget_portfolio_breakdown = AsyncMock(return_value={"total_value_usd": 749.04})
    engine = MagicMock()
    engine.trading_platform = platform

    result = await get_open_positions(_api_user="dev", engine=engine)

    assert result["positions"][0]["close_policy_action"] == "REDUCE_SHORT"
    assert result["positions"][0]["close_legacy_action_compatibility"] == "BUY"
