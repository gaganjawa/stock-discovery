"""Pinned session calendars and point-in-time split adjustments (STK-020)."""
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from .data import Candle, Provenance, aware


@dataclass(frozen=True)
class Session:
    opens_at: datetime
    closes_at: datetime

    def __post_init__(self):
        if aware(self.opens_at) >= aware(self.closes_at):
            raise ValueError('invalid session')


@dataclass(frozen=True)
class Calendar:
    version: str
    sessions: tuple[Session, ...]
    provenance: Provenance

    def __post_init__(self):
        if not self.version or not self.sessions:
            raise ValueError('versioned calendar required')
        if any(a.closes_at >= b.opens_at for a,b in zip(self.sessions,self.sessions[1:])):
            raise ValueError('sessions must be ordered and disjoint')

    def through(self, cutoff: datetime) -> tuple[Session, ...]:
        if not self.provenance.eligible(cutoff):
            raise ValueError('calendar unavailable at cutoff')
        return tuple(s for s in self.sessions if s.closes_at <= cutoff)


@dataclass(frozen=True)
class CorporateAction:
    action_id: str
    instrument_id: str
    kind: str
    effective_at: datetime
    value: Decimal  # split: new shares per old share; dividend: INR per share
    provenance: Provenance

    def __post_init__(self):
        aware(self.effective_at)
        if self.kind not in ('split','dividend') or not self.value.is_finite() or self.value <= 0:
            raise ValueError('invalid corporate action')


def split_adjusted(candles: tuple[Candle, ...], actions: tuple[CorporateAction, ...],
                   cutoff: datetime) -> tuple[Candle, ...]:
    """Feature-only price normalization. Raw candles and execution remain unchanged.

    Volume is left raw; relative-volume windows crossing a split must be excluded.
    Cash dividends are not silently turned into total-return price adjustments.
    """
    aware(cutoff)
    if any(c.ends_at > cutoff or not c.provenance.eligible(cutoff) for c in candles):
        raise ValueError('future candle supplied to feature adjustment')
    if len({a.action_id for a in actions}) != len(actions):
        raise ValueError("duplicate corporate action")
    if any(c.adjustment_version != "raw-v1" for c in candles):
        raise ValueError("adjustment requires raw input")
    result = []
    for c in candles:
        factor = Decimal(1)
        ids = []
        for action in actions:
            if (action.instrument_id == c.instrument_id and action.kind == 'split'
                and c.ends_at < action.effective_at <= cutoff
                and action.provenance.eligible(cutoff)):
                factor *= action.value
                ids.append(action.action_id)
        result.append(replace(c, open=c.open/factor, high=c.high/factor, low=c.low/factor,
                              close=c.close/factor,
                              adjustment_version='split-price-v1:'+','.join(sorted(ids))))
    return tuple(result)


def action_crosses_window(actions: tuple[CorporateAction, ...], instrument_id: str,
                          start: datetime, end: datetime, cutoff: datetime) -> bool:
    """Fail closed for unsupported dividend/split trading and volume windows."""
    return any(a.instrument_id == instrument_id and start < a.effective_at <= end
               and a.provenance.eligible(cutoff) for a in actions)
