from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from stock_discovery_analysis import AnalysisMode, synthetic_recommendation


def run_once() -> dict[str, object]:
    """Execute one deterministic synthetic cycle; live ingestion is deferred."""
    return {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "job": "synthetic-heartbeat",
        "recommendation": synthetic_recommendation(AnalysisMode.LIVE),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Stock Discovery scheduled worker")
    parser.add_argument("--once", action="store_true", help="run one synthetic cycle and exit")
    parser.add_argument("--interval-seconds", type=int, default=60)
    args = parser.parse_args()

    while True:
        print(json.dumps(run_once(), sort_keys=True), flush=True)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
