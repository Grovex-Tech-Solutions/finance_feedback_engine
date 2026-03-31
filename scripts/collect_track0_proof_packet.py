#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from finance_feedback_engine.monitoring.track0_audit import (
    collect_track0_proof_packet,
    render_packet_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect an FFE Track 0 proof packet for a decision id"
    )
    parser.add_argument("decision_id", help="Decision id to audit")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="FFE data directory (default: data)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional log file to scan for accepted/adaptive packet lines",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text summary",
    )
    args = parser.parse_args()

    log_text = ""
    if args.log_file:
        log_text = Path(args.log_file).read_text(encoding="utf-8")

    packet = collect_track0_proof_packet(
        data_dir=args.data_dir,
        decision_id=args.decision_id,
        log_text=log_text,
    )

    if args.json:
        json.dump(packet.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_packet_summary(packet))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
