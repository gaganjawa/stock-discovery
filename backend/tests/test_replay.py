from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import pytest
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze,stamp
from stock_discovery_analysis.replay import simulate,Costs
from stock_discovery_analysis.evaluation import portfolio, summarize


def scenario(prices):
    d=demo_dataset(); cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    a=analyze(d,'SYN-ALPHA',cutoff,code_version='test')
    bars=list(d.candles)
    for i,(o,h,l,c) in enumerate(prices,40):
        bars[i]=replace(bars[i],open=D(o),high=D(h),low=D(l),close=D(c))
    d=replace(d,candles=tuple(bars)); r=a['recommendation']; r['versions']['dataset']=d.version
    r['execution']['entry']['trigger_price']='102'; r['execution']['stop']['price']='98'
    r['execution']['targets'][0]['price']='110'; r['execution']['quantity']=1
    r['execution']['entry_expires_at']=stamp(d.calendar.sessions[42].opens_at)
    a['sizing']['entry_cap']='105'
    end=d.calendar.sessions[44].closes_at+timedelta(minutes=1)
    return a,d,end


@pytest.mark.parametrize('second,reason,net',[
    (('104','111','103','108'),'target','5.75'),
    (('103','105','97','100'),'stop','-6.30'),
    (('95','99','94','98'),'gap_stop','-9.30')])
def test_known_profit_loss_and_gap(second,reason,net):
    a,d,end=scenario([('102','105','101','104'),second])
    out=simulate(a,d,end); t=out['trade']
    assert t['status']=='closed' and t['reason']==reason and t['net_pnl']==D(net)
    assert t['estimated_costs']==D('2.20')
    assert portfolio(out['equity_curve'])['cash_profit']==D(net)


def test_no_entry_expiry_and_time_exit():
    a,d,end=scenario([('100','101','99','100')]*2)
    out=simulate(a,d,end)
    assert out['trade']['status']=='no_entry' and out['trade']['net_pnl'] is None
    a,d,end=scenario([('102','105','101','103')]*3)
    t=simulate(a,d,end)['trade']
    assert t['reason']=='maximum_holding_expired' and t['net_pnl']==D('-1.30')


def test_ambiguity_never_becomes_scalar_profit():
    for first,reason in [(('103','111','97','105'),'stop_target_order_unknown'),
                         (('101','111','97','105'),'entry_stop_order_unknown')]:
        a,d,end=scenario([first]); t=simulate(a,d,end)['trade']
        assert t['status']=='ambiguous' and t['reason']==reason
        assert t['net_pnl'] is None and t['sensitivity_net_pnl'] is not None


def test_missing_data_cost_dates_and_unelapsed_horizon():
    a,d,end=scenario([('102','105','101','104')])
    missing=replace(d,candles=tuple(c for c in d.candles if c!=d.candles[40]))
    a['recommendation']['versions']['dataset']=missing.version
    assert simulate(a,missing,end)['trade']['status']=='invalid_data'
    a['recommendation']['versions']['dataset']=d.version
    before=d.calendar.sessions[39].closes_at+timedelta(minutes=2)
    assert simulate(a,d,before)['forecast']['status']=='pending'
    assert simulate(a,d,end,Costs(effective_to=before))['trade']['reason']=='cost_schedule_unavailable'
    assert summarize([])['direction']['value'] is None
