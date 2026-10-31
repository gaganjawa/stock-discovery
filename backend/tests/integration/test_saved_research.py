"""Saved replay discovery and existing worker batches; all data fictional."""
import os
from datetime import timedelta
from uuid import uuid4
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest
from stock_discovery_analysis.service import freeze,read_frozen,saved_analyses
from stock_discovery_analysis.historical_fixtures import seed,SOURCE
from stock_discovery_analysis.historical_research import freeze_full
from stock_discovery_analysis.grant_fences import restrict
from stock_discovery_analysis.jobs import enqueue,run_job,execution_versions

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')
@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()

def prepare(c):
    d=demo_dataset();ingest(c,d);seed(c,'SYN-ALPHA')
    cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    full=freeze_full(c,d,'SYN-ALPHA',cutoff,'saved-test')
    freeze(c,d,'SYN-BETA',cutoff,'saved-test')
    freeze_full(c,d,'SYN-ALPHA',d.calendar.sessions[59].closes_at+timedelta(minutes=1),'saved-test')
    return d,full

def test_pagination_filtering_stable_metadata_and_no_future_outcome_leak(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,_=prepare(c);before=c.execute('SELECT count(*) FROM research.runs').fetchone()
        ids=[];cursor=None
        for _ in range(3):
            page=saved_analyses(c,dataset=d.version,before=cursor,limit=2)
            assert page==saved_analyses(c,dataset=d.version,before=cursor,limit=2)
            assert page['evaluation']['paired_sample_size']==0 and page['evaluation']['ai_performance'] is None
            assert all('candles' not in r and 'financial_facts' not in r for r in page['runs'])
            ids += [r['recommendation_id'] for r in page['runs']];cursor=page['next_cursor']
        assert cursor is None and len(set(ids))==5
        assert len(saved_analyses(c,instrument='SYN-ALPHA')['runs'])==4
        assert len(saved_analyses(c,instrument='SYN-BETA')['runs'])==1
        assert not saved_analyses(c,dataset='unknown')['runs']
        with pytest.raises(ValueError):saved_analyses(c,before='unknown')
        with pytest.raises(ValueError):saved_analyses(c,limit=51)
        assert c.execute('SELECT count(*) FROM research.runs').fetchone()==before

def test_revocation_redacts_full_run_while_unrelated_baseline_remains_usable(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,a=prepare(c);restrict(c,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked')
        page=saved_analyses(c)
        denied=[r for r in page['runs'] if r['availability']!='available']
        assert len(denied)==2
        assert all(set(r)=={'recommendation_id','availability'} for r in denied)
        assert any(r.get('instrument_id')=='SYN-BETA' for r in page['runs'])
        assert page['evaluation']['counts']['restricted_or_unavailable']==2
        with pytest.raises(PermissionError):read_frozen(c,a['recommendation']['recommendation_id'])

def test_authenticated_saved_history_and_open_rehide_recorded_outcomes(isolated_url,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.research import db
    from stock_discovery_analysis.service import reveal
    monkeypatch.setenv('AUTH_TOKEN','h'*40)
    with psycopg.connect(isolated_url,autocommit=True) as c:
        _,a=prepare(c);rid=a['recommendation']['recommendation_id'];reveal(c,rid)
        app.dependency_overrides[db]=lambda:c
        try:
            client=TestClient(app);assert client.get('/api/v1/analysis').status_code==401
            client.headers['Authorization']='Bearer '+'h'*40
            page=client.get('/api/v1/analysis?limit=2');assert page.status_code==200,page.text
            assert page.headers['cache-control']=='no-store'
            assert client.get('/api/v1/analysis?limit=51').status_code==422
            assert client.get('/api/v1/analysis?before=unknown').status_code==400
            opened=client.get('/api/v1/analysis/'+rid).json()
            assert len(opened['candles'])==40 and 'trade' not in opened and 'comparison' not in opened
            assert opened['historical_snapshot']==a['historical_snapshot']
        finally:app.dependency_overrides.pop(db,None)

def test_full_financial_batch_uses_existing_jobs_across_dates_and_instruments(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d=demo_dataset();ingest(c,d);jobs=[]
        for n in (39,59):
            for instrument in ('SYN-ALPHA','SYN-BETA'):
                payload=dict(execution_versions('batch-test'),dataset_version=d.version,instrument_id=instrument,
                    cutoff=(d.calendar.sessions[n].closes_at+timedelta(minutes=1)).isoformat(),include_financial=True)
                jid=enqueue(c,'replay',payload);assert enqueue(c,'replay',payload)==jid;jobs.append(jid)
        for _ in jobs:assert run_job(c,'batch-test')['status']=='completed'
        assert run_job(c,'batch-test') is None
        assert c.execute("SELECT count(*) FROM research.jobs WHERE attempts=1 AND status='completed'").fetchone()==(4,)
        assert c.execute('SELECT count(*) FROM research.runs').fetchone()==(8,)
        assert c.execute('SELECT count(*) FROM research.trade_outcomes').fetchone()==(8,)
        page=saved_analyses(c);assert page['evaluation']['paired_sample_size']==0
        assert page['evaluation']['counts']['unqualified_combined']==4
        assert c.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(0,)
        assert c.execute('SELECT count(*) FROM discovery.recommendations').fetchone()==(0,)

def test_metadata_rechecks_earlier_source_after_all_later_locks(isolated_url,monkeypatch):
    import stock_discovery_analysis.historical_research as module
    original=module.authorize_snapshot;calls={}
    def expired(c,snapshot):
        original(c,snapshot);key=snapshot['snapshot_id'];calls[key]=calls.get(key,0)+1
        if calls[key]>1:raise PermissionError('synthetic_expiry_after_later_dependency')
    with psycopg.connect(isolated_url,autocommit=True) as c:
        prepare(c);monkeypatch.setattr(module,'authorize_snapshot',expired)
        page=saved_analyses(c)
        assert page['evaluation']['counts']['restricted_or_unavailable']==2
        assert not any(r.get('cohort')=='unqualified_combined' for r in page['runs'])

@pytest.mark.parametrize('flag',['true','false',1,None])
def test_worker_rejects_malformed_financial_flag_without_creating_decisions(isolated_url,flag):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d=demo_dataset();ingest(c,d)
        payload=dict(execution_versions('bad-option'),dataset_version=d.version,instrument_id='SYN-ALPHA',
            cutoff=(d.calendar.sessions[39].closes_at+timedelta(minutes=1)).isoformat(),include_financial=flag)
        enqueue(c,'replay',payload);r=run_job(c,'bad-option')
        assert r['status']=='retry_or_failed' and r['error_code']=='ValueError'
        assert c.execute('SELECT count(*) FROM research.runs').fetchone()==(0,)
