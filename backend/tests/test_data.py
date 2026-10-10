from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import pytest
from stock_discovery_analysis.data import (
    Candle, Provenance, HistoricalClock, LiveClock, SyntheticAdapter, Document, AccountSnapshot,
)

T = datetime(2025, 8, 6, 10, tzinfo=timezone.utc)


def candle():
    return Candle('SYN-A', T-timedelta(hours=6), T, D('100'), D('110'), D('90'), D('105'), 100,
                  Provenance('synthetic', 'v1', T, T+timedelta(minutes=1),
                             T+timedelta(days=400), 'fictional_fixture'))


def test_historical_availability_and_closed_bar_boundary():
    c = candle()
    adapter = SyntheticAdapter([c])
    assert adapter.candles('SYN-A', HistoricalClock(T)) == ()
    assert adapter.candles('SYN-A', HistoricalClock(T+timedelta(minutes=1))) == (c,)
    assert adapter.candles('other', HistoricalClock(T+timedelta(days=1))) == ()
    assert not c.provenance.eligible(T+timedelta(days=1), live=True)


def test_late_revisions_and_observed_live_cannot_leak():
    p = candle().provenance
    assert not replace(p, available_at=T+timedelta(days=2)).eligible(T+timedelta(days=1))
    assert not replace(p, availability_basis='observed_live').eligible(T+timedelta(days=1))
    assert replace(p, availability_basis='verified_archive').eligible(T+timedelta(days=1))


@pytest.mark.parametrize('changes', [dict(high=D('NaN')), dict(close=D('111')),
    dict(volume=-1), dict(volume=True), dict(ends_at=T+timedelta(days=1)),
    dict(starts_at=T.replace(tzinfo=None))])
def test_invalid_candles_rejected(changes):
    with pytest.raises(ValueError):
        replace(candle(), **changes)


def test_adapters_share_cutoff_for_documents_and_accounts():
    p = candle().provenance
    d = Document('d', 'SYN-A', 'fixture:1', 'synthetic-only', p)
    a = AccountSnapshot('SYN-account', D('1000'), (('SYN-A', 1),), p)
    adapter = SyntheticAdapter(documents=[d], accounts=[a])
    assert adapter.documents('SYN-A', HistoricalClock(T)) == ()
    assert adapter.snapshot('SYN-account', HistoricalClock(T)) is None
    clock = HistoricalClock(T+timedelta(minutes=1))
    assert adapter.documents('SYN-A', clock) == (d,)
    assert adapter.snapshot('SYN-account', clock) == a


def test_clock_and_source_validation():
    assert LiveClock().now().tzinfo is not None
    with pytest.raises(ValueError):
        HistoricalClock(T.replace(tzinfo=None))
    with pytest.raises(ValueError):
        SyntheticAdapter([candle(), candle()])
    with pytest.raises(ValueError):
        SyntheticAdapter([replace(candle(), provenance=replace(candle().provenance,
                         availability_basis='verified_archive'))])
