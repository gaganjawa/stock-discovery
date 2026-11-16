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
