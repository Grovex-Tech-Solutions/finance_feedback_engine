"""Test Alpha Vantage usage for forex data - ensure it uses intraday from exchanges."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from finance_feedback_engine.data_providers.alpha_vantage_provider import AlphaVantageProvider
from finance_feedback_engine.data_providers.unified_data_provider import UnifiedDataProvider


class TestAlphaVantageForexFallback:
    """Test that Alpha Vantage is used as backup for forex data."""

    def test_forex_daily_data_timestamp_format(self):
        """Test that forex data timestamp is properly formatted."""
        # Parse a daily data date and format as ISO timestamp
        data_date = datetime.strptime("2026-02-27", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        ts = data_date.replace(hour=23, minute=59, second=0).isoformat()
        data_timestamp = ts.replace('+00:00', 'Z') if data_date.tzinfo else ts + 'Z'
        
        assert data_timestamp.endswith('Z'), "Timestamp should end with Z for UTC"
        assert "2026-02-27" in data_timestamp, "Date should be preserved"

    def test_stale_data_detection_with_market_status(self):
        """Test that stale data detection respects market status."""
        from finance_feedback_engine.utils.validation import validate_data_freshness
        from finance_feedback_engine.utils.market_schedule import MarketSchedule

        # Simulate data from Feb 27 (Friday) at 23:59 UTC
        data_date = datetime.strptime("2026-02-27", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        data_timestamp = data_date.replace(hour=23, minute=59, second=0).isoformat().replace('+00:00', 'Z')

        # Market status for Monday morning (market open)
        market_status = MarketSchedule.get_market_status(
            asset_pair="EURUSD",
            asset_type="forex",
            now_utc=datetime.now(timezone.utc)
        )

        is_fresh, age_str, warning_msg = validate_data_freshness(
            data_timestamp,
            asset_type="forex",
            timeframe="daily",
            market_status=market_status,
        )

        # Friday data on Monday morning should be stale (>24 hours old)
        assert not is_fresh, "Friday data on Monday should be stale"
        assert "70" in age_str or "69" in age_str, f"Age should be around 70 hours, got: {age_str}"

    def test_intraday_data_should_be_fresh(self):
        """Test that intraday data has different thresholds."""
        from finance_feedback_engine.utils.validation import validate_data_freshness
        from finance_feedback_engine.utils.market_schedule import MarketSchedule

        # Recent timestamp (within last 5 minutes)
        recent_time = datetime.now(timezone.utc)
        data_timestamp = recent_time.isoformat().replace('+00:00', 'Z')

        market_status = MarketSchedule.get_market_status(
            asset_pair="EURUSD",
            asset_type="forex",
            now_utc=recent_time
        )

        is_fresh, age_str, warning_msg = validate_data_freshness(
            data_timestamp,
            asset_type="forex",
            timeframe="intraday",  # Intraday has stricter thresholds
            market_status=market_status,
        )

        # Recent data should be fresh
        assert is_fresh, "Recent data should be fresh"

    @pytest.mark.asyncio
    async def test_unified_provider_uses_exchange_for_forex(self):
        """Test that unified provider uses Oanda for forex intraday data."""
        # Mock Oanda provider
        mock_oanda = MagicMock()
        mock_oanda.get_candles = AsyncMock(
            return_value=[
                {
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "open": 1.0850,
                    "high": 1.0860,
                    "low": 1.0840,
                    "close": 1.0855,
                }
            ]
        )

        # Mock unified provider
        unified = UnifiedDataProvider(
            alpha_vantage=None,
            coinbase=None,
            oanda=mock_oanda,
            cache_ttl_seconds=60,
        )

        # Fetch intraday candles for forex
        candles, provider = await unified.get_candles("EURUSD", "1m")

        # Should use Oanda for forex
        assert provider == "oanda", f"Should use Oanda for forex, got: {provider}"
        assert len(candles) > 0, "Should have candles"

    @pytest.mark.asyncio
    async def test_unified_provider_should_not_use_alpha_vantage_for_candles(self):
        """Test that unified provider skips Alpha Vantage for get_candles."""
        mock_av = MagicMock()
        # Alpha Vantage has get_candles method but returns None for forex
        mock_av.get_candles = AsyncMock(return_value=None)

        unified = UnifiedDataProvider(
            alpha_vantage=mock_av,
            coinbase=None,
            oanda=None,
            cache_ttl_seconds=60,
        )

        # Try to fetch candles - should skip Alpha Vantage
        with pytest.raises(ValueError, match="All providers failed"):
            await unified.get_candles("EURUSD", "1m")
