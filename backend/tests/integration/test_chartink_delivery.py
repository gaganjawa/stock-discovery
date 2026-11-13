"""STK-097 synthetic HTTPS delivery through separate receiver and Mac databases."""
import os
import socket
import ssl
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime,timezone
import psycopg
import uvicorn
import pytest

pytestmark=pytest.mark.skipif(not os.getenv("STK_TEST_DATABASE_URL"),reason="requires disposable PostgreSQL")
from fastapi.testclient import TestClient
from test_candidates import isolated_url,scanner
from stock_discovery_analysis.chartink import normalize
from stock_discovery_analysis import candidate_store as store
from worker.candidates import pull


def test_https_delivery_reconnect_and_candidates_api(tmp_path,monkeypatch):
    from app.chartink_receiver import app as receiver
    from app.main import app
    from app.research import db
    with contextmanager(isolated_url.__wrapped__)() as remote, contextmanager(isolated_url.__wrapped__)() as local:
        cert=tmp_path/'cert.pem';key=tmp_path/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
            '-keyout',str(key),'-out',str(cert),'-subj','/CN=localhost',
            '-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
        monkeypatch.setenv('SSL_CERT_FILE',str(cert))
        monkeypatch.setenv('CHARTINK_RECEIVER_ENABLED','true')
        monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET','w'*40)
        monkeypatch.setenv('CHARTINK_PULL_SECRET','p'*40)
        monkeypatch.setenv('AUTH_TOKEN','o'*40)
        config=tmp_path/'scanner.json';config.write_text(scanner().model_dump_json())
        monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(config))
        def remote_db():
            with psycopg.connect(remote,autocommit=True) as c:yield c
        def local_db():
            with psycopg.connect(local,autocommit=True) as c:yield c
        receiver.dependency_overrides[db]=remote_db
        app.dependency_overrides[db]=local_db
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(receiver,ssl_certfile=str(cert),ssl_keyfile=str(key),access_log=False,log_level='critical'))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
        try:
            for _ in range(100):
                if server.started:break
                time.sleep(.05)
            assert server.started
            payload=normalize(dict(stocks='SYN097',trigger_prices='100',triggered_at='6:00 pm',
                scan_name=scanner().scan_name,scan_url=scanner().scan_url,alert_name=scanner().alert_name),scanner(),datetime.now(timezone.utc))['payload']
            import urllib.request,json
            url=f'https://localhost:{port}'
            request=urllib.request.Request(url+'/hooks/chartink/'+'w'*40,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=10) as response:assert response.status==202
            with psycopg.connect(remote,autocommit=True) as c:
                assert c.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()[0]==1
            with psycopg.connect(local,autocommit=True) as c:assert pull(c,url)==1
            with psycopg.connect(local,autocommit=True) as c:
                assert pull(c,url)==0
                store.materialize_one(c)
                assert store.rows(c)['total']==1
            with urllib.request.urlopen(request,timeout=10) as response:assert json.load(response)['duplicate']
            result=TestClient(app).get('/v1/real-research/candidates',headers={'Authorization':'Bearer '+'o'*40})
            assert result.status_code==200
            assert result.json()['rows'][0]['symbol']=='SYN097'
            assert not result.json()['actionable']
            assert TestClient(receiver).get('/healthz').json()['database']=='available'
            assert TestClient(receiver).get('/candidate-health').status_code==401
            health=TestClient(receiver).get('/candidate-health?after=0',headers={'Authorization':'Bearer '+'p'*40}).json()
            assert health['events_after_cursor']==1 and health['stored_events']==1
            assert health['coverage']=='unknown_partial_alerts'
            assert 'w'*40 not in str(health)
            if os.getenv('STK097_BROWSER')=='1':
                monkeypatch.setenv('COOKIE_SECURE','false')
                monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'watchlist'))
                import sys
                from pathlib import Path
                sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
                from chartink_browser_acceptance import verify
                verify(app)
        finally:
            server.should_exit=True;thread.join(timeout=10);sock.close()
            receiver.dependency_overrides.clear();app.dependency_overrides.clear()


def test_receiver_role_cannot_read_private_evidence(tmp_path):
    from pathlib import Path
    from uuid import uuid4
    from psycopg import sql
    with contextmanager(isolated_url.__wrapped__)() as url:
        with psycopg.connect(url,autocommit=True) as c:
            role='stk097_'+uuid4().hex[:12]
            # Role and grants roll back together; no shared role persists.
            with c.transaction():
                c.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
                script=(Path(__file__).resolve().parents[3]/'deploy/chartink/grants.sql').read_text()
                for line in script.splitlines():
                    if line.startswith('GRANT ') and 'ON DATABASE' not in line:
                        c.execute(line.replace('chartink_receiver',role))
                c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
                assert c.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(0,)
                # STK-095: expanded rows and exact JSONB size checks need no extra grants.
                from test_chartink_rejection_diagnostics import batch_payload
                e=normalize(batch_payload(scanner(),150),scanner(),datetime.now(timezone.utc))
                assert not store.accept(c,e)['duplicate']
                assert store.accept(c,e)['duplicate']
                assert store.feed(c)['events'][0]['envelope']==e
                assert c.execute('SELECT octet_length(envelope::text)>65536 FROM discovery.candidate_events').fetchone()==(True,)
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with c.transaction():c.execute('ALTER TABLE discovery.candidate_events DROP CONSTRAINT candidate_events_envelope_check')
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with c.transaction():c.execute('SELECT * FROM discovery.revisions LIMIT 1')
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with c.transaction():c.execute('DELETE FROM discovery.candidate_events')
                c.execute('RESET ROLE')
                c.execute('ROLLBACK')
