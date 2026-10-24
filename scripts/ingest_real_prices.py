"""Opt-in incremental D3-03 ingestion. No price, permission or credential defaults."""
import argparse
import json
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from worker.real_market import MarketConfig, ingest_prices, ingest_calendar, ingest_configured_financials


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--refresh-calendar',action='store_true',help='Observe dated sessions first; requires lookback_days <= 44')
    args=parser.parse_args()
    config=MarketConfig.model_validate_json(args.config.read_text())
    with psycopg.connect(setting('DATABASE_URL'),autocommit=True,connect_timeout=5) as conn:
        calendar=ingest_calendar(conn,config) if args.refresh_calendar or config.refresh_calendar else None
        result=ingest_prices(conn,config)
        if calendar:result['calendar_refresh']=calendar
        if config.financial_statements and result['status']!='busy':
            result['financials']=ingest_configured_financials(conn,config,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
