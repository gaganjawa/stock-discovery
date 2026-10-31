"""A full-evidence request cannot silently become a technical-only job."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db

@pytest.mark.parametrize('path,extra',[
    ('/scan',{'include_financial':True}),('/replay-job',{'include_financial':True}),
    ('/analysis',{'historical_ai_run_id':'stored-run'}),
])
def test_unsupported_evidence_options_are_rejected_before_database_use(monkeypatch,path,extra):
    monkeypatch.setenv('AUTH_TOKEN','s'*40)
    app.dependency_overrides[db]=lambda:object()
    try:
        c=TestClient(app,headers={'Authorization':'Bearer '+'s'*40})
        r=c.post('/api/v1'+path,json=dict(dataset_version='SYN-test',instrument_id='SYN-ALPHA',date='2025-06-25',**extra))
        assert r.status_code==400
        assert 'financial' in r.json()['detail'].lower()
    finally:app.dependency_overrides.pop(db,None)
