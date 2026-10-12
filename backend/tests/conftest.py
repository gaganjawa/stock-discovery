import pytest


@pytest.fixture(autouse=True)
def fresh_login_limiter(monkeypatch):
    from app.main import app
    from app.security import LoginLimiter
    monkeypatch.setattr(app.state, "login_limiter", LoginLimiter())
