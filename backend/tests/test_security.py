from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.security import LoginLimiter
from stock_discovery_analysis.runtime import validate_private


def test_login_limits_ignore_spoofed_forwarding_headers(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN", "x" * 40)
    monkeypatch.setattr(app.state, "login_limiter", LoginLimiter())
    c = TestClient(app)
    for i in range(5):
        assert c.post("/api/v1/session", json={"token": "wrong"},
                      headers={"X-Forwarded-For": str(i)}).status_code == 401
    r = c.post("/api/v1/session", json={"token": "x" * 40})
    assert r.status_code == 429 and r.headers["retry-after"] == "60"


def test_limiter_recovers_and_bounds_unique_peers():
    now = [0]
    limiter = LoginLimiter(lambda: now[0])
    assert all(limiter.allow(str(i)) for i in range(20))
    assert not limiter.allow("new")
    assert len(limiter.peers) == 20
    now[0] = 61
    assert limiter.allow("new")
    assert len(limiter.peers) == 1


def test_private_config_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOYMENT_MODE", "private")
    monkeypatch.setenv("APP_ORIGIN", "http://localhost")
    with pytest.raises(ValueError): validate_private()
    monkeypatch.setenv("APP_ORIGIN", "https://stock.example.ts.net")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(ValueError): validate_private()
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("CODE_VERSION", "test-commit")
    p = tmp_path / "db"
    monkeypatch.setenv("DATABASE_URL_FILE", str(p))
    p.write_text("postgresql://stk_owner:" + "x"*40 + "@database/stock_discovery")
    with pytest.raises(ValueError): validate_private()
    p.write_text("postgresql://stk_runtime:" + "x"*40 + "@database/stock_discovery")
    validate_private()


def test_private_startup_requires_owner_secret_file(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOYMENT_MODE", "private")
    monkeypatch.setenv("APP_ORIGIN", "https://stock.example.ts.net")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("CODE_VERSION", "test")
    p = tmp_path / "db"
    p.write_text("postgresql://stk_runtime:" + "x"*40 + "@database/stock_discovery")
    monkeypatch.setenv("DATABASE_URL_FILE", str(p))
    monkeypatch.delenv("AUTH_TOKEN_FILE", raising=False)
    with pytest.raises(ValueError), TestClient(app): pass
