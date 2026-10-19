from fastapi.testclient import TestClient
from app.main import app


def test_real_research_auth_and_no_synthetic_fallback(monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    monkeypatch.setenv('COOKIE_SECURE','false')
    c=TestClient(app)
    assert c.get('/v1/real-research/status').status_code==401
    c.post('/api/v1/session',json={'token':'x'*40})
    response=c.get('/v1/real-research/status')
    assert response.status_code==200
    body=response.json()
    assert body['status']=='blocked' and body['qualified'] is False and body['actionable'] is False
    assert body['recommendations']==[] and body['price_series']==[] and body['analysis_history']==[]
    assert body['forward_paper']['status']=='blocked'
    assert body['scheduler']['outcomes']=='blocked'
