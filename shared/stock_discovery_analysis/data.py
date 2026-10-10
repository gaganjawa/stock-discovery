"""Availability-aware shared boundaries. Real providers remain disabled."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, Sequence


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone-aware timestamp required')
    return value


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class HistoricalClock:
    cutoff: datetime

    def __post_init__(self):
        aware(self.cutoff)

    def now(self) -> datetime:
        return self.cutoff


class LiveClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Provenance:
    source_ref: str
    source_version: str
    published_at: datetime
    available_at: datetime
    fetched_at: datetime
    availability_basis: str

    def __post_init__(self):
        for value in (self.published_at, self.available_at, self.fetched_at):
            aware(value)
        if not self.published_at <= self.available_at <= self.fetched_at:
            raise ValueError('invalid availability ordering')
        if not self.source_ref.strip() or not self.source_version.strip():
            raise ValueError('source and version required')
        if self.availability_basis not in ('observed_live', 'verified_archive', 'fictional_fixture'):
            raise ValueError('unknown availability basis')

    def eligible(self, cutoff: datetime, *, live: bool = False) -> bool:
        aware(cutoff)
        return self.available_at <= cutoff and (
            self.fetched_at <= cutoff or
            (not live and self.availability_basis in ('verified_archive', 'fictional_fixture'))
        )


@dataclass(frozen=True)
class Candle:
    instrument_id: str
    starts_at: datetime
    ends_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    provenance: Provenance
    adjustment_version: str = 'raw-v1'

    def __post_init__(self):
        aware(self.starts_at)
        aware(self.ends_at)
        if not self.starts_at < self.ends_at <= self.provenance.published_at:
            raise ValueError('candle must be closed before publication')
        prices = (self.open, self.high, self.low, self.close)
        if any(not isinstance(p, Decimal) or not p.is_finite() or p <= 0 for p in prices):
            raise ValueError('finite positive Decimal prices required')
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError('invalid OHLC')
        if type(self.volume) is not int or self.volume < 0:
            raise ValueError('invalid volume')
        if not self.instrument_id.strip() or not self.adjustment_version.strip():
            raise ValueError('identity and adjustment version required')


@dataclass(frozen=True)
class Document:
    document_id: str
    instrument_id: str
    locator: str
    rights_ref: str
    provenance: Provenance


@dataclass(frozen=True)
class AccountSnapshot:
    account_ref: str
    cash: Decimal
    holdings: tuple[tuple[str, int], ...]
    provenance: Provenance


class MarketDataAdapter(Protocol):
    def candles(self, instrument_id: str, clock: Clock) -> tuple[Candle, ...]: ...


class DocumentAdapter(Protocol):
    def documents(self, instrument_id: str, clock: Clock) -> tuple[Document, ...]: ...


class AccountAdapter(Protocol):
    def snapshot(self, account_ref: str, clock: Clock) -> AccountSnapshot | None: ...


class SyntheticAdapter:
    """Closed, immutable fixture records only; no network or broker capability."""
    def __init__(self, candles: Sequence[Candle] = (), documents: Sequence[Document] = (),
                 accounts: Sequence[AccountSnapshot] = ()):
        self._candles, self._documents, self._accounts = tuple(candles), tuple(documents), tuple(accounts)
        for record in (*self._candles, *self._documents, *self._accounts):
            if record.provenance.availability_basis != 'fictional_fixture':
                raise ValueError('synthetic adapter requires fictional provenance')
        keys = [(c.instrument_id, c.starts_at) for c in self._candles]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate candle: select a pinned dataset revision first')

    def candles(self, instrument_id: str, clock: Clock) -> tuple[Candle, ...]:
        cutoff = clock.now()
        return tuple(sorted((c for c in self._candles if c.instrument_id == instrument_id
                             and c.ends_at <= cutoff
                             and c.provenance.eligible(cutoff, live=isinstance(clock, LiveClock))),
                            key=lambda c: c.starts_at))

    def documents(self, instrument_id: str, clock: Clock) -> tuple[Document, ...]:
        cutoff = clock.now()
        return tuple(d for d in self._documents if d.instrument_id == instrument_id
                     and d.provenance.eligible(cutoff, live=isinstance(clock, LiveClock)))

    def snapshot(self, account_ref: str, clock: Clock) -> AccountSnapshot | None:
        cutoff = clock.now()
        eligible = [a for a in self._accounts if a.account_ref == account_ref
                    and a.provenance.eligible(cutoff, live=isinstance(clock, LiveClock))]
        return max(eligible, key=lambda a: a.provenance.available_at, default=None)
