"""Deterministic Decimal indicators; missing values are never imputed."""
from decimal import Decimal as D
from .data import Candle


def _validate(values, period):
    if type(period) is not int or period<1: raise ValueError('positive integer period required')
    if any(not isinstance(v,D) or not v.is_finite() for v in values):
        raise ValueError('finite Decimal values required')


def sma(values: tuple[D,...], period: int) -> tuple[D|None,...]:
    _validate(values,period)
    return tuple(None if i+1<period else sum(values[i+1-period:i+1],D(0))/period for i in range(len(values)))


def ema(values: tuple[D,...], period: int) -> tuple[D|None,...]:
    _validate(values,period)
    result=[]; prior=None; alpha=D(2)/D(period+1)
    for i,value in enumerate(values):
        if i+1<period: result.append(None); continue
        prior=sum(values[:period],D(0))/period if prior is None else prior+alpha*(value-prior)
        result.append(prior)
    return tuple(result)


def atr(bars: tuple[Candle,...], period: int) -> tuple[D|None,...]:
    ranges=tuple(max(c.high-c.low,abs(c.high-bars[i-1].close),abs(c.low-bars[i-1].close))
                 if i else c.high-c.low for i,c in enumerate(bars))
    _validate(ranges,period)
    result=[]; prior=None
    for i,value in enumerate(ranges):
        if i+1<period: result.append(None); continue
        prior=sum(ranges[:period],D(0))/period if prior is None else (prior*(period-1)+value)/period
        result.append(prior)
    return tuple(result)


def relative_volume(bars: tuple[Candle,...], period: int) -> tuple[D|None,...]:
    _validate((),period)
    result=[]
    for i,c in enumerate(bars):
        average=sum((D(b.volume) for b in bars[max(0,i-period):i]),D(0))/period
        result.append(None if i<period or average==0 else D(c.volume)/average)
    return tuple(result)


def breakout_levels(bars: tuple[Candle,...], period: int) -> tuple[tuple[D,D]|None,...]:
    _validate((),period)
    return tuple(None if i<period else (max(c.high for c in bars[i-period:i]),
                                        min(c.low for c in bars[i-period:i])) for i in range(len(bars)))


def features(bars: tuple[Candle,...]) -> dict:
    if not bars: return {}
    if len({(c.instrument_id,c.adjustment_version) for c in bars})!=1 or any(a.ends_at>=b.starts_at for a,b in zip(bars,bars[1:])):
        raise ValueError('features require one ordered instrument/adjustment series')
    closes=tuple(c.close for c in bars)
    level=breakout_levels(bars,20)[-1]
    return {'sma20':sma(closes,20)[-1], 'ema10':ema(closes,10)[-1], 'ema30':ema(closes,30)[-1],
            'atr14':atr(bars,14)[-1], 'relative_volume20':relative_volume(bars,20)[-1],
            'breakout20':level[0] if level else None, 'support20':level[1] if level else None}
