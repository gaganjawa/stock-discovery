from fastapi.testclient import TestClient
from app.main import app


def test_protected_endpoints_fail_closed(monkeypatch):
    c=TestClient(app)
    monkeypatch.delenv('AUTH_TOKEN',raising=False)
    assert c.get('/api/v1/dashboard').status_code==503
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    assert c.get('/api/v1/dashboard').status_code==401
    assert c.post('/api/v1/session',json={'token':'wrong'}).status_code==401


def test_cookie_session_origin_and_logout(monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    monkeypatch.setenv('COOKIE_SECURE','false')
    monkeypatch.setenv('APP_ORIGIN','http://testserver')
    c=TestClient(app)
    r=c.post('/api/v1/session',json={'token':'x'*40})
    assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
    assert c.get('/api/v1/session').status_code==200
    assert c.delete('/api/v1/session',headers={'origin':'https://untrusted.invalid'}).status_code==403
    assert c.delete('/api/v1/session',headers={'origin':'http://testserver'}).status_code==200
    assert c.get('/api/v1/session').status_code==401


def test_revocation_rejects_existing_cookie(monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','x'*40);monkeypatch.setenv('COOKIE_SECURE','false')
    c=TestClient(app);c.post('/api/v1/session',json={'token':'x'*40})
    monkeypatch.setenv('AUTH_TOKEN','y'*40)
    assert c.get('/api/v1/session').status_code==401


def test_unicode_credentials_are_rejected_without_server_error(monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    c=TestClient(app)
    assert c.post('/api/v1/session',json={'token':'wrong-🔒'}).status_code==401
    assert c.get('/api/v1/session',headers={b'authorization':b'Bearer wrong-\xc3\xa9'}).status_code==401


def test_expired_and_tampered_sessions_are_rejected(monkeypatch):
    from app import auth
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    monkeypatch.setenv('COOKIE_SECURE','false')
    c=TestClient(app)
    c.post('/api/v1/session',json={'token':'x'*40})
    cookie=c.cookies.get('stk_session')
    c.cookies.clear()
    c.cookies.set('stk_session',cookie+'tampered')
    assert c.get('/api/v1/session').status_code==401
    c.cookies.set('stk_session',cookie)
    now=auth.time.time()
    monkeypatch.setattr(auth.time,'time',lambda:now+8*3600+1)
    assert c.get('/api/v1/session').status_code==401
