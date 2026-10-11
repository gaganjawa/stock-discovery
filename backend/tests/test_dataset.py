from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import pytest
from stock_discovery_analysis.dataset import demo_dataset


def test_demo_is_deterministic_versioned_and_asof():
    d=demo_dataset(); cutoff=d.calendar.sessions[59].closes_at+timedelta(minutes=1)
    assert d.version==demo_dataset().version
    assert len(d.asof('SYN-ALPHA',cutoff))==60
    assert d.quality('SYN-ALPHA',cutoff,30)==()
    assert 'insufficient_warmup' in d.quality('SYN-ALPHA',d.calendar.sessions[2].closes_at+timedelta(minutes=1),30)
    changed=replace(d,candles=(replace(d.candles[0],volume=10),*d.candles[1:]))
    assert changed.version!=d.version
    assert 'missing_or_off_calendar_candles' in replace(d,candles=tuple(c for c in d.candles if c!=d.candles[50])).quality('SYN-ALPHA',cutoff,30)
    with pytest.raises(ValueError): replace(d,rights_ref='unapproved-real-data')


def test_future_append_cannot_change_historical_inputs():
    d=demo_dataset(); cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    altered=replace(d,candles=tuple(replace(c,close=c.high) if c.ends_at>cutoff else c for c in d.candles))
    assert d.asof('SYN-ALPHA',cutoff)==altered.asof('SYN-ALPHA',cutoff)
