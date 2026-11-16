"""STK-095 real PostgreSQL, fabricated values; no live webhook or provider calls."""
import json
import os
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.chartink_receiver import app
from app.research import db
from app import chartink_diagnostics
from stock_discovery_analysis.chartink_columns import COLUMNS
from test_candidates import isolated_url,scanner

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def test_raw_schema_drift_is_durable_quarantined_and_replayable(columns_receiver,isolated_url,monkeypatch):
    from stock_discovery_analysis import candidate_store as store,chartink_columns
    client,url,config=columns_receiver
    payload=batch_payload(config,1)
    payload['columns'][0]['Future EMA']=payload['columns'][0].pop('EMA10')
    first=client.post(url,json=payload)
    assert first.status_code==202 and first.json()['delivery_kind']=='unclassified'
    eid=first.json()['event_id']
    assert client.post(url,json=payload).json()['duplicate']
    good=batch_payload(config,1);good['stocks']='GOOD';good['columns'][0]['symbol']='GOOD'
    assert client.post(url,json=good).status_code==202
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        original=conn.execute('SELECT envelope FROM discovery.candidate_events WHERE event_id=%s',(eid,)).fetchone()[0]
        assert 'Future EMA' in original['raw_json'] and 'w'*40 not in original['raw_json']
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(0,)
        assert store.materialize_one(conn)==eid
        state=conn.execute('SELECT status,error_code,diagnostics FROM discovery.candidate_event_state WHERE event_id=%s',(eid,)).fetchone()
        assert state[:2]==('failed','invalid_columns_fields')
        assert state[2]['columns'][0]['missing']==['EMA10']
        assert state[2]['columns'][0]['extra']==['Future EMA']
        assert state[2]['columns'][0]['types']['Future EMA']=='number'
        assert store.materialize_one(conn)  # poison receipt cannot block later candidates
        assert store.rows(conn)['total']==1
        assert store.retry_event(conn,eid)
        assert not store.retry_event(conn,eid)
        # Synthetic future parser support; no speculative production alias is added.
        original_adapt=chartink_columns.adapt
        def future(rows,symbols):
            rows=[{('EMA10' if k=='Future EMA' else k):v for k,v in row.items()} for row in rows]
            return original_adapt(rows,symbols)
        monkeypatch.setattr(chartink_columns,'adapt',future)
        assert store.materialize_one(conn)==eid
        assert store.rows(conn)['total']==2
        assert conn.execute('SELECT envelope FROM discovery.candidate_events WHERE event_id=%s',(eid,)).fetchone()[0]==original
        assert conn.execute('SELECT status,deliveries,diagnostics FROM discovery.candidate_event_state WHERE event_id=%s',(eid,)).fetchone()==('completed',2,None)
        assert not store.retry_event(conn,eid)
        assert client.post(url,json=payload).json()['duplicate']
        assert store.materialize_one(conn) is None


@pytest.mark.parametrize('triggered_at',['11:45 am','7:43 pm','12:00 am'])
def test_observed_provider_test_is_classified_only_after_durable_intake(columns_receiver,isolated_url,triggered_at):
    from test_chartink_columns import provider_payload
    from stock_discovery_analysis import candidate_store as store
    client,url,config=columns_receiver
    payload={**provider_payload(),**{k:getattr(config,k) for k in ('scan_name','scan_url','alert_name')},'triggered_at':triggered_at}
    response=client.post(url,json=payload)
    assert response.status_code==202 and response.json()['delivery_kind']=='unclassified'
    assert client.post(url,json=payload).json()['duplicate']
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert store.materialize_one(conn)
        parsed=conn.execute('SELECT parsed_envelope FROM discovery.candidate_event_state').fetchone()[0]
        assert parsed['delivery_kind']=='provider_test'
        for table in ('candidate_sessions','candidates','candidate_matches','candidate_research_runs'):
            assert conn.execute('SELECT count(*) FROM discovery.'+table).fetchone()==(0,)
        invalid=client.post(url,json={**payload,'triggered_at':'13:43 pm'})
        assert invalid.status_code==202
        assert store.materialize_one(conn)
        assert conn.execute("SELECT error_code FROM discovery.candidate_event_state WHERE status='failed'").fetchone()==('invalid_provider_test_payload',)


@pytest.fixture
def columns_receiver(isolated_url,tmp_path,monkeypatch):
    monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
    monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    monkeypatch.setattr(chartink_diagnostics,'FILE',tmp_path/'shapes.json')
    config=scanner().model_copy(update={'mode':'provider_alert'})
    path=tmp_path/'scanner';path.write_text(config.model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(path))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    try:
        with TestClient(app) as client:
            yield client,'/hooks/chartink/'+'w'*40,config
    finally:app.dependency_overrides.clear()


def batch_payload(config,count):
    from test_chartink_columns import candidate_payload
    p=candidate_payload()
    p['columns'][0].update(sector='Synthetic diversified industrial manufacturing sector',
        industry='Synthetic diversified industrial manufacturing industry')
    p.update({k:getattr(config,k) for k in ('scan_name','scan_url','alert_name')})
    symbols=['SYN'+str(i).zfill(3) for i in range(count)]
    p.update(stocks=','.join(symbols),trigger_prices=','.join(['100']*count),
        columns=[{**p['columns'][0],'symbol':symbol} for symbol in symbols])
    return p


@pytest.mark.parametrize('count',[35,40,50,150])
def test_columns_batches_commit_replay_and_authenticated_feed(columns_receiver,isolated_url,count):
    from stock_discovery_analysis import candidate_store as store
    from stock_discovery_analysis.chartink import MAX_BYTES
    client,url,config=columns_receiver
    payload=batch_payload(config,count)
    assert len(json.dumps(payload).encode())<MAX_BYTES
    result=client.post(url,json=payload)
    assert result.status_code==202,result.text
    assert client.post(url,json=payload).json()['duplicate']
    assert client.get('/candidate-feed').status_code==401
    events=client.get('/candidate-feed',headers={'Authorization':'Bearer '+'p'*40}).json()['events']
    assert len(events)==1
    raw=events[0]['envelope']
    from stock_discovery_analysis.chartink_intake import parse
    envelope=parse(raw)
    assert len(envelope['symbols'])==len(envelope['enrichment'])==count
    stored_bytes=len(json.dumps(envelope).encode())
    assert stored_bytes<=store.MAX_EVENT_BYTES
    if count>=40:assert stored_bytes>MAX_BYTES
    assert 'webhook_url' not in envelope['payload'] and 'REDACTED' not in json.dumps(envelope)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert conn.execute('SELECT envelope FROM discovery.candidate_events').fetchone()[0]==raw
        assert conn.execute('SELECT deliveries FROM discovery.candidate_event_state').fetchone()==(2,)
        assert store.materialize_one(conn)
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(count,)


def test_request_storage_and_inbox_capacity_failures(columns_receiver,isolated_url,monkeypatch):
    from stock_discovery_analysis import candidate_store as store
    client,url,config=columns_receiver
    # Real transport bound, before persistence.
    assert client.post(url,json=batch_payload(config,500)).status_code==413
    payload=batch_payload(config,40)
    with monkeypatch.context() as limits:
        limits.setattr(store,'MAX_EVENT_BYTES',64)
        response=client.post(url,json=payload)
        assert response.status_code==413 and 'storage limit' in response.text
        assert chartink_diagnostics.read()['records'][-1]['reason']=='event_too_large'
    with monkeypatch.context() as limits:
        limits.setattr(store,'MAX_EVENTS',0)
        assert client.post(url,json=payload).status_code==503
        assert chartink_diagnostics.read()['records'][-1]['reason']=='inbox_capacity'
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(0,)
        assert conn.execute('SELECT count(*) FROM discovery.candidate_event_state').fetchone()==(0,)
        with pytest.raises(ValueError,match='event_too_large'):
            store.accept(conn,{'oversized':'x'*store.MAX_EVENT_BYTES})
    assert client.post(url,json=payload).status_code==202
    with monkeypatch.context() as limits:
        limits.setattr(store,'MAX_EVENTS',1)
        assert client.post(url,json=payload).json()['duplicate']
        assert client.post(url,json=batch_payload(config,50)).status_code==503


def test_decimal_overflow_is_durable_quarantine(columns_receiver,isolated_url):
    from stock_discovery_analysis import candidate_store as store
    client,url,config=columns_receiver
    payload=batch_payload(config,1);payload['columns'][0]['AVG_VOLUME20']='1e-1000000'
    assert client.post(url,json=payload).status_code==202
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert store.materialize_one(conn)
        state=conn.execute('SELECT error_code,diagnostics FROM discovery.candidate_event_state').fetchone()
        assert state[0]=='invalid_enrichment_number'
        assert state[1]['columns'][0]['types']['AVG_VOLUME20']=='string'
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(0,)


def test_large_envelope_backlog_replays_with_bounded_pages(columns_receiver,isolated_url,monkeypatch):
    import io
    from datetime import datetime,timezone
    from urllib.parse import urlsplit,parse_qs
    from worker import candidates
    from stock_discovery_analysis.chartink import normalize
    client,url,config=columns_receiver
    events=[]
    for index in range(10):
        payload=batch_payload(config,150);payload['triggered_at']=f'1:0{index} pm'
        events.append({'sequence':index+1,'envelope':normalize(payload,config,datetime.now(timezone.utc))})
    assert len(json.dumps(events).encode())>2*1024*1024
    class Opener:
        def open(self,request,timeout):
            query=parse_qs(urlsplit(request.full_url).query)
            assert query['limit']==['1']
            after=int(query['after'][0]);page=events[after:after+1]
            return io.BytesIO(json.dumps({'events':page,'next_cursor':after+len(page)}).encode())
    monkeypatch.setattr(candidates,'build_opener',lambda *args:Opener())
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        for _ in events:assert candidates.pull(conn,'https://receiver.invalid')==1
        assert candidates.pull(conn,'https://receiver.invalid')==0
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(10,)
        assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(10,)


@pytest.mark.parametrize('body',[b'{"password":"PRIVATE",bad',b'{"stocks":"A","stocks":"B"}',b'[]'])
def test_malformed_and_unknown_shapes_are_durable_quarantine(columns_receiver,isolated_url,body):
    from stock_discovery_analysis import candidate_store as store
    client,url,config=columns_receiver
    response=client.post(url,content=body,headers={'Content-Type':'application/json'})
    assert response.status_code==202
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert store.materialize_one(conn)
        assert conn.execute('SELECT status FROM discovery.candidate_event_state').fetchone()==('failed',)
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(0,)
        assert 'PRIVATE' not in json.dumps(conn.execute('SELECT envelope FROM discovery.candidate_events').fetchone()[0])


def test_raw_cursor_isolation_interruption_and_replay(columns_receiver,isolated_url,tmp_path,monkeypatch):
    import io
    from contextlib import contextmanager
    from urllib.parse import urlsplit,parse_qs
    from worker import candidates
    from stock_discovery_analysis import candidate_store as store,chartink_intake
    client,url,config=columns_receiver
    bad=batch_payload(config,1);del bad['columns'][0]['EMA10']
    bad_id=client.post(url,json=bad).json()['event_id']
    good_id=client.post(url,json=batch_payload(config,1)).json()['event_id']
    def open_feed(self,request,timeout):
        cursor=int(parse_qs(urlsplit(request.full_url).query)['after'][0])
        with psycopg.connect(isolated_url,autocommit=True) as remote:
            return io.BytesIO(json.dumps(store.feed(remote,after=cursor,limit=1)).encode())
    monkeypatch.setattr(candidates,'build_opener',lambda *a:type('Feed',(),{'open':open_feed})())
    with contextmanager(isolated_url_fixture())() as local:
        with psycopg.connect(local,autocommit=True) as conn:
            assert candidates.pull(conn,'https://receiver.invalid')==1
            assert candidates.pull(conn,'https://receiver.invalid')==1
            assert candidates.pull(conn,'https://receiver.invalid')==0
            assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(2,)
            original=chartink_intake.parse
            def interrupted(*a,**k):raise KeyboardInterrupt('synthetic interruption')
            with monkeypatch.context() as patch:
                patch.setattr(chartink_intake,'parse',interrupted)
                with pytest.raises(KeyboardInterrupt):store.materialize_one(conn)
            assert conn.execute('SELECT count(*) FROM discovery.candidate_event_state WHERE status=\'pending\'').fetchone()==(2,)
            assert store.materialize_one(conn)==bad_id
            assert store.materialize_one(conn)==good_id
            assert store.rows(conn)['total']==1
            assert store.retry_event(conn,bad_id)
            assert store.materialize_one(conn)==bad_id  # unchanged parser -> same quarantine
            assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(2,)
            assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(2,)
            assert store.rows(conn)['total']==1


def isolated_url_fixture():
    # Fresh local inbox, separate from the fixture's remote receiver database.
    from test_candidates import isolated_url
    return isolated_url.__wrapped__


def test_legacy_to_raw_duplicate_keeps_candidate_and_existing_research(isolated_url):
    from datetime import datetime
    from test_candidates import event
    from stock_discovery_analysis import candidate_store as store
    from stock_discovery_analysis.chartink_intake import capture
    original=event(['INFY'])
    raw=capture(json.dumps(original['payload']).encode(),scanner(),datetime.fromisoformat(original['received_at']))
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        store.accept(conn,original);store.materialize_one(conn)
        conn.execute("UPDATE discovery.candidates SET research_status='completed',result='{}'")
        store.accept(conn,raw);store.materialize_one(conn)
        store.accept(conn,raw)
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(1,)
        assert conn.execute('SELECT research_status FROM discovery.candidates').fetchone()==('completed',)
        assert store.materialize_one(conn) is None
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()==(0,)
        assert conn.execute('SELECT count(*) FROM discovery.candidate_matches').fetchone()==(2,)
