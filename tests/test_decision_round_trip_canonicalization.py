import copy
import uuid

import pytest

from finance_feedback_engine.persistence.decision_store import (
    DECISION_SCHEMA_VERSION,
    DecisionStore,
)


CANONICAL_IDENTITY_FIELDS = (
    "id",
    "decision_id",
    "_schema_version",
    "timestamp",
)

CANONICAL_TRADING_FIELDS = (
    "asset_pair",
    "action",
    "confidence",
)

CANONICAL_LINEAGE_FIELDS = (
    "ai_provider",
    "ensemble_metadata",
    "recovery_metadata",
    "policy_trace",
    "market_data",
)


def _make_store(tmp_path):
    return DecisionStore({"storage_path": str(tmp_path / "decisions")})


def _base_decision():
    return {
        "id": str(uuid.uuid4()),
        "timestamp": "2026-03-30T05:00:00+00:00",
        "asset_pair": "BTCUSD",
        "action": "BUY",
        "confidence": 72,
        "reasoning": "canonical test fixture",
        "market_data": {
            "current_price": 68500.0,
            "bid": 68495.0,
            "ask": 68505.0,
        },
    }


def _minimal_fixture():
    return _base_decision()


def _debate_fixture():
    fixture = _base_decision()
    fixture.update(
        {
            "ai_provider": "ensemble",
            "action": "HOLD",
            "ensemble_metadata": {
                "voting_strategy": "debate",
                "debate_mode": True,
                "original_weights": {},
                "adjusted_weights": {},
                "provider_decisions": {
                    "deepseek-r1:8b": {
                        "action": "HOLD",
                        "confidence": 55,
                        "reasoning": "judge",
                    }
                },
                "role_decisions": {
                    "bull": {"provider": "gemma2:9b", "action": "BUY"},
                    "bear": {"provider": "llama3.1:8b", "action": "SELL"},
                    "judge": {"provider": "deepseek-r1:8b", "action": "HOLD"},
                },
                "debate_seats": {
                    "bull": "gemma2:9b",
                    "bear": "llama3.1:8b",
                    "judge": "deepseek-r1:8b",
                },
            },
        }
    )
    return fixture


def _weighted_fixture():
    fixture = _base_decision()
    fixture.update(
        {
            "ai_provider": "ensemble",
            "action": "OPEN_SMALL_SHORT",
            "asset_pair": "ETHUSD",
            "ensemble_metadata": {
                "voting_strategy": "weighted",
                "original_weights": {
                    "gemma2:9b": 0.25,
                    "llama3.1:8b": 0.25,
                    "deepseek-r1:8b": 0.25,
                    "gemma3:4b": 0.25,
                },
                "adjusted_weights": {
                    "gemma2:9b": 0.15,
                    "llama3.1:8b": 0.35,
                    "deepseek-r1:8b": 0.30,
                    "gemma3:4b": 0.20,
                },
                "provider_decisions": {
                    "gemma2:9b": {"action": "HOLD", "confidence": 40},
                    "llama3.1:8b": {"action": "OPEN_SMALL_SHORT", "confidence": 78},
                    "deepseek-r1:8b": {"action": "OPEN_SMALL_SHORT", "confidence": 75},
                },
                "providers_used": ["gemma2:9b", "llama3.1:8b", "deepseek-r1:8b"],
                "providers_failed": ["gemma3:4b"],
                "fallback_tier": "weighted",
            },
        }
    )
    return fixture


def _recovery_fixture():
    fixture = _base_decision()
    fixture.update(
        {
            "ai_provider": "recovery",
            "action": "SELL",
            "asset_pair": "ETP20DEC30CDE",
            "recovery_metadata": {
                "product_id": "ETP-20DEC30-CDE",
                "asset_pair_alias": "ETHUSD",
                "source": "startup_position_recovery",
            },
        }
    )
    return fixture


def _policy_trace_fixture():
    fixture = _base_decision()
    fixture.update(
        {
            "policy_trace": {
                "policy_package": {
                    "policy_state": {"position_state": "flat", "version": 1},
                    "action_context": {
                        "structural_action_validity": "valid",
                        "version": 1,
                    },
                    "version": 1,
                },
                "decision_envelope": {
                    "action": "BUY",
                    "policy_action": "OPEN_SMALL_LONG",
                    "legacy_action_compatibility": "BUY",
                    "confidence": 72,
                    "reasoning": "canonical test fixture",
                    "version": 1,
                },
                "decision_metadata": {
                    "asset_pair": "BTCUSD",
                    "ai_provider": "ensemble",
                    "decision_id": fixture["id"],
                },
                "trace_version": 1,
            }
        }
    )
    return fixture


@pytest.mark.parametrize(
    ("fixture_factory", "expected_lineage_fields"),
    [
        (_minimal_fixture, ("market_data",)),
        (_debate_fixture, ("ai_provider", "ensemble_metadata", "market_data")),
        (_weighted_fixture, ("ai_provider", "ensemble_metadata", "market_data")),
        (_recovery_fixture, ("ai_provider", "recovery_metadata", "market_data")),
        (_policy_trace_fixture, ("policy_trace", "market_data")),
    ],
)
def test_canonical_decision_fields_round_trip_by_shape(
    tmp_path, fixture_factory, expected_lineage_fields
):
    store = _make_store(tmp_path)
    decision = fixture_factory()

    store.save_decision(copy.deepcopy(decision))
    loaded = store.get_decision_by_id(decision["id"])

    assert loaded is not None

    for field in CANONICAL_IDENTITY_FIELDS:
        assert field in loaded
    assert loaded["id"] == decision["id"]
    assert loaded["decision_id"] == decision["id"]
    assert loaded["_schema_version"] == DECISION_SCHEMA_VERSION
    assert loaded["timestamp"] == decision["timestamp"]

    for field in CANONICAL_TRADING_FIELDS:
        assert loaded[field] == decision[field]

    for field in expected_lineage_fields:
        assert loaded[field] == decision[field]


def test_round_trip_allows_id_alias_normalization_but_not_payload_mutation(tmp_path):
    store = _make_store(tmp_path)
    canonical_id = str(uuid.uuid4())
    decision = {
        "decision": {"id": canonical_id},
        "timestamp": "2026-03-30T05:10:00+00:00",
        "asset_pair": "BTCUSD",
        "action": "BUY",
        "confidence": 80,
        "ai_provider": "ensemble",
        "ensemble_metadata": {
            "voting_strategy": "weighted",
            "original_weights": {"gemma2:9b": 0.5, "llama3.1:8b": 0.5},
            "adjusted_weights": {"gemma2:9b": 0.4, "llama3.1:8b": 0.6},
            "provider_decisions": {
                "gemma2:9b": {"action": "BUY", "confidence": 70},
                "llama3.1:8b": {"action": "BUY", "confidence": 85},
            },
        },
    }

    store.save_decision(copy.deepcopy(decision))
    loaded = store.get_decision_by_id(canonical_id)

    assert loaded is not None
    assert loaded["id"] == canonical_id
    assert loaded["decision_id"] == canonical_id
    assert loaded["_schema_version"] == DECISION_SCHEMA_VERSION
    assert loaded["ensemble_metadata"] == decision["ensemble_metadata"]
    assert loaded.get("decision") == decision["decision"]


def test_recovery_shape_keeps_recovery_metadata_and_canonical_id_fields(tmp_path):
    store = _make_store(tmp_path)
    decision = _recovery_fixture()

    store.save_decision(copy.deepcopy(decision))
    loaded = store.get_decision_by_id(decision["id"])

    assert loaded is not None
    assert loaded["id"] == decision["id"]
    assert loaded["decision_id"] == decision["id"]
    assert loaded["ai_provider"] == "recovery"
    assert loaded["recovery_metadata"] == decision["recovery_metadata"]
    assert loaded["asset_pair"] == "ETP20DEC30CDE"
