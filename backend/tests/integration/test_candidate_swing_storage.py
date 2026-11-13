"""Invented stored Upstox-shaped data; disposable databases only."""
import os
from datetime import timedelta
import psycopg
import pytest
from fastapi.testclient import TestClient
from test_candidates import isolated_url,event,drain
from test_adjusted_research_storage import setup
from test_real_market import NOW
from stock_discovery_analysis import candidate_store as store,candidate_swing

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


@pytest.mark.parametrize('missing,lag,expected',[(False,0,1),(True,0,None),(False,2,None)])
def test_stored_candidate_to_current_price_review_api(isolated_url,tmp_path,monkeypatch,missing,lag,expected):
    from app.main import app
    from app.research import db
    from app import candidates
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,missing=missing,lag=lag)
        store.accept(conn,event(['TEST','UNKNOWN']));drain(conn)
        before=conn.execute('SELECT count(*) FROM discovery.candidate_research_runs').fetchone()
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    monkeypatch.setattr(candidates,'view_config',lambda:config)
    original=candidate_swing.page
    monkeypatch.setattr(candidate_swing,'page',lambda *a,**kw:original(*a,**kw,clock=lambda:NOW))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    try:
        client=TestClient(app);headers={'Authorization':'Bearer '+'o'*40};url='/v1/real-research/candidates/swing-review'
        assert client.get(url).status_code==401
        response=client.get(url,headers=headers)
        assert response.status_code==200 and response.headers['cache-control']=='no-store'
        data=response.json();rows={r['symbol']:r for r in data['rows']}
        assert rows['TEST']['swing_review']['rank']==expected
        assert rows['UNKNOWN']['swing_review']['rank'] is None
        assert data['provider_requests']==data['model_requests']==0
        assert client.get(url+'?limit=21',headers=headers).status_code==422
        # Every request rechecks current grants, even after a successful review.
        from pathlib import Path
        Path(config.sources.grant_file).write_text('[]')
        denied=client.get(url,headers=headers).json()['rows']
        assert all(r['swing_review']['rank'] is None for r in denied)
        assert all('technical' not in r['research'] for r in denied)
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert conn.execute('SELECT count(*) FROM discovery.candidate_research_runs').fetchone()==before
            assert conn.execute('SELECT count(*) FROM discovery.candidate_receivers').fetchone()==(0,)
    finally:app.dependency_overrides.clear()
