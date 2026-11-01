"""Read-only evaluation of persisted fictional data and immutable outcomes."""
from datetime import timedelta
from dataclasses import replace
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db
from test_rag_research import isolated_url
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest
from stock_discovery_analysis.service import freeze,reveal,scorecard,load_dataset


@pytest.fixture
def prepared(isolated_url,monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','synthetic-performance-owner-key-32-characters')
    with psycopg.connect(isolated_url,autocommit=True) as c:
        original=demo_dataset()
        # Explicit disposable high-volume fixture for the existing 1% liquidity
        # gate. The original dataset and its historical evaluations are untouched.
        d=replace(original,candles=tuple(replace(b,volume=b.volume*10) for b in original.candles));ingest(c,d)
        a=freeze(c,d,'SYN-ALPHA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),'performance-api')
        reveal(c,a['recommendation']['recommendation_id'])
        group=next(g['id'] for g in scorecard(c)['cohorts'] if g['code']=='performance-api')
        app.dependency_overrides[db]=lambda:c
        try:
            with TestClient(app) as client:
                client.headers['Authorization']='Bearer synthetic-performance-owner-key-32-characters'
                yield c,client,group
        finally:app.dependency_overrides.pop(db,None)


def test_authenticated_report_is_pinned_costed_read_only_and_reproducible(prepared):
    c,client,group=prepared
    before=c.execute('SELECT (SELECT count(*) FROM research.runs),(SELECT count(*) FROM research.trade_outcomes),'
        '(SELECT count(*) FROM paper.ledger)').fetchone()
    query={'cohort':group,'benchmark_instrument':'SYN-BETA'}
    response=client.get('/api/v1/scorecard',params=query)
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    r=response.json()['performance']
    assert r['status']=='available' and r['decisions']==1
    assert r['source_mode']=='synthetic' and r['missing_outcomes']==0
    assert r['benchmark']['status']=='available' and r['benchmark']['cost_version']=='SYN-daily-costs-v1'
    assert r['benchmark']['start_at']==r['start_at'] and r['benchmark']['end_at']==r['end_at']
    assert r['paired_comparison']['eligible_pairs']==0 and r['paired_comparison']['ai_performance'] is None
    assert r['walk_forward']['status']=='unavailable'
    assert client.get('/api/v1/scorecard',params=query).json()['performance']==r
    assert c.execute('SELECT (SELECT count(*) FROM research.runs),(SELECT count(*) FROM research.trade_outcomes),'
        '(SELECT count(*) FROM paper.ledger)').fetchone()==before
    client.headers.clear();assert client.get('/api/v1/scorecard',params=query).status_code==401


def test_missing_benchmark_and_unknown_selection_fail_explicitly(prepared):
    _,client,group=prepared
    assert client.get('/api/v1/scorecard',params={'cohort':group}).json()['performance']['benchmark']['reason']=='benchmark_not_selected'
    response=client.get('/api/v1/scorecard',params={'cohort':group,'benchmark_instrument':'NSE:INFY'})
    assert response.status_code==400 and response.json()['detail']=='Unknown synthetic benchmark'


def test_no_inference_or_holdout_access_and_missing_outcome_preserved(prepared):
    c,client,existing_group=prepared
    d=load_dataset(c,next(g['dataset'] for g in scorecard(c)['cohorts'] if g['id']==existing_group))
    freeze(c,d,'SYN-ALPHA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),'unevaluated-performance')
    group=next(g['id'] for g in scorecard(c)['cohorts'] if g['code']=='unevaluated-performance')
    response=client.get('/api/v1/scorecard',params={'cohort':group,'benchmark_instrument':'SYN-BETA'})
    r=response.json()['performance']
    assert r['missing_outcomes']==1 and r['status']=='unavailable'
    assert r['net_return'] is None and r['benchmark']['net_return'] is None
    assert r['risk']['sharpe'] is None and r['profit_factor'] is None
    assert c.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(0,)


def test_restricted_full_evidence_never_becomes_cached_performance(prepared):
    from uuid import uuid4
    from stock_discovery_analysis.historical_fixtures import seed,SOURCE
    from stock_discovery_analysis.historical_research import freeze_full
    from stock_discovery_analysis.grant_fences import restrict
    c,client,existing_group=prepared
    d=load_dataset(c,next(g['dataset'] for g in scorecard(c)['cohorts'] if g['id']==existing_group))
    seed(c,'SYN-ALPHA')
    freeze_full(c,d,'SYN-ALPHA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),'restricted-performance')
    group=next(g['id'] for g in scorecard(c)['cohorts'] if g['code']=='restricted-performance' and g['configuration']=='SYN-COMBINED-ABSTAIN-1')
    query={'cohort':group,'benchmark_instrument':'SYN-BETA'}
    r=client.get('/api/v1/scorecard',params=query)
    assert r.status_code==200 and r.json()['performance']['status']=='unavailable'
    with c.transaction(force_rollback=True):
        restrict(c,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked')
        denied=client.get('/api/v1/scorecard',params=query)
        assert denied.status_code==403 and 'performance' not in denied.json()
        assert SOURCE not in denied.text and 'revenue' not in denied.text
