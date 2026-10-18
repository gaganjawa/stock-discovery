"""D3-09 deterministic authority and v2 relational contracts."""
from copy import deepcopy
import pytest
from stock_discovery_contracts.v2 import validate_bundle
from stock_discovery_analysis.publication import decision, build_artifact
from stock_discovery_analysis.publication_fixtures import inputs


@pytest.mark.parametrize('profile',['swing','short_term','long_term'])
@pytest.mark.parametrize('case,expected',[('ready','BUY'),('waiting','WATCH'),('risk','AVOID'),('missing','INSUFFICIENT_EVIDENCE')])
def test_three_horizons_four_actions(profile,case,expected):
    data,policy=inputs(profile,case)
    a=build_artifact(run_id='SYN-test',data=data,strategy=policy,issuer='SYN-issuer',cohort='quant',research=None,bundle=None,
        generated_at='2026-10-17T12:00:00Z',code_version='test',permissions={})
    r=a['recommendation']
    assert r['action']==expected
    assert r['paper_admission']['quantity'] is None and r['paper_admission']['status']=='blocked'
    assert r['cohort']['shadow'] and r['synthetic']
    validate_bundle(a['contract_bundle'])
    if r['execution']:assert r['execution']['earliest_entry_at']>r['decision_available_at']


def q(action='BUY',adverse=(),reasons=()):
    return dict(action=action,known_adverse=list(adverse),reasons=list(reasons))


def ai(action='BUY',**changes):
    return dict(status='completed',validator={'semantic':'supported'},assessment=dict(action=action,missing=[],contradictions=[],**changes))


def test_ai_cannot_override_risk_or_missing_inputs():
    assert decision(q('AVOID',['prohibited']),ai(),required=True)[0]=='AVOID'
    assert decision(q('INSUFFICIENT_EVIDENCE',reasons=['filing_missing']),ai(),required=True)[0]=='INSUFFICIENT_EVIDENCE'
    assert decision(q('WATCH'),ai(),required=True)[0]=='WATCH'
    assert decision(q(),ai('WATCH'),required=True)[0]=='WATCH'
    assert decision(q(),required=True)[0]=='INSUFFICIENT_EVIDENCE'
    assert decision(q(),ai('AVOID'),required=True)[0]=='WATCH'  # unsupported AI assertion is not a verified adverse fact


def test_conflicts_and_failed_judge_fail_closed():
    a=ai();a['assessment']['contradictions']=[['a','b']]
    assert decision(q(),a,required=True)[0]=='INSUFFICIENT_EVIDENCE'
    a=ai();a['validator']['semantic']='not_supported'
    assert decision(q(),a,required=True)[0]=='INSUFFICIENT_EVIDENCE'


def test_future_statement_and_missing_policy_cannot_buy():
    data,policy=inputs('long_term','ready')
    data['statements']=tuple(s.model_copy(update={'evidence':s.evidence.model_copy(update={
        'published_at':'2027-01-01T00:00:00Z','available_at':'2027-01-01T00:00:00Z','fetched_at':'2027-01-01T00:00:00Z'})}) for s in data['statements'])
    a=build_artifact(run_id='SYN-test',data=data,strategy=policy,issuer='SYN-issuer',cohort='quant',research=None,bundle=None,
        generated_at='2026-10-17T12:00:00Z',code_version='test',permissions={})
    assert a['recommendation']['action']=='INSUFFICIENT_EVIDENCE'
    assert all(e['available_at']<=data['cutoff'] for e in a['recommendation']['evidence'])
