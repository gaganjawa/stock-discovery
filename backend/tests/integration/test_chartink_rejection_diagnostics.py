"""STK-095 real PostgreSQL, fabricated values; no live webhook or provider calls."""
import json
import os
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.chartink_receiver import app
from app.research import db
from app import chartink_diagnostics
from test_candidates import isolated_url,scanner

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def test_rejection_shape_is_private_and_original_format_commits_and_replays(isolated_url,tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
    monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    monkeypatch.setattr(chartink_diagnostics,'FILE',tmp_path/'shapes.json')
    config=tmp_path/'scanner.json';config.write_text(scanner().model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(config))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    try:
        client=TestClient(app);url='/hooks/chartink/'+'w'*40
        base=dict(stocks='SYN095',trigger_prices='123',triggered_at='5:00 pm',
            scan_name=scanner().scan_name,scan_url=scanner().scan_url,alert_name=scanner().alert_name,
            webhook_url='https://private.invalid/'+('w'*40))
        # Incomplete column rows remain rejected under the observed exact-field adapter.
        customized={**base,'columns':[{'symbol':'SYN095','close':123}]}
        assert client.post(url,json=customized).status_code==422
        assert client.get('/candidate-health').status_code==401
        private=client.get('/candidate-health',headers={'Authorization':'Bearer '+'p'*40}).json()
        assert private['stored_events']==0 and private['rejection_records']==1
        record=private['rejection_diagnostics']['records'][0]
        assert record['reason']=='invalid_columns_fields'
        assert record['shape']['fields']['columns']['type']=='array'
        for value in ('SYN095','123','private.invalid','w'*40):assert value not in json.dumps(record)
        # Original documented format remains durable, deduplicated and authenticated.
        accepted=client.post(url,json=base)
        assert accepted.status_code==202
        assert client.post(url,json=base).json()['duplicate']
        assert client.get('/candidate-feed').status_code==401
        feed=client.get('/candidate-feed',headers={'Authorization':'Bearer '+'p'*40})
        assert feed.status_code==200 and len(feed.json()['events'])==1
        event=feed.json()['events'][0]['envelope']
        assert event['symbols']==['SYN095'] and event['version']=='chartink-event-v1'
        assert 'webhook_url' not in event['payload'] and 'w'*40 not in json.dumps(event)
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(1,)
            assert conn.execute('SELECT reason FROM discovery.candidate_rejections').fetchone()==('invalid_columns_fields',)
        malformed=b'{"stocks":"SECRET","stocks":"OTHER"}'
        assert client.post(url,content=malformed,headers={'Content-Type':'application/json'}).status_code==422
        assert 'SECRET' not in chartink_diagnostics.FILE.read_text()
        assert capsys.readouterr().out==''
    finally:app.dependency_overrides.clear()


def test_observed_provider_test_and_columns_delivery_persistence_feed_and_worker(isolated_url,tmp_path,monkeypatch):
    from test_chartink_columns import provider_payload,candidate_payload
    from stock_discovery_analysis import candidate_store as store
    from stock_discovery_analysis.chartink import normalize
    from datetime import datetime
    monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
    monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
    monkeypatch.delenv('CHARTINK_REJECTION_DIAGNOSTICS',raising=False)
    # Provider transport mode, not the earlier synthetic_enrichment_v1 extension.
    config=scanner().model_copy(update={'mode':'provider_alert'})
    path=tmp_path/'scanner';path.write_text(config.model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(path))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as conn:yield conn
    app.dependency_overrides[db]=connection
    def identity(p):
        return {**p,**{k:getattr(config,k) for k in ('scan_name','scan_url','alert_name')}}
    try:
        client=TestClient(app);url='/hooks/chartink/'+'w'*40
        probe=identity(provider_payload())
        response=client.post(url,json=probe)
        assert response.status_code==202 and response.json()['delivery_kind']=='provider_test'
        assert client.post(url,json=probe).json()['duplicate']
        headers={'Authorization':'Bearer '+'p'*40}
        health=client.get('/candidate-health',headers=headers).json()
        assert health['provider_test_events']==1 and health['candidate_delivery_events']==0
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert store.materialize_one(conn)
            for table in ('candidate_sessions','candidates','candidate_matches','candidate_research_runs'):
                assert conn.execute('SELECT count(*) FROM discovery.'+table).fetchone()==(0,)
        live=identity(candidate_payload())
        result=client.post(url,json=live)
        assert result.status_code==202 and result.json()['delivery_kind']=='candidate_alert'
        assert client.post(url,json=live).json()['duplicate']
        assert client.get('/candidate-feed').status_code==401
        page=client.get('/candidate-feed',headers=headers).json()
        assert len(page['events'])==2
        for item in page['events']:
            e=item['envelope']
            assert normalize(e['payload'],config,datetime.fromisoformat(e['received_at']))==e
            assert 'webhook_url' not in e['payload']
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert store.materialize_one(conn)
            assert store.materialize_one(conn) is None
            assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(1,)
            assert conn.execute('SELECT count(*) FROM discovery.candidate_sessions').fetchone()==(1,)
            assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(2,)
            assert store.rows(conn)['rows'][0]['chartink_snapshot']['values']['rsi14']=='60'
        health=client.get('/candidate-health',headers=headers).json()
        assert health['provider_test_events']==health['candidate_delivery_events']==1
    finally:app.dependency_overrides.clear()


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
    envelope=events[0]['envelope']
    assert len(envelope['symbols'])==len(envelope['enrichment'])==count
    stored_bytes=len(json.dumps(envelope).encode())
    assert stored_bytes<=store.MAX_EVENT_BYTES
    if count>=40:assert stored_bytes>MAX_BYTES
    assert 'webhook_url' not in envelope['payload'] and 'REDACTED' not in json.dumps(envelope)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert conn.execute('SELECT envelope FROM discovery.candidate_events').fetchone()[0]==envelope
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
        limits.setattr(store,'MAX_EVENT_BYTES',65536)
        response=client.post(url,json=payload)
        assert response.status_code==413 and 'storage limit' in response.text
    with monkeypatch.context() as limits:
        limits.setattr(store,'MAX_EVENTS',0)
        assert client.post(url,json=payload).status_code==503
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


def test_decimal_overflow_is_durable_private_422(columns_receiver,isolated_url,capsys):
    client,url,config=columns_receiver
    payload=batch_payload(config,1)
    payload['columns'][0]['AVG_VOLUME20']='1e-1000000'
    response=client.post(url,json=payload)
    assert response.status_code==422 and response.json()['detail']=='invalid_enrichment_number'
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        assert conn.execute('SELECT reason FROM discovery.candidate_rejections').fetchone()==('invalid_enrichment_number',)
        assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(0,)
    assert client.get('/candidate-health').status_code==401
    record=client.get('/candidate-health',headers={'Authorization':'Bearer '+'p'*40}).json()['rejection_diagnostics']['records'][0]
    assert record['reason']=='invalid_enrichment_number'
    assert record['shape']['fields']['columns']['sampled_shapes'][0]['fields']['AVG_VOLUME20']['type']=='string'
    for value in ('1e-1000000','SYN000','REDACTED','w'*40):assert value not in json.dumps(record)
    assert capsys.readouterr().out==''
