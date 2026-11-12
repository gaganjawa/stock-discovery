"""STK-099 disposable synthetic-only notification, restart and isolation tests."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import psycopg
from psycopg import sql
import pytest
from fastapi.testclient import TestClient
from test_candidates import isolated_url, scanner
from stock_discovery_analysis.chartink import normalize
from stock_discovery_analysis import candidate_store as store
from worker.candidate_events import bridge, serve

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def envelope(symbol='SYN097'):
    return normalize(dict(stocks=symbol,trigger_prices='100',triggered_at='6:00 pm',
        scan_name=scanner().scan_name,scan_url=scanner().scan_url,alert_name=scanner().alert_name),scanner(),datetime.now(timezone.utc))


def configure(monkeypatch,tmp_path):
    config=tmp_path/'scanner.json';config.write_text(scanner().model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(config))
    monkeypatch.delenv('REAL_RESEARCH_VIEW_CONFIG',raising=False)


def test_notify_only_after_commit_and_no_hint_for_rollback(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as listener, psycopg.connect(isolated_url,autocommit=True) as writer:
        listener.execute('LISTEN stk_candidates')
        with pytest.raises(RuntimeError),writer.transaction():
            store.accept(writer,envelope('ROLLBACK'))
            assert list(listener.notifies(timeout=.1,stop_after=1))==[]
            raise RuntimeError('simulated interruption')
        assert list(listener.notifies(timeout=.1,stop_after=1))==[]
        assert store.feed(writer)['events']==[]
        store.accept(writer,envelope())
        assert len(list(listener.notifies(timeout=2,stop_after=1)))==1


def test_bridge_atomic_cursor_reconnect_duplicates_and_roles(tmp_path,monkeypatch):
    configure(monkeypatch,tmp_path)
    identity='https://synthetic.invalid'
    with contextmanager(isolated_url.__wrapped__)() as remote,contextmanager(isolated_url.__wrapped__)() as local:
        with psycopg.connect(remote,autocommit=True) as source,psycopg.connect(local,autocommit=True) as dest:
            store.accept(source,envelope())
            with pytest.raises(RuntimeError),dest.transaction():
                assert bridge(dest,source,identity)==1
                raise RuntimeError('crash before commit')
            assert store.feed(dest)['events']==[]
            assert dest.execute('SELECT count(*) FROM discovery.candidate_receivers').fetchone()==(0,)
        with psycopg.connect(remote,autocommit=True) as source,psycopg.connect(local,autocommit=True) as dest:
            assert bridge(dest,source,identity)==1
            assert bridge(dest,source,identity)==0
            store.accept(source,envelope())
            assert bridge(dest,source,identity)==0
            assert len(store.feed(dest)['events'])==1
            dest.execute('UPDATE discovery.candidate_receivers SET cursor=99999')
            with pytest.raises(ValueError,match='cursor_ahead'):bridge(dest,source,identity)


def test_recurring_worker_catches_up_without_notification_and_reconnects(tmp_path,monkeypatch):
    from app.main import app
    from app.research import db
    from app.chartink_receiver import app as receiver
    configure(monkeypatch,tmp_path)
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
    with contextmanager(isolated_url.__wrapped__)() as remote,contextmanager(isolated_url.__wrapped__)() as local:
        def remote_db():
            with psycopg.connect(remote,autocommit=True) as conn:yield conn
        def local_db():
            with psycopg.connect(local,autocommit=True) as conn:yield conn
        receiver.dependency_overrides[db]=remote_db;app.dependency_overrides[db]=local_db
        monkeypatch.setenv('DATABASE_URL',local)
        monkeypatch.setenv('CANDIDATE_SOURCE_DATABASE_URL',remote)
        monkeypatch.delenv('DATABASE_URL_FILE',raising=False)
        monkeypatch.setenv('CHARTINK_RECEIVER_URL','https://synthetic.invalid')
        stop=threading.Event();thread=None
        try:
            client=TestClient(receiver)
            assert client.post('/hooks/chartink/wrong',json=envelope()['payload']).status_code==401
            assert client.post('/hooks/chartink/'+'w'*40,json=envelope()['payload']).status_code==202
            # Event arrived before LISTEN. No surviving notification is required.
            thread=threading.Thread(target=serve,kwargs=dict(stop=stop,recovery_seconds=.2),daemon=True);thread.start()
            def wait_count(n):
                for _ in range(150):
                    with psycopg.connect(local,autocommit=True) as conn:
                        if conn.execute("SELECT count(*) FROM discovery.candidates WHERE research_status='blocked'").fetchone()[0]==n:return
                    time.sleep(.1)
                pytest.fail('worker did not recover')
            wait_count(1)
            with psycopg.connect(remote,autocommit=True) as conn:
                conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='stk099-candidate-worker' AND datname=current_database()")
            assert client.post('/hooks/chartink/'+'w'*40,json=envelope('RECONNECT')['payload']).status_code==202
            wait_count(2)
            assert client.post('/hooks/chartink/'+'w'*40,json=envelope()['payload']).json()['duplicate']
            with psycopg.connect(local,autocommit=True) as conn:
                assert conn.execute('SELECT count(*) FROM discovery.candidate_research_runs').fetchone()==(2,)
            result=TestClient(app).get('/v1/real-research/candidates',headers={'Authorization':'Bearer '+'o'*40})
            assert result.status_code==200 and result.json()['total']==2 and not result.json()['actionable']
            assert TestClient(app).get('/v1/real-research/candidates').status_code==401
            if os.getenv('STK099_BROWSER')=='1':
                monkeypatch.setenv('COOKIE_SECURE','false')
                monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'watchlist'))
                import sys
                sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
                from chartink_browser_acceptance import verify
                verify(app)
        finally:
            stop.set()
            if thread:thread.join(10);assert not thread.is_alive()
            receiver.dependency_overrides.clear();app.dependency_overrides.clear()


def test_hosted_grants_deny_evidence_writes_and_allow_candidate_pipeline(isolated_url,tmp_path,monkeypatch):
    configure(monkeypatch,tmp_path)
    root=Path(__file__).resolve().parents[3]
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        with conn.transaction():
            for role in ('stk_runtime','stk_candidate_worker','stk_inbox_reader'):
                # Integration transaction owns these roles; rollback removes them.
                if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    conn.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
            script='\n'.join(line for line in (root/'deploy/bookmyhost/grants.sql').read_text().splitlines() if not line.startswith('--'))
            body=script.split('BEGIN;')[1].rsplit('COMMIT;',1)[0]
            body='\n'.join(line for line in body.splitlines() if 'ON DATABASE' not in line)
            conn.execute(body)
            conn.execute('SET LOCAL ROLE stk_candidate_worker')
            store.accept(conn,envelope());assert store.materialize_one(conn)
            from worker.candidates import cycle
            assert cycle(conn,remote_pull=False)['research']==1
            for statement in ['DELETE FROM discovery.candidate_events','UPDATE discovery.revisions SET payload=payload',
                              'UPDATE discovery.grant_fences SET state=state','INSERT INTO research.jobs DEFAULT VALUES']:
                with pytest.raises(psycopg.errors.InsufficientPrivilege),conn.transaction():conn.execute(statement)
            conn.execute('RESET ROLE')
            # Read-only inbox role has no access to research or mutation.
            conn.execute('GRANT USAGE ON SCHEMA discovery TO stk_inbox_reader')
            conn.execute('GRANT SELECT ON discovery.candidate_events TO stk_inbox_reader')
            conn.execute('SET LOCAL ROLE stk_inbox_reader')
            assert store.feed(conn)['events']
            with pytest.raises(psycopg.errors.InsufficientPrivilege),conn.transaction():
                conn.execute('SELECT * FROM discovery.revisions')
            conn.execute('RESET ROLE');conn.execute('ROLLBACK')


def apply_hosted_grants(conn):
    root=Path(__file__).resolve().parents[3]
    for role in ('stk_runtime','stk_candidate_worker'):
        if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
            conn.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
    body=(root/'deploy/bookmyhost/grants.sql').read_text().split('BEGIN;')[1].rsplit('COMMIT;',1)[0]
    conn.execute('\n'.join(line for line in body.splitlines() if 'ON DATABASE' not in line))


def test_hosted_authenticated_paper_writes_and_permission_boundaries(isolated_url,monkeypatch):
    from app.main import app
    from app.research import db
    from stock_discovery_analysis.publication_store import enqueue,run_next,RunRequest
    from test_paper import cfg,rec
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    with psycopg.connect(isolated_url,autocommit=True) as conn,conn.transaction():
        enqueue(conn,RunRequest(horizon='swing'),'hosted-paper','test')
        assert run_next(conn,'test')['status']=='completed'
        rid=rec((conn,isolated_url))
        apply_hosted_grants(conn)
        conn.execute('SET LOCAL ROLE stk_runtime')
        def restricted():yield conn
        app.dependency_overrides[db]=restricted
        try:
            client=TestClient(app)
            headers={'Authorization':'Bearer '+'o'*40,'Idempotency-Key':'hosted-paper'}
            body=cfg().model_dump(mode='json')
            assert client.post('/v1/paper-portfolio',json=body).status_code==401
            response=client.post('/v1/paper-portfolio',json=body,headers=headers)
            assert response.status_code==201,response.text
            pid=response.json()['portfolio_id'];base='/v1/paper-portfolio/'+pid
            admitted=client.post(base+'/admissions',json={'recommendation_id':rid},headers=headers)
            assert admitted.status_code==200,admitted.text
            assert admitted.json()['status']=='admitted'
            from stock_discovery_analysis.paper_contracts import FICTIONAL
            from stock_discovery_analysis import paper_store
            _,last=paper_store.config_state(conn,pid)
            session=paper_store.next_session(conn,last[1]['orders'][rid])
            observation=dict(contract_version=FICTIONAL,session_close_at=session['closes_at'],observed_at=session['closes_at'],bars=[])
            response=client.post(base+'/observations',json=observation,headers=headers)
            assert response.status_code==202,response.text
            assert client.post(base+'/observations',json=observation,headers=headers).json()==response.json()
            assert client.get(base,headers=headers).status_code==200
            assert client.post('/v1/discovery-runs',json={'horizon':'swing'},headers={**headers,'Idempotency-Key':'hosted-new-run'}).status_code==202
            for statement in ["UPDATE discovery.publication_source_controls SET source_id=source_id",
                "UPDATE discovery.publication_source_controls SET revoked=false",
                "UPDATE discovery.grant_fences SET state=state",'DELETE FROM paper.ledger',
                'INSERT INTO paper.processed DEFAULT VALUES','UPDATE discovery.revisions SET payload=payload',
                'CREATE TABLE public.hosted_forbidden(id int)']:
                with pytest.raises(psycopg.errors.InsufficientPrivilege),conn.transaction():conn.execute(statement)
            with pytest.raises(psycopg.Error),conn.transaction():
                conn.execute('UPDATE paper.portfolios SET portfolio_id=portfolio_id')
            assert conn.execute("SELECT has_sequence_privilege(current_user,'discovery.candidate_events_sequence_seq','USAGE')").fetchone()==(False,)
        finally:
            app.dependency_overrides.clear()
            conn.execute('RESET ROLE')
            conn.execute('ROLLBACK')


def test_hosted_research_executes_evidence_and_permission_paths(isolated_url,tmp_path,monkeypatch):
    from test_adjusted_research_storage import setup
    from test_real_market import NOW
    from stock_discovery_analysis.candidate_research import analyze
    from worker.candidates import cycle
    monkeypatch.setenv('PRIVATE_ACCESS_MODE','authenticated_proxy')
    with psycopg.connect(isolated_url,autocommit=True) as conn,conn.transaction():
        config,listing=setup(conn,tmp_path)
        view=tmp_path/'view.json';view.write_text(config.model_dump_json())
        monkeypatch.setenv('REAL_RESEARCH_VIEW_CONFIG',str(view))
        apply_hosted_grants(conn)
        conn.execute('SET LOCAL ROLE stk_candidate_worker')
        store.accept(conn,envelope('TEST'))
        # Use a pinned historical fixture clock; never current-market acceptance.
        monkeypatch.setattr('worker.candidates.analyze',lambda c,v,s,d:analyze(c,v,s,d,clock=lambda:NOW))
        assert cycle(conn,remote_pull=False)['research']==1
        result=store.rows(conn)['rows'][0]['research']
        assert result['status']=='completed' and result['market_data']['bars']==30
        assert result['technical']['metrics']['sma20']=='105'
        Path(config.sources.grant_file).write_text('[]')
        assert analyze(conn,config,'TEST','2026-11-12',clock=lambda:NOW)['reasons']==['source_permission_denied']
        assert analyze(conn,config,'ABSENT','2026-11-12',clock=lambda:NOW)['reasons']==['nse_identity_missing_or_ambiguous']
        assert result['acquisition']['provider_requests']==result['acquisition']['model_requests']==0
        conn.execute('RESET ROLE');conn.execute('ROLLBACK')
