from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import pytest
from stock_discovery_analysis.calendar import Calendar, Session, CorporateAction, split_adjusted, action_crosses_window
from test_data import T, candle


def test_split_is_asof_and_raw_prices_remain_unchanged():
    c=candle(); cutoff=T+timedelta(days=2)
    p=replace(c.provenance,published_at=T,available_at=T,fetched_at=T)
    split=CorporateAction('split','SYN-A','split',T+timedelta(days=1),D(2),p)
    assert split_adjusted((c,),(split,),T+timedelta(minutes=1))[0].close == D(105)
    adjusted=split_adjusted((c,),(split,),cutoff)[0]
    assert adjusted.close == D('52.5') and c.close == D(105)
    late=replace(split,provenance=replace(p,available_at=cutoff+timedelta(days=1),fetched_at=cutoff+timedelta(days=1)))
    assert split_adjusted((c,),(late,),cutoff)[0].close == D(105)
    dividend=replace(split,kind='dividend',value=D(1))
    assert split_adjusted((c,),(dividend,),cutoff)[0].close == D(105)
    assert action_crosses_window((split,),'SYN-A',T,cutoff,cutoff)
    with pytest.raises(ValueError): split_adjusted((c,),(),T)


def test_calendar_holidays_and_availability():
    c=candle(); p=replace(c.provenance,published_at=T,available_at=T,fetched_at=T)
    s=Session(T+timedelta(days=1),T+timedelta(days=1,hours=6))
    next_session=Session(T+timedelta(days=4),T+timedelta(days=4,hours=6))
    cal=Calendar('fictional-v1',(s,next_session),p)
    assert cal.through(T+timedelta(days=3)) == (s,)
    with pytest.raises(ValueError): cal.through(T-timedelta(seconds=1))
    with pytest.raises(ValueError): Calendar('bad',(s,s),p)
