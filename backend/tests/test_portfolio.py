from copy import deepcopy
from decimal import Decimal as D
from stock_discovery_analysis.portfolio import replay_portfolio
from stock_discovery_analysis.replay import simulate
from test_replay import scenario


def test_single_slot_never_double_counts_overlapping_recommendations():
    a,d,end=scenario([('102','105','101','104'),('104','111','103','108')])
    b=deepcopy(a);b['recommendation']['recommendation_id']='second';b['recommendation']['instrument']['symbol']='ZZZ'
    out=simulate(a,d,end)
    p=replay_portfolio([(a,out),(b,out)])
    assert p['cash_profit']==D('5.75')
    assert len(p['admitted_ids'])==1
    assert p['exclusions']==[{'id':'second','reason':'single_slot_reserved_at_signal'}]
    assert p['time_weighted_return']==D('5.75')/100000


def test_ambiguous_portfolio_stays_undefined():
    a,d,end=scenario([('103','111','97','105')])
    p=replay_portfolio([(a,simulate(a,d,end))])
    assert p['reason']=='unresolved_admitted_trade' and p['time_weighted_return'] is None
