"""Tests for crypto enrichment routing away from Alpha Vantage."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from finance_feedback_engine.data_providers.alpha_vantage_provider import (
    AlphaVantageProvider,
)


@pytest.mark.asyncio
async def test_crypto_pairs_skip_alpha_vantage_indicator_calls_during_enrichment():
    """Crypto enrichment should use local computation and never call Alpha Vantage indicators."""
    provider = AlphaVantageProvider(api_key="test_key", is_backtest=False)

    try:
        market_data = {
            "open": 50000.0,
            "high": 50500.0,
            "low": 49500.0,
            "close": 50200.0,
            "provider": "coinbase",
        }

        with patch.object(
            provider,
            "_get_technical_indicators",
            new=AsyncMock(return_value={}),
        ) as mock_alpha_vantage_indicators, patch.object(
            provider,
            "_get_local_crypto_technical_indicators",
            new=AsyncMock(return_value={"rsi": 55.0, "rsi_signal": "neutral"}),
            create=True,
        ) as mock_local_indicators:
            enriched = await provider._enrich_market_data(market_data, "BTCUSD")

        mock_alpha_vantage_indicators.assert_not_called()
        mock_local_indicators.assert_called_once_with("BTCUSD")
        assert enriched["rsi"] == 55.0
        assert enriched["rsi_signal"] == "neutral"
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_forex_pairs_still_use_alpha_vantage_indicators_during_enrichment():
    """Forex enrichment should keep existing Alpha Vantage indicator flow."""
    provider = AlphaVantageProvider(api_key="test_key", is_backtest=False)

    try:
        market_data = {
            "open": 1.0800,
            "high": 1.0850,
            "low": 1.0750,
            "close": 1.0820,
            "provider": "alpha_vantage",
        }

        with patch.object(
            provider,
            "_get_technical_indicators",
            new=AsyncMock(return_value={"rsi": 47.0}),
        ) as mock_alpha_vantage_indicators, patch.object(
            provider,
            "_get_local_crypto_technical_indicators",
            new=AsyncMock(return_value={}),
            create=True,
        ) as mock_local_indicators:
            enriched = await provider._enrich_market_data(market_data, "EURUSD")

        mock_alpha_vantage_indicators.assert_called_once_with("EURUSD")
        mock_local_indicators.assert_not_called()
        assert enriched["rsi"] == 47.0
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_crypto_indicators_are_computed_locally_from_coinbase_candles():
    """Local crypto indicator computation should derive RSI/MACD from Coinbase candles."""
    provider = AlphaVantageProvider(api_key="test_key", is_backtest=False)

    try:
        candles = [
            {
                "timestamp": 1700000000 + i * 3600,
                "open": 50000.0 + i,
                "high": 50020.0 + i,
                "low": 49980.0 + i,
                "close": 50000.0 + (i * 3),
                "volume": 1000.0 + i,
            }
            for i in range(80)
        ]

        provider.coinbase_provider = Mock()
        provider.coinbase_provider.get_candles.return_value = candles

        indicators = await provider._get_local_crypto_technical_indicators("BTCUSD")

        provider.coinbase_provider.get_candles.assert_called_once()
        assert "rsi" in indicators
        assert "macd" in indicators
        assert "macd_signal" in indicators
        assert "macd_hist" in indicators
        assert isinstance(indicators["rsi"], float)
    finally:
        await provider.close()
