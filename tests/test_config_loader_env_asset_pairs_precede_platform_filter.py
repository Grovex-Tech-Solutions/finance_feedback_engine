from finance_feedback_engine.utils.config_loader import _normalize_runtime_config


def test_env_asset_pairs_are_applied_before_crypto_only_platform_filter(monkeypatch):
    monkeypatch.setenv("AGENT_ASSET_PAIRS", "BTCUSD,ETHUSD")

    cfg = {
        "trading_platform": "unified",
        "platforms": [
            {"name": "coinbase_advanced", "credentials": {"api_key": "x", "api_secret": "y"}},
            {"name": "oanda", "credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        ],
        "providers": {
            "coinbase": {"credentials": {"api_key": "x", "api_secret": "y"}},
            "oanda": {"credentials": {"api_key": "", "account_id": "", "environment": "practice"}},
        },
        # Base YAML still mentions forex, env override should win.
        "agent": {"asset_pairs": ["BTCUSD", "EURUSD"]},
    }

    out = _normalize_runtime_config(cfg)

    assert out["agent"]["asset_pairs"] == ["BTCUSD", "ETHUSD"]
    assert [p["name"] for p in out["platforms"]] == ["coinbase_advanced"]
    assert out["enabled_platforms"] == ["coinbase_advanced"]
    assert "oanda" not in out.get("providers", {})
