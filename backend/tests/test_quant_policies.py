from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D, localcontext
import json

import pytest
from stock_discovery_contracts.v2 import Policy, Ref, digest
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze
from stock_discovery_analysis.quant_fixtures import fixture_policy, fixture_inputs, fixture_assessment
from stock_discovery_analysis.quant_policies import (PolicyRegistry, Statement, assess, horizon_for,
    legacy_swing, LEGACY_REGISTRATION, LEGACY_REGISTRATION_HASH)

PROFILES=('swing','short_term','long_term')


def run(profile='long_term', settings=None, **changes):
    policy=fixture_policy(profile,**(settings or {}))
    registry=PolicyRegistry()
    registry.register(policy)
    inputs=fixture_inputs(profile)
    inputs.update(changes)
    return assess(registry,policy.ref,**inputs)


@pytest.mark.parametrize('profile',PROFILES)
def test_fixture_research_buy_is_separate_from_admission(profile):
    result=run(profile)
    assert result['action']=='BUY' and result['capability']=='technical_only'
    assert result['paper_admission']==dict(status='blocked',quantity=None,reason='paper_admission_not_evaluated')
    assert result['horizon']['profile']==profile
    assert result['conditions']['invalidation'] and result['conditions']['entry']
    assert result==run(profile)


@pytest.mark.parametrize('profile',PROFILES)
def test_missing_policy_and_fixture_never_live(profile):
    args=fixture_inputs(profile)
    ref=fixture_policy(profile).ref
    result=assess(PolicyRegistry(),ref,**args)
    assert result['action']=='INSUFFICIENT_EVIDENCE' and 'policy_not_configured' in result['reasons']
    assert 'policy_not_configured' in run(profile,mode='live_paper')['reasons']


def test_registry_roundtrip_immutable_metadata_and_copy_isolation():
    registry=PolicyRegistry()
    policy=fixture_policy('short_term')
    manifest=registry.register(policy)
    assert manifest==registry.register(policy)
    assert PolicyRegistry.restore(registry.export()).export()==registry.export()
    original=registry.get(policy.ref)
    original.parameters.clear()
    assert registry.get(policy.ref).parameters
    with pytest.raises(ValueError,match='conflict'):
        registry.register(fixture_policy('short_term',bear_pe='40'))
    changed=policy.model_copy(update={'effective_at':'2021-01-01T00:00:00Z'})
    with pytest.raises(ValueError,match='conflict'):
        registry.register(changed)
    with pytest.raises(ValueError,match='hash'):
        registry.get(Ref(id=policy.ref.id,version=policy.ref.version,content_hash='0'*64))
    with pytest.raises(TypeError):
        LEGACY_REGISTRATION['holding_sessions']=7
    assert digest(dict(LEGACY_REGISTRATION))==LEGACY_REGISTRATION_HASH


@pytest.mark.parametrize('profile,settings',[('swing',{'duration':'11'}),('short_term',{'duration':'4'}),
    ('long_term',{'duration':'6'}),('long_term',{'durability_years':'1'}),('short_term',{'bear_pe':'99'}),
    ('short_term',{'min_margin_of_safety':'1'}),('short_term',{'entry_sessions':'0'}),('short_term',{'report_months':'6'})])
def test_invalid_policy_settings(profile,settings):
    with pytest.raises(ValueError):
        PolicyRegistry().register(fixture_policy(profile,**settings))


@pytest.mark.parametrize('profile',PROFILES)
def test_missing_coverage_never_no_pick(profile):
    result=run(profile,coverage=())
    assert result['action']=='INSUFFICIENT_EVIDENCE'
    assert 'missing_or_stale:material_events' in result['reasons']


def test_missing_policy_keeps_known_adverse_evidence():
    args=fixture_inputs('long_term')
    args['coverage']=(args['coverage'][0].model_copy(update={'adverse':True}),)
    result=assess(PolicyRegistry(),fixture_policy('long_term').ref,**args)
    assert result['action']=='INSUFFICIENT_EVIDENCE' and result['known_adverse']==['verified_adverse:actions']


@pytest.mark.parametrize('field',['revenue','earnings','operating_cash_flow','capital_expenditure','debt','cash','equity','diluted_shares'])
def test_missing_financial_values(field):
    args=fixture_inputs('long_term')
    statements=args['statements'][:-1]+(args['statements'][-1].model_copy(update={field:None}),)
    assert run(statements=statements)['action']=='INSUFFICIENT_EVIDENCE'


def test_zero_is_observed_not_imputed_missing():
    args=fixture_inputs('long_term')
    zero=args['statements'][:-1]+(args['statements'][-1].model_copy(update={'operating_cash_flow':'0'}),)
    result=run(statements=zero)
    assert result['metrics']['free_cash_flow']=='-20'
    assert result['metrics']['ocf_margin']=='0'
    assert result['metrics']['net_debt_to_ocf'] is None
    assert 'undefined_quality_ratio' in result['reasons']


@pytest.mark.parametrize('profile',('short_term','long_term'))
def test_future_statement_and_price_changes_cannot_influence_result(profile):
    args=fixture_inputs(profile)
    current=args['statements'][-1]
    future_time=(__import__('datetime').datetime.strptime(args['cutoff'],'%Y-%m-%dT%H:%M:%SZ')+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    future=current.model_copy(update={'revision_id':'future','earnings':'999999',
        'evidence':current.evidence.model_copy(update={'revision_id':'future','evidence_id':'future',
            'published_at':future_time,'available_at':future_time,'fetched_at':future_time})})
    changed=tuple(replace(b,close=b.low) if b.ends_at.strftime('%Y-%m-%dT%H:%M:%SZ')>args['cutoff'] else b for b in args['bars'])
    assert run(profile)==run(profile,statements=args['statements']+(future,),bars=changed)


def test_stale_financial_prices_and_unsupported_sector():
    assert 'stale_financial_data' in run(settings={'max_statement_age_days':'1'})['reasons']
    args=fixture_inputs('long_term')
    assert 'price_features_unavailable' in run(bars=args['bars'][:5])['reasons']
    assert run(sector='bank')['reasons']==['unsupported_sector_metrics']
    old=tuple(r.model_copy(update={'evidence':r.evidence.model_copy(update={'available_at':'2020-01-01T00:00:00Z','published_at':'2020-01-01T00:00:00Z'})}) for r in args['coverage'])
    assert 'missing_or_stale:business' in run(coverage=old)['reasons']


def test_valuation_sensitivity_watch_and_avoid():
    base=run()
    lower=run(settings={'bear_pe':'10','base_pe':'20','bull_pe':'30'})
    assert lower['action']=='WATCH'
    assert D(base['valuation']['low'])==D(lower['valuation']['low'])*5
    assert base['valuation']['assumptions'] and len(base['valuation']['calculation_ids'])==3
    assert run(settings={'max_net_debt_to_ocf':'0.01'})['action']=='AVOID'
    assert run(risk_prohibited=True)['action']=='AVOID'
    assert run(eligible=False)['action']=='AVOID'


def test_reproducible_with_input_order_and_decimal_context():
    args=fixture_inputs('long_term')
    expected=run()
    with localcontext() as ctx:
        ctx.prec=6
        assert run(statements=tuple(reversed(args['statements'])),bars=tuple(reversed(args['bars'])),coverage=tuple(reversed(args['coverage'])))==expected


@pytest.mark.parametrize('index',[2,38,39])
def test_legacy_swing_exact_compatibility(index):
    data=demo_dataset()
    cutoff=data.calendar.sessions[index].closes_at+timedelta(minutes=1)
    args=dict(code_version='test',generated_at=data.candles[-1].provenance.fetched_at)
    assert legacy_swing(data,'SYN-ALPHA',cutoff,**args)==analyze(data,'SYN-ALPHA',cutoff,**args)


@pytest.mark.parametrize('profile,duration',[('swing','2'),('swing','10'),('short_term','3'),('long_term','5')])
def test_calendar_aware_endpoint_and_expiry(profile,duration):
    result=run(profile,settings={'duration':duration})
    assert result['horizon']['duration']==int(duration)
    assert result['horizon']['anchor_at']<result['horizon']['entry_expires_at']<=result['horizon']['holding_end_at']
    assert result['horizon']['holding_end_at'] in [s.closes_at.strftime('%Y-%m-%dT%H:%M:%SZ') for s in fixture_inputs(profile)['calendar'].sessions]
    args=fixture_inputs(profile)
    truncated=replace(args['calendar'],sessions=args['calendar'].sessions[:40])
    assert 'calendar_horizon_unavailable' in run(profile,calendar=truncated)['reasons']


def test_entry_expiry_and_price_gate_never_admit_paper():
    from stock_discovery_analysis.quant_policies import entry_conditions_met
    for profile in PROFILES:
        result=run(profile)
        terms=result['entry_terms']
        price=D(terms.get('trigger',terms.get('max_price')))
        assert entry_conditions_met(result,terms['earliest_entry_at'],price)
        assert not entry_conditions_met(result,result['horizon']['entry_expires_at'],price)
        assert not entry_conditions_met(result,result['information_cutoff_at'],price)
        assert not entry_conditions_met(result,terms['earliest_entry_at'],price*10)
        assert result['paper_admission']['quantity'] is None


def test_quarterly_momentum_uses_prior_year_and_annual_valuation():
    args=fixture_inputs('short_term')
    original=args['statements'][-1]
    quarters=[]
    # The latest available annual is Dec 2023; quarters compare March 2022/2023.
    annual_year=int(original.period_end_at[:4])
    for year,earnings in ((annual_year-1,'20'),(annual_year,'30')):
        end=f'{year}-03-31T00:00:00Z'
        published=f'{year}-04-15T00:00:00Z'
        rid='SYN-Q'+str(year)
        quarters.append(original.model_copy(update={'revision_id':rid,'period_kind':'quarter',
            'period_start_at':f'{year}-01-01T00:00:00Z','period_end_at':end,'earnings':earnings,
            'evidence':original.evidence.model_copy(update={'evidence_id':rid,'revision_id':rid,'period_end_at':end,
                'published_at':published,'available_at':published,'fetched_at':published})}))
    result=run('short_term',settings={'report_months':'3','max_statement_age_days':'1000'},statements=args['statements']+tuple(quarters))
    assert result['metrics']['earnings_growth']=='0.5'
    assert result['metrics']['eps']==run('short_term')['metrics']['eps']


def test_future_policy_and_unavailable_parameter_fail_closed():
    policy=fixture_policy('short_term')
    args=fixture_inputs('short_term')
    future=policy.model_copy(update={'effective_at':'2099-01-01T00:00:00Z'})
    registry=PolicyRegistry(); registry.register(future)
    assert assess(registry,future.ref,**args)['reasons']==['policy_not_configured']
    data=policy.model_dump()
    data['parameters'][0].update(value=None,unavailable_reason='not_approved')
    data['ref']['content_hash']=digest(data['parameters'])
    policy=Policy.model_validate(data)
    registry=PolicyRegistry(); registry.register(policy)
    assert assess(registry,policy.ref,**args)['reasons']==['policy_not_configured']


def test_period_scope_ambiguity_and_restatement():
    args=fixture_inputs('long_term')
    latest=args['statements'][-1]
    wrong=latest.model_copy(update={'scope':'standalone'})
    assert 'incompatible_statement_periods' in run(statements=args['statements'][:-1]+(wrong,))['reasons']
    twin=latest.model_copy(update={'revision_id':'SYN-twin','earnings':'1',
        'evidence':latest.evidence.model_copy(update={'revision_id':'SYN-twin','evidence_id':'SYN-twin'})})
    assert 'ambiguous_statement_revision' in run(statements=args['statements']+(twin,))['reasons']


def test_month_end_leap_anniversary_and_preceding_holiday_session():
    from datetime import datetime, timezone
    from stock_discovery_analysis.calendar import Calendar, Session
    from stock_discovery_analysis.data import Provenance
    start=datetime(2024,1,1,3,45,tzinfo=timezone.utc)
    provenance=Provenance('SYN-calendar','1',start-timedelta(days=1),start-timedelta(days=1),start-timedelta(days=1),'fictional_fixture')
    sessions=[]
    day=start
    while day.year<2026:
        if day.weekday()<5 and day.strftime('%Y-%m-%d')!='2025-02-28':
            sessions.append(Session(day,day+timedelta(hours=6,minutes=15)))
        day+=timedelta(days=1)
    calendar=Calendar('SYN-holidays',tuple(sessions),provenance)
    def resolve(profile,cutoff):
        values={p.name:D(p.value) for p in fixture_policy(profile).parameters}
        return horizon_for(profile,values,calendar,cutoff)
    assert resolve('short_term','2024-01-31T10:01:00Z').holding_end_at=='2024-02-29T10:00:00Z'
    assert resolve('long_term','2024-02-29T10:01:00Z').holding_end_at=='2025-02-27T10:00:00Z'


def test_checked_in_registry_schemas_and_results_reproduce():
    from pathlib import Path
    from stock_discovery_analysis.quant_policies import CoverageCheck
    root=Path(__file__).resolve().parents[2]/'docs/contracts/quant'
    for profile in PROFILES:
        assert json.loads((root/(profile+'.synthetic.json')).read_text())==fixture_assessment(profile)
    assert json.loads((root/'statement.schema.json').read_text())==Statement.model_json_schema()
    assert json.loads((root/'coverage-check.schema.json').read_text())==CoverageCheck.model_json_schema()
    records=json.loads((root/'policies.synthetic.json').read_text())
    assert len(PolicyRegistry.restore(tuple(json.dumps(r) for r in records)).export())==3


def test_review_after_period_close_uses_next_period_last_session():
    args=fixture_inputs('short_term')
    friday=next(s for s in args['calendar'].sessions if s.closes_at.weekday()==4)
    cutoff=(friday.closes_at+timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    policy=fixture_policy('short_term')
    horizon=horizon_for('short_term',{p.name:D(p.value) for p in policy.parameters},args['calendar'],cutoff)
    assert horizon.next_review_at==(friday.closes_at+timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
