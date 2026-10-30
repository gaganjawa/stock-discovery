"""Synthetic-only MVP read authorization; disposable PostgreSQL, no providers."""
import json
import os
import uuid
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')

@pytest.fixture
def isolated_url():
    yield from _isolated_url.__wrapped__()
from test_real_evidence import setup, NOW
from stock_discovery_analysis.real_views import company, ViewConfig
from stock_discovery_analysis.grant_fences import restrict


def view(conn,tmp_path):
    evidence=setup(conn,tmp_path)
    return ViewConfig(sources=evidence.sources,listing_ids=('NSE:test',))


@pytest.mark.parametrize('kind',['provider','account','grant'])
def test_stored_company_denied_after_restriction(isolated_url,tmp_path,kind):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path)
        assert company(conn,config,'NSE:test',clock=lambda:NOW)['symbol']=='TEST'
        restrict(conn,request_id=uuid.uuid4(),kind=kind,source_id='test-official',
            account_ref='test' if kind!='provider' else '',
            grant_id='p2-test' if kind=='grant' else '',grant_version='1' if kind=='grant' else '',reason='revoked')
        with pytest.raises(PermissionError):
            company(conn,config,'NSE:test',clock=lambda:NOW)


@pytest.mark.parametrize('change',['missing','revoked','expired','renewed','file_unavailable'])
def test_current_grant_failure_cannot_reuse_stored_company(isolated_url,tmp_path,change):
    from pathlib import Path
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path); path=Path(config.sources.grant_file)
        grants=json.loads(path.read_text())
        if change=='missing':grants=[]
        elif change=='revoked':grants[0].update(status='revoked',revoked_at=NOW)
        elif change=='expired':grants[0]['expires_at']='2026-10-18T00:00:00Z'
        elif change=='renewed':grants[0]['version']='2'
        path.write_text(json.dumps(grants))
        if change=='file_unavailable':path.unlink()
        with pytest.raises(PermissionError,match='^real_read_access_denied$'):
            company(conn,config,'NSE:test',clock=lambda:NOW)
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==1


def test_missing_revision_and_malformed_citation_fail_closed(isolated_url,tmp_path):
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path); access=source_access(config.sources,lambda:NOW)
        for value in ({'revision_id':'does-not-exist'},{'revision_id':None},{'source_revisions':'not-a-list'}):
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):
                with guarded_read(conn,access) as guard:guard.collect(value)
            assert conn.execute('SELECT 1').fetchone()==(1,)


def test_direct_authenticated_api_cannot_return_fenced_content(isolated_url,tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import real_research
    from app.research import db
    monkeypatch.setenv('AUTH_TOKEN','synthetic-read-fence-test-token-0000000000')
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path)
        monkeypatch.setattr(real_research,'view_config',lambda:config)
        app.dependency_overrides[db]=lambda:conn
        try:
            client=TestClient(app)
            headers={'Authorization':'Bearer synthetic-read-fence-test-token-0000000000'}
            assert client.get('/v1/real-research/companies/NSE:test',headers=headers).status_code==200
            restrict(conn,request_id=uuid.uuid4(),kind='provider',source_id='test-official',reason='revoked')
            response=client.get('/v1/real-research/companies/NSE:test',headers=headers)
            assert response.status_code==403
            assert response.json()=={'detail':'Source permission denied'}
            assert 'TEST' not in response.text
        finally:app.dependency_overrides.pop(db,None)


def test_mixed_sources_denied_but_unrelated_source_stays_usable(isolated_url,tmp_path):
    from pathlib import Path
    from stock_discovery_contracts.rights import Grant
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read
    from stock_discovery_analysis.revisions import Revision
    from stock_discovery_analysis.revision_storage import Stream,Page,ingest_page
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path);path=Path(config.sources.grant_file);g=json.loads(path.read_text())[0]
        other={**g,'source_id':'other','grant_id':'other-grant'}
        path.write_text(json.dumps([g,other]));access=source_access(config.sources,lambda:NOW)
        r=Revision.model_validate(conn.execute('SELECT payload FROM discovery.revisions').fetchone()[0])
        r=r.model_copy(update={'revision_id':'other-identity','source_id':'other','listing_id':'NSE:other'})
        stream=Stream(stream_id='other',source_id='other',account_ref='test',scope='universe')
        grant=Grant.model_validate_json(json.dumps(other));request=access.request_for(stream)
        ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(r.model_dump(mode='json'),)),load_grant=lambda:grant,request=request,audit=lambda d:None)
        restrict(conn,request_id=uuid.uuid4(),kind='provider',source_id='test-official',reason='revoked')
        with guarded_read(conn,access) as guard:guard.collect({'source_revisions':['other-identity']})
        for ids in (['P2-identity','other-identity'],['other-identity','P2-identity']):
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):
                with guarded_read(conn,access) as guard:guard.collect({'source_revisions':ids})
        permitted=config.model_copy(update={'listing_ids':('NSE:other',)})
        assert company(conn,permitted,'NSE:other',clock=lambda:NOW)['listing_id']=='NSE:other'


def test_read_error_rolls_back_and_resets_context(isolated_url,tmp_path):
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path); access=source_access(config.sources,lambda:NOW)
        with pytest.raises(PermissionError,match='^real_read_access_denied$'):
            with guarded_read(conn,access):conn.execute('SELECT 1/0')
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)
        assert company(conn,config,'NSE:test',clock=lambda:NOW)['symbol']=='TEST'


def test_completed_research_history_rechecks_original_dependencies(isolated_url,tmp_path):
    import httpx
    from test_real_evidence import HTML
    from worker.real_evidence import run
    from worker.providers.documents import OfficialDocument
    from stock_discovery_analysis.rag_research import MockResearchProvider
    from stock_discovery_analysis.rag_retrieval import MockEmbeddings
    def adapter(spec,**kw):return OfficialDocument(spec,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML)),**kw)
    def model(name,**kw):
        result=MockEmbeddings() if 'embed' in name else MockResearchProvider()
        result.close=lambda:None
        return result
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=setup(conn,tmp_path)
        run(conn,config,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
        v=ViewConfig(sources=config.sources,listing_ids=('NSE:test',))
        assert company(conn,v,'NSE:test',clock=lambda:NOW)['analysis_history']
        before=conn.execute('SELECT count(*) FROM discovery.rag_results').fetchone()
        restrict(conn,request_id=uuid.uuid4(),kind='grant',source_id='test-official',account_ref='test',grant_id='p2-test',grant_version='1',reason='revoked')
        with pytest.raises(PermissionError):company(conn,v,'NSE:test',clock=lambda:NOW)
        assert conn.execute('SELECT count(*) FROM discovery.rag_results').fetchone()==before


def wait_blocked(conn,pid):
    import time
    end=time.monotonic()+5
    while time.monotonic()<end:
        if conn.execute('SELECT cardinality(pg_blocking_pids(%s))>0',(pid,)).fetchone()[0]:return
        time.sleep(.01)
    raise AssertionError('expected PostgreSQL lock wait was not observed')


def test_restriction_between_assembly_and_authorization_denies(isolated_url,tmp_path):
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read
    with psycopg.connect(isolated_url,autocommit=True) as reader, psycopg.connect(isolated_url,autocommit=True) as operator:
        config=view(reader,tmp_path)
        with pytest.raises(PermissionError):
            with guarded_read(reader,source_access(config.sources,lambda:NOW)) as guard:
                guard.add('P2-identity')
                restrict(operator,request_id=uuid.uuid4(),kind='provider',source_id='test-official',reason='revoked')
        assert reader.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)


def test_read_locks_serialize_restriction_until_transaction_end(isolated_url,tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from stock_discovery_analysis.read_fences import ReadGuard
    locked,release,writer_ready=Event(),Event(),Event();pids=[]
    original=ReadGuard.authorize
    def held(guard):
        original(guard);locked.set();assert release.wait(5)
    with psycopg.connect(isolated_url,autocommit=True) as admin:
        config=view(admin,tmp_path)
        monkeypatch.setattr(ReadGuard,'authorize',held)
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as conn:return company(conn,config,'NSE:test',clock=lambda:NOW)
        def revoke():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                pids.append(conn.info.backend_pid);writer_ready.set()
                return restrict(conn,request_id=uuid.uuid4(),kind='provider',source_id='test-official',reason='revoked')
        with ThreadPoolExecutor(2) as pool:
            reading=pool.submit(read);assert locked.wait(5)
            writing=pool.submit(revoke);assert writer_ready.wait(5)
            try:wait_blocked(admin,pids[0]);assert not writing.done()
            finally:release.set()
            assert reading.result(timeout=5)['symbol']=='TEST'
            assert writing.result(timeout=5)==1
        monkeypatch.setattr(ReadGuard,'authorize',original)
        with pytest.raises(PermissionError):company(admin,config,'NSE:test',clock=lambda:NOW)


def test_repeatable_read_old_snapshot_cannot_hide_restriction(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as admin, psycopg.connect(isolated_url,autocommit=True) as reader:
        config=view(admin,tmp_path)
        reader.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
        with reader.transaction():
            reader.execute('SELECT * FROM discovery.grant_fences').fetchall()
            restrict(admin,request_id=uuid.uuid4(),kind='account',source_id='test-official',account_ref='test',reason='revoked')
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):
                company(reader,config,'NSE:test',clock=lambda:NOW)
        assert reader.execute('SELECT 1').fetchone()==(1,)


def test_expiry_during_lock_wait_is_rechecked_with_database_time(isolated_url,tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from pathlib import Path
    from datetime import timedelta
    import time
    ready=Event();pids=[]
    with psycopg.connect(isolated_url,autocommit=True) as admin, psycopg.connect(isolated_url,autocommit=True) as locker:
        config=view(admin,tmp_path);path=Path(config.sources.grant_file)
        deadline=admin.execute('SELECT clock_timestamp()').fetchone()[0]+timedelta(seconds=2)
        grants=json.loads(path.read_text());grants[0]['expires_at']=deadline.strftime('%Y-%m-%dT%H:%M:%SZ');path.write_text(json.dumps(grants))
        locker.execute('BEGIN')
        locker.execute("SELECT scope_id FROM discovery.grant_fences WHERE kind='grant' FOR UPDATE")
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                pids.append(conn.info.backend_pid);ready.set()
                return company(conn,config,'NSE:test',clock=lambda:NOW)
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(read);assert ready.wait(5)
            try:
                wait_blocked(admin,pids[0])
                while admin.execute('SELECT clock_timestamp()').fetchone()[0]<deadline:time.sleep(.01)
            finally:locker.execute('ROLLBACK')
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):future.result(timeout=5)


@pytest.mark.parametrize('manifest',['valid','missing','dangling','malformed'])
def test_saved_scan_boundary_requires_original_revision_manifest(isolated_url,tmp_path,monkeypatch,manifest):
    from stock_discovery_analysis import real_scan_view
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path).model_copy(update={'pilot_scope_id':'synthetic-read-test'})
        scan={'universe_revision_ids':['P2-identity'],'rows':[{'source_revisions':['P2-identity']}]}
        if manifest=='missing':scan.pop('universe_revision_ids')
        elif manifest=='dangling':scan['universe_revision_ids']=['absent']
        elif manifest=='malformed':scan['rows'][0]['source_revisions']=[None]
        # Isolate the public boundary from legacy scan assembly. All authorization
        # and original acquisition lookups below use actual PostgreSQL records.
        monkeypatch.setattr(real_scan_view,'_scan_view',lambda *a:{'scan':scan})
        if manifest=='valid':
            assert real_scan_view.scan_view(conn,config)['scan']==scan
            restrict(conn,request_id=uuid.uuid4(),kind='account',source_id='test-official',account_ref='test',reason='revoked')
        with pytest.raises(PermissionError,match='^real_read_access_denied$'):
            real_scan_view.scan_view(conn,config)


def test_missing_fence_state_and_bundle_fail_closed(isolated_url,tmp_path):
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path); access=source_access(config.sources,lambda:NOW)
        for key in ('bundle_hash','baseline_hash','final_bundle_hash'):
            with pytest.raises(PermissionError,match='^real_read_access_denied$'):
                with guarded_read(conn,access) as guard:guard.collect({key:'f'*64})
        # Unknown scope must never cause read-side registration/authorization.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT discovery.lock_grant_fences('unknown','unknown','unknown','1')")
        assert conn.execute("SELECT count(*) FROM discovery.grant_fences WHERE source_id='unknown'").fetchone()==(0,)


def test_price_chart_rechecks_original_price_account(isolated_url,tmp_path):
    from pathlib import Path
    from stock_discovery_contracts.rights import Grant
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.revisions import Revision,CandleData
    from stock_discovery_analysis.revision_storage import Stream,Page,ingest_page
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=view(conn,tmp_path);path=Path(config.sources.grant_file)
        grants=json.loads(path.read_text());g={**grants[0],'account_ref':'prices','grant_id':'prices-grant','scopes':['prices']}
        path.write_text(json.dumps([*grants,g]));grant=Grant.model_validate_json(json.dumps(g))
        identity=Revision.model_validate(conn.execute('SELECT payload FROM discovery.revisions').fetchone()[0])
        bar=identity.model_copy(update={'revision_id':'price-1','instrument_revision_id':'P2-identity',
            'data':CandleData(kind='candle',interval='1d',starts_at='2026-10-19T03:45:00Z',ends_at='2026-10-19T10:00:00Z',
                open='100',high='110',low='90',close='105',volume=100,adjustment_basis='raw')})
        stream=Stream(stream_id='price-stream',source_id='test-official',account_ref='prices',scope='prices')
        access=source_access(config.sources,lambda:NOW)
        ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(bar.model_dump(mode='json'),)),
            load_grant=lambda:grant,request=access.request_for(stream),audit=lambda d:None)
        assert company(conn,config,'NSE:test',clock=lambda:NOW)['price_series'][0]['close']=='105'
        restrict(conn,request_id=uuid.uuid4(),kind='account',source_id='test-official',account_ref='prices',reason='revoked')
        with pytest.raises(PermissionError):company(conn,config,'NSE:test',clock=lambda:NOW)
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(2,)
