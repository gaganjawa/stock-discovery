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
    identity_basis: Literal['verified_ingestion_pages','verified_ingestion_pages_multi_stream_v1'] = 'verified_ingestion_pages'
    page_hashes: tuple[Text, ...] = Field(min_length=1)
    stream_batches: tuple[Text, ...] = ()
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
            coverage=self.session_coverage
            check(self.batch is not None and len(self.observations)>=coverage.required_sessions>=30
                  and coverage.observed_bars==len(self.observations) and not self.unavailable_reasons, 'unverified_adjusted_result')
            check(coverage.warmup_complete and coverage.latest_session_present and not coverage.duplicate_bars
                  and not coverage.missing_sessions and not coverage.unverified_bar_sessions, 'incomplete_session_coverage')
            check(set(self.metrics)=={'sma20','ema10','ema30','atr14','relative_volume20','breakout20','support20'}, 'incomplete_indicator_keys')
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


MULTI_STREAM_REASONS={'adjusted_stream_conflict','adjusted_stream_continuity_unverified','batch_stream_limit','adjusted_vintage_unverified'}


def stream_evidence(conn, stream_id):
    stream=conn.execute('SELECT stream_id,source_id,scope,complete FROM discovery.streams WHERE stream_id=%s',(stream_id,)).fetchone()
    stored=conn.execute("SELECT payload,grant_id,grant_version FROM discovery.revisions WHERE stream_id=%s ORDER BY payload->'data'->>'ends_at',revision_id LIMIT 5001",(stream_id,)).fetchall()
    pages=conn.execute('SELECT cursor_key,content_hash,next_cursor,complete,accepted,quarantined FROM discovery.pages WHERE stream_id=%s LIMIT 5001',(stream_id,)).fetchall()
    return stream,stored,pages


def verify_streams(conn, bars, stream_ids, *, cutoff):
    """Authorize and verify full streams; overlap cannot certify adjustment vintage.

    Until a coherent vintage is independently established, even matching streams
    remain unavailable. This diagnostic path never grants qualification.
    """
    check(1<len(stream_ids)<=60, 'batch_stream_limit')
    verified=[];grants={};by_id={};inputs=[]
    for sid in stream_ids:
        stream,stored,pages=stream_evidence(conn,sid)
        records=tuple(Revision.model_validate(row[0]) for row in stored)
        inputs.append((sid,stream,stored,pages,records))
    from .read_fences import authorize_revision_dependencies
    authorize_revision_dependencies(conn,[r.revision_id for _,_,_,_,records in inputs for r in records],cutoff)
    for sid,stream,stored,pages,records in inputs:
        verified.append((at(records[0].fetched_at) if records else None,sid,verify_pages(records,stored,stream,pages),records))
        grants.update({r.revision_id:(row[1],row[2]) for r,row in zip(records,stored)})
        by_id.update({r.revision_id:r for r in records})
    check(all(r.revision_id in by_id and by_id[r.revision_id].model_dump()==r.model_dump() for r in bars), 'batch_revision_set_mismatch')
    verified.sort(key=lambda v:(v[0],v[1]))
    seen={}
    for position,(_,_,_,records) in enumerate(verified):
        overlap=0
        for r in records:
            if r.logical_key in seen:
                check(seen[r.logical_key]==r.data.model_dump(), 'adjusted_stream_conflict');overlap+=1
            else:seen[r.logical_key]=r.data.model_dump()
        # Without a shared candle, a provider re-adjustment between streams is undetectable.
        check(position==0 or overlap>0, 'adjusted_stream_continuity_unverified')
    # Matching overlap does not prove the unrefetched dates share an adjustment vintage.
    # No provider adjustment ledger/version is stored; owner approval cannot supply it.
    raise ValueError('adjusted_vintage_unverified')


def verified_session_boundaries(bars, sessions, cutoff):
    """Match actual daily candles one-to-one to known closed session intervals."""
    if len(bars)<30 or any(r.data.kind!='candle' or r.data.interval!='1d' for r in bars):
        return False
    intervals=[(at(r.data.starts_at),at(r.data.ends_at)) for r in bars]
    first_close=min(end for _,end in intervals)
    expected=[(at(r.data.opens_at),at(r.data.closes_at)) for r in sessions
              if r.data.kind=='session' and first_close<=at(r.data.closes_at)<=at(cutoff)]
    # Do not collapse duplicate or competing calendar boundaries into a set.
    return (len(intervals)==len(expected)==len(set(intervals))
            and len({start for start,_ in expected})==len(expected)
            and len({end for _,end in expected})==len(expected)
            and set(intervals)==set(expected))


def boundary_reason(bars, sessions, cutoff):
    """STK-079: name the failure precisely; both outcomes keep research unavailable."""
    if len(bars)>=30 and all(r.data.kind=='candle' and r.data.interval=='1d' for r in bars):
        intervals=[(at(r.data.starts_at),at(r.data.ends_at)) for r in bars]
        first_close=min(end for _,end in intervals);last_close=max(end for _,end in intervals)
        expected=[(at(r.data.opens_at),at(r.data.closes_at)) for r in sessions
                  if r.data.kind=='session' and first_close<=at(r.data.closes_at)<=at(cutoff)]
        through_last=[e for e in expected if e[1]<=last_close]
        distinct=len({s for s,_ in expected})==len({e for _,e in expected})==len(expected)
        # Every stored candle matches a verified session; only later sessions lack prices.
        if (distinct and len(intervals)==len(set(intervals))==len(through_last)==len(set(through_last))
                and set(intervals)==set(through_last) and len(expected)>len(through_last)):
            return 'recent_sessions_not_ingested'
    return 'session_boundaries_unverified'


def describe(conn, listing, bars, sessions, readiness, cutoff, *, historical_request, provenance, multi_stream=False):
    result=dict(instrument_id=listing,evaluated_at=cutoff,status='UNAVAILABLE',session_coverage={k:tuple(readiness[k]) if k in ('missing_sessions','unverified_bar_sessions') else readiness[k] for k in SessionCoverage.model_fields},
                calendar_revision_ids=tuple(r.revision_id for r in sessions))
    reasons=[]; batch=None; observations=()
    if historical_request:reasons.append('historical_adjusted_research_not_supported')
    if not verified_session_boundaries(bars,sessions,cutoff):
        reasons.append(boundary_reason(bars,sessions,cutoff))
    if not bars or any(r.source_id!='upstox' or r.data.adjustment_basis!='split_bonus_adjusted' for r in bars):
        reasons.append('adjusted_observations_unavailable')
    if not readiness['warmup_complete'] or readiness['missing_sessions'] or readiness['unverified_bar_sessions'] or readiness['duplicate_bars'] or not readiness['latest_session_present']:
        reasons.append('session_coverage_unavailable')
    if not reasons:
        rows=conn.execute('SELECT DISTINCT stream_id FROM discovery.revisions WHERE revision_id=ANY(%s)',([r.revision_id for r in bars],)).fetchall()
        if len(rows)!=1 and not (multi_stream and len(rows)>1):reasons.append('batch_identity_missing_or_ambiguous')
        else:
            try:
                if len(rows)==1:
                    stream,stored,pages=stream_evidence(conn,rows[0][0])
                    batch=verify_pages(bars,stored,stream,pages)
                    grants={r.revision_id:(row[1],row[2]) for r,row in zip(bars,stored)}
                else:
                    batch,grants=verify_streams(conn,bars,sorted(r[0] for r in rows),cutoff=cutoff)
                observations=tuple(Observation(revision_id=r.revision_id,source_version=r.source_revision,
                    instrument_revision_id=r.instrument_revision_id,published_at=r.published_at,available_at=r.available_at,
                    acquired_at=r.fetched_at,observed_at=r.fetched_at,grant_id=grants[r.revision_id][0],grant_version=grants[r.revision_id][1]) for r in bars)
                check(all(at(r.available_at)<=at(r.fetched_at)<=at(cutoff) for r in bars), 'future_adjusted_observation')
            except (ValueError,KeyError) as error:
                reasons.append(str(error) if str(error) in MULTI_STREAM_REASONS else 'batch_provenance_unverified');batch=None;observations=()
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
    if batch is not None and batch.stream_batches:
        result['limitations']=AdjustedResearch.model_fields['limitations'].default+('owner_approved_multi_stream_rule_v1',)
    return AdjustedResearch(**result,batch=batch,observations=observations,metrics=metrics,unavailable_reasons=tuple(sorted(set(reasons))))
