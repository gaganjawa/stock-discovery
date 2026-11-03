from fastapi.testclient import TestClient
from app.main import app


def test_real_research_auth_and_no_synthetic_fallback(monkeypatch):
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    monkeypatch.setenv('COOKIE_SECURE','false')
    c=TestClient(app)
    monkeypatch.delenv('REAL_RESEARCH_VIEW_CONFIG',raising=False)
    assert c.get('/v1/real-research/companies').status_code==401
    assert c.get('/v1/real-research/status').status_code==401
    c.post('/api/v1/session',json={'token':'x'*40})
    response=c.get('/v1/real-research/status')
    assert response.status_code==200
    assert c.get('/v1/real-research/companies').status_code==503
    body=response.json()
    assert body['status']=='blocked' and body['qualified'] is False and body['actionable'] is False
    assert body['recommendations']==[] and body['price_series']==[] and body['analysis_history']==[]
    assert body['forward_paper']['status']=='blocked'
    assert body['scheduler']['outcomes']=='blocked'
    assert 'real_policies_required' in body['publication_blockers']
    assert 'cash_flow_reconciliation_unresolved' in body['publication_blockers']


def test_unmigrated_database_is_not_reported_as_permission_denial(monkeypatch,tmp_path):
    from app import real_research
    monkeypatch.setenv('AUTH_TOKEN','x'*40)
    monkeypatch.setenv('COOKIE_SECURE','false')
    monkeypatch.delenv('REAL_RESEARCH_VIEW_CONFIG',raising=False)
    monkeypatch.setattr(real_research,'schema_state',lambda:dict(schema_version='0013',required='0015',state='migration_required'))
    c=TestClient(app);c.post('/api/v1/session',json={'token':'x'*40})
    body=c.get('/v1/real-research/status').json()
    assert body['database']['state']=='migration_required' and body['blockers'][0].startswith('Database migration required')
    assert body['readiness']['level']=='none' and body['qualified'] is False
    error=real_research.denied()
    assert error.status_code==503 and error.detail.startswith('Database migration required')
    monkeypatch.setattr(real_research,'schema_state',lambda:dict(schema_version='0015',required='0015',state='current'))
    assert real_research.denied().status_code==403
