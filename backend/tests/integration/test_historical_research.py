"""Full replay with invented disclosures, never real financial-quality evidence."""
import json,os
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest
from stock_discovery_analysis.historical_fixtures import seed,SOURCE,ACCOUNT
from stock_discovery_analysis.historical_research import freeze_full,authorize_snapshot,comparison
from stock_discovery_analysis.service import freeze,read_frozen,reveal
from stock_discovery_analysis.grant_fences import restrict
from stock_discovery_contracts.v2 import digest

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')
@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()

def prepare(conn):
    d=demo_dataset();ingest(conn,d);seed(conn,'SYN-ALPHA')
    return d,d.calendar.sessions[39].closes_at+timedelta(minutes=1)


def test_full_freeze_is_asof_immutable_and_restart_reveal_preserves_snapshot(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);a=freeze_full(c,d,'SYN-ALPHA',cutoff,'test');s=a['historical_snapshot']
        assert a['recommendation']['action']=='INSUFFICIENT_EVIDENCE' and a['recommendation']['execution'] is None
        assert len(s['documents'])==2 and s['financial_facts'] and s['financial_calculations']
        assert all('v2' not in p['revision_id'] and '2025-v1' not in p['revision_id'] for p in s['source_revisions'])
        assert len(s['technical_inputs']['bars'])==40 and s['ai'] is None
        assert 'ai_research_not_frozen' in s['missing_evidence'] and not s['financial_qualified']
        assert freeze_full(c,d,'SYN-ALPHA',cutoff,'test')==a
        rid=a['recommendation']['recommendation_id'];before=deepcopy(a)
        with pytest.raises(psycopg.Error):
            with c.transaction():c.execute("UPDATE research.runs SET manifest='{}'::jsonb WHERE run_id=%s",(a['recommendation']['run_id'],))
    with psycopg.connect(isolated_url,autocommit=True) as c:
        assert read_frozen(c,rid)==before
        out=reveal(c,rid);baseline=reveal(c,a['baseline_recommendation_id'])
        assert out['trade']['status']=='not_applicable' and baseline['trade']['status'] in ('closed','ambiguous','no_entry','cancelled')
        assert baseline['evaluator_version']=='daily-replay-v1'
        assert comparison(a,baseline)['paired_sample_size']==0 and comparison(a,baseline)['ai_performance'] is None
        assert read_frozen(c,rid)==before and reveal(c,rid)==out


def test_later_correction_uses_new_version_without_rewriting_earlier_freeze(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);old=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        new=freeze_full(c,d,'SYN-ALPHA',d.calendar.sessions[59].closes_at+timedelta(minutes=1),'test')
        assert any(p['revision_id'].endswith('2024-v2') for p in new['historical_snapshot']['source_revisions'])
        assert all(not p['revision_id'].endswith('2024-v2') for p in old['historical_snapshot']['source_revisions'])
        assert read_frozen(c,old['recommendation']['recommendation_id'])==old


@pytest.mark.parametrize('kind',['provider','account','grant'])
def test_revocation_blocks_frozen_read_reveal_and_new_freeze(isolated_url,kind):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);a=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        kw={} if kind=='provider' else dict(account_ref=ACCOUNT)
        if kind=='grant':kw.update(grant_id='SYN-replay-grant',grant_version='fixture-1')
        restrict(c,request_id=uuid4(),kind=kind,source_id=SOURCE,reason='revoked',**kw)
        for operation in (lambda:read_frozen(c,a['recommendation']['recommendation_id']),
                          lambda:reveal(c,a['recommendation']['recommendation_id']),
                          lambda:freeze_full(c,d,'SYN-ALPHA',cutoff,'test')):
            with pytest.raises(PermissionError):operation()
        assert c.execute('SELECT count(*) FROM research.runs').fetchone()==(2,)
        assert c.execute('SELECT count(*) FROM research.trade_outcomes').fetchone()==(0,)


def test_duplicate_ingestion_does_not_inflate_facts_or_sessions(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);a=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        seed(c,'SYN-ALPHA');b=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        assert a==b
        fs=b['historical_snapshot']['financial_facts']
        assert len({f['fact_id'] for f in fs})==len(fs)
        assert c.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(0,)


@pytest.mark.parametrize('bad',['available','fetched','hash','missing_time'])
def test_future_missing_and_changed_provenance_denied(isolated_url,bad):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);s=deepcopy(freeze_full(c,d,'SYN-ALPHA',cutoff,'test')['historical_snapshot'])
        p=s['source_revisions'][-1]
        if bad=='available':p['revision']['available_at']='2099-01-01T00:00:00Z'
        if bad=='fetched':p['revision']['fetched_at']='2099-01-01T00:00:00Z'
        if bad=='hash':p['revision_hash']='a'*64
        if bad=='missing_time':del p['revision']['available_at']
        s['snapshot_id']=digest({k:v for k,v in s.items() if k!='snapshot_id'})
        with pytest.raises(ValueError):authorize_snapshot(c,s)


def test_missing_financial_evidence_is_unavailable_not_inferred(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d=demo_dataset();ingest(c,d)
        a=freeze_full(c,d,'SYN-BETA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),'test')
        assert not a['historical_snapshot']['financial_facts']
        assert 'financial_evidence_not_frozen' in a['historical_snapshot']['missing_evidence']
        assert comparison(freeze(c,d,'SYN-BETA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),'test'),None)['reason']=='financial_evidence_not_frozen'


def test_authenticated_api_freeze_read_reveal_and_denied_export(isolated_url,monkeypatch):
    from app.main import app
    from app.research import db
    from fastapi.testclient import TestClient
    monkeypatch.setenv('AUTH_TOKEN','r'*40);monkeypatch.setenv('COOKIE_SECURE','false');monkeypatch.setenv('APP_ORIGIN','http://testserver')
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d=demo_dataset();ingest(c,d);app.dependency_overrides[db]=lambda:c
        try:
            client=TestClient(app,headers={'Origin':'http://testserver'});client.post('/api/v1/session',json={'token':'r'*40})
            body=dict(dataset_version=d.version,instrument_id='SYN-ALPHA',date=d.calendar.sessions[39].closes_at.date().isoformat(),include_financial=True)
            response=client.post('/api/v1/analysis',json=body);assert response.status_code==200,response.text
            a=response.json();rid=a['recommendation']['recommendation_id']
            assert a['historical_snapshot']['documents']
            unknown=client.post('/api/v1/analysis',json=dict(body,historical_ai_run_id='UNKNOWN-RUN')).json()
            assert unknown['historical_snapshot']['ai'] is None
            assert 'contemporaneous_ai_unavailable' in unknown['historical_snapshot']['missing_evidence']
            out=client.post('/api/v1/analysis/'+rid+'/reveal',json={}).json()
            assert out['comparison']['status']=='unavailable' and out['comparison']['baseline']['trade']
            assert client.get('/api/v1/analysis/'+rid).json()['historical_snapshot']==a['historical_snapshot']
            restrict(c,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked')
            for path in ('/analysis/'+rid,'/experiments/export'):
                assert client.get('/api/v1'+path).status_code==403
        finally:app.dependency_overrides.pop(db,None)


@pytest.mark.parametrize('timing',['before','after','unknown'])
def test_only_explicit_contemporaneous_ai_on_exact_bundle_can_be_frozen(isolated_url,timing):
    from psycopg.types.json import Jsonb
    from stock_discovery_analysis.historical_research import build_snapshot
    from stock_discovery_analysis.rag_contracts import Bundle
    from stock_discovery_analysis.factual_research import candidates,validate_response
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);b=freeze(c,d,'SYN-ALPHA',cutoff,'test');s=build_snapshot(c,d,'SYN-ALPHA',cutoff,b)
        bundle=Bundle.model_validate_json(json.dumps(s['bundle']));selected=candidates(bundle)[0]
        raw=json.dumps(dict(factual_claims=[dict(candidate_id=selected['candidate_id'],text=selected['text'],
            citation_ids=list(dict.fromkeys(x['evidence_id'] for x in selected['citations'])))],interpretations=[]))
        result=dict(status='completed',research_only=True,factual_report=validate_response(raw,bundle,candidates(bundle)),
            model={'id':'SCRIPTED-SYNTHETIC-NOT-A-MODEL'},prompt_hash='test',bundle_hash=bundle.content_hash)
        if timing!='unknown':result['completed_at']='2025-06-20T00:00:00Z' if timing=='before' else '2026-10-30T00:00:00Z'
        c.execute('INSERT INTO discovery.rag_bundles VALUES (%s,%s)',(bundle.content_hash,Jsonb(bundle.model_dump(mode='json'))))
        c.execute("INSERT INTO discovery.rag_reservations VALUES ('scripted-replay','test','test','2025-06-19',1,0)")
        c.execute("INSERT INTO discovery.rag_results VALUES ('scripted-replay',%s,%s)",(bundle.content_hash,Jsonb(result)))
        a=freeze_full(c,d,'SYN-ALPHA',cutoff,'test',ai_run_id='scripted-replay')
        assert bool(a['historical_snapshot']['ai'])==(timing=='before')
        assert a['historical_snapshot']['financial_qualified'] is False
        assert comparison(a,None)['status']=='unavailable'


def test_restriction_during_assembly_rolls_back_new_run_and_preserves_baseline(isolated_url,monkeypatch):
    import stock_discovery_analysis.historical_research as module
    with psycopg.connect(isolated_url,autocommit=True) as c,psycopg.connect(isolated_url,autocommit=True) as op:
        d,cutoff=prepare(c);baseline=freeze(c,d,'SYN-ALPHA',cutoff,'test');original=module.build_snapshot
        def revoke(*a,**kw):
            s=original(*a,**kw);restrict(op,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked');return s
        monkeypatch.setattr(module,'build_snapshot',revoke)
        with pytest.raises(PermissionError):freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        assert c.execute('SELECT count(*) FROM research.runs').fetchone()==(1,)
        assert read_frozen(c,baseline['recommendation']['recommendation_id'])==baseline


def test_financial_conflicts_are_frozen_and_excluded_from_comparable_calculations(isolated_url):
    from stock_discovery_analysis.evidence import Document,EvidencePage,content_hash
    from stock_discovery_analysis.evidence_storage import ingest_evidence_page
    from stock_discovery_analysis.historical_research import access_for
    from stock_discovery_analysis.revision_storage import Stream
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c)
        raw,body=c.execute("SELECT d.payload,b.body FROM discovery.evidence_documents d JOIN discovery.evidence_blobs b USING(content_hash) WHERE revision_id='SYN-ALPHA-fictional-annual-2024-v1'").fetchone()
        old=Document.model_validate_json(json.dumps(dict(raw,body=body)));p=json.loads(body);p['facts'][0]['value']='999';body=json.dumps(p)
        rev=old.revision.model_copy(update={'revision_id':'SYN-conflict','source_revision':'other','data':old.revision.data.model_copy(update={'document_id':'SYN-conflict','content_hash':content_hash(body)})})
        doc=old.model_copy(update={'revision':rev,'body':body})
        from dataclasses import replace
        from stock_discovery_analysis.historical_research import original_grant
        read_access=access_for(c)
        access=replace(read_access,load_grant=lambda s:original_grant(c,old.revision.revision_id),
            request_for=lambda s:read_access.request_for(s).model_copy(update={'units':100}))
        result=ingest_evidence_page(c,Stream(stream_id='SYN-conflict',source_id=SOURCE,account_ref=ACCOUNT,scope='filings'),
            EvidencePage(cursor=None,next_cursor=None,complete=True,records=(doc.model_dump(mode='json'),)),access=access)
        assert result['quarantined']==0,result
        s=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')['historical_snapshot']
        assert s['contradictions'] and 'conflicting_financial_evidence' in s['missing_evidence']
        assert not any(x['metric']=='revenue_yoy' for x in s['financial_calculations'])


def test_fence_activation_serializes_with_full_snapshot_commit(isolated_url,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from test_read_fences import wait_blocked
    import stock_discovery_analysis.historical_research as module
    locked,release,ready=Event(),Event(),Event();pids=[];original=module.persist_analysis
    def held(*a,**kw):
        locked.set();assert release.wait(10);return original(*a,**kw)
    with psycopg.connect(isolated_url,autocommit=True) as admin:
        d,cutoff=prepare(admin);monkeypatch.setattr(module,'persist_analysis',held)
        def freeze_worker():
            with psycopg.connect(isolated_url,autocommit=True) as c:return freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        def revoke():
            with psycopg.connect(isolated_url,autocommit=True) as c:
                pids.append(c.info.backend_pid);ready.set()
                return restrict(c,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked')
        with ThreadPoolExecutor(2) as pool:
            freezing=pool.submit(freeze_worker);assert locked.wait(10)
            fencing=pool.submit(revoke);assert ready.wait(5)
            try:wait_blocked(admin,pids[0]);assert not fencing.done()
            finally:release.set()
            a=freezing.result(timeout=10);assert fencing.result(timeout=10)==1
        with pytest.raises(PermissionError):read_frozen(admin,a['recommendation']['recommendation_id'])
        assert admin.execute('SELECT count(*) FROM research.runs').fetchone()==(2,)


def test_new_combined_run_does_not_backdate_generation_to_cached_baseline(isolated_url,monkeypatch):
    import stock_discovery_analysis.historical_research as module
    with psycopg.connect(isolated_url,autocommit=True) as c:
        d,cutoff=prepare(c);baseline=freeze(c,d,'SYN-ALPHA',cutoff,'test')
        monkeypatch.setattr(module,'now',lambda:'2027-01-01T00:00:00Z')
        a=freeze_full(c,d,'SYN-ALPHA',cutoff,'test')
        assert a['recommendation']['generated_at']=='2027-01-01T00:00:00Z'
        assert baseline['recommendation']['generated_at']!=a['recommendation']['generated_at']
        assert read_frozen(c,baseline['recommendation']['recommendation_id'])==baseline
        assert freeze_full(c,d,'SYN-ALPHA',cutoff,'test')==a
