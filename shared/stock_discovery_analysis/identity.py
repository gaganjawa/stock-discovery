"""Stable identities and point-in-time mappings (STK-019)."""
from dataclasses import dataclass
from datetime import datetime
from .data import Provenance, aware


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    isin: str | None
    exchange: str
    series: str
    synthetic: bool = True

    def __post_init__(self):
        if not all(s.strip() for s in (self.instrument_id, self.exchange, self.series)):
            raise ValueError('identity fields required')
        if self.synthetic:
            if self.isin is not None or not self.exchange.startswith('SYNTHETIC_'):
                raise ValueError('fictional identities must not resolve to real securities')
        elif self.isin is None or len(self.isin) != 12:
            raise ValueError('verified ISIN required for real securities')


@dataclass(frozen=True)
class SymbolMapping:
    instrument_id: str
    namespace: str  # NSE symbol+series, BSE code, broker-specific identifier
    symbol: str
    valid_from: datetime
    valid_to: datetime | None
    provenance: Provenance

    def __post_init__(self):
        aware(self.valid_from)
        if self.valid_to is not None and aware(self.valid_to) <= self.valid_from:
            raise ValueError('invalid effective interval')
        if not all(s.strip() for s in (self.instrument_id, self.namespace, self.symbol)):
            raise ValueError('mapping identity fields required')

    def eligible(self, at: datetime, cutoff: datetime) -> bool:
        return (self.valid_from <= aware(at) and (self.valid_to is None or at < self.valid_to)
                and self.provenance.eligible(cutoff))


def resolve(mappings: tuple[SymbolMapping, ...], namespace: str, symbol: str,
            at: datetime, cutoff: datetime) -> str | None:
    if aware(at) > aware(cutoff):
        raise ValueError('identity lookup cannot exceed information cutoff')
    matches = {m.instrument_id for m in mappings
               if m.namespace == namespace and m.symbol == symbol and m.eligible(at, cutoff)}
    if len(matches) > 1:
        raise ValueError('ambiguous identity mapping')
    return next(iter(matches), None)
