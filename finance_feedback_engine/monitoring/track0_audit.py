from __future__ import annotations

import ast
import glob
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class Track0ProofPacket:
    decision_id: str
    decision_path: Optional[str]
    outcome_path: Optional[str]
    product: Optional[str]
    asset_pair: Optional[str]
    ai_provider: Optional[str]
    shadowed_from_decision_id: Optional[str]
    lineage_source: Optional[str]
    accepted_handoff_timestamp: Optional[str]
    accepted_handoff_line: Optional[str]
    adaptive_handoff_line: Optional[str]
    adaptive_weights_line: Optional[str]
    realized_pnl: Optional[float]
    provider_decisions_keys: Optional[list[str]]
    weights_before: Optional[dict[str, float]]
    weights_after: Optional[dict[str, float]]
    changed_weight_keys: Optional[list[str]]
    history_path: Optional[str]
    verdict: str
    verdict_reason: str
    lower_chain_passed: bool
    adaptation_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_decision_path(data_dir: str | Path, decision_id: str) -> Optional[Path]:
    root = Path(data_dir)
    matches = sorted(root.glob(f"decisions/*_{decision_id}.json"))
    return matches[-1] if matches else None


def find_outcome_path(data_dir: str | Path, decision_id: str) -> Optional[Path]:
    root = Path(data_dir)
    direct = root / "memory" / f"outcome_{decision_id}.json"
    if direct.exists():
        return direct
    for path in sorted(root.glob("memory/outcome_*.json")):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        if payload.get("decision_id") == decision_id:
            return path
    return None


def _find_line(log_text: str, needle: str, decision_id: str) -> Optional[str]:
    for line in log_text.splitlines():
        if needle in line and decision_id in line:
            return line.strip()
    return None


def _find_following_line(
    log_text: str,
    *,
    anchor_needle: str,
    anchor_decision_id: str,
    target_needle: str,
    stop_needles: tuple[str, ...] = (),
) -> Optional[str]:
    lines = log_text.splitlines()
    anchor_index = None
    for idx, line in enumerate(lines):
        if anchor_needle in line and anchor_decision_id in line:
            anchor_index = idx
            break
    if anchor_index is None:
        return None
    for line in lines[anchor_index + 1 :]:
        if any(stop in line for stop in stop_needles):
            return None
        if target_needle in line:
            return line.strip()
    return None


def _extract_mapping(line: Optional[str], key: str) -> Optional[dict[str, float]]:
    if not line or f"{key}=" not in line:
        return None
    tail = line.split(f"{key}=", 1)[1]
    start = tail.find("{")
    if start == -1:
        return None
    depth = 0
    end = None
    for idx, ch in enumerate(tail[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    if end is None:
        return None
    try:
        return ast.literal_eval(tail[start:end])
    except Exception:
        return None


def _extract_scalar(line: Optional[str], key: str) -> Optional[str]:
    if not line or f"{key}=" not in line:
        return None
    tail = line.split(f"{key}=", 1)[1]
    return tail.split(" | ", 1)[0].strip() or None


def _extract_timestamp(line: Optional[str]) -> Optional[str]:
    if not line:
        return None
    parts = line.split(" | ", 1)
    return parts[0].strip() if parts else None


def _extract_float(line: Optional[str], key: str) -> Optional[float]:
    scalar = _extract_scalar(line, key)
    if scalar is None:
        return None
    try:
        return float(scalar)
    except (TypeError, ValueError):
        return None


def _extract_provider_decisions_keys(line: Optional[str]) -> Optional[list[str]]:
    if not line or "provider_decisions=" not in line:
        return None
    tail = line.split("provider_decisions=", 1)[1]
    start = tail.find("[")
    end = tail.find("]", start + 1)
    if start == -1 or end == -1:
        return None
    try:
        parsed = ast.literal_eval(tail[start : end + 1])
    except Exception:
        return None
    return list(parsed) if isinstance(parsed, list) else None


def _changed_weight_keys(
    before: Optional[dict[str, float]], after: Optional[dict[str, float]]
) -> Optional[list[str]]:
    if before is None or after is None:
        return None
    keys = sorted(set(before) | set(after))
    changed = [key for key in keys if before.get(key) != after.get(key)]
    return changed


def _derive_verdict(
    *,
    decision_path: Optional[Path],
    outcome_path: Optional[Path],
    accepted_handoff_line: Optional[str],
    adaptive_handoff_line: Optional[str],
    adaptive_weights_line: Optional[str],
    weights_before: Optional[dict[str, float]],
    weights_after: Optional[dict[str, float]],
) -> tuple[str, str]:
    if decision_path is None:
        return ("incomplete", "missing_decision_artifact")
    if outcome_path is None:
        return ("incomplete", "missing_outcome_artifact")
    if not accepted_handoff_line:
        return ("incomplete", "missing_accepted_handoff")
    if not adaptive_handoff_line:
        return ("lower_chain_only", "missing_adaptive_handoff")
    if not adaptive_weights_line:
        return ("lower_chain_only", "missing_adaptive_weights_line")
    if weights_before is None or weights_after is None:
        return ("lower_chain_only", "missing_weight_payload")
    if weights_before == weights_after:
        return ("adaptive_no_delta", "weights_unchanged")
    return ("pr4_proved", "weights_changed_after_ensemble_attributed_close")


def collect_track0_proof_packet(
    *,
    data_dir: str | Path,
    decision_id: str,
    log_text: str = "",
) -> Track0ProofPacket:
    decision_path = find_decision_path(data_dir, decision_id)
    outcome_path = find_outcome_path(data_dir, decision_id)

    decision_payload: dict[str, Any] = _read_json(decision_path) if decision_path else {}
    recovery_metadata = decision_payload.get("recovery_metadata") or {}

    accepted_handoff_line = _find_line(log_text, "Learning handoff ACCEPTED", decision_id)
    adaptive_handoff_line = _find_line(log_text, "Adaptive learning handoff", decision_id)
    adaptive_weights_line = _find_line(log_text, "Adaptive weights updated", decision_id)
    if adaptive_weights_line is None and adaptive_handoff_line is not None:
        adaptive_weights_line = _find_following_line(
            log_text,
            anchor_needle="Adaptive learning handoff",
            anchor_decision_id=decision_id,
            target_needle="Adaptive weights updated",
            stop_needles=(
                "Adaptive learning handoff",
                "Learning handoff ACCEPTED",
                "Learning handoff ATTEMPT",
            ),
        )

    weights_before = _extract_mapping(adaptive_weights_line, "weights_before")
    weights_after = _extract_mapping(adaptive_weights_line, "weights_after")
    history_path = _extract_scalar(adaptive_weights_line, "history_path")
    lineage_source = _extract_scalar(accepted_handoff_line, "lineage_source")
    accepted_handoff_timestamp = _extract_timestamp(accepted_handoff_line)
    realized_pnl = _extract_float(accepted_handoff_line, "realized_pnl")
    provider_decisions_keys = _extract_provider_decisions_keys(adaptive_handoff_line)
    changed_weight_keys = _changed_weight_keys(weights_before, weights_after)

    verdict, verdict_reason = _derive_verdict(
        decision_path=decision_path,
        outcome_path=outcome_path,
        accepted_handoff_line=accepted_handoff_line,
        adaptive_handoff_line=adaptive_handoff_line,
        adaptive_weights_line=adaptive_weights_line,
        weights_before=weights_before,
        weights_after=weights_after,
    )

    lower_chain_passed = bool(decision_path and outcome_path and accepted_handoff_line)
    adaptation_passed = verdict == "pr4_proved"

    return Track0ProofPacket(
        decision_id=decision_id,
        decision_path=str(decision_path) if decision_path else None,
        outcome_path=str(outcome_path) if outcome_path else None,
        product=(decision_payload.get("recovery_metadata") or {}).get("product_id"),
        asset_pair=decision_payload.get("asset_pair"),
        ai_provider=decision_payload.get("ai_provider"),
        shadowed_from_decision_id=recovery_metadata.get("shadowed_from_decision_id"),
        lineage_source=lineage_source,
        accepted_handoff_timestamp=accepted_handoff_timestamp,
        accepted_handoff_line=accepted_handoff_line,
        adaptive_handoff_line=adaptive_handoff_line,
        adaptive_weights_line=adaptive_weights_line,
        realized_pnl=realized_pnl,
        provider_decisions_keys=provider_decisions_keys,
        weights_before=weights_before,
        weights_after=weights_after,
        changed_weight_keys=changed_weight_keys,
        history_path=history_path,
        verdict=verdict,
        verdict_reason=verdict_reason,
        lower_chain_passed=lower_chain_passed,
        adaptation_passed=adaptation_passed,
    )


def render_packet_summary(packet: Track0ProofPacket) -> str:
    lines = [
        "Track 0 packet summary",
        f"- decision_id: {packet.decision_id}",
        f"- product: {packet.product}",
        f"- asset_pair: {packet.asset_pair}",
        f"- ai_provider: {packet.ai_provider}",
        f"- shadowed_from_decision_id: {packet.shadowed_from_decision_id}",
        f"- decision artifact: {packet.decision_path}",
        f"- outcome artifact: {packet.outcome_path}",
        f"- lineage_source: {packet.lineage_source}",
        f"- accepted_handoff_timestamp: {packet.accepted_handoff_timestamp}",
        f"- realized_pnl: {packet.realized_pnl}",
        f"- accepted close: {'yes' if packet.accepted_handoff_line else 'no'}",
        f"- adaptive handoff seen: {'yes' if packet.adaptive_handoff_line else 'no'}",
        f"- adaptive weight delta seen: {'yes' if packet.adaptation_passed else 'no'}",
        f"- provider_decisions_keys: {packet.provider_decisions_keys}",
        f"- weights_before: {packet.weights_before}",
        f"- weights_after: {packet.weights_after}",
        f"- changed_weight_keys: {packet.changed_weight_keys}",
        f"- history_path: {packet.history_path}",
        f"- verdict: {packet.verdict}",
        f"- verdict_reason: {packet.verdict_reason}",
        f"- lower_chain_passed: {packet.lower_chain_passed}",
        f"- adaptation_passed: {packet.adaptation_passed}",
    ]
    return "\n".join(lines)
