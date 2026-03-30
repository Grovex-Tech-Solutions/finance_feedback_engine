import json
import logging

from finance_feedback_engine.decision_engine.ensemble_manager import EnsembleDecisionManager


def test_update_base_weights_mutates_state_and_persists_history(tmp_path):
    manager = EnsembleDecisionManager(
        {
            "persistence": {"storage_path": str(tmp_path)},
            "ensemble": {
                "enabled_providers": ["local", "qwen"],
                "provider_weights": {"local": 0.5, "qwen": 0.5},
                "voting_strategy": "weighted",
                "adaptive_learning": True,
                "learning_rate": 1.0,
                "debate_mode": False,
            },
        }
    )

    provider_decisions = {
        "local": {"action": "BUY", "confidence": 80},
        "qwen": {"action": "SELL", "confidence": 75},
    }

    assert manager.base_weights == {"local": 0.5, "qwen": 0.5}
    assert manager.performance_tracker.performance_history == {}

    manager.update_base_weights(
        provider_decisions=provider_decisions,
        actual_outcome="BUY",
        performance_metric=10.0,
    )

    assert manager.performance_tracker.performance_history["local"] == {
        "correct": 1,
        "total": 1,
        "avg_performance": 10.0,
    }
    assert manager.performance_tracker.performance_history["qwen"] == {
        "correct": 0,
        "total": 1,
        "avg_performance": 10.0,
    }
    assert manager.base_weights == {"local": 1.0, "qwen": 0.0}

    history_path = tmp_path / "ensemble_history.json"
    assert history_path.exists()

    history = json.loads(history_path.read_text())
    assert history["local"]["correct"] == 1
    assert history["local"]["total"] == 1
    assert history["qwen"]["correct"] == 0
    assert history["qwen"]["total"] == 1


def test_update_base_weights_logs_before_after_packet(tmp_path, caplog):
    manager = EnsembleDecisionManager(
        {
            "persistence": {"storage_path": str(tmp_path)},
            "ensemble": {
                "enabled_providers": ["local", "qwen"],
                "provider_weights": {"local": 0.5, "qwen": 0.5},
                "voting_strategy": "weighted",
                "adaptive_learning": True,
                "learning_rate": 1.0,
                "debate_mode": False,
            },
        }
    )

    provider_decisions = {
        "local": {"action": "BUY", "confidence": 80},
        "qwen": {"action": "SELL", "confidence": 75},
    }

    with caplog.at_level(logging.INFO):
        manager.update_base_weights(
            provider_decisions=provider_decisions,
            actual_outcome="BUY",
            performance_metric=10.0,
        )

    assert (
        "Adaptive weights updated | actual_outcome=BUY | performance_metric=10.0 | "
        "provider_decisions=['local', 'qwen'] | weights_before={'local': 0.5, 'qwen': 0.5} | "
        "weights_after={'local': 1.0, 'qwen': 0.0} | history_file="
    ) in caplog.text
