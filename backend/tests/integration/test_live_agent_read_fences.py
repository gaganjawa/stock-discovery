"""Observed-mode fixtures only: no provider/model/network calls."""
import json
import os
import time
from types import SimpleNamespace
import httpx
import psycopg
import pytest
from test_read_fences import isolated_url
from test_real_evidence import setup,NOW,HTML
from stock_discovery_analysis.real_access import source_access
from stock_discovery_analysis.rag_contracts import Bundle,RetrievalPolicy
from stock_discovery_analysis.rag_research import MockResearchProvider
from stock_discovery_analysis.rag_retrieval import MockEmbeddings
from stock_discovery_analysis.agent_contracts import Conflicts,AgentPolicy
from stock_discovery_analysis.agent_storage import ReadOnlyTools

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def prepared(conn,tmp_path):
    from worker.real_evidence import run
    from worker.providers.documents import OfficialDocument
    config=setup(conn,tmp_path)
    def adapter(spec,**kw):return OfficialDocument(spec,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML)),**kw)
    def model(name,**kw):
        value=MockEmbeddings() if 'embed' in name else MockResearchProvider()
        value.close=lambda:None
        return value
    run(conn,config,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
    bundle=Bundle.model_validate_json(json.dumps(conn.execute('SELECT payload FROM discovery.rag_bundles LIMIT 1').fetchone()[0]))
    return bundle,source_access(config.sources,lambda:NOW)


def meter():return SimpleNamespace(ensure=lambda *a:None,charge=lambda *a:None,deadline=time.monotonic()+30,clock=time.monotonic)


def test_permitted_live_agent_read_only_tool(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        result,response=ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Conflicts(name='inspect_conflicts'),bundle,AgentPolicy(),meter())
        assert result==bundle and response['contradictions']==[]
        assert conn.info.transaction_status==psycopg.pq.TransactionStatus.IDLE


def test_unique_bundle_limit_accepts_duplicate_at_boundary(isolated_url,tmp_path):
    from psycopg.types.json import Jsonb
    from stock_discovery_analysis.read_fences import ReadGuard
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path);guard=ReadGuard(conn,access);keys=[]
        for i in range(101):
            b=bundle.model_copy(update={'query':bundle.query.model_copy(update={'text':f'boundary {i}'})})
            conn.execute('INSERT INTO discovery.rag_bundles VALUES (%s,%s)',(b.content_hash,Jsonb(b.model_dump(mode='json'))))
            keys.append(b.content_hash)
        for key in keys[:100]:guard.bundle(key)
        assert len(guard.bundles)==100
        guard.bundle(keys[0])
        assert len(guard.bundles)==100
        with pytest.raises(PermissionError,match='^real_read_access_denied$'):guard.bundle(keys[100])
        assert len(guard.bundles)==100


def test_live_retrieval_keeps_database_write_prohibition(isolated_url,tmp_path):
    from stock_discovery_analysis.agent_contracts import Search
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path);observed=[]
        class Writes(MockEmbeddings):
            def embed(self,*a,**k):
                assert conn.execute('SHOW transaction_read_only').fetchone()[0]=='on'
                try:conn.execute('CREATE TABLE public.forbidden_live_agent_write(id integer)')
                except psycopg.errors.ReadOnlySqlTransaction as exc:
                    observed.append(exc.sqlstate)
                    raise
                raise AssertionError('PostgreSQL accepted a tool write')
        tool=Search(name='retrieve',text='earnings',categories=('annual_report',))
        with pytest.raises((PermissionError,RuntimeError)):
            ReadOnlyTools(conn,access,RetrievalPolicy(),Writes()).execute(tool,bundle,AgentPolicy(),meter())
        assert observed==['25006']
        assert conn.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
        assert conn.execute("SELECT to_regclass('public.forbidden_live_agent_write')").fetchone()==(None,)
        result,_=ReadOnlyTools(conn,access,RetrievalPolicy(),MockEmbeddings()).execute(tool,bundle,AgentPolicy(),meter())
        assert set(bundle.documents)<=set(result.documents)


@pytest.mark.parametrize('kind',['provider','account','grant'])
def test_restriction_wins_before_live_tool(isolated_url,tmp_path,kind):
    from uuid import uuid4
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        restrict(conn,request_id=uuid4(),kind=kind,source_id='test-official',reason='revoked',
            account_ref='test' if kind!='provider' else '',grant_id='p2-test' if kind=='grant' else '',grant_version='1' if kind=='grant' else '')
        with pytest.raises(PermissionError,match='^real_read_access_denied$'):
            ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Conflicts(name='inspect_conflicts'),bundle,AgentPolicy(),meter())
        assert conn.info.transaction_status==psycopg.pq.TransactionStatus.IDLE


@pytest.mark.parametrize('isolation',[psycopg.IsolationLevel.READ_COMMITTED,psycopg.IsolationLevel.REPEATABLE_READ])
def test_restriction_waits_for_live_tool_read_and_locks_release(isolated_url,tmp_path,monkeypatch,isolation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from uuid import uuid4
    from stock_discovery_analysis import agent_storage
    from stock_discovery_analysis.grant_fences import restrict
    from test_read_fences import wait_blocked
    entered,release,ready=Event(),Event(),Event();pids=[]
    original=agent_storage.recheck
    def paused(conn,bundle,access):
        original(conn,bundle,access)
        assert conn.execute('SHOW transaction_read_only').fetchone()[0]=='on'
        entered.set();assert release.wait(5)
    with psycopg.connect(isolated_url,autocommit=True) as admin:
        bundle,access=prepared(admin,tmp_path);monkeypatch.setattr(agent_storage,'recheck',paused)
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                conn.isolation_level=isolation
                return ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Conflicts(name='inspect_conflicts'),bundle,AgentPolicy(),meter())
        def fence():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                pids.append(conn.info.backend_pid);ready.set()
                return restrict(conn,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')
        with ThreadPoolExecutor(2) as pool:
            reading=pool.submit(read);assert entered.wait(5)
            fencing=pool.submit(fence);assert ready.wait(5)
            try:wait_blocked(admin,pids[0]);assert not fencing.done()
            finally:release.set()
            assert reading.result(timeout=5)[0]==bundle
            assert fencing.result(timeout=5)==1
        with pytest.raises(PermissionError):read()


def test_live_tool_failure_releases_authorization_locks(isolated_url,tmp_path,monkeypatch):
    from uuid import uuid4
    from stock_discovery_analysis import agent_storage
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        def fail(*args):raise RuntimeError('controlled tool failure')
        monkeypatch.setattr(agent_storage,'recheck',fail)
        with pytest.raises(RuntimeError,match='controlled tool failure'):
            ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Conflicts(name='inspect_conflicts'),bundle,AgentPolicy(),meter())
        assert conn.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
        conn.execute("SET lock_timeout='1s'")
        assert restrict(conn,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')==1


def test_observed_investigation_completes_and_reuses_without_budget_reset(isolated_url,tmp_path):
    from uuid import uuid4
    from test_agent_investigation import ToolOnce
    from stock_discovery_analysis.agent_research import MockJudge
    from stock_discovery_analysis.agent_storage import run_investigation
    from stock_discovery_analysis.rag_contracts import Budget
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        args=dict(run_id='observed-test-agent',query=bundle.query,retrieval_policy=RetrievalPolicy(),access=access,
            budget=Budget(account='observed-agent-test',max_run_units=500000),provider=ToolOnce(),judge=MockJudge(),embeddings=MockEmbeddings())
        result=run_investigation(conn,**args)
        assert result['status']=='completed' and result['trace'][0]['status']=='completed'
        assert not result['actionable'] and result['paper_admission']=='blocked'
        before=conn.execute('SELECT * FROM discovery.rag_reservations ORDER BY run_id').fetchall()
        class NoCalls(ToolOnce):
            def step(self,*a,**k):raise AssertionError('duplicate inference')
        assert run_investigation(conn,**{**args,'provider':NoCalls()})['cache_reused']
        assert conn.execute('SELECT * FROM discovery.rag_reservations ORDER BY run_id').fetchall()==before
        restrict(conn,request_id=uuid4(),kind='provider',source_id='test-official',reason='revoked')
        with pytest.raises(PermissionError):run_investigation(conn,**args)
        assert conn.execute('SELECT * FROM discovery.rag_reservations ORDER BY run_id').fetchall()==before
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()==(0,)
        assert conn.execute('SELECT count(*) FROM paper.portfolios').fetchone()==(0,)


def test_new_tool_dependency_is_checked_before_embeddings(isolated_url,tmp_path,monkeypatch):
    from uuid import uuid4
    from stock_discovery_analysis import agent_storage
    from stock_discovery_analysis.agent_contracts import Search
    from stock_discovery_analysis.evidence_storage import read_evidence
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        # Start with no document dependency: simulate an expanded retrieval
        # discovering a revision which was not in the initial bundle.
        empty=bundle.model_copy(update={'documents':(),'hits':(),'facts':()})
        restrict(conn,request_id=uuid4(),kind='grant',source_id='test-official',account_ref='test',grant_id='p2-test',grant_version='1',reason='revoked')
        reached=[]
        def retrieve(*a,**kw):
            read_evidence(conn,bundle.documents[0],access=access,cutoff=NOW,mode='live_paper')
            reached.append('embedding would consume evidence')
            return bundle
        monkeypatch.setattr(agent_storage,'retrieve',retrieve)
        with pytest.raises(PermissionError):
            ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Search(name='retrieve',text='earnings',categories=('annual_report',)),empty,AgentPolicy(),meter())
        assert reached==[]


def test_authorizer_connection_failure_is_sanitized(isolated_url,tmp_path,monkeypatch):
    from stock_discovery_analysis import read_fences
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        bundle,access=prepared(conn,tmp_path)
        def failure(*a,**k):raise psycopg.OperationalError('private connection details must not escape')
        with monkeypatch.context() as patch:
            patch.setattr(read_fences.psycopg,'connect',failure)
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):
                ReadOnlyTools(conn,access,RetrievalPolicy()).execute(Conflicts(name='inspect_conflicts'),bundle,AgentPolicy(),meter())
        assert conn.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
