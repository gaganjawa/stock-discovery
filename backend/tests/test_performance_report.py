"""Hand-calculated synthetic reporting arithmetic; never strategy acceptance."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import pytest
from test_replay import scenario
from stock_discovery_analysis.evaluation import risk_ratios
from stock_discovery_analysis.reports import session_risk,synthetic_benchmark,performance_report
from stock_discovery_analysis.replay import simulate
from stock_discovery_analysis.portfolio import replay_portfolio
from stock_discovery_analysis.splits import split_report


def test_ratio_definitions_no_annualization_and_explicit_denominators():
    r=risk_ratios(['.1','-.1','0'],risk_free='0')
    assert r['sharpe']==r['sortino']==0 and r['intervals']==3 and not r['annualized']
    r=risk_ratios(['.1','-.2'],risk_free='0')
    assert abs(r['sharpe']-(-D('.05')/(D('.045').sqrt())))<D('1e-25')
    assert abs(r['sortino']-(-D('.05')/(D('.02').sqrt())))<D('1e-25')


@pytest.mark.parametrize('values,rate,reason',[([], '0','insufficient_return_intervals'),
    (['.1'],'0','insufficient_return_intervals'),(['.1','.2'],None,'risk_free_unavailable'),
    (['0','0'],'0','zero_return_variance')])
def test_undefined_ratios_are_unavailable(values,rate,reason):
    result=risk_ratios(values,risk_free=rate)
    assert result['sharpe'] is None and result['sharpe_reason']==reason
    if values==['0','0']:assert result['sortino_reason']=='no_downside_deviation'


@pytest.mark.parametrize('value',['NaN','Infinity'])
def test_nonfinite_returns_rejected(value):
    with pytest.raises(ValueError):risk_ratios([value,'0'],risk_free='0')


def test_benchmark_hand_calculated_costed_same_window_and_versions():
    a,d,knowledge= scenario([('102','105','101','104'),('104','111','103','108')])
    start=a['recommendation']['information_cutoff_at'];end=d.calendar.sessions[41].closes_at.isoformat()
    b=synthetic_benchmark(d,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())
    assert b['status']=='available' and b['quantity']==9
    assert b['fees']==D('3.8') and b['slippage']==D('.9')
    assert b['net_return']==D('49.30')/1000
    assert b['dataset_version']==d.version and b['source_mode']=='synthetic'
    assert b['start_at']==start and b['end_at']==end and b['observation_count']==2
    assert b==synthetic_benchmark(d,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())


def test_benchmark_missing_future_prices_and_liquidity_do_not_resize():
    a,d,knowledge= scenario([('102','105','101','104'),('104','111','103','108')])
    start=a['recommendation']['information_cutoff_at'];end=d.calendar.sessions[41].closes_at.isoformat()
    removed=replace(d,candles=tuple(c for c in d.candles if c!=d.candles[41]))
    b=synthetic_benchmark(removed,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())
    assert b['net_return'] is None and b['missing_observations']==1
    late=replace(d,candles=tuple(replace(c,provenance=replace(c.provenance,available_at=d.calendar.sessions[45].closes_at)) if c==d.candles[41] else c for c in d.candles))
    assert synthetic_benchmark(late,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())['net_return'] is None
    low=replace(d,candles=tuple(replace(c,volume=1) if c==d.candles[41] else c for c in d.candles))
    assert synthetic_benchmark(low,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())['reason']=='benchmark_liquidity_unavailable'
    assert synthetic_benchmark(d,None,start,end,D(1000),knowledge_at=knowledge.isoformat())['reason']=='benchmark_not_selected'
    with pytest.raises(ValueError):synthetic_benchmark(d,'NSE:INFY',start,end,D(1000),knowledge_at=knowledge.isoformat())


def test_missing_position_mark_fails_but_idle_cash_can_be_carried():
    _,d,_=scenario([])
    curve=[dict(at=d.calendar.sessions[39].closes_at.isoformat(),cash=100,positions=[],external_flow=0),
           dict(at=d.calendar.sessions[43].closes_at.isoformat(),cash=100,positions=[],external_flow=0)]
    r=session_risk(curve,d)
    assert r['closing_marks']==4 and r['intervals']==3 and r['sharpe'] is None
    curve[0]['positions']=[dict(quantity=1,mark=10)]
    assert session_risk(curve,d)['reason']=='missing_session_position_marks'
    curve[0]['positions']=[];curve[1]['external_flow']=1
    assert session_risk(curve,d)['reason']=='session_flow_timing_unqualified'


def test_report_is_reproducible_excludes_unqualified_pairs_and_preserves_inputs():
    a,d,end=scenario([('102','105','101','104'),('104','111','103','108')])
    o=simulate(a,d,end);records=[(a,o)]
    rows=[dict(id=a['recommendation']['recommendation_id'],action='BUY',trade_status='closed',net='5.75',
        forecast_status='matured',direction=True,target_status='not_applicable',target=None,entry=True,target_first=True,forecast_due=True,target_due=False,entry_due=True,trade_due=True,reason='target')]
    before=deepcopy(records);p=replay_portfolio(records);audit=split_report(d,[a])
    r=performance_report(d,records,rows,p,audit,'SYN-BETA')
    assert r['net_return']==D('5.75')/100000 and r['win_rate']['denominator']==1
    assert r['profit_factor'] is None and r['profit_factor_reason']=='no_realized_losses'
    assert r['paired_comparison']['eligible_pairs']==0 and r['paired_comparison']['ai_performance'] is None
    assert r['walk_forward']['status']=='unavailable' and len(r['partitions'])==3
    assert records==before and r==performance_report(d,list(reversed(records)),rows,p,audit,'SYN-BETA')
    a['recommendation']['strategy']['config_version']='SYN-COMBINED-ABSTAIN-1'
    blocked=performance_report(d,records,rows,p,audit,'SYN-BETA')
    assert blocked['status']=='unavailable' and blocked['net_return'] is None and not blocked['curve']
    assert blocked['win_rate']['value'] is None and blocked['profit_factor'] is None


def test_benchmark_requires_knowledge_clock_and_rejects_actions_and_future_outcome():
    from stock_discovery_analysis.calendar import CorporateAction
    a,d,knowledge=scenario([('102','105','101','104'),('104','111','103','108')])
    start=a['recommendation']['information_cutoff_at'];end=d.calendar.sessions[41].closes_at.isoformat()
    assert synthetic_benchmark(d,'SYN-ALPHA',start,end,D(1000))['reason']=='benchmark_knowledge_cutoff_missing'
    assert synthetic_benchmark(d,'SYN-ALPHA',start,end,D(1000),knowledge_at=start)['reason']=='benchmark_outcome_immature'
    action=CorporateAction('SYN-dividend','SYN-ALPHA','dividend',d.calendar.sessions[40].opens_at,D(1),d.calendar.provenance)
    changed=replace(d,actions=(*d.actions,action))
    assert synthetic_benchmark(changed,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())['reason']=='benchmark_actions_unsupported'


def test_benchmark_rejects_late_disclosed_action_known_by_outcome_cutoff():
    from datetime import timedelta
    from stock_discovery_analysis.calendar import CorporateAction
    a,d,knowledge=scenario([('102','105','101','104'),('104','111','103','108')])
    start=a['recommendation']['information_cutoff_at'];end=d.calendar.sessions[41].closes_at.isoformat()
    provenance=replace(d.calendar.provenance,published_at=d.calendar.sessions[42].closes_at,
        available_at=d.calendar.sessions[42].closes_at,fetched_at=d.calendar.sessions[42].closes_at)
    action=CorporateAction('SYN-late-dividend','SYN-ALPHA','dividend',d.calendar.sessions[40].opens_at,D(1),provenance)
    changed=replace(d,actions=(*d.actions,action))
    r=synthetic_benchmark(changed,'SYN-ALPHA',start,end,D(1000),knowledge_at=knowledge.isoformat())
    assert r['status']=='unavailable' and r['reason']=='benchmark_actions_unsupported'
    earlier=(d.calendar.sessions[41].closes_at+timedelta(minutes=1)).isoformat()
    assert synthetic_benchmark(changed,'SYN-ALPHA',start,end,D(1000),knowledge_at=earlier)['status']=='available'
