from finance_feedback_engine.trading_platforms.unified_platform import UnifiedTradingPlatform


def test_unified_platform_skips_oanda_when_credentials_are_placeholders():
    creds = {
        'coinbase': {'api_key': 'real', 'api_secret': 'real'},
        'oanda': {
            'api_key': 'YOUR_OANDA_API_KEY',
            'account_id': 'YOUR_OANDA_ACCOUNT_ID',
            'environment': 'practice',
        },
    }
    platform = UnifiedTradingPlatform(creds, config={})
    assert 'coinbase' in platform.platforms
    assert 'oanda' not in platform.platforms
