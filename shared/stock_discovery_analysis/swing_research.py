"""STK-079: fenced stored evidence -> qualification -> research-only swing.

The server pins a reviewed, immutable coverage document, not client assertions.
No model, acquisition, result cache, publication or portfolio writes occur here.
"""
from datetime import timezone
from decimal import Decimal as D, Context, localcontext, DecimalException
from typing import Annotated, Literal

from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Text, Hash, Timestamp, Number, at, digest, check
from stock_discovery_contracts.rights import authorize
from .calendar import Calendar, Session
from .data import Candle, Provenance
from .evidence import content_hash
from .evidence_storage import read_evidence
from .grant_fences import database_request
from .indicators import features
from .publication_store import now
from .read_fences import guarded_read
from .real_access import source_access
from .revisions import Revision, eligible
from .risk import sizing
from .strategy import STRATEGY_VERSION, swing_conditions, swing_levels
from .swing_qualification import SwingInputs, InputEvidence, Requirement, SCOPES, qualify

VERSION = 'stored-swing-research-2'


class Coverage(Strict):
    requirement: Requirement
    covers_from: Timestamp
    covers_through: Timestamp
    fresh_until: Timestamp
    complete: bool


class GrantReview(Strict):
    # Hash pins the original grant's whole immutable policy, not just a provider.
    grant_hash: Hash
    policy_evidence_ref: Text
    retention_compliant: bool
    deletion_obligations_supported: bool


class CoverageReview(Strict):
    schema_version: Literal['swing-coverage-1']
    listing_id: Text
    # Exact full revisions, including original instrument parents. No market
    # values/settings in configuration; all are loaded from these stored rows.
    revisions: Annotated[dict[Text, Hash], Field(min_length=1, max_length=600)]
    coverage: Annotated[tuple[Coverage, ...], Field(max_length=6)]
    grants: Annotated[tuple[GrantReview, ...], Field(max_length=32)]
    volume_basis: Literal['raw', 'adjusted', 'unknown']
    action_free_window: bool | None
    risk_prohibited: bool | None


class HypotheticalRisk(Strict):
    # Explicit scenario, never the actual account or an admission decision.
    approved_ceiling: Number
    period_base: Number
    active_equity: Number
    per_trade_fraction: Number
    combined_fraction: Number
    existing_and_pending_risk: Number
    spendable_cash: Number
    entry_variable_fee: Number
    exit_variable_fee: Number
    entry_fixed_fee: Number
    exit_fixed_fee: Number
    instrument_fraction: Number
    sector_fraction: Number
    gross_fraction: Number
    instrument_exposure: Number
    sector_exposure: Number
    gross_exposure: Number
    stop_slippage: Number


class SwingConfig(Strict):
    listing_id: Text
    review_revision_id: Text
    review_content_hash: Hash
    # Operator reviewed semantic/policy approval of this exact document hash.
    review_approval_ref: Text
    policy_version: Text
    max_price_age_seconds: Annotated[int, Field(gt=0, le=604800)]
    risk: HypotheticalRisk


def provenance(r):
    return Provenance(r.source_id, r.source_revision,
        *(at(t).replace(tzinfo=timezone.utc) for t in (r.published_at,r.available_at,r.fetched_at)),
        'observed_live')


def current_identity(revisions, cutoff):
    """Select effective settings, retaining all originals elsewhere for rights.

    InstrumentData supports effective_at only (no invented effective-until).
    Equal-effective corrections within one source use its immutable sequence;
    independent provider identities remain ambiguous rather than being spliced.
    """
    candidates={}
    for r in revisions:
        if r.data.kind!='instrument' or not eligible(r,cutoff,'live_paper') or at(r.data.effective_at)>at(cutoff):
            continue
        candidates.setdefault(r.source_id,[]).append(r)
    if len(candidates)!=1:return None
    rows=next(iter(candidates.values()))
    latest=max((at(r.data.effective_at),r.sequence) for r in rows)
    current={r.content_hash:r for r in rows if (at(r.data.effective_at),r.sequence)==latest}
    return next(iter(current.values())) if len(current)==1 else None


def valid_geometry(levels, tick_size):
    """Reject inconsistent real-research levels; never alter frozen formulas."""
    try:
        if not tick_size.is_finite() or tick_size<=0:return False
        values=[levels[k] for k in ('stop','entry','entry_cap','target')]
        if any(not v.is_finite() or v<=0 or v%tick_size!=0 for v in values):return False
        stop,entry,cap,target=values
        return stop<entry<=cap<target
    except (DecimalException,KeyError,TypeError):
        return False


def document_role(document, source_id, access):
    """Only typed immutable metadata and trusted-source configuration classify.

    Titles, filenames and JSON/prose in the body never promote a document.
    Legacy unclassified secondary filings are not silently grandfathered in.
    """
    if document['category']=='coverage_review':return 'coverage_review'
    if document['category']=='news' and document['revision']['data']['document_type']=='news':return 'news'
    if (document['category'] in ('annual_report','quarterly_report','announcement')
        and document['revision']['data']['document_type']=='filing'
        and document['authority']=='issuer_primary' and source_id in access.primary_source_ids):return 'filing'
    return 'unknown'


def unavailable(listing, cutoff, reasons):
    return dict(mode='real_research', research_only=True, instrument_id=listing,
        analysis_cutoff_at=cutoff, status='INSUFFICIENT_EVIDENCE', reasons=sorted(set(reasons)),
        actionable=False, publication_authorized=False, paper_admission_authorized=False,
        trading_authorized=False, evidence_revisions=[], indicators={}, levels=None,
        hypothetical_sizing=None, qualification=None, freshness=None, analysis_id=None)


def research(conn, config, listing, *, cutoff_at=None, clock=now):
    """Existing authenticated company endpoint's optional swing view.

    Always reload/reauthorize immutable inputs; no cached result is trusted.
    A denied read returns no source IDs, values or grant diagnostics.
    """
    cutoff=cutoff_at or clock()
    check(listing in config.listing_ids, 'listing_not_configured')
    if at(cutoff)>at(clock()):
        return unavailable(listing,cutoff,['future_analysis_cutoff'])
    if config.swing is None or config.swing.listing_id!=listing:
        return unavailable(listing,cutoff,['swing_coverage_review_not_configured'])
    access=source_access(config.sources,clock)
    try:
        with guarded_read(conn,access) as guard:
            with localcontext(Context(prec=28)):
                result=_research(conn,config.swing,listing,cutoff,access,guard)
        return result
    except PermissionError:
        return unavailable(listing,cutoff,['source_access_or_provenance_unavailable'])


def _research(conn, policy, listing, cutoff, access, guard):
    item=read_evidence(conn,policy.review_revision_id,access=access,cutoff=cutoff,mode='live_paper')
    doc=item['document']; review_revision=Revision.model_validate(doc['revision'])
    check(doc['category']=='coverage_review' and doc['media_type']=='text/plain' and content_hash(doc['body'])==policy.review_content_hash,
          'review_pin_mismatch')
    check(review_revision.listing_id==listing, 'review_identity_mismatch')
    review=CoverageReview.model_validate_json(doc['body'])
    check(review.listing_id==listing, 'review_identity_mismatch')
    check(len({c.requirement for c in review.coverage})==len(review.coverage), 'ambiguous_coverage')
    check(len({g.grant_hash for g in review.grants})==len(review.grants), 'ambiguous_policy_review')
    check(all(at(c.covers_from)<=at(c.covers_through)<=at(review_revision.fetched_at)
              and at(c.covers_through)<=at(c.fresh_until) for c in review.coverage), 'unobserved_coverage_claim')
    records={}
    for rid, expected in sorted(review.revisions.items()):
        guard.add(rid)
        row=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(rid,)).fetchone()
        check(row is not None,'revision_missing')
        r=Revision.model_validate(row[0])
        check(r.revision_id==rid and r.content_hash==expected and eligible(r,cutoff,'live_paper'), 'revision_pin_or_time')
        check(r.listing_id==listing or r.data.kind=='session' and r.listing_id=='NSE', 'revision_instrument')
        records[rid]=r
    records[review_revision.revision_id]=review_revision
    # An old pinned evidence set must not suppress newly observed corrections,
    # bars, actions, filings or events. No live fetch is performed to fill gaps.
    latest=conn.execute("""SELECT DISTINCT ON (source_id,logical_key) payload FROM discovery.revisions
        WHERE (listing_id=%s OR (kind='session' AND listing_id='NSE')) AND available_at<=%s
        AND payload->>'availability_basis'='observed' AND (payload->>'fetched_at')::timestamptz<=%s
        ORDER BY source_id,logical_key,sequence DESC LIMIT 602""",(listing,cutoff,cutoff)).fetchall()
    current=[Revision.model_validate(r[0]) for r in latest]
    check(len(current)<=601, 'evidence_limit')
    for r in current:guard.add(r.revision_id)
    if any(r.revision_id not in records for r in current):
        return unavailable(listing,cutoff,['coverage_review_requires_refresh'])
    for r in records.values():
        check(r.instrument_revision_id is None or r.instrument_revision_id in records,'instrument_parent_unpinned')
    guard.authorize()  # Complete dependency lock set, held through strategy and return.
    deps=guard.dependencies()
    coverage={c.requirement:c for c in review.coverage}
    policies={g.grant_hash:g for g in review.grants}
    evidence=[]; scoped=[]
    def evidence_row(r, requirement):
        original, stream, _=deps[r.revision_id]
        scoped_stream=stream.model_copy(update={'scope':SCOPES[requirement]})
        request=access.request_for(scoped_stream).model_copy(update={'uses':('acquire','store','derive')})
        current=access.load_grant(stream)
        p=policies.get(digest(original.model_dump(mode='json')))
        c=coverage.get(requirement)
        scoped.append((original,scoped_stream))
        evidence.append(InputEvidence(requirement=requirement,instrument_id=listing,revision_id=r.revision_id,
            acquisition_grant_id=original.grant_id,acquisition_grant_version=original.version,
            acquisition_grant=original,grant=current,acquired_at=r.fetched_at,revision_provenance=provenance(r),
            request=request,observed_at=r.fetched_at,
            covers_from=c.covers_from if c else cutoff,covers_through=c.covers_through if c else cutoff,
            fresh_until=c.fresh_until if c else cutoff,complete=c.complete if c else False,
            policy_evidence_ref=p.policy_evidence_ref if p else None,
            retention_compliant=p.retention_compliant if p else None,
            deletion_obligations_supported=p.deletion_obligations_supported if p else None,fences_open=True))
    # The pinned review document itself is evidence for coverage/absence claims.
    # Its ORIGINAL grant must authorize every asserted data scope independently.
    for requirement in SCOPES:evidence_row(review_revision,requirement)
    by_kind={kind:sorted((r for r in records.values() if r.data.kind==kind),key=lambda r:r.revision_id)
             for kind in ('instrument','membership','candle','session','action','document')}
    for kind,requirement in [('instrument','instrument'),('membership','instrument'),('candle','prices'),
                             ('session','calendar'),('action','corporate_actions')]:
        for r in by_kind[kind]:evidence_row(r,requirement)
    adverse_events=False; substantive_filing=False; unknown_document=False
    for r in by_kind['document']:
        if r.revision_id!=review_revision.revision_id:
            document=read_evidence(conn,r.revision_id,access=access,cutoff=cutoff,mode='live_paper')
            role=document_role(document['document'],r.source_id,access)
            substantive_filing |= role=='filing'
            unknown_document |= role=='unknown'
            # A reviewed coverage flag cannot suppress a contradictory stored
            # default/restatement/auditor/regulatory claim. Unverified adverse
            # claims also need resolution; do not infer they are harmless.
            adverse_events |= any(e['event_type']!='earnings' for e in document['events'])
            evidence_row(r,'filings' if r.data.document_type=='filing' else 'material_events')
    bars=sorted(by_kind['candle'],key=lambda r:r.data.ends_at)
    sessions=sorted(by_kind['session'],key=lambda r:r.data.opens_at)
    identities=by_kind['instrument']; memberships=by_kind['membership']
    identity=current_identity(identities,cutoff)
    members=[r for r in memberships if at(r.data.valid_from_at)<=at(cutoff)
             and (r.data.valid_until_at is None or at(cutoff)<at(r.data.valid_until_at))]
    candles=tuple(Candle(listing,at(r.data.starts_at).replace(tzinfo=timezone.utc),
        at(r.data.ends_at).replace(tzinfo=timezone.utc),*(D(getattr(r.data,k)) for k in ('open','high','low','close')),
        r.data.volume,provenance(r),adjustment_version='raw-v1' if r.data.adjustment_basis=='raw' and r.source_id!='upstox'
        else 'unqualified-provider-basis') for r in bars)
    cal=Calendar(digest([r.revision_id for r in sessions]),tuple(Session(
        at(r.data.opens_at).replace(tzinfo=timezone.utc),at(r.data.closes_at).replace(tzinfo=timezone.utc)) for r in sessions),
        provenance(sessions[-1])) if sessions else None
    start=at(bars[0].data.starts_at) if bars else at(cutoff)
    action_free=review.action_free_window is True and not any(start<=at(r.data.effective_at)<=at(cutoff) for r in by_kind['action'])
    inputs=SwingInputs(instrument_id=listing,cutoff_at=cutoff,evidence=tuple(evidence),bars=candles,
        bar_revision_ids=tuple(r.revision_id for r in bars),calendar=cal,calendar_revision_id=sessions[-1].revision_id if sessions else None,
        price_basis='raw' if all(r.data.adjustment_basis=='raw' for r in bars) else 'split_bonus_adjusted',
        volume_basis=review.volume_basis,action_free_window=action_free,
        tick_size=D(identity.data.tick_size) if identity else None,lot_size=identity.data.lot_size if identity else None,
        eligible=identity is not None and identity.data.status=='active' and len(members)==1 and members[0].data.eligible,
        risk_prohibited=True if adverse_events else review.risk_prohibited)
    qualification=qualify(inputs)
    reasons=[category+':'+reason for category,items in qualification.checks.items() for reason in items]
    if not substantive_filing:
        reasons.append('filings:stored_filing_missing')
    if unknown_document:reasons.append('filings:document_classification_unverified')
    age=int((at(cutoff)-at(bars[-1].data.ends_at)).total_seconds()) if bars else None
    if age is None or age>policy.max_price_age_seconds:reasons.append('prices:stale_or_missing')
    result=unavailable(listing,cutoff,reasons)
    result.update(qualification=qualification.model_dump(mode='json'),
        evidence_revisions=sorted(records),freshness=dict(latest_bar_at=bars[-1].data.ends_at if bars else None,
            price_age_seconds=age,max_price_age_seconds=policy.max_price_age_seconds),
        instrument_revision_id=identity.revision_id if identity else None,
        formula_version=VERSION,strategy_version=STRATEGY_VERSION,policy_version=policy.policy_version,
        input_hash=digest({rid:r.content_hash for rid,r in sorted(records.items())}),policy_hash=digest(policy.model_dump(mode='json')))
    if not reasons:
        f=features(candles);result['indicators']={k:format(v,'f') for k,v in f.items()}
        result['status']='WAIT';result['reasons']=['technical_conditions_not_met']
        if swing_conditions(f,candles[-1].close):
            levels=swing_levels(candles[-1].high,f['atr14'],inputs.tick_size)
            risk=policy.risk.model_dump();slippage=D(risk.pop('stop_slippage'))
            stop=levels['stop']-slippage
            if not valid_geometry(levels,inputs.tick_size):
                result.update(status='INSUFFICIENT_EVIDENCE',reasons=['invalid_swing_geometry'])
            elif slippage<0 or stop<=0:
                result.update(status='INSUFFICIENT_EVIDENCE',reasons=['invalid_protective_exit'])
            else:
                sized=sizing(dict(risk,entry=str(levels['entry_cap']),protective_exit=str(stop)))
                quantity=sized['quantity']//inputs.lot_size*inputs.lot_size
                # Recompute cash/loss at rounded-down whole-lot quantity.
                loss=quantity*(levels['entry_cap']-stop+D(risk['entry_variable_fee'])+D(risk['exit_variable_fee']))
                cash=quantity*(levels['entry_cap']+D(risk['entry_variable_fee']))
                if quantity:loss+=D(risk['entry_fixed_fee'])+D(risk['exit_fixed_fee']);cash+=D(risk['entry_fixed_fee'])
                result.update(status='BUY' if quantity else 'WAIT',reasons=['technical_conditions_met'] if quantity else ['hypothetical_risk_capacity_zero'],
                    levels={k:format(v,'f') for k,v in levels.items()},hypothetical_sizing=dict(
                        quantity=quantity,planned_loss=format(loss,'f'),entry_cash=format(cash,'f'),
                        stop_fill_assumption=format(stop,'f'),scenario_only=True))
    # Scope-specific attestations may require more than a document's filing scope.
    # Check every original/current grant after all locks and computation, using DB
    # time. No extra locks are acquired by this pass; the outer guard rechecks too.
    for original,stream in scoped:
        req=database_request(conn,access.request_for(stream),('store','derive'))
        if not authorize(original,req).allowed or not authorize(access.load_grant(stream),req).allowed:
            raise PermissionError('real_read_access_denied')
    # Current validity, AFTER computation and all lock waits. An old requested
    # cutoff cannot revive stale input; no wall-clock value enters the input hash.
    dbtime=conn.execute('SELECT clock_timestamp()').fetchone()[0].astimezone(timezone.utc).replace(tzinfo=None)
    expired=[c.requirement+':expired_coverage' for c in review.coverage if dbtime>at(c.fresh_until)]
    if bars and (dbtime-at(bars[-1].data.ends_at)).total_seconds()>policy.max_price_age_seconds:
        expired.append('prices:expired_at_read')
    if expired:
        result.update(status='INSUFFICIENT_EVIDENCE',reasons=sorted(set(reasons+expired)),levels=None,hypothetical_sizing=None)
    result['analysis_id']=digest(result)
    return result
