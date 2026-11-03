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
    monkeypatch.setattr(real_research,'schema_state',lambda:dict(state='migration_required'))
    c=TestClient(app);c.post('/api/v1/session',json={'token':'x'*40})
    body=c.get('/v1/real-research/status').json()
    assert body['database']=={'state':'migration_required'} and body['blockers'][0].startswith('Database migration required')
    assert body['readiness']['level']=='none' and body['qualified'] is False
    error=real_research.denied()
    assert error.status_code==503 and error.detail.startswith('Database migration required')
    monkeypatch.setattr(real_research,'schema_state',lambda:dict(state='current'))
    assert real_research.denied().status_code==403


def test_pilot_coverage_reports_each_company_without_inventing_prices(monkeypatch,tmp_path):
    import json
    from app import real_research, research
    from stock_discovery_analysis import real_views
    config=tmp_path/'view.json'
    config.write_text(json.dumps({'sources':{'grant_file':str(tmp_path/'g.json'),'retention_days':30},'listing_ids':['NSE:A','NSE:B','NSE:C','NSE:D']}))
    monkeypatch.setenv('AUTH_TOKEN','x'*40);monkeypatch.setenv('COOKIE_SECURE','false')
    monkeypatch.setenv('REAL_RESEARCH_VIEW_CONFIG',str(config))
    monkeypatch.setattr(real_research,'schema_state',lambda:dict(state='current'))
    def company(conn,config,listing):
        if listing=='NSE:B':raise PermissionError('grant_expired')
        if listing=='NSE:C':raise ValueError('real_identity_missing_or_ambiguous')
        if listing=='NSE:D':return dict(symbol='D',price_series=[],adjusted_research=dict(status='UNAVAILABLE',unavailable_reasons=['batch_identity_missing_or_ambiguous'],metrics={}))
        return dict(symbol='A',price_series=[{'time':'2026-10-22'},{'time':'2026-10-23'}],
                    adjusted_research=dict(status='AVAILABLE_DESCRIPTIVE_ONLY',unavailable_reasons=[],metrics={'sma20':'1','relative_volume':None}))
    monkeypatch.setattr(real_views,'company',company)
    app.dependency_overrides[research.db]=lambda:None
    try:
        c=TestClient(app);c.post('/api/v1/session',json={'token':'x'*40})
        response=c.get('/v1/real-research/coverage');body=response.json()
        monkeypatch.setattr(real_research,'schema_state',lambda:dict(state='migration_required'))
        blocked=c.get('/v1/real-research/coverage')
    finally:app.dependency_overrides.clear()
    assert response.headers['cache-control']=='no-store'
    assert body['available']==1 and body['total']==4 and body['actionable'] is False and body['execution_qualified'] is False
    a,b,cc,d=body['rows']
    assert a==dict(listing_id='NSE:A',symbol='A',state='available',reasons=[],sessions=2,last_session='2026-10-23',indicators=['sma20'])
    assert b==dict(listing_id='NSE:B',state='denied',reasons=['source_permission_denied'])
    assert cc['state']=='unavailable' and cc['reasons']==['real_identity_missing_or_ambiguous']
    assert d['state']=='unavailable' and d['reasons']==['batch_identity_missing_or_ambiguous'] and d['sessions']==0
    assert blocked.status_code==503 and blocked.json()['detail'].startswith('Database migration required')
