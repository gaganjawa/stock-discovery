"""Opt-in incremental D3-03 ingestion. No price, permission or credential defaults."""
import argparse
import json
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from worker.real_market import MarketConfig, ingest_prices


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    config=MarketConfig.model_validate_json(args.config.read_text())
    with psycopg.connect(setting('DATABASE_URL'),autocommit=True,connect_timeout=5) as conn:
        result=ingest_prices(conn,config)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
