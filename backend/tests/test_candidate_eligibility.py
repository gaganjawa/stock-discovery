"""Qualification projections use invented evidence; never live authorization."""
import pytest
from stock_discovery_analysis.candidate_eligibility import qualification


def eligible():
    return {'research':{'status':'completed','identity_status':'verified_stored_nse_eq',
        'analyzed_at':'2026-11-13T12:00:00Z','reasons':[],
        'market_data':{'latest_session':'2026-11-13','warmup_complete':True,'freshness':{'status':'current'}},
        'technical':{'status':'AVAILABLE_DESCRIPTIVE_ONLY'}}}


def test_eligible_stored_research_does_not_authorize_acquisition_or_signal():
    row=eligible();q=qualification(row,current=True)
    assert q['research_eligibility']=='eligible_stored_research'
    assert q['latest_qualified_price_session']=='2026-11-13'
    assert q['source_permission']=='permitted_stored_research'
    assert q['refresh_eligibility']=='not_verified'
    assert q['signal']=='unqualified' and q['actionable'] is False
    assert qualification(row)['latest_qualified_price_session'] is None
    assert qualification(row)['evidence_basis']=='last_stored_analysis'


@pytest.mark.parametrize('reason,permission',[('nse_identity_missing_or_ambiguous','not_verified'),('source_permission_denied','denied'),('real_source_configuration_required','not_verified')])
def test_blocked_identity_and_permissions(reason,permission):
    q=qualification({'research':{'status':'blocked','reasons':[reason]}})
    assert q['universe']=='not_verified' and q['source_permission']==permission
    assert q['research_eligibility']=='blocked_or_unverified'
    assert q['blockers']==[reason] and q['latest_qualified_price_session'] is None


@pytest.mark.parametrize('state',['stale','delayed','unavailable'])
def test_noncurrent_prices_are_never_qualified(state):
    row=eligible();row['research']['market_data']['freshness']['status']=state
    assert qualification(row,current=True)['latest_qualified_price_session'] is None


def test_incomplete_batch_and_pending_analysis():
    row=eligible();row['research'].update(status='blocked',reasons=['price_batch_superseded_or_unavailable'])
    row['research']['market_data']['warmup_complete']=False
    q=qualification(row,current=True)
    assert q['latest_qualified_price_session'] is None
    assert q['completeness']=='insufficient_or_unavailable'
    assert qualification({'research_status':'pending'})['research_state']=='pending'


@pytest.mark.parametrize('status,expected',[('queued','pending'),('running','pending'),('retry_wait','pending'),('completed','completed'),('failed','failed'),('missed','blocked')])
def test_refresh_is_a_record_not_current_worker_authorization(status,expected):
    row=eligible();row['price_refresh']={'status':status,'reason':'readiness'}
    q=qualification(row,current=True)
    assert q['refresh_state']==expected and q['refresh_reason']=='readiness'
    assert q['refresh_eligibility']=='previously_admitted_not_current_authorization'


@pytest.mark.parametrize('warmup',[False,None,0,1,'true'])
def test_current_freshness_cannot_override_incomplete_warmup(warmup):
    row=eligible();row['research']['market_data']['warmup_complete']=warmup
    assert qualification(row,current=True)['latest_qualified_price_session'] is None


@pytest.mark.parametrize('session',[None,'','bad','2026-02-30','2026-11-13T25:00:00Z',20261113])
def test_current_freshness_requires_valid_price_session(session):
    row=eligible();row['research']['market_data']['latest_session']=session
    assert qualification(row,current=True)['latest_qualified_price_session'] is None


@pytest.mark.parametrize('reason',['price_batch_superseded_or_unavailable','session_coverage_unavailable','batch_provenance_unverified'])
@pytest.mark.parametrize('location',['research','technical'])
def test_current_completed_research_cannot_override_batch_blocker(reason,location):
    row=eligible()
    if location=='research':row['research']['reasons']=[reason]
    else:row['research']['technical']['unavailable_reasons']=[reason]
    assert qualification(row,current=True)['latest_qualified_price_session'] is None


@pytest.mark.parametrize('field,value',[('warmup_complete',False),('latest_session_present',False),('missing_sessions',['2026-11-12']),('unverified_bar_sessions',['2026-11-12']),('duplicate_bars',True)])
def test_contradictory_coverage_is_not_qualified(field,value):
    row=eligible();coverage=dict(warmup_complete=True,latest_session_present=True,missing_sessions=[],unverified_bar_sessions=[],duplicate_bars=False)
    coverage[field]=value;row['research']['technical']['session_coverage']=coverage
    assert qualification(row,current=True)['latest_qualified_price_session'] is None


def test_valid_timestamp_and_descriptive_limitations_remain_price_only():
    row=eligible();row['research']['market_data']['latest_session']='2026-11-13T00:00:00Z'
    row['research']['technical']['limitations']=['volume_basis_unverified','action_coverage_unverified']
    q=qualification(row,current=True)
    assert q['latest_qualified_price_session']=='2026-11-13T00:00:00Z'
    assert q['actionable'] is False and q['signal']=='unqualified'
    assert qualification(row,current=False)['latest_qualified_price_session'] is None


@pytest.mark.parametrize('case',['warmup','session','batch','complete'])
def test_candidates_api_preserves_current_vs_cached_qualification(monkeypatch,case):
    from copy import deepcopy
    from fastapi.testclient import TestClient
    from app.main import app
    from app.research import db
    from app import candidates
    from stock_discovery_analysis import candidate_swing
    research=eligible()['research']
    if case=='warmup':research['market_data']['warmup_complete']=False
    if case=='session':research['market_data']['latest_session']=None
    if case=='batch':research['reasons']=['price_batch_superseded_or_unavailable']
    row=dict(candidate_id='fixture',symbol='INFY',session_date='2026-11-13',research=research)
    monkeypatch.setenv('AUTH_TOKEN','q'*40)
    monkeypatch.setattr(candidates,'view_config',lambda:None)
    monkeypatch.setattr(candidates.store,'rows',lambda *a,**k:{'rows':[deepcopy(row)],'total':1})
    monkeypatch.setattr(candidate_swing,'analyze',lambda *a,**k:deepcopy(research))
    class Connection:
        def execute(self,*args):return []
    app.dependency_overrides[db]=lambda:Connection()
    try:
        client=TestClient(app);headers={'Authorization':'Bearer '+'q'*40}
        q=client.get('/v1/real-research/candidates/swing-review',headers=headers).json()['rows'][0]['qualification']
        assert q['latest_qualified_price_session']==('2026-11-13' if case=='complete' else None)
        assert q['actionable'] is False and q['signal']=='unqualified'
        cached=client.get('/v1/real-research/candidates',headers=headers).json()['rows'][0]['qualification']
        assert cached['latest_qualified_price_session'] is None
    finally:app.dependency_overrides.clear()
