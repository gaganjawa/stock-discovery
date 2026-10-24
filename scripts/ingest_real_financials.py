"""Opt-in structured numerical Upstox financials using existing D3-06 storage."""
import argparse
import json
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.revisions import Revision
from stock_discovery_analysis.evidence_storage import stored_stream
from stock_discovery_analysis.real_access import SourceConfig,source_access
from worker.providers.upstox import Upstox
from worker.providers.upstox_financials import ingest_financials


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--token-file',type=Path,required=True)
    parser.add_argument('--listing',required=True)
    parser.add_argument('--account-ref',required=True)
    args=parser.parse_args()
    access=source_access(SourceConfig.model_validate_json(args.sources.read_text()))
    with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as conn:
        # Same account lock as market ingestion prevents overlapping revision chains.
        lock='REAL-001:'+args.account_ref
        if not conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0]:
            raise RuntimeError('real_ingestion_busy')
        try:
            rows=conn.execute("SELECT payload FROM discovery.revisions WHERE source_id='upstox' AND listing_id=%s AND kind='instrument' ORDER BY sequence DESC LIMIT 1",(args.listing,)).fetchall()
            if not rows:raise ValueError('observed_instrument_required')
            identity=Revision.model_validate(rows[0][0])
            access.require(stored_stream(conn,identity.revision_id),('derive',))
            if identity.availability_basis!='observed':raise ValueError('observed_instrument_required')
            client=Upstox(access=access,token=args.token_file.read_text().strip())
            try:results=ingest_financials(conn,client,identity,args.account_ref)
            finally:client.close()
            print(json.dumps(results))
        finally:conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))

if __name__=='__main__':main()
