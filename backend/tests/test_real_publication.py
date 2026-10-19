"""Fabricated observed-mode tests only; never real-market acceptance evidence."""
from dataclasses import replace
from copy import deepcopy
from datetime import timedelta
import pytest
from stock_discovery_contracts.v2 import Ref,at,validate_bundle
from stock_discovery_analysis.publication import build_artifact,policy,reproduce_quant
from stock_discovery_analysis.publication_fixtures import inputs


def arguments(profile='swing'):
    data,strategy=inputs(profile,'missing')
    data.update(mode='live_paper',instrument_id='NSE:test',statements=(),coverage=(),eligible=None,risk_prohibited=None)
    data['bars']=tuple(replace(b,instrument_id='NSE:test',provenance=replace(b.provenance,availability_basis='observed_live')) for b in data['bars'])
    data['calendar']=replace(data['calendar'],provenance=replace(data['calendar'].provenance,availability_basis='observed_live'))
    strategy=strategy.model_copy(update={'status':'approved','approval_ref':'FABRICATED TEST APPROVAL',
        'ref':strategy.ref.model_copy(update={'id':'test-strategy'})})
    policies=[strategy]
    for kind in ('horizon','research','risk','cost','retrieval','schedule','universe'):
        p=policy(kind,profile,{'unqualified':'1'})
        policies.append(p.model_copy(update={'status':'unconfigured','ref':p.ref.model_copy(update={'id':'test-'+kind})}))
    return dict(run_id='test-run',data=data,strategy=strategy,issuer='test-issuer',cohort='quant',research=None,bundle=None,
        generated_at=(at(data['cutoff'])+timedelta(seconds=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),code_version='test',permissions={},
        real=dict(instrument=dict(instrument_id='NSE:test',issuer_id='test-issuer',symbol='TEST',exchange='NSE',series='EQ',isin='INE009A01021',currency='INR',exchange_timezone='Asia/Kolkata',lot_size=1),
            policies=policies,price_evidence=[],dataset_version='fabricated-test'))


@pytest.mark.parametrize('profile',['swing','short_term','long_term'])
def test_actual_publication_clock_and_no_invented_execution(profile):
    args=arguments(profile);a=build_artifact(**args);r=a['recommendation']
    validate_bundle(a['contract_bundle'])
    assert r['decision_available_at']==args['generated_at']>r['information_cutoff_at']
    assert not r['synthetic'] and not r['availability_simulated']
    assert r['action']=='INSUFFICIENT_EVIDENCE' and r['execution'] is None
    assert r['paper_admission']['status']=='blocked' and r['cohort']['shadow']
    assert reproduce_quant(a)==a['prepublication_quantitative']


def test_reject_fixture_calendar_policy_and_future_publication_cutoff():
    args=arguments();args['generated_at']=args['data']['cutoff']
    with pytest.raises(ValueError,match='publication_must_follow_cutoff'):build_artifact(**args)
    args=arguments();args['real']['policies'][1]=policy('horizon','swing',{'unqualified':'1'})
    with pytest.raises(ValueError,match='fixture_policy'):build_artifact(**args)
    args=arguments();args['data']['calendar']=inputs('swing','missing')[0]['calendar']
    with pytest.raises(ValueError,match='observed_calendar_required'):build_artifact(**args)
