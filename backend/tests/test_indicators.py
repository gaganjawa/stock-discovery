from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import pytest
from stock_discovery_analysis.indicators import sma,ema,atr,relative_volume,breakout_levels,features
from test_data import candle


def test_sma_ema_hand_references_and_warmup():
    values=tuple(map(D,('1','2','3','4')))
    assert sma(values,3)==(None,None,D(2),D(3))
    assert ema(values,3)==(None,None,D(2),D(3))
    actual=ema((D(2),D(4),D(8),D(10)),3)
    assert actual[:3]==(None,None,D(14)/3)
    assert abs(actual[-1]-D(22)/3)<D('1e-25')
    with pytest.raises(ValueError): sma(values,0)
    with pytest.raises(ValueError): ema((D('NaN'),),1)


def test_atr_wilder_gap_reference():
    c=candle()
    # TR: 20, 30 (gap from previous 105 to high 135), 10.
    bars=(c,replace(c,open=D(130),high=D(135),low=D(125),close=D(130)),
          replace(c,open=D(130),high=D(135),low=D(125),close=D(130)))
    assert atr(bars,2)==(None,D(25),D('17.5'))


def test_volume_and_breakout_exclude_current_candle():
    c=candle(); bars=(c,replace(c,volume=200),replace(c,volume=600,high=D(999)))
    assert relative_volume(bars,2)==(None,None,D(4))
    assert breakout_levels(bars,2)==(None,None,(D(110),D(90)))
    assert relative_volume((replace(c,volume=0),c),1)[1] is None
