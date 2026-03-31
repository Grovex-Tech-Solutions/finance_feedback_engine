import json
from pathlib import Path

from finance_feedback_engine.monitoring.track0_audit import (
    collect_track0_proof_packet,
    render_packet_summary,
)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_collect_track0_proof_packet_reports_lower_chain_without_adaptation(tmp_path):
    decision_id = "plain-recovery-close-1"
    _write_json(
        tmp_path / "decisions" / f"2026-03-31_{decision_id}.json",
        {
            "id": decision_id,
            "asset_pair": "BIP20DEC30CDE",
            "action": "SELL",
            "ai_provider": "recovery",
            "recovery_metadata": {"product_id": "BIP-20DEC30-CDE"},
        },
    )
    _write_json(
        tmp_path / "memory" / f"outcome_{decision_id}.json",
        {
            "decision_id": decision_id,
            "action": "SELL",
            "realized_pnl": -75.0,
        },
    )
    log_text = (
        f"2026-03-31 01:19:42 | Learning handoff ACCEPTED | decision_id={decision_id} "
        "| lineage_source=decision_store.recovery_metadata_product | realized_pnl=-75.0\n"
    )

    packet = collect_track0_proof_packet(
        data_dir=tmp_path,
        decision_id=decision_id,
        log_text=log_text,
    )

    assert packet.lower_chain_passed is True
    assert packet.adaptation_passed is False
    assert packet.ai_provider == "recovery"
    assert packet.lineage_source == "decision_store.recovery_metadata_product"
    assert packet.verdict == "lower_chain_only"
    assert packet.verdict_reason == "missing_adaptive_handoff"
    assert packet.realized_pnl == -75.0


def test_collect_track0_proof_packet_reports_full_adaptive_packet(tmp_path):
    decision_id = "1f5bcd7e-7634-4d5a-9bad-aba0de70ba7c"
    _write_json(
        tmp_path / "decisions" / f"2026-03-31_{decision_id}.json",
        {
            "id": decision_id,
            "asset_pair": "BIP20DEC30CDE",
            "action": "SELL",
            "ai_provider": "ensemble",
            "recovery_metadata": {
                "product_id": "BIP-20DEC30-CDE",
                "shadowed_from_decision_id": "2a620bdf-53d5-45f5-8549-6353295471ed",
                "shadowed_from_provider": "ensemble",
            },
            "ensemble_metadata": {
                "voting_strategy": "debate",
                "providers_used": ["gemma2:9b", "llama3.1:8b", "deepseek-r1:8b"],
            },
        },
    )
    _write_json(
        tmp_path / "memory" / f"outcome_{decision_id}.json",
        {
            "decision_id": decision_id,
            "action": "SELL",
            "realized_pnl": -885.0,
        },
    )
    log_text = "\n".join(
        [
            f"2026-03-31 01:19:42 | Learning handoff ACCEPTED | decision_id={decision_id} | lineage_source=outcome | realized_pnl=-885.0",
            f"2026-03-31 01:19:42 | Adaptive learning handoff | decision_id={decision_id} | ai_provider=ensemble | shadowed_from_decision_id=2a620bdf-53d5-45f5-8549-6353295471ed | provider_decisions=['deepseek-r1:8b'] | actual_outcome=SELL | performance_metric=-1.3322294144211952",
            "2026-03-31 01:19:42 | Adaptive weights updated | actual_outcome=SELL | performance_metric=-1.3322294144211952 | provider_decisions=['deepseek-r1:8b'] | weights_before={'llama3.1:8b': 0.25, 'deepseek-r1:8b': 0.25, 'gemma2:9b': 0.25, 'gemma3:4b': 0.25} | weights_after={'llama3.1:8b': 0.3333333333333333, 'deepseek-r1:8b': 0.0, 'gemma2:9b': 0.3333333333333333, 'gemma3:4b': 0.3333333333333333} | history_path=data/decisions/ensemble_history.json",
        ]
    )

    packet = collect_track0_proof_packet(
        data_dir=tmp_path,
        decision_id=decision_id,
        log_text=log_text,
    )

    assert packet.lower_chain_passed is True
    assert packet.adaptation_passed is True
    assert packet.ai_provider == "ensemble"
    assert packet.shadowed_from_decision_id == "2a620bdf-53d5-45f5-8549-6353295471ed"
    assert packet.accepted_handoff_timestamp == "2026-03-31 01:19:42"
    assert packet.realized_pnl == -885.0
    assert packet.provider_decisions_keys == ["deepseek-r1:8b"]
    assert packet.weights_before["deepseek-r1:8b"] == 0.25
    assert packet.weights_after["deepseek-r1:8b"] == 0.0
    assert packet.changed_weight_keys == [
        "deepseek-r1:8b",
        "gemma2:9b",
        "gemma3:4b",
        "llama3.1:8b",
    ]
    assert packet.history_path == "data/decisions/ensemble_history.json"
    assert packet.verdict == "pr4_proved"
    assert packet.verdict_reason == "weights_changed_after_ensemble_attributed_close"

    summary = render_packet_summary(packet)
    assert "adaptive weight delta seen: yes" in summary
    assert "adaptation_passed: True" in summary
    assert "verdict: pr4_proved" in summary


def test_collect_track0_proof_packet_classifies_adaptive_no_delta(tmp_path):
    decision_id = "adaptive-no-delta-1"
    _write_json(
        tmp_path / "decisions" / f"2026-03-31_{decision_id}.json",
        {
            "id": decision_id,
            "asset_pair": "BIP20DEC30CDE",
            "action": "SELL",
            "ai_provider": "ensemble",
            "recovery_metadata": {
                "product_id": "BIP-20DEC30-CDE",
                "shadowed_from_decision_id": "source-1",
                "shadowed_from_provider": "ensemble",
            },
        },
    )
    _write_json(
        tmp_path / "memory" / f"outcome_{decision_id}.json",
        {
            "decision_id": decision_id,
            "action": "SELL",
            "realized_pnl": -25.0,
        },
    )
    log_text = "\n".join(
        [
            f"2026-03-31 02:00:00 | Learning handoff ACCEPTED | decision_id={decision_id} | lineage_source=outcome | realized_pnl=-25.0",
            f"2026-03-31 02:00:00 | Adaptive learning handoff | decision_id={decision_id} | ai_provider=ensemble | shadowed_from_decision_id=source-1 | provider_decisions=['deepseek-r1:8b'] | actual_outcome=SELL | performance_metric=-0.1",
            "2026-03-31 02:00:00 | Adaptive weights updated | actual_outcome=SELL | performance_metric=-0.1 | provider_decisions=['deepseek-r1:8b'] | weights_before={'deepseek-r1:8b': 0.0, 'gemma2:9b': 0.3333333333333333} | weights_after={'deepseek-r1:8b': 0.0, 'gemma2:9b': 0.3333333333333333} | history_path=data/decisions/ensemble_history.json",
        ]
    )

    packet = collect_track0_proof_packet(
        data_dir=tmp_path,
        decision_id=decision_id,
        log_text=log_text,
    )

    assert packet.lower_chain_passed is True
    assert packet.adaptation_passed is False
    assert packet.verdict == "adaptive_no_delta"
    assert packet.verdict_reason == "weights_unchanged"


def test_collect_track0_proof_packet_ignores_interleaved_unrelated_weight_update(tmp_path):
    decision_id = "target-decision-1"
    _write_json(
        tmp_path / "decisions" / f"2026-03-31_{decision_id}.json",
        {
            "id": decision_id,
            "asset_pair": "BIP20DEC30CDE",
            "action": "SELL",
            "ai_provider": "ensemble",
            "recovery_metadata": {"product_id": "BIP-20DEC30-CDE"},
        },
    )
    _write_json(
        tmp_path / "memory" / f"outcome_{decision_id}.json",
        {
            "decision_id": decision_id,
            "action": "SELL",
            "realized_pnl": -100.0,
        },
    )
    log_text = "\n".join(
        [
            f"2026-03-31 03:00:00 | Learning handoff ACCEPTED | decision_id={decision_id} | lineage_source=outcome | realized_pnl=-100.0",
            f"2026-03-31 03:00:00 | Adaptive learning handoff | decision_id={decision_id} | ai_provider=ensemble | shadowed_from_decision_id=source-target | provider_decisions=['deepseek-r1:8b'] | actual_outcome=SELL | performance_metric=-1.0",
            "2026-03-31 03:00:01 | Adaptive learning handoff | decision_id=other-decision-2 | ai_provider=ensemble | shadowed_from_decision_id=source-other | provider_decisions=['gemma2:9b'] | actual_outcome=BUY | performance_metric=1.0",
            "2026-03-31 03:00:02 | Adaptive weights updated | actual_outcome=BUY | performance_metric=1.0 | provider_decisions=['gemma2:9b'] | weights_before={'gemma2:9b': 0.2} | weights_after={'gemma2:9b': 1.0} | history_path=data/decisions/ensemble_history.json",
        ]
    )

    packet = collect_track0_proof_packet(
        data_dir=tmp_path,
        decision_id=decision_id,
        log_text=log_text,
    )

    assert packet.lower_chain_passed is True
    assert packet.adaptation_passed is False
    assert packet.adaptive_handoff_line is not None
    assert packet.adaptive_weights_line is None
    assert packet.verdict == "lower_chain_only"
    assert packet.verdict_reason == "missing_adaptive_weights_line"
