from finance_feedback_engine.utils.config_loader import _normalize_runtime_config


def test_normalize_runtime_config_excludes_oanda_provider_for_crypto_only_runtime():
    cfg = {
        'trading_platform': 'unified',
        'platforms': [
            {'name': 'coinbase_advanced', 'credentials': {'api_key': 'x', 'api_secret': 'y'}},
            {'name': 'oanda', 'credentials': {'api_key': 'YOUR_OANDA_API_KEY', 'account_id': 'YOUR_OANDA_ACCOUNT_ID'}},
        ],
        'providers': {
            'coinbase': {'credentials': {'api_key': 'x', 'api_secret': 'y'}},
            'oanda': {'credentials': {'api_key': 'YOUR_OANDA_API_KEY', 'account_id': 'YOUR_OANDA_ACCOUNT_ID'}},
        },
        'enabled_platforms': ['coinbase_advanced'],
        'agent': {'asset_pairs': ['BTCUSD', 'ETHUSD']},
    }

    out = _normalize_runtime_config(cfg)

    assert 'oanda' not in out.get('providers', {})
    assert out.get('enabled_platforms') == ['coinbase_advanced']
    assert [p['name'] for p in out.get('platforms', [])] == ['coinbase_advanced']
