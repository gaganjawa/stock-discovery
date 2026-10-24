"""Run configured, permitted real filings and local RAG; no automatic grants."""
import argparse
import json
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from worker.real_evidence import EvidenceConfig, run


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    config=EvidenceConfig.model_validate_json(args.config.read_text())
    with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as conn:
        result=run(conn,config)
    # Content remains in rights-aware storage; console emits only state/identifiers.
    print(json.dumps({'status':result['status'],'publication':result['publication'],
        'runs':[{'run_id':r['run_id'],'status':r['result']['status']} for r in result['research']]}))

if __name__=='__main__':main()
