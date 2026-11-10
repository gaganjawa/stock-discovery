"""STK-094 invented webhook/market observations only, on disposable PostgreSQL."""
import os
from datetime import datetime, timezone
from pathlib import Path
import psycopg
import pytest
from fastapi.testclient import TestClient
from stock_discovery_analysis.chartink import Scanner, fixture_snapshot
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.candidate_research import analyze, permitted_result
from test_rag_research import isolated_url as _isolated_url
from test_adjusted_research_storage import setup
from test_real_market import NOW as MARKET_NOW

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')
NOW=datetime(2026,11,5,13,tzinfo=timezone.utc)


@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()


def scanner():
    return Scanner(scan_name='Synthetic EOD',scan_url='synthetic-eod',alert_name='Synthetic',version='1',
        rules='Synthetic fixture only; not a live scanner',rights_reference='SYNTHETIC',
        enabled_until='2028-01-01T00:00:00Z',mode='synthetic_fixture')


def event(symbols,day='2026-11-05',complete=False):
    return fixture_snapshot(scanner(),symbols,day,NOW,complete=complete)


def drain(conn):
    while store.materialize_one(conn):pass


def test_35_28_7_replay_out_of_order_downtime_restart(isolated_url):
    continuing=['SYN'+str(i).zfill(3) for i in range(7)]
    new=['NEW'+str(i).zfill(3) for i in range(28)]
    today=event(continuing+new,complete=True)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert not store.accept(conn,today)['duplicate']
        assert store.accept(conn,today)['duplicate']
        assert store.rows(conn)['delivery_status']=='missing_delivery_not_verified_zero'
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        drain(conn)
        store.accept(conn,event(continuing+['OLD'],'2026-11-04',complete=True));drain(conn)
        rows=store.rows(conn,session='2026-11-05')
        assert rows['total']==35
        assert sum(r['match_status']=='continuing_observed' for r in rows['rows'])==7
        assert sum(r['match_status']=='new_vs_previous_snapshot' for r in rows['rows'])==28
        before=conn.execute('SELECT candidate_id,first_observed_at,last_observed_at FROM discovery.candidates ORDER BY 1').fetchall()
        assert store.accept(conn,today)['duplicate'];drain(conn)
        assert conn.execute('SELECT candidate_id,first_observed_at,last_observed_at FROM discovery.candidates ORDER BY 1').fetchall()==before
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(2,)
        assert len(store.feed(conn)['events'])==2
        assert store.rows(conn,session='2026-11-06')['delivery_status']=='missing_delivery_not_verified_zero'
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert store.rows(conn,session='2026-11-05')['total']==35
        with pytest.raises(psycopg.Error):conn.execute("UPDATE discovery.candidate_events SET envelope='{}'")


def test_alerts_partial_retry_and_current_stored_research(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path)
        store.accept(conn,event(['TEST','MISSING']));drain(conn)
        calls=[]
        def run(c,s,d):
            calls.append(s)
            return analyze(c,config,s,d,clock=lambda:MARKET_NOW)
        while store.research_one(conn,run):pass
        results={r['symbol']:r for r in store.rows(conn)['rows']}
        good=results['TEST']['research'];blocked=results['MISSING']['research']
        assert good['status']=='completed' and good['technical']['metrics']['sma20']=='105'
        assert good['listing_id']==listing and good['acquisition']['provider_requests']==0
        assert good['source_revision_ids'] and not good['evaluation_eligible']
        assert blocked['status']=='blocked' and blocked['reasons']==['nse_identity_missing_or_ambiguous']
        assert all(r['completeness']=='partial_unverified' for r in results.values())
        store.accept(conn,event(['TEST','MISSING']));drain(conn)
        assert store.research_one(conn,run) is None and len(calls)==2
        assert permitted_result(conn,config,good,clock=lambda:MARKET_NOW)['status']=='completed'
        Path(config.sources.grant_file).write_text('[]')
        denied=permitted_result(conn,config,good,clock=lambda:MARKET_NOW)
        assert denied['status']=='blocked' and 'technical' not in denied and not denied.get('listing_id')
        assert store.retry(conn,results['MISSING']['candidate_id'])
        assert not store.retry(conn,results['MISSING']['candidate_id'])


def test_bounded_retry_and_crash_rollback(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        store.accept(conn,event(['FAIL']));drain(conn)
        def fail(*a):raise RuntimeError('SECRET MUST NOT BE STORED')
        for _ in range(3):
            assert store.research_one(conn,fail)
            conn.execute("UPDATE discovery.candidates SET retry_at=now()")
        assert store.research_one(conn,fail) is None
        row=store.rows(conn)['rows'][0]
        assert row['research_status']=='failed' and row['error_code']=='RuntimeError'
        assert store.retry(conn,row['candidate_id'])
        with pytest.raises(RuntimeError):
            with conn.transaction():
                store.research_one(conn,lambda *a:dict(status='blocked',reasons=['missing']))
                raise RuntimeError('crash before commit')
        assert store.rows(conn)['rows'][0]['research_status']=='pending'


def test_receiver_auth_rejection_limits_and_durable_ack(isolated_url,tmp_path,monkeypatch):
    from app.chartink_receiver import app
    from app.research import db
    monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
    monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
    path=tmp_path/'scanner.json';path.write_text(scanner().model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(path))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    p=event(['INFY'])['payload'];p['webhook_url']='https://private.invalid/'+('w'*40)
    try:
        c=TestClient(app);url='/hooks/chartink/'+('w'*40)
        monkeypatch.delenv('CHARTINK_RECEIVER_ENABLED')
        assert c.post(url,json=p).status_code==503
        monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
        assert c.post('/hooks/chartink/bad',json=p).status_code==401
        assert c.post(url,json={**p,'scan_url':'wrong'}).status_code==422
        assert c.post(url,content=b'x'*65537,headers={'Content-Type':'application/json'}).status_code==413
        assert c.post(url,content='{}').status_code==415
        assert c.post(url,json=p).status_code==202
        assert c.post(url,json=p).json()['duplicate']
        assert c.get('/candidate-feed').status_code==401
        feed=c.get('/candidate-feed',headers={'Authorization':'Bearer '+'p'*40})
        assert feed.status_code==200 and len(feed.json()['events'])==1
        assert 'w'*40 not in feed.text
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert conn.execute('SELECT count(*) FROM discovery.candidate_rejections').fetchone()==(1,)
            assert conn.execute('SELECT status FROM discovery.candidate_event_state').fetchone()==('pending',)
            conn.execute('UPDATE discovery.candidate_rate SET attempts=60')
        assert c.post(url,json=p).status_code==429
    finally:app.dependency_overrides.clear()


def test_capacity_fails_closed_but_replays_still_ack(isolated_url,monkeypatch):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        monkeypatch.setattr(store,'MAX_EVENTS',1)
        e=event(['ONE']);store.accept(conn,e)
        assert store.accept(conn,e)['duplicate']
        with pytest.raises(OverflowError):store.accept(conn,event(['TWO']))
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(1,)


def test_outbound_recovery_checkpoint_is_atomic(isolated_url,tmp_path,monkeypatch):
    import json
    import io
    from worker import candidates
    from stock_discovery_analysis.chartink import normalize
    s=scanner();config=tmp_path/'scanner.json';config.write_text(s.model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(config))
    monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
    e=normalize(event(['ONE'])['payload'],s,NOW)
    page=dict(events=[dict(sequence=1,envelope=e)],next_cursor=1)
    class Opener:
        def open(self,request,timeout):
            assert timeout==15 and request.headers['Authorization']=='Bearer '+'p'*40
            return io.BytesIO(json.dumps(page).encode())
    monkeypatch.setattr(candidates,'build_opener',lambda *a:Opener())
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        page['next_cursor']=2
        with pytest.raises(ValueError,match='invalid_receiver_cursor'):candidates.pull(conn,'https://receiver.invalid')
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(0,)
        page['next_cursor']=1
        assert candidates.pull(conn,'https://receiver.invalid')==1
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        page.update(events=[],next_cursor=1)
        assert candidates.pull(conn,'https://receiver.invalid')==0
        assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(1,)
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(1,)
        with pytest.raises(ValueError):candidates.pull(conn,'http://receiver.invalid')


def test_unresolved_candidate_watchlist_and_asof_boundary(isolated_url,tmp_path,monkeypatch):
    from app.main import app
    from app.research import db
    from app import real_research
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'watchlist'))
    monkeypatch.delenv('REAL_RESEARCH_VIEW_CONFIG',raising=False)
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    try:
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            e=event(['UNRESOLVED']);store.accept(conn,e);drain(conn)
            key=store.rows(conn)['rows'][0]['watchlist_key']
            assert not store.asof_candidates(conn,e['scanner_key'],'2026-11-04T00:00:00Z')['events']
            assert len(store.asof_candidates(conn,e['scanner_key'],'2026-11-06T00:00:00Z')['events'])==1
        c=TestClient(app);h={'Authorization':'Bearer '+'o'*40}
        assert c.put('/v1/real-research/watchlist/'+key,headers=h,json={'note':'monitor until identity evidence exists'}).status_code==200
        assert c.get('/v1/real-research/candidates',headers=h).json()['total']==1
        assert c.get('/v1/real-research/candidates').status_code==401
        workbench=TestClient(app).get('/v1/real-research/workbench',headers=h).json()['rows']
        assert workbench[0]['unresolved_candidate'] and workbench[0]['symbol']=='UNRESOLVED'
        assert 'monitor until' in TestClient(app).get('/v1/real-research/watchlist',headers=h).text
        assert c.put('/v1/real-research/watchlist/CHARTINK:unknown:BAD',headers=h,json={}).status_code==404
    finally:app.dependency_overrides.clear()


def test_failed_event_is_retained_and_replayable(isolated_url):
    # An internal processing error is not a silently acknowledged empty universe.
    from psycopg.types.json import Jsonb
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        e=event(['SYN']);store.accept(conn,e)
        conn.execute("ALTER TABLE discovery.candidates ADD CONSTRAINT test_failure CHECK(false)")
        assert store.materialize_one(conn)==e['event_id']
        assert conn.execute('SELECT status,error_code FROM discovery.candidate_event_state').fetchone()==('failed','CheckViolation')
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(0,)
        conn.execute('ALTER TABLE discovery.candidates DROP CONSTRAINT test_failure')
        assert store.retry_event(conn,e['event_id'])
        drain(conn)
        assert store.rows(conn)['total']==1


def test_enriched_csv_restart_api_and_replay(isolated_url,monkeypatch):
    from stock_discovery_analysis.candidate_csv import events
    from app.main import app
    from app.research import db
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    raw=b'Symbol,symbol,close,volume,AVG_VOLUME20,EMA10,ema30\nINFY,infy,100,200,100,99,98\n'
    e=events(raw,scanner(),NOW,session='2026-11-05')[0][0]
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        store.accept(conn,e)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        drain(conn)
        assert store.accept(conn,e)['duplicate']
        assert store.rows(conn)['total']==1
        assert store.rows(conn)['rows'][0]['chartink_snapshot']['metrics']['relative_volume']=='2'
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    try:
        response=TestClient(app).get('/v1/real-research/candidates',headers={'Authorization':'Bearer '+'o'*40})
        assert response.status_code==200
        row=response.json()['rows'][0]
        assert row['chartink_snapshot']==e['enrichment']['INFY']
        assert row['completeness']=='partial_unverified'
    finally:app.dependency_overrides.clear()
