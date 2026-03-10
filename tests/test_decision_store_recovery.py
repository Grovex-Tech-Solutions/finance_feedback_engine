from finance_feedback_engine.persistence.decision_store import DecisionStore


def test_find_equivalent_recovery_decision_matches_existing(tmp_path):
    store = DecisionStore({"storage_path": str(tmp_path)})
    decision = {
        "id": "dec-1",
        "asset_pair": "EURUSD",
        "timestamp": "2026-03-10T16:19:30.565027Z",
        "action": "BUY",
        "confidence": 75,
        "recommended_position_size": 1.0,
        "entry_price": 1.15595,
        "ai_provider": "recovery",
        "recovery_metadata": {
            "platform": "oanda",
            "product_id": "EUR_USD",
            "opened_at": None,
        },
    }
    store.save_decision(decision)

    match = store.find_equivalent_recovery_decision(
        asset_pair="EURUSD",
        action="BUY",
        entry_price=1.15595,
        position_size=1.0,
        platform="oanda",
        product_id="EUR_USD",
    )

    assert match is not None
    assert match["id"] == "dec-1"


def test_find_equivalent_recovery_decision_ignores_non_recovery(tmp_path):
    store = DecisionStore({"storage_path": str(tmp_path)})
    store.save_decision(
        {
            "id": "dec-2",
            "asset_pair": "EURUSD",
            "timestamp": "2026-03-10T16:19:30.565027Z",
            "action": "BUY",
            "confidence": 75,
            "recommended_position_size": 1.0,
            "entry_price": 1.15595,
            "ai_provider": "gemini",
        }
    )

    match = store.find_equivalent_recovery_decision(
        asset_pair="EURUSD",
        action="BUY",
        entry_price=1.15595,
        position_size=1.0,
        platform="oanda",
        product_id="EUR_USD",
    )

    assert match is None
