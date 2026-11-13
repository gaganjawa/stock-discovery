"""Disposable hosted rehearsal only: fabricated stored evidence, no network calls.

Run by stk099_rehearsal with integration fixture sources mounted read-only. Never
run against production. All inserted rows and role changes roll back together.
"""
import json
from pathlib import Path
import tempfile
import psycopg
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.candidate_research import analyze
from test_adjusted_research_storage import setup
from test_real_market import NOW


def main():
    # Rehearsal's owner_url points at its unique, disposable Compose database.
    with psycopg.connect(setting('DATABASE_URL'),dbname='stk_real001_private',autocommit=True) as conn:
        with conn.transaction(),tempfile.TemporaryDirectory() as tmp:
            config,listing=setup(conn,Path(tmp))
            for role in ('stk_runtime','stk_candidate_worker'):
                conn.execute('SET LOCAL ROLE '+role)
                actual=ViewConfig.model_validate_json(Path('/run/private/view.json').read_text())
                assert json.loads(Path(actual.sources.grant_file).read_text())==[]
                permitted=analyze(conn,config,'TEST','2026-11-12',clock=lambda:NOW)
                assert permitted['status']=='completed' and permitted['market_data']['bars']==30
                assert permitted['technical']['metrics']['sma20']=='105'
                denied=analyze(conn,actual,'TEST','2026-11-12',clock=lambda:NOW)
                assert denied['reasons']==['source_permission_denied']
                assert denied['source_revision_ids']==[]
                for result in (permitted,denied):
                    assert result['acquisition']['provider_requests']==result['acquisition']['model_requests']==0
                conn.execute('RESET ROLE')
            conn.execute('ROLLBACK')
    print(json.dumps(dict(stored_research_bars=30,permission_denial_verified=True,roles=['stk_runtime','stk_candidate_worker'],provider_requests=0,model_requests=0)))


if __name__=='__main__':main()
