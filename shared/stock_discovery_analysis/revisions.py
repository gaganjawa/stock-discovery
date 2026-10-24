"""D3-03 typed point-in-time inputs. No provider or model access."""
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from stock_discovery_contracts.v2 import (
    Hash, Mode, Number, Ref, Strict, Text, Timestamp, at, check, digest,
)


class InstrumentData(Strict):
    kind: Literal['instrument']
    issuer_id: Text
    symbol: Text
    isin: Text | None
    series: Literal['EQ']
    status: Literal['active', 'suspended', 'delisted']
    lot_size: Annotated[int, Field(gt=0)]
    tick_size: Number
    effective_at: Timestamp

    @model_validator(mode='after')
    def tick(self):
        check(Decimal(self.tick_size) > 0, 'tick size')
        return self


class MembershipData(Strict):
    kind: Literal['membership']
    universe_version: Text
    valid_from_at: Timestamp
    valid_until_at: Timestamp | None
    eligible: bool
    reason: Text
    selection_inputs_hash: Hash

    @model_validator(mode='after')
    def interval(self):
        check(self.valid_until_at is None or at(self.valid_from_at) < at(self.valid_until_at), 'membership interval')
        return self


class CandleData(Strict):
    kind: Literal['candle']
    interval: Literal['1d']
    starts_at: Timestamp
    ends_at: Timestamp
    open: Number
    high: Number
    low: Number
    close: Number
    volume: Annotated[int, Field(ge=0)]
    # Provider-adjusted observations are a separate basis, never raw execution prices.
    # Their revision fetched_at is the observation anchor, not historical knowledge.
    adjustment_basis: Literal['raw', 'split_bonus_adjusted']

    @model_validator(mode='after')
    def ohlcv(self):
        o, h, l, c = map(Decimal, (self.open, self.high, self.low, self.close))
        check(0 < l <= min(o, c) <= max(o, c) <= h, 'OHLC range')
        check(at(self.starts_at) < at(self.ends_at), 'bar interval')
        return self


class ActionData(Strict):
    kind: Literal['action']
    action_id: Text
    action_type: Literal['split', 'bonus', 'dividend', 'unsupported']
    effective_at: Timestamp
    # New shares / old shares, e.g. split 2, 1:1 bonus 2.
    share_ratio: Number | None
    cash_per_share: Number | None
    currency: Literal['INR']

    @model_validator(mode='after')
    def economics(self):
        if self.action_type in ('split', 'bonus'):
            check(self.share_ratio is not None and Decimal(self.share_ratio) > 0 and self.cash_per_share is None, 'share action ratio')
        elif self.action_type == 'dividend':
            check(self.cash_per_share is not None and Decimal(self.cash_per_share) >= 0 and self.share_ratio is None, 'dividend cash')
        else:
            check(self.share_ratio is None and self.cash_per_share is None, 'unsupported action arithmetic')
        return self


class DocumentData(Strict):
    kind: Literal['document']
    document_id: Text
    document_type: Literal['filing', 'news']
    url: Annotated[str, Field(pattern=r'^https://[^\s]+$')]
    content_hash: Hash
    locator: Text
    metadata_only: Literal[True]


class SessionData(Strict):
    kind: Literal['session']
    calendar_version: Text
    opens_at: Timestamp
    closes_at: Timestamp

    @model_validator(mode='after')
    def interval(self):
        check(at(self.opens_at) < at(self.closes_at), 'calendar interval')
        return self


Data = Annotated[
    InstrumentData | MembershipData | CandleData | ActionData | DocumentData | SessionData,
    Field(discriminator='kind'),
]


class Revision(Strict):
    schema_version: Literal['1.0.0']
    revision_id: Text
    source_id: Text
    source_revision: Text
    sequence: Annotated[int, Field(gt=0)]
    listing_id: Text
    instrument_revision_id: Text | None
    published_at: Timestamp
    available_at: Timestamp
    fetched_at: Timestamp
    availability_basis: Literal['fictional_fixture', 'observed', 'verified_archive']
    archive_evidence_ref: Text | None
    archive_revision_id: Text | None
    supersedes_id: Text | None
    data: Data

    @model_validator(mode='after')
    def consistency(self):
        check(at(self.published_at) <= at(self.available_at) <= at(self.fetched_at), 'revision chronology')
        check((self.data.kind in ('instrument', 'session')) == (self.instrument_revision_id is None), 'instrument reference required')
        check(self.supersedes_id != self.revision_id, 'self supersession')
        check((self.sequence == 1) == (self.supersedes_id is None), 'revision chain required')
        if self.availability_basis == 'verified_archive':
            check(self.archive_evidence_ref is not None and self.archive_revision_id == self.revision_id, 'exact archive proof required')
        else:
            check(self.archive_evidence_ref is None and self.archive_revision_id is None, 'unexpected archive proof')
        if self.data.kind == 'candle':
            check(at(self.data.ends_at) <= at(self.published_at), 'unclosed candle')
        if self.availability_basis == 'fictional_fixture':
            check(self.source_id.startswith('SYN-') and self.listing_id.startswith('SYN-'), 'fictional identities')
            if self.data.kind == 'instrument':
                check(self.data.isin is None, 'fictional ISIN')
        elif self.data.kind == 'instrument':
            check(self.data.isin is not None, 'real ISIN required')
        return self

    @property
    def scope(self):
        if self.data.kind == 'document':
            return 'filings' if self.data.document_type == 'filing' else 'news'
        return {'instrument': 'universe', 'membership': 'universe', 'candle': 'prices',
                'action': 'corporate_actions', 'session': 'calendar'}[self.data.kind]

    @property
    def logical_key(self):
        d = self.data
        suffix = {
            'instrument': (), 'membership': (getattr(d, 'universe_version', None),),
            'candle': (getattr(d, 'interval', None), getattr(d, 'ends_at', None)),
            'action': (getattr(d, 'action_id', None),),
            'document': (getattr(d, 'document_id', None),),
            'session': (getattr(d, 'calendar_version', None), getattr(d, 'opens_at', None)),
        }[d.kind]
        return digest([d.kind, self.listing_id, *suffix])

    @property
    def content_hash(self):
        return digest(self.model_dump(mode='json'))


def eligible(revision: Revision, cutoff: str, mode: Mode) -> bool:
    if at(revision.available_at) > at(cutoff):
        return False
    if mode == 'synthetic':
        return revision.availability_basis == 'fictional_fixture'
    if mode == 'live_paper':
        return revision.availability_basis == 'observed' and at(revision.fetched_at) <= at(cutoff)
    if mode == 'historical_reconstructed':
        # A current back-adjusted series cannot prove the adjustment basis known
        # at a past decision, even when individual closes have archive metadata.
        if revision.data.kind == 'candle' and (revision.data.adjustment_basis != 'raw' or revision.source_id == 'upstox'):
            return False
        return revision.availability_basis == 'verified_archive'
    raise ValueError('unknown mode')


class Snapshot(Strict):
    schema_version: Literal['1.0.0']
    snapshot_id: Hash
    mode: Mode
    information_cutoff_at: Timestamp
    created_at: Timestamp
    universe_version: Text
    calendar_version: Text
    revisions: tuple[Revision, ...]
    dependencies: tuple[Revision, ...]
    grant_refs: tuple[Ref, ...]
    stream_ids: tuple[Text, ...]
    complete: bool
    issues: tuple[Text, ...]
    universe_total: Annotated[int, Field(ge=0)]
    eligible_count: Annotated[int, Field(ge=0)]
    ineligible_count: Annotated[int, Field(ge=0)]
    excluded_listings: tuple[Text, ...]


def make_snapshot(records, *, mode, cutoff, created_at, universe_version,
                  calendar_version, stream_ids, grant_refs=(), streams_complete=True, issues=()):
    """Select latest eligible revisions, retaining missing/ambiguous coverage."""
    check(at(cutoff) <= at(created_at), 'future snapshot cutoff')
    check(len({r.revision_id for r in records}) == len(records), 'duplicate revision identity')
    selected = {}
    problems = list(issues)
    for r in records:
        if not eligible(r, cutoff, mode):
            continue
        check(at(r.fetched_at) <= at(created_at), 'snapshot before fetch')
        d = r.data
        if d.kind == 'instrument' and at(d.effective_at) > at(cutoff):
            continue
        key = (r.source_id, r.logical_key)
        previous = selected.get(key)
        if previous is None or (at(r.available_at), r.sequence) > (at(previous.available_at), previous.sequence):
            selected[key] = r
    rows = sorted(selected.values(), key=lambda r: r.revision_id)
    # Multiple sources for a logical observation cannot be silently spliced.
    keys = [r.logical_key for r in rows]
    check(len(keys) == len(set(keys)), 'ambiguous source selection')
    all_by_id = {r.revision_id: r for r in records}
    dependencies = {}
    valid_rows = []
    for r in rows:
        if r.instrument_revision_id:
            parent = all_by_id.get(r.instrument_revision_id)
            if parent is None or parent.data.kind != 'instrument' or parent.listing_id != r.listing_id or not eligible(parent,cutoff,mode):
                problems.append('unresolved_instrument:' + r.listing_id)
                continue
            check(at(parent.fetched_at) <= at(created_at), 'dependency fetched after snapshot')
            dependencies[parent.revision_id] = parent
        valid_rows.append(r)
    rows = valid_rows
    dependencies = tuple(dependencies[k] for k in sorted(dependencies) if k not in {r.revision_id for r in rows})
    memberships = [r for r in rows if r.data.kind == 'membership' and r.data.universe_version == universe_version
                   and at(r.data.valid_from_at) <= at(cutoff)
                   and (r.data.valid_until_at is None or at(cutoff) < at(r.data.valid_until_at))]
    instruments = {r.listing_id: r for r in rows if r.data.kind == 'instrument'}
    sessions = [r for r in rows if r.data.kind == 'session' and r.data.calendar_version == calendar_version and at(r.data.closes_at) <= at(cutoff)]
    if not memberships:
        problems.append('universe_unavailable')
    if not sessions:
        problems.append('calendar_unavailable')
    excluded = set()
    for member in memberships:
        instrument = instruments.get(member.listing_id)
        if instrument is None or instrument.data.status != 'active' or not member.data.eligible:
            excluded.add(member.listing_id)
            problems.append('ineligible:' + member.listing_id)
            continue
        candles = [r for r in rows if r.listing_id == member.listing_id and r.data.kind == 'candle']
        required = {(r.data.opens_at,r.data.closes_at) for r in sessions}
        actual = {(r.data.starts_at,r.data.ends_at) for r in candles if r.data.volume > 0}
        if not required or not required <= actual:
            problems.append('missing_sessions:' + member.listing_id)
    for r in rows:
        if r.data.kind == 'action' and r.data.action_type == 'unsupported' and at(r.data.effective_at) <= at(cutoff):
            problems.append('unsupported_action:' + r.listing_id)
            excluded.add(r.listing_id)
    member_ids = {r.listing_id for r in memberships}
    excluded &= member_ids
    fields = dict(schema_version='1.0.0', mode=mode, information_cutoff_at=cutoff,
                  created_at=created_at, universe_version=universe_version,
                  dependencies=dependencies, grant_refs=tuple(grant_refs),
                  calendar_version=calendar_version, revisions=tuple(rows),
                  stream_ids=tuple(sorted(stream_ids)), issues=tuple(sorted(set(problems))),
                  complete=streams_complete and not any(not p.startswith('ineligible:') for p in problems),
                  universe_total=len(member_ids), eligible_count=len(member_ids-excluded),
                  ineligible_count=len(excluded), excluded_listings=tuple(sorted(excluded)))
    # Include full immutable inputs, including provenance; source IDs alone are insufficient.
    wire = {**fields, 'revisions': [r.model_dump(mode='json') for r in rows],
            'dependencies': [r.model_dump(mode='json') for r in dependencies],
            'grant_refs': [r.model_dump(mode='json') for r in grant_refs]}
    return Snapshot(snapshot_id=digest(wire), **fields)


def adjusted_close(candle: Revision, snapshot: Snapshot) -> Decimal:
    """Split/bonus adjusted research feature, never an executable price."""
    check(candle in snapshot.revisions and candle.data.kind == 'candle', 'snapshot candle required')
    check(candle.data.adjustment_basis == 'raw', 'provider_adjusted_candle_requires_action_coverage')
    check(candle.source_id != 'upstox', 'upstox_legacy_raw_basis_unverified')
    value = Decimal(candle.data.close)
    for r in snapshot.revisions:
        d = r.data
        if d.kind != 'action' or r.listing_id != candle.listing_id:
            continue
        if at(candle.data.ends_at) < at(d.effective_at) <= at(snapshot.information_cutoff_at):
            check(d.action_type != 'unsupported', 'unsupported adjustment')
            if d.action_type in ('split', 'bonus'):
                value /= Decimal(d.share_ratio)
    return value
