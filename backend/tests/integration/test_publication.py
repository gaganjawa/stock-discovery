"""Real PostgreSQL orchestration, auth, revocation and immutable publication."""
import json
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db as api_db
from stock_discovery_analysis.publication_store import RunRequest,enqueue,run_next,run_status,read_artifact,now
from stock_discovery_analysis.publication_fixtures import SOURCE,access_for,inputs
from stock_discovery_analysis.rag_contracts import Query,RetrievalPolicy
from stock_discovery_analysis.rag_retrieval import retrieve
from test_rag_research import isolated_url


@pytest.fixture(scope='module')
def database(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        runs={}
        for profile in ('swing','short_term','long_term'):
            rid=enqueue(conn,RunRequest(horizon=profile),'test-'+profile,'test')
            assert run_next(conn,'test')['status']=='completed',run_status(conn,rid)
            runs[profile]=rid
        yield conn,runs,isolated_url


@pytest.fixture
def client(database,monkeypatch):
    conn,_,_=database
    monkeypatch.setenv('AUTH_TOKEN','test-discovery-owner-key-at-least-32-characters')
    monkeypatch.setenv('CODE_VERSION','test')
    def connection():yield conn
    app.dependency_overrides[api_db]=connection
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear()


HEADERS={'Authorization':'Bearer test-discovery-owner-key-at-least-32-characters'}


@pytest.mark.parametrize('profile',['swing','short_term','long_term'])
def test_published_horizon_modes_and_provenance(database,profile):
    conn,runs,_=database
    rows=conn.execute('SELECT payload,artifact FROM discovery.recommendations WHERE run_id=%s',(runs[profile],)).fetchall()
    assert len(rows)==15
    assert {r['action'] for r,a in rows}=={'BUY','WATCH','AVOID','INSUFFICIENT_EVIDENCE'}
    for r,a in rows:
        assert r['horizon']['profile']==profile and a['permissions']
        assert all(b['ends_at'][:19]<=r['information_cutoff_at'][:19] for b in a['input_manifest']['bars'])
        assert r['paper_admission']['quantity'] is None and r['cohort']['shadow']
        if r['cohort']['arm']!='quant' and r['instrument']['symbol'].endswith('READY'):
            assert r['research_status']=='succeeded' and a['research']['judge']
            assert a['citations'] and a['research']['validator']['semantic']=='supported'
        if r['instrument']['symbol'].endswith('WAITING'):assert r['candidate_origin']=='both' and r['event_ids']
    batch=conn.execute('SELECT payload FROM discovery.publication_batches WHERE run_id=%s',(runs[profile],)).fetchone()[0]
    for c in batch['coverage'].values():
        assert c['universe_total']==c['eligible']+c['ineligible']
        assert c['eligible']==c['screened']+c['unscreened']
        assert c['screened']==c['candidate']+c['noncandidate']
        assert c['candidate']==sum(c[k] for k in ('research_complete','research_pending','research_failed','research_not_selected'))


def test_api_auth_pagination_evidence_and_comparison(client):
    assert client.get('/v1/discovery').status_code==401
    assert client.post('/v1/discovery-runs',json={'horizon':'swing'}).status_code==401
    assert client.get('/v1/discovery?cursor=anything',headers=HEADERS).status_code==400
    first=client.get('/v1/discovery?limit=2',headers=HEADERS).json()
    assert first['recommendations'][0]['action']=='BUY'
    second=client.get('/v1/discovery',params={'limit':2,'cursor':first['next_cursor'],'batch_id':first['batch_id']},headers=HEADERS).json()
    assert not {r['recommendation_id'] for r in first['recommendations']} & {r['recommendation_id'] for r in second['recommendations']}
    assert second['batch_id']==first['batch_id']
    data=client.get('/v1/discovery?cohort=quant_rag',headers=HEADERS).json()
    r=next(r for r in data['recommendations'] if r['instrument']['symbol'].endswith('READY'))
    rid=r['recommendation_id']
    assert len(client.get('/v1/recommendations/'+rid+'/comparisons',headers=HEADERS).json()['recommendations'])==3
    evidence=client.get('/v1/recommendations/'+rid+'/evidence',headers=HEADERS).json()
    citation=evidence['citations'][0]
    response=client.get('/v1/evidence/'+citation['revision_id'],params={'recommendation_id':rid},headers=HEADERS)
    assert response.status_code==200 and response.json()['chunks']
    assert client.get('/v1/evidence/other',params={'recommendation_id':rid},headers=HEADERS).status_code==404
    assert client.get('/v1/discovery?mode=live_paper',headers=HEADERS).status_code==422
    assert client.get('/v1/coverage',headers=HEADERS).json()['coverage']['universe_total']==5


def test_idempotency_and_authentication(client,database):
    key=uuid4().hex;h={**HEADERS,'Idempotency-Key':key}
    first=client.post('/v1/discovery-runs',json={'horizon':'swing'},headers=h)
    assert first.status_code==202
    assert client.post('/v1/discovery-runs',json={'horizon':'swing'},headers=h).json()==first.json()
    assert client.post('/v1/discovery-runs',json={'horizon':'long_term'},headers=h).status_code==409
    assert client.post('/v1/discovery-runs',json={'horizon':'swing'},headers=HEADERS).status_code==422
    assert client.post('/v1/discovery-runs',json={'horizon':'swing','mode':'live_paper'},headers=h).status_code==422
    assert client.get(first.json()['status_url'],headers=HEADERS).json()['status']=='queued'
    database[0].execute("UPDATE discovery.publication_runs SET status='failed' WHERE run_id=%s",(first.json()['run_id'],))
    assert client.get('/v1/discovery',headers=HEADERS).json()['latest_run']['status']=='failed'
    assert client.get('/v1/discovery',headers=HEADERS).json()['recommendations']


def test_revoked_sources_block_all_stored_content(client,database):
    conn,runs,_=database
    rid=conn.execute('SELECT recommendation_id FROM discovery.recommendations WHERE run_id=%s LIMIT 1',(runs['swing'],)).fetchone()[0]
    with conn.transaction(force_rollback=True):
        conn.execute('INSERT INTO discovery.publication_source_controls VALUES (%s,true) ON CONFLICT (source_id) DO UPDATE SET revoked=true',(SOURCE,))
        for path in ('/v1/discovery','/v1/recommendations/'+rid,'/v1/recommendations/'+rid+'/evidence','/v1/recommendations/'+rid+'/comparisons'):
            response=client.get(path,headers=HEADERS)
            assert response.status_code==403 and 'source_permission_denied' in response.text
            assert 'Fictional' not in response.text


def test_immutable_rows_and_duplicate_queue(database):
    conn,runs,url=database
    with pytest.raises(psycopg.Error):conn.execute("UPDATE discovery.recommendations SET payload='{}'")
    with pytest.raises(psycopg.Error):conn.execute('DELETE FROM discovery.publication_batches')
    with pytest.raises(psycopg.Error):conn.execute("UPDATE discovery.publication_runs SET request='{}'")
    key=uuid4().hex
    def submit(_):
        with psycopg.connect(url,autocommit=True) as other:return enqueue(other,RunRequest(horizon='swing'),key,'test')
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(submit,range(2)))
    assert ids[0]==ids[1]
    conn.execute("UPDATE discovery.publication_runs SET status='failed' WHERE run_id=%s",(ids[0],))
    assert conn.execute('SELECT count(*) FROM discovery.publication_outbox').fetchone()[0]==3


def test_historical_cutoff_cannot_see_later_documents(database):
    conn,_,_=database;data,_=inputs('swing','ready')
    q=Query(issuer_id=data['instrument_id']+'-issuer',listing_id=data['instrument_id'],horizon='swing',mode='synthetic',
        cutoff_at='2025-06-23T10:01:00Z',text='earnings',categories=('annual_report',))
    b=retrieve(conn,q,RetrievalPolicy(),access=access_for(conn,now))
    assert not b.documents and not b.hits


def test_wrong_worker_version_fails_without_publication(database):
    conn,_,_=database
    rid=enqueue(conn,RunRequest(horizon='swing'),uuid4().hex,'different')
    assert run_next(conn,'test')['status']=='failed'
    assert run_status(conn,rid)['error_code']=='execution_version_mismatch'
    assert not conn.execute('SELECT 1 FROM discovery.publication_batches WHERE run_id=%s',(rid,)).fetchone()


def test_frozen_quant_reproduces_without_sources(database):
    from stock_discovery_analysis.publication import reproduce_quant
    conn,runs,_=database
    for profile in runs:
        a=conn.execute("SELECT artifact FROM discovery.recommendations WHERE run_id=%s AND cohort='quant' LIMIT 1",(runs[profile],)).fetchone()[0]
        assert reproduce_quant(a)==a['quantitative']


def test_source_failure_never_publishes_partial_batch(database):
    conn,_,_=database
    rid=enqueue(conn,RunRequest(horizon='swing'),uuid4().hex,'test')
    conn.execute('INSERT INTO discovery.publication_source_controls VALUES (%s,true) ON CONFLICT (source_id) DO UPDATE SET revoked=true',(SOURCE,))
    try:
        assert run_next(conn,'test')['status']=='failed'
        assert run_status(conn,rid)['error_code']=='source_unavailable'
        assert not conn.execute('SELECT 1 FROM discovery.publication_batches WHERE run_id=%s',(rid,)).fetchone()
    finally:conn.execute('UPDATE discovery.publication_source_controls SET revoked=false WHERE source_id=%s',(SOURCE,))


def test_budget_failure_keeps_independent_quant_cohort(database,monkeypatch):
    from stock_discovery_analysis import publication_store
    conn,_,_=database
    original=publication_store.research_candidate
    def exhausted(conn,run_id,data,issuer,cohort,access):
        if cohort!='quant':raise ValueError('budget exhausted')
        return original(conn,run_id,data,issuer,cohort,access)
    monkeypatch.setattr(publication_store,'research_candidate',exhausted)
    rid=enqueue(conn,RunRequest(horizon='swing'),uuid4().hex,'test')
    assert run_next(conn,'test')['status']=='completed'
    rows=[r[0] for r in conn.execute('SELECT payload FROM discovery.recommendations WHERE run_id=%s',(rid,))]
    assert any(r['action']=='BUY' and r['cohort']['arm']=='quant' for r in rows)
    for r in rows:
        if r['cohort']['arm']!='quant':
            assert r['action']=='INSUFFICIENT_EVIDENCE' and r['research_status']=='unavailable'
            assert 'research_budget_exhausted' in r['action_reason_codes']


def test_failure_mid_batch_has_no_partial_publication(database,monkeypatch):
    from stock_discovery_analysis import publication_store
    conn,_,_=database
    original=publication_store.build_artifact;calls=[]
    def broken(**kwargs):
        calls.append(kwargs['cohort'])
        if len(calls)==4:raise ValueError('synthetic mid-batch fault')
        return original(**kwargs)
    monkeypatch.setattr(publication_store,'build_artifact',broken)
    rid=enqueue(conn,RunRequest(horizon='swing'),uuid4().hex,'test')
    assert run_next(conn,'test')['status']=='failed' and len(calls)==4
    assert not conn.execute('SELECT 1 FROM discovery.recommendations WHERE run_id=%s',(rid,)).fetchone()
    assert not conn.execute('SELECT 1 FROM discovery.publication_outbox WHERE run_id=%s',(rid,)).fetchone()
