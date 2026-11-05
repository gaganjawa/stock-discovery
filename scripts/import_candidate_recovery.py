"""STK-094 explicit exceptional CSV recovery; print counts before writing."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import psycopg
from stock_discovery_analysis.chartink import Scanner
from stock_discovery_analysis.candidate_csv import events
from stock_discovery_analysis.candidate_store import accept
from stock_discovery_analysis.runtime import setting


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv',type=Path)
    parser.add_argument('--symbol-column',default='Symbol')
    parser.add_argument('--date-column',default='Date',help='ISO session dates; mapping is explicit')
    parser.add_argument('--date-format',default='%Y-%m-%d',help='Use %%d-%%m-%%Y for the supplied historical export')
    parser.add_argument('--session',help='ISO session for a single-day export')
    parser.add_argument('--apply-recovery',action='store_true',help='persist unverified recovery events; default is counts only')
    args=parser.parse_args()
    scanner=Scanner.model_validate_json(Path(os.environ['CHARTINK_SCANNER_CONFIG']).read_text())
    with args.csv.open('rb') as f:raw=f.read(10*1024*1024+1)
    incoming,summary=events(raw,scanner,datetime.now(timezone.utc),symbol_column=args.symbol_column,date_column=args.date_column,session=args.session,date_format=args.date_format)
    if args.apply_recovery:
        with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as conn:
            # Atomic whole-file import; replay can safely recover an interrupted CLI.
            with conn.transaction():
                results=[accept(conn,e) for e in incoming]
        summary['events_stored']=sum(not r['duplicate'] for r in results)
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
