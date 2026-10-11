from __future__ import annotations

import argparse
import json
import time
import os
import psycopg
from stock_discovery_analysis.jobs import run_job,enqueue
from stock_discovery_analysis.service import load_dataset
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
    parser.add_argument("--interval-seconds", type=int, default=5)
    args = parser.parse_args()

    while True:
        if os.getenv('DATABASE_URL') and not args.once:
            try:
                with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True) as conn:
                    row=conn.execute('SELECT dataset_version FROM research.datasets ORDER BY created_at DESC LIMIT 1').fetchone()
                    if row:
                        dataset=load_dataset(conn,row[0])
                        latest=max(c.provenance.available_at for c in dataset.candles)
                        enqueue(conn,'scan',{'dataset_version':dataset.version,'cutoff':latest.isoformat(),
                                            'scheduled_day':datetime.now(timezone.utc).date().isoformat()})
                    result=run_job(conn,os.getenv('CODE_VERSION','local-unversioned'))
                if result: print(json.dumps(result,sort_keys=True),flush=True)
            except psycopg.Error:
                print(json.dumps({'status':'database_unavailable_or_unmigrated'}),flush=True)
        else:
            print(json.dumps(run_once(), sort_keys=True), flush=True)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
