from decimal import Decimal as D
import pytest
from stock_discovery_analysis.paper_contracts import PortfolioConfig,Observation,FICTIONAL
from stock_discovery_analysis.paper_engine import step, reservation, size_order


def policy(**changes):
    return PortfolioConfig(name='Test',mode='fictional_simulation',contract_version=FICTIONAL,
        starting_capital='100000',simulation_start_at='2025-06-25T10:01:01Z',**changes).model_dump(mode='json')


def order(**changes):
    return dict(recommendation_id='test',listing_id='ABC',issuer_id='issuer',sector='software',horizon='swing',cohort='quant',
        lot_size=1,cap='102',remaining=10,quantity=0,terms=dict(entry_type='buy_stop',entry_price='100',stop_price='95',target_price='110',
            earliest_entry_at='2025-06-26T03:45:00Z',entry_expires_at='2025-06-27T10:00:00Z',time_exit_at='2025-06-30T10:00:00Z'),
        status='pending',reason='reservation',fills=[],fees='0',slippage='0',basis='0',entry_cost='0',entry_notional='0',exit_notional='0',
        bought=0,sold=0,realized_pnl='0',entry_at=None,exit_at=None,exit_pending=None,mark='100',mark_at='2025-06-25T10:01:01Z',
        holding_sessions=0,mae='0',mfe='0',excursion_sessions=0,**changes)


def bar(**changes):
    return dict(dict(listing_id='ABC',open='100',high='105',low='98',close='103',session_open_at='2025-06-26T03:45:00Z',
        session_close_at='2025-06-26T10:00:00Z',available_at='2025-06-26T10:00:00Z',entry_capacity=None,exit_capacity=None),**changes)


def run(o=None,b=None,p=None,at='2025-06-26T10:00:00Z'):
    return step(o or order(),b or bar(),at,p or policy())


def test_entry_costs_and_no_mutation():
    original=order();o,cash=run(original)
    assert original['quantity']==0 and original['fills']==[]
    assert o['quantity']==10 and o['remaining']==0
    assert cash == -(D('100.1')*10+D('2.001'))
    assert D(o['slippage'])==1 and D(o['fees'])==D('2.001')


@pytest.mark.parametrize('b,reason',[({'high':'111','low':'94'},'daily_bar_sequence_unknown'),
    ({'open':'99','high':'111','low':'98'},'daily_bar_sequence_unknown')])
def test_ambiguous_entry_or_stop_target(b,reason):
    o,c=run(b=bar(**b));assert o['status']=='ambiguous' and o['reason']==reason
    assert not any(f['side']=='sell' for f in o['fills'])


def test_gap_through_stop_uses_open_not_stop():
    opened,_=run();o,c=run(opened,bar(open='90',high='96',low='89',close='94'))
    assert o['status']=='closed' and o['fills'][-1]['price']=='89.910'
    assert o['reason']=='stop_gap' and D(o['realized_pnl'])<0


def test_partial_entry_and_reservations_cover_repeated_fixed_fees():
    o,c=run(b=bar(entry_capacity=3));assert o['quantity']==3 and o['remaining']==7
    assert reservation(o,policy())>D(102)*7
    o,c=run(o,bar(entry_capacity=2));assert o['quantity']==5 and o['remaining']==5


def test_zero_capacity_never_fills_and_lot_sizes():
    o=order();o['lot_size']=5
    updated,c=run(o,bar(entry_capacity=4));assert updated['quantity']==0 and c==0


def test_partial_exit_persists_without_reentry():
    opened,_=run();part,_=run(opened,bar(open='94',high='96',low='93',close='95',exit_capacity=3))
    assert part['quantity']==7 and part['remaining']==0 and part['exit_pending']=='stop_gap'
    part,_=run(part,bar(open='100',high='105',low='98',close='103',exit_capacity=3))
    assert part['quantity']==4 and part['exit_pending']=='stop_gap'
    closed,_=run(part,bar(open='100',high='105',low='98',close='103'))
    assert closed['status']=='closed' and closed['fills'][-1]['reason']=='pending_exit' and closed['reason']=='stop_gap'


def test_gap_above_entry_cap_no_fill():
    o,c=run(b=bar(open='104',high='106',low='103',close='105'));assert o['quantity']==0 and c==0


def test_limit_never_pays_above_limit():
    o=order();o['terms']['entry_type']='limit';o['cap']='100'
    updated,_=run(o);assert updated['fills'][0]['price']=='100'


def test_missing_and_stale_prices_unavailable():
    o,c=step(order(),None,'2025-06-26T10:00:00Z',policy());assert o['status']=='unavailable' and c==0
    o,c=run(p=policy(mark_max_age_seconds=1),at='2025-06-26T10:00:03Z');assert o['reason']=='stale_price'


def test_time_exit_and_expiry():
    opened,_=run();o,c=run(opened,at='2025-06-30T10:00:00Z');assert o['reason']=='time_exit' and o['status']=='closed'
    o,c=run(b=bar(open='90',high='94',low='89',close='91'),at='2025-06-27T10:00:00Z');assert o['status']=='no_entry'


def test_sizing_includes_pending_cross_horizon_issuer():
    p=policy();state={'cash':'100000','reserved':'0','period_base':'100000','orders':{}}
    first=order();q=size_order(state,first,p);assert q>0
    first['remaining']=q;state['orders']['first']=first;state['reserved']=str(reservation(first,p))
    second=order();second['horizon']='long_term';q2=size_order(state,second,p)
    assert q2<q and (q+q2)*D('102')<=D('20000')


def test_insufficient_cash_and_tiny_risk():
    state={'cash':'1','reserved':'0','period_base':'100000','orders':{}}
    assert size_order(state,order(),policy())==0
    state['cash']='100000';assert size_order(state,order(),policy(per_trade_risk='.000001'))==0


@pytest.mark.parametrize('changes',[{'mode':'forward_paper'},{'simulation_start_at':None},{'starting_capital':'NaN'},{'issuer_limit':'.9'}])
def test_invalid_config(changes):
    base=policy();base.update(changes)
    with pytest.raises(ValueError):PortfolioConfig.model_validate(base)


def test_future_observation_is_rejected():
    with pytest.raises(ValueError):Observation(contract_version=FICTIONAL,session_close_at='2025-06-26T10:00:00Z',observed_at='2025-06-25T10:00:00Z',bars=[])


def test_exit_fees_remain_reserved_until_position_is_closed():
    p=policy(fixed_fee='25');o=order();opened,delta=run(o,p=p)
    assert reservation(opened,p)==D('250')
    closed,cash=run(opened,bar(open='0.01',high='0.02',low='0.005',close='0.01'),p)
    assert reservation(closed,p)==0 and cash<0  # reserved cash covers the fee
    assert 100000+delta+cash>=0


def test_pending_exit_has_known_open_priority_over_ambiguous_daily_range():
    opened,_=run();part,_=run(opened,bar(open='94',high='96',low='93',close='95',exit_capacity=3))
    result,_=run(part,bar(open='100',high='120',low='90',close='101'))
    assert result['status']=='closed' and result['fills'][-1]['reason']=='pending_exit'


def test_target_at_open_and_partial_exit_costs():
    opened,_=run();closed,_=run(opened,bar(open='115',high='118',low='110',close='116'))
    assert closed['status']=='closed' and closed['reason']=='target_gap'
    assert D(closed['realized_pnl'])>0 and D(closed['fees'])>0


def test_missing_metrics_keep_unresolved_outcomes_in_denominator():
    from stock_discovery_analysis.paper_reporting import cohort_metrics
    rows=[dict(status=s,admission='admitted',forecast={'status':'provisional'}) for s in ('pending','open','ambiguous','unavailable','no_entry')]
    result=cohort_metrics(rows)
    assert result['decisions']==5 and result['resolved_trades']==0 and result['win_rate'] is None
    assert result['ambiguous']==1 and result['unavailable']==1 and result['no_entry']==1
