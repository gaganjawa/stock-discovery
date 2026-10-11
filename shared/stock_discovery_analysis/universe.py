"""Point-in-time eligibility, including historical delistings and suspensions."""
from dataclasses import dataclass
from datetime import datetime
from .data import Provenance, aware


@dataclass(frozen=True)
class Membership:
    instrument_id: str
    effective_at: datetime
    state: str
    provenance: Provenance

    def __post_init__(self):
        aware(self.effective_at)
        if self.state not in ('listed','suspended','delisted'):
            raise ValueError('unknown universe state')


def universe_asof(events: tuple[Membership, ...], cutoff: datetime) -> tuple[str, ...]:
    aware(cutoff)
    latest = {}
    for event in events:
        if event.effective_at <= cutoff and event.provenance.eligible(cutoff):
            key=(event.effective_at,event.provenance.available_at)
            prior=latest.get(event.instrument_id)
            if prior is not None and key == prior[0] and event.state != prior[1]:
                raise ValueError('conflicting membership revisions')
            if prior is None or key > prior[0]: latest[event.instrument_id]=(key,event.state)
    return tuple(sorted(k for k,v in latest.items() if v[1]=='listed'))
