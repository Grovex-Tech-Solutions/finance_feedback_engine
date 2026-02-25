#!/usr/bin/env python3
"""Automated intent cycling for FFE Phase 4D progress.

Reads configured asset pairs from /api/v1/bot/status and repeatedly calls
/api/v1/decisions in round-robin order.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def http_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 180) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def get_asset_pairs(base_url: str) -> list[str]:
    status = http_json(f"{base_url}/api/v1/bot/status")
    pairs = status.get("config", {}).get("asset_pairs", [])
    if not pairs:
        raise RuntimeError("No asset pairs found at /api/v1/bot/status config.asset_pairs")
    return pairs


def run_cycle(base_url: str, total_intents: int, start_count: int, pause_seconds: float, provider: str) -> dict[str, Any]:
    pairs = get_asset_pairs(base_url)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    error_patterns: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()

    start_ts = datetime.now(timezone.utc)

    for i in range(total_intents):
        pair = pairs[i % len(pairs)]
        payload = {
            "asset_pair": pair,
            "provider": provider,
            "include_sentiment": True,
            "include_macro": True,
        }

        intent_no = start_count + i + 1
        try:
            response = http_json(f"{base_url}/api/v1/decisions", method="POST", payload=payload, timeout=240)
            decision_id = response.get("decision_id")
            action = response.get("action", "UNKNOWN")
            confidence = response.get("confidence")

            successes.append(
                {
                    "intent_number": intent_no,
                    "asset_pair": pair,
                    "decision_id": decision_id,
                    "action": action,
                    "confidence": confidence,
                }
            )
            action_counts[action] += 1
            pair_counts[pair] += 1
            print(f"[{i+1}/{total_intents}] OK {pair} -> {action} (confidence={confidence}, decision_id={decision_id})", flush=True)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = str(e)
            key = f"HTTP {e.code}"
            error_patterns[key] += 1
            failures.append({"intent_number": intent_no, "asset_pair": pair, "error": key, "detail": err_body})
            print(f"[{i+1}/{total_intents}] FAIL {pair} -> {key}", flush=True)
        except Exception as e:
            key = type(e).__name__
            error_patterns[key] += 1
            failures.append({"intent_number": intent_no, "asset_pair": pair, "error": key, "detail": str(e)})
            print(f"[{i+1}/{total_intents}] FAIL {pair} -> {key}: {e}", flush=True)

        if pause_seconds > 0 and i < total_intents - 1:
            time.sleep(pause_seconds)

    end_ts = datetime.now(timezone.utc)

    return {
        "base_url": base_url,
        "provider": provider,
        "asset_pairs": pairs,
        "start_count": start_count,
        "target_total": 300,
        "requested_this_run": total_intents,
        "processed_this_run": len(successes) + len(failures),
        "successful_this_run": len(successes),
        "failed_this_run": len(failures),
        "estimated_cumulative_after_run": start_count + len(successes) + len(failures),
        "phase4d_remaining_after_run": max(0, 300 - (start_count + len(successes) + len(failures))),
        "action_counts": dict(action_counts),
        "pair_counts": dict(pair_counts),
        "error_patterns": dict(error_patterns),
        "successes": successes,
        "failures": failures,
        "started_at_utc": start_ts.isoformat(),
        "ended_at_utc": end_ts.isoformat(),
        "duration_seconds": (end_ts - start_ts).total_seconds(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run automated intent cycling against FFE API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=20, help="Number of intents to process this run")
    parser.add_argument("--start-count", type=int, default=2, help="Existing processed intents before this run")
    parser.add_argument("--pause", type=float, default=0.5, help="Pause in seconds between intent requests")
    parser.add_argument("--provider", default="ensemble", help="Decision provider")
    parser.add_argument("--report-path", default="", help="Optional explicit report output path")
    args = parser.parse_args()

    report = run_cycle(
        base_url=args.base_url,
        total_intents=args.count,
        start_count=args.start_count,
        pause_seconds=args.pause,
        provider=args.provider,
    )

    if args.report_path:
        report_path = Path(args.report_path)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path("scripts") / f"intent_cycle_report_{ts}.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    print(json.dumps({
        "successful_this_run": report["successful_this_run"],
        "failed_this_run": report["failed_this_run"],
        "estimated_cumulative_after_run": report["estimated_cumulative_after_run"],
        "phase4d_remaining_after_run": report["phase4d_remaining_after_run"],
        "error_patterns": report["error_patterns"],
        "report_path": str(report_path),
    }, indent=2))

    return 0 if report["failed_this_run"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
