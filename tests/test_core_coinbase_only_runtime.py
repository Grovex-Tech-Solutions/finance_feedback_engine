from finance_feedback_engine.utils.config_loader import _normalize_runtime_config


def test_crypto_only_runtime_normalization_leaves_only_coinbase_platform_and_no_oanda_provider():
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
    assert [p['name'] for p in out['platforms']] == ['coinbase_advanced']
    assert 'oanda' not in out.get('providers', {})
