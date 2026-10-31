"""Observed-mode contracts with fabricated filings and scripted AI ONLY."""
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from test_real_evidence import setup, NOW, HTML
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.combined_research import research, replay_context
from stock_discovery_analysis.rag_research import MockResearchProvider
from stock_discovery_analysis.grant_fences import restrict
from worker.real_evidence import run
from worker.providers.documents import OfficialDocument

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')

@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()


def prepared(conn,tmp_path):
    class Select(MockResearchProvider):
        def assess(self,request,**kwargs):
            c=json.loads(request)['bundle']['candidates'][0]
            return json.dumps(dict(factual_claims=[dict(candidate_id=c['candidate_id'],text=c['text'],
                citation_ids=c['citation_ids'])],interpretations=[]))
    def adapter(spec,**kw):return OfficialDocument(spec,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML)),**kw)
    def model(name,**kw):
        p=Select();p.close=lambda:None;return p
    c=setup(conn,tmp_path).model_copy(update={'factual_report':True,'embedding_model':None})
    result=run(conn,c,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
    assert result['research'][0]['result']['status']=='completed'
    return ViewConfig(sources=c.sources,listing_ids=('NSE:test',))


def counts(conn):
    return [conn.execute('SELECT count(*) FROM '+table).fetchone() for table in
        ('discovery.rag_reservations','discovery.rag_results','discovery.revisions','discovery.recommendations','research.decisions')]


def test_qualified_technical_and_verified_financial_analysis_flow_together(isolated_url,tmp_path):
    from test_swing_research import setup as swing_setup
    from stock_discovery_analysis.rag_contracts import Query,RetrievalPolicy,Budget
    from stock_discovery_analysis.rag_research import run_research
    from stock_discovery_analysis.real_access import source_access
    class Select(MockResearchProvider):
        def assess(self,request,**kwargs):
            context=json.loads(request)['bundle'];cs=context['candidates']
            chosen=[c for c in cs if '_yoy' in c['text']][:2]
            excerpts=context['excerpt_candidates'][:1]
            return json.dumps(dict(factual_claims=chosen,interpretations=[],source_excerpts=excerpts))
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=swing_setup(conn,tmp_path,'combined_financial')
        query=Query(issuer_id='test-issuer',listing_id='NSE:TEST',horizon='swing',mode='live_paper',
            cutoff_at=cutoff,text='revenue earnings cash flow',categories=('annual_report',))
        r=run_research(conn,run_id='TEST-combined',query=query,policy=RetrievalPolicy(),
            access=source_access(config.sources,lambda:cutoff),budget=Budget(account='TEST-combined'),provider=Select(),factual_report=True)
        assert r['status']=='completed',r
        before=counts(conn);report=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert report['technical']['condition']=='conditions_met'
        assert report['financial']['findings'] and report['financial']['trends']
        assert report['financial']['source_excerpts'] and report['financial']['quality_acceptance']=='BLOCKED'
        assert report['status']=='INSUFFICIENT_EVIDENCE' and not report['actionable']
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)==report and counts(conn)==before


def test_stored_filing_model_verifier_api_and_repeated_authorization(isolated_url,tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.research import db
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=prepared(conn,tmp_path);before=counts(conn)
        path=tmp_path/'view.json';path.write_text(config.model_dump_json())
        monkeypatch.setenv('REAL_RESEARCH_VIEW_CONFIG',str(path));monkeypatch.setenv('AUTH_TOKEN','c'*40);monkeypatch.setenv('COOKIE_SECURE','false')
        app.dependency_overrides[db]=lambda:conn
        try:
            c=TestClient(app);url='/v1/real-research/companies/NSE:test?analysis=combined&cutoff_at='+NOW
            assert c.get(url).status_code==401
            c.post('/api/v1/session',json={'token':'c'*40})
            response=c.get(url);assert response.status_code==200 and response.headers['cache-control']=='no-store'
            result=response.json();assert result['financial']['findings'] and result['new_model_calls']==0
            assert result['status']=='INSUFFICIENT_EVIDENCE' and c.get(url).json()==result
            assert counts(conn)==before
            restrict(conn,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')
            denied=c.get(url).json()
            assert denied['financial'] is None and not denied['technical']['indicators']
            assert 'source_access_or_provenance_unavailable' in denied['gaps']
            assert '1000000000' not in json.dumps(denied) and counts(conn)==before
        finally:app.dependency_overrides.pop(db,None)


@pytest.mark.parametrize('case',['buy','wait','mixed'])
def test_qualified_technical_component_is_never_combined_buy(isolated_url,tmp_path,case):
    from test_swing_research import setup as swing_setup
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=swing_setup(conn,tmp_path,case)
        r=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert r['technical']['condition']==('conditions_not_met' if case=='wait' else 'conditions_met')
        assert r['status']=='INSUFFICIENT_EVIDENCE' and r['financial'] is None
        assert 'levels' not in r['technical'] and r['new_model_calls']==0
        if case=='mixed':
            restrict(conn,request_id=uuid4(),kind='provider',source_id='test-other',reason='revoked')
            assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['technical']['indicators']=={}


def test_historical_cutoff_cannot_read_future_report(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=prepared(conn,tmp_path)
        assert research(conn,config,'NSE:test',cutoff_at='2026-01-01T00:00:00Z')['financial'] is None
        assert research(conn,config,'NSE:test',cutoff_at='2099-01-01T00:00:00Z')['financial'] is None
        Path(config.sources.grant_file).write_text('[]')
        assert research(conn,config,'NSE:test',cutoff_at=NOW)['financial'] is None


def test_restriction_racing_combined_assembly_withholds_every_component(isolated_url,tmp_path,monkeypatch):
    import stock_discovery_analysis.combined_research as module
    with psycopg.connect(isolated_url,autocommit=True) as conn, psycopg.connect(isolated_url,autocommit=True) as operator:
        config=prepared(conn,tmp_path);original=module.compose
        def racing(*a,**kw):
            result=original(*a,**kw)
            if result['financial']:
                restrict(operator,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')
            return result
        monkeypatch.setattr(module,'compose',racing)
        r=research(conn,config,'NSE:test',cutoff_at=NOW)
        assert r['financial'] is None and r['technical']['indicators']=={}
        assert conn.execute('SELECT 1').fetchone()==(1,)


@pytest.mark.parametrize('correction',[False,True])
def test_new_filing_or_revision_requires_refresh_but_not_at_earlier_cutoff(isolated_url,tmp_path,correction):
    from stock_discovery_analysis.evidence import Document,EvidencePage
    from stock_discovery_analysis.evidence_storage import ingest_evidence_page
    from stock_discovery_analysis.revision_storage import Stream
    from stock_discovery_analysis.real_access import source_access
    later='2026-10-20T12:00:00Z'
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=prepared(conn,tmp_path)
        before=research(conn,config,'NSE:test',cutoff_at=NOW)
        raw,body=conn.execute('SELECT d.payload,b.body FROM discovery.evidence_documents d JOIN discovery.evidence_blobs b USING(content_hash)').fetchone()
        doc=Document.model_validate(dict(raw,body=body));old=doc.revision
        rev=old.model_copy(update=dict(revision_id='NEW-DOC',source_revision='new-version',
            sequence=2 if correction else 1,supersedes_id=old.revision_id if correction else None,
            published_at=later,available_at=later,fetched_at=later,
            data=old.data if correction else old.data.model_copy(update={'document_id':'other-report'})))
        stream=Stream(stream_id='new-doc',source_id=rev.source_id,account_ref='test',scope='filings')
        result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,
            records=(doc.model_copy(update={'revision':rev}).model_dump(mode='json'),)),access=source_access(config.sources,lambda:later))
        assert result['quarantined']==0
        assert research(conn,config,'NSE:test',cutoff_at=NOW)==before
        new=research(conn,config,'NSE:test',cutoff_at=later)
        assert new['financial'] is None and 'financial_research_requires_refresh' in new['gaps']


def test_combined_read_holds_fences_until_response_is_assembled(isolated_url,tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from test_read_fences import wait_blocked
    from stock_discovery_analysis.read_fences import ReadGuard
    locked,release,ready=Event(),Event(),Event();pids=[];original=ReadGuard.authorize
    def held(guard):
        original(guard);locked.set();assert release.wait(10)
    with psycopg.connect(isolated_url,autocommit=True) as admin:
        config=prepared(admin,tmp_path);monkeypatch.setattr(ReadGuard,'authorize',held)
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as c:return research(c,config,'NSE:test',cutoff_at=NOW)
        def revoke():
            with psycopg.connect(isolated_url,autocommit=True) as c:
                pids.append(c.info.backend_pid);ready.set()
                return restrict(c,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')
        with ThreadPoolExecutor(2) as pool:
            reading=pool.submit(read);assert locked.wait(10)
            writing=pool.submit(revoke);assert ready.wait(5)
            try:wait_blocked(admin,pids[0]);assert not writing.done()
            finally:release.set()
            assert reading.result(timeout=10)['financial']
            assert writing.result(timeout=10)==1
        monkeypatch.setattr(ReadGuard,'authorize',original)
        assert research(admin,config,'NSE:test',cutoff_at=NOW)['financial'] is None


def test_replay_projection_survives_restart_and_future_reveal_unchanged(isolated_url):
    from datetime import timedelta
    from stock_discovery_analysis.dataset import demo_dataset
    from stock_discovery_analysis.storage import ingest
    from stock_discovery_analysis.service import freeze,read_frozen,reveal
    d=demo_dataset();cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        ingest(conn,d);a=freeze(conn,d,'SYN-ALPHA',cutoff,'combined-test');r=replay_context(a)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        rid=a['recommendation']['recommendation_id'];reveal(conn,rid)
        assert read_frozen(conn,rid)==a and replay_context(read_frozen(conn,rid))==r
        assert conn.execute('SELECT count(*) FROM research.decisions').fetchone()==(1,)
