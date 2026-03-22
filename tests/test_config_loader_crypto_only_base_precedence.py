from finance_feedback_engine.utils.config_loader import _deep_merge, _normalize_runtime_config, _restore_base_precedence


def test_restore_base_precedence_does_not_reintroduce_oanda_for_crypto_only_runtime(monkeypatch):
    monkeypatch.setenv("TRADING_PLATFORM", "unified")
    monkeypatch.setenv("AGENT_ASSET_PAIRS", "BTCUSD,ETHUSD")

    base_config = {
        "trading_platform": "unified",
        "platforms": [
            {"name": "coinbase_advanced", "credentials": {"api_key": "x", "api_secret": "y"}},
            {"name": "oanda", "credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        ],
        "providers": {
            "coinbase": {"credentials": {"api_key": "x", "api_secret": "y"}},
            "oanda": {"credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        },
        "agent": {"asset_pairs": ["BTCUSD", "ETHUSD"]},
    }

    env_config = {
        "trading_platform": "unified",
        "platforms": [
            {"name": "coinbase_advanced", "credentials": {"api_key": "x", "api_secret": "y"}},
            {"name": "oanda", "credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        ],
        "providers": {
            "coinbase": {"credentials": {"api_key": "x", "api_secret": "y"}},
            "oanda": {"credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        },
        "agent": {"asset_pairs": ["BTCUSD", "ETHUSD"]},
    }

    merged = _deep_merge(base_config, env_config)
    restored = _restore_base_precedence(base_config, merged)
    out = _normalize_runtime_config(restored)

    assert [p["name"] for p in out["platforms"]] == ["coinbase_advanced"]
    assert out["enabled_platforms"] == ["coinbase_advanced"]
    assert "oanda" not in out.get("providers", {})
