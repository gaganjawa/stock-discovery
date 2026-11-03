"""STK-004/014: descriptive observed history, never execution or historical PIT."""
from typing import Literal
from decimal import Decimal
from pydantic import Field
from pydantic import model_validator
from stock_discovery_contracts.v2 import Strict, Text, Timestamp, digest, at, check
from .revision_storage import Page
from .revisions import Revision


class Observation(Strict):
    revision_id: Text
    source_version: Text
    instrument_revision_id: Text
    published_at: Timestamp
    available_at: Timestamp
    acquired_at: Timestamp
    observed_at: Timestamp
    acquisition_clock_basis: Literal['stored_revision_fetched_at'] = 'stored_revision_fetched_at'
    grant_id: Text
    grant_version: Text


class Batch(Strict):
    identity: Text
    identity_basis: Literal['verified_ingestion_pages'] = 'verified_ingestion_pages'
    page_hashes: tuple[Text, ...] = Field(min_length=1)
    response_hash: Text | None = None


class SessionCoverage(Strict):
    required_sessions: int
    observed_bars: int
    missing_sessions: tuple[Timestamp, ...]
    unverified_bar_sessions: tuple[Timestamp, ...]
    latest_session_present: bool
    duplicate_bars: bool
    warmup_complete: bool
    calendar_completeness: Literal['not_attested_by_session_list']


class AdjustedResearch(Strict):
    contract_version: Literal['adjusted-research-v1'] = 'adjusted-research-v1'
    instrument_id: Text
    provider_id: Literal['upstox'] = 'upstox'
    evaluated_at: Timestamp
    status: Literal['AVAILABLE_DESCRIPTIVE_ONLY', 'UNAVAILABLE']
    observations: tuple[Observation, ...] = ()
    batch: Batch | None = None
    price_basis: Literal['split_bonus_adjusted'] = 'split_bonus_adjusted'
    volume_basis: Literal['unknown'] = 'unknown'
    adjustment_methodology: Literal['provider_statement_only_factors_and_rounding_unverified'] = 'provider_statement_only_factors_and_rounding_unverified'
    calendar_revision_ids: tuple[Text, ...] = ()
    session_coverage: SessionCoverage
    metrics: dict[Literal['sma20','ema10','ema30','atr14','relative_volume20','breakout20','support20'], str | None] = Field(default_factory=dict)
    unavailable_reasons: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ('volume_basis_unverified', 'action_coverage_unverified', 'not_historical_decision_evidence')
    actionable: Literal[False] = False
    execution_qualified: Literal[False] = False
    historical_pit_qualified: Literal[False] = False
    publication_authorized: Literal[False] = False
    paper_admission_authorized: Literal[False] = False

    @model_validator(mode='after')
    def invariant(self):
        check(all(v is None or Decimal(v).is_finite() for v in self.metrics.values()), 'invalid_indicator_value')
        check(len({o.revision_id for o in self.observations})==len(self.observations), 'duplicate_observation')
        check(all(at(o.published_at)<=at(o.available_at)<=at(o.acquired_at)==at(o.observed_at)<=at(self.evaluated_at) for o in self.observations), 'invalid_observation_time')
        check(self.status != 'UNAVAILABLE' or bool(self.unavailable_reasons), 'unavailable_reason_required')
        check(self.metrics.get('relative_volume20') is None, 'adjusted_relative_volume_unavailable')
        check(self.status != 'UNAVAILABLE' or not self.metrics, 'unavailable_metrics')
        if self.status == 'AVAILABLE_DESCRIPTIVE_ONLY':
            check(self.batch is not None and len(self.observations)>=30 and not self.unavailable_reasons, 'unverified_adjusted_result')
        return self


def verify_pages(bars, rows, stream, pages):
    """Reconstruct existing adapter pages; timestamps alone are never identity."""
    check(bool(bars) and len(rows)<=5000 and len(pages)<=5000, 'batch_missing_or_oversized')
    check(stream is not None and stream[1:] == ('upstox','prices',True), 'batch_stream_unverified')
    records=tuple(Revision.model_validate(row[0]) for row in rows)
    check({r.revision_id for r in records}=={r.revision_id for r in bars}
          and len(records)==len(bars), 'batch_revision_set_mismatch')
    check(all(r.model_dump()==b.model_dump() for r,b in zip(records,bars)), 'batch_revision_payload_mismatch')
    check(len({r.fetched_at for r in records})==1, 'mixed_observation_times')
    check(all(r.source_id=='upstox' and r.data.kind=='candle' and r.availability_basis=='observed'
              and r.data.adjustment_basis=='split_bonus_adjusted' for r in records), 'invalid_adjusted_provenance')
    by_cursor={p[0]:p for p in pages}; check(len(by_cursor)==len(pages), 'ambiguous_batch_pages')
    cursor='';offset=0;hashes=[];seen=set()
    while True:
        check(cursor in by_cursor and cursor not in seen, 'batch_page_chain_invalid');seen.add(cursor)
        _,content_hash,next_cursor,complete,accepted,quarantined=by_cursor[cursor]
        check(quarantined==0 and 0<accepted<=100, 'batch_page_incomplete')
        part=records[offset:offset+accepted];offset+=accepted
        page=Page(cursor=cursor or None,next_cursor=next_cursor,complete=complete,records=tuple(r.model_dump(mode='json') for r in part))
        check(digest(page.model_dump(mode='json'))==content_hash, 'batch_page_hash_mismatch')
        hashes.append(content_hash)
        if complete:
            check(next_cursor is None and offset==len(records) and len(seen)==len(pages), 'batch_page_coverage_mismatch');break
        check(next_cursor==str(offset), 'batch_cursor_unverified');cursor=next_cursor
    return Batch(identity=digest([stream[0],hashes,[r.revision_id for r in records]]),page_hashes=tuple(hashes))


def describe(conn, listing, bars, sessions, readiness, cutoff, *, historical_request, provenance):
    result=dict(instrument_id=listing,evaluated_at=cutoff,status='UNAVAILABLE',session_coverage={k:tuple(readiness[k]) if k in ('missing_sessions','unverified_bar_sessions') else readiness[k] for k in SessionCoverage.model_fields},
                calendar_revision_ids=tuple(r.revision_id for r in sessions))
    reasons=[]; batch=None; observations=()
    if historical_request:reasons.append('historical_adjusted_research_not_supported')
    if not bars or any(r.source_id!='upstox' or r.data.adjustment_basis!='split_bonus_adjusted' for r in bars):
        reasons.append('adjusted_observations_unavailable')
    if not readiness['warmup_complete'] or readiness['missing_sessions'] or readiness['unverified_bar_sessions'] or readiness['duplicate_bars'] or not readiness['latest_session_present']:
        reasons.append('session_coverage_unavailable')
    if not reasons:
        rows=conn.execute('SELECT DISTINCT stream_id FROM discovery.revisions WHERE revision_id=ANY(%s)',([r.revision_id for r in bars],)).fetchall()
        if len(rows)!=1:reasons.append('batch_identity_missing_or_ambiguous')
        else:
            sid=rows[0][0]
            stream=conn.execute('SELECT stream_id,source_id,scope,complete FROM discovery.streams WHERE stream_id=%s',(sid,)).fetchone()
            stored=conn.execute("SELECT payload,grant_id,grant_version FROM discovery.revisions WHERE stream_id=%s ORDER BY payload->'data'->>'ends_at',revision_id LIMIT 5001",(sid,)).fetchall()
            pages=conn.execute('SELECT cursor_key,content_hash,next_cursor,complete,accepted,quarantined FROM discovery.pages WHERE stream_id=%s LIMIT 5001',(sid,)).fetchall()
            try:
                batch=verify_pages(bars,stored,stream,pages)
                observations=tuple(Observation(revision_id=r.revision_id,source_version=r.source_revision,
                    instrument_revision_id=r.instrument_revision_id,published_at=r.published_at,available_at=r.available_at,
                    acquired_at=r.fetched_at,observed_at=r.fetched_at,grant_id=row[1],grant_version=row[2]) for r,row in zip(bars,stored))
                check(all(at(r.available_at)<=at(r.fetched_at)<=at(cutoff) for r in bars), 'future_adjusted_observation')
            except ValueError:
                reasons.append('batch_provenance_unverified');batch=None;observations=()
    metrics={}
    if not reasons:
        from .data import Candle
        from .indicators import features
        from decimal import Decimal
        from datetime import timezone
        series=tuple(Candle(listing,at(r.data.starts_at).replace(tzinfo=timezone.utc),at(r.data.ends_at).replace(tzinfo=timezone.utc),
            *(Decimal(getattr(r.data,k)) for k in ('open','high','low','close')),r.data.volume,provenance(r),batch.identity) for r in bars)
        metrics={k:format(v,'f') if v is not None else None for k,v in features(series).items()}
        metrics['relative_volume20']=None
        result['status']='AVAILABLE_DESCRIPTIVE_ONLY'
    return AdjustedResearch(**result,batch=batch,observations=observations,metrics=metrics,unavailable_reasons=tuple(sorted(set(reasons))))
