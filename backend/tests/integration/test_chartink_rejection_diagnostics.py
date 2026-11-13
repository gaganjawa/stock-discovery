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
        # Only partial provider preview is verified: keep columns rejected pending actual evidence.
        customized={**base,'columns':[{'symbol':'SYN095','close':123}]}
        assert client.post(url,json=customized).status_code==422
        assert client.get('/candidate-health').status_code==401
        private=client.get('/candidate-health',headers={'Authorization':'Bearer '+'p'*40}).json()
        assert private['stored_events']==0 and private['rejection_records']==1
        record=private['rejection_diagnostics']['records'][0]
        assert record['reason']=='invalid_payload_fields'
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
            assert conn.execute('SELECT reason FROM discovery.candidate_rejections').fetchone()==('invalid_payload_fields',)
        malformed=b'{"stocks":"SECRET","stocks":"OTHER"}'
        assert client.post(url,content=malformed,headers={'Content-Type':'application/json'}).status_code==422
        assert 'SECRET' not in chartink_diagnostics.FILE.read_text()
        assert capsys.readouterr().out==''
    finally:app.dependency_overrides.clear()
