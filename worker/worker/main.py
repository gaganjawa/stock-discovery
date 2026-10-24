from __future__ import annotations

import argparse
import json
import time
import os
from pathlib import Path
from stock_discovery_analysis.scheduling import ScheduleConfig, stamp
from stock_discovery_analysis.schedule_runner import tick
import psycopg
from stock_discovery_analysis.runtime import setting, validate_private
from stock_discovery_analysis.operations import heartbeat, event
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
    parser.add_argument('--synthetic-evidence', action='store_true', help='automatically ingest fictional filings/news; requires --synthetic-schedule')
    parser.add_argument('--synthetic-schedule', action='store_true', help='use fictional D3-04 acceptance adapter')
    parser.add_argument('--schedule-config', type=Path, help='versioned D3-04 calendar/policy JSON')
    parser.add_argument('--real-market-config', type=Path, help='opt-in REAL-001 price adapter config; downstream research stays blocked')
    parser.add_argument('--real-pilot-config',type=Path,help='bounded factual research using existing durable schedule')
    args = parser.parse_args()
    if args.real_pilot_config and (args.real_market_config or args.synthetic_schedule or args.synthetic_evidence):
        parser.error('real pilot cannot mix adapter modes')
    if args.real_market_config and (args.synthetic_schedule or args.synthetic_evidence):
        parser.error('real and synthetic adapters cannot be combined')
    if args.interval_seconds < 1:
        parser.error('interval must be positive')
    if args.synthetic_evidence and not args.synthetic_schedule:
        parser.error('--synthetic-evidence requires --synthetic-schedule')
    config = ScheduleConfig.model_validate_json(args.schedule_config.read_text()) if args.schedule_config else None
    if config and not setting('DATABASE_URL'):
        parser.error('scheduler requires DATABASE_URL')

    validate_private()
    schedule_handlers = None
    if args.synthetic_schedule:
        if config is None:
            parser.error('--synthetic-schedule requires --schedule-config')
        from stock_discovery_analysis.schedule_fixtures import handlers
        schedule_handlers = handlers(config)
        if args.synthetic_evidence:
            from stock_discovery_analysis.evidence_fixtures import scheduled_handlers
            schedule_handlers = scheduled_handlers(config)
    if args.real_market_config:
        from .real_market import handlers, MarketConfig
        if config is None: parser.error('--real-market-config requires --schedule-config')
        market = MarketConfig.model_validate_json(args.real_market_config.read_text())
        schedule_handlers = handlers(config, market)
    if args.real_pilot_config:
        from .real_pilot import handlers, PilotConfig
        if config is None:parser.error('--real-pilot-config requires --schedule-config')
        schedule_handlers=handlers(config,PilotConfig.model_validate_json(args.real_pilot_config.read_text()))
    while True:
        if config:
            with psycopg.connect(setting('DATABASE_URL'), autocommit=True, connect_timeout=5) as conn:
                result = tick(conn, config, handlers=schedule_handlers, clock=lambda: stamp(datetime.now(timezone.utc)),lease_seconds=900 if args.real_pilot_config else 120)
            print(json.dumps(result, sort_keys=True), flush=True)
        elif setting('DATABASE_URL') and not args.once:
            try:
                with psycopg.connect(setting('DATABASE_URL'),autocommit=True,connect_timeout=5) as conn:
                    row=conn.execute('SELECT dataset_version FROM research.datasets ORDER BY created_at DESC LIMIT 1').fetchone()
                    if row:
                        dataset=load_dataset(conn,row[0])
                        latest=max(c.provenance.available_at for c in dataset.candles)
                        enqueue(conn,'scan',{'dataset_version':dataset.version,'cutoff':latest.isoformat(),
                                            'scheduled_day':datetime.now(timezone.utc).date().isoformat()})
                    from stock_discovery_analysis.publication_store import run_next
                    from stock_discovery_analysis.paper_store import run_next as track_paper
                    result=track_paper(conn)
                    if result is None: result=run_next(conn,os.getenv('CODE_VERSION','local-unversioned'))
                    if result is None: result=run_job(conn,os.getenv('CODE_VERSION','local-unversioned'))
                heartbeat(True)
                if result: print(event("job_cycle", status=1 if result["status"]=="completed" else 0),flush=True)
            except Exception:
                heartbeat(False)
                print(event("worker_cycle_failed", status=0),flush=True)
        else:
            print(json.dumps(run_once(), sort_keys=True), flush=True)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
