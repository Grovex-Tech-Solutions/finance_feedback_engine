
def filter_platform_breakdowns(portfolio, enabled_platforms):
    platform_breakdowns = portfolio.get('platform_breakdowns') or {}
    enabled = {str(p).lower() for p in enabled_platforms}
    return {
        name: data
        for name, data in platform_breakdowns.items()
        if name.lower() in enabled or (name.lower() == 'coinbase' and 'coinbase_advanced' in enabled)
    }


def test_coinbase_only_runtime_filters_oanda_from_platform_breakdowns():
    portfolio = {
        'platform_breakdowns': {
            'coinbase': {'total_value_usd': 749.04},
            'oanda': {'total_value_usd': 0, 'error': 'auth'},
        }
    }
    filtered = filter_platform_breakdowns(portfolio, ['coinbase_advanced'])
    assert set(filtered.keys()) == {'coinbase'}
