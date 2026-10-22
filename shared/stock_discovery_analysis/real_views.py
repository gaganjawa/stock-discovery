"""Rights-aware actual observations and research reads. Never a synthetic fallback."""
import json
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Text, Ref, Policy, Evidence, check, digest, at
from .real_access import SourceConfig, source_access
from .revisions import Revision
from .evidence_storage import read_evidence, stored_stream
from .rag_contracts import Bundle
from .rag_research import recheck
from .quant_policies import assess, PolicyRegistry
from .evidence import statement_from_evidence
from .data import Provenance, Candle
from .calendar import Calendar, Session
from .publication_store import now

class ViewConfig(Strict):
    sources: SourceConfig
    listing_ids: Annotated[tuple[Text,...],Field(min_length=1,max_length=100)]
    policy_file: Text | None = None


def eligible_revisions(conn,listing,cutoff,access):
    # Latest version known at this cutoff; no future fetched revisions or fixtures.
    rows=conn.execute("""SELECT DISTINCT ON (source_id,logical_key) payload FROM discovery.revisions
        WHERE (listing_id=%s OR (kind='session' AND listing_id='NSE'))
        AND available_at<=%s AND payload->>'availability_basis'='observed'
        AND (payload->>'fetched_at')::timestamptz<=%s
        ORDER BY source_id,logical_key,sequence DESC""",(listing,cutoff,cutoff)).fetchall()
    result=[]
    for raw, in rows:
        revision=Revision.model_validate(raw)
        access.require(stored_stream(conn,revision.revision_id),('derive',))
        result.append(revision)
    return result


def market_readiness(bars,sessions,cutoff):
    """Describe coverage against D3-05, without approving adjusted execution."""
    known=at(cutoff)
    closed=[s for s in sessions if at(s.data.closes_at)<=known]
    latest=max((s.data.closes_at for s in closed),default=None)
    ends=[b.data.ends_at for b in bars]
    expected=[s.data.closes_at for s in closed if not ends or s.data.closes_at>=min(ends)]
    gaps=sorted(set(expected)-set(ends))
    extra=sorted(set(ends)-{s.data.closes_at for s in closed})
    age=None if not ends else max(0,int((known-at(max(ends))).total_seconds()))
    return dict(required_sessions=30,observed_bars=len(bars),latest_verified_session=latest,
        latest_bar=max(ends) if ends else None,missing_sessions=gaps,unverified_bar_sessions=extra,
        duplicate_bars=len(ends)!=len(set(ends)),warmup_complete=len(ends)>=30,
        latest_session_present=bool(ends and latest and max(ends)==latest),price_age_seconds=age,
        proposed_max_age_seconds=86400,within_proposed_age=age is not None and age<=86400,
        adjustment_basis=sorted({b.data.adjustment_basis for b in bars}),
        execution_qualified=False,volume_basis='unverified',corporate_actions='coverage_unverified',
        historical_pit='unqualified',input_revision_ids=[b.revision_id for b in bars])


def company(conn,config,listing,*,clock=now,publication_inputs=False,cutoff_at=None):
    config=ViewConfig.model_validate(config)
    check(listing in config.listing_ids,'listing_not_configured')
    cutoff=cutoff_at or clock();check(at(cutoff)<=at(clock()),'future_read_cutoff');access=source_access(config.sources,clock)
    records=eligible_revisions(conn,listing,cutoff,access)
    identities=[r for r in records if r.data.kind=='instrument']
    check(len(identities)==1,'real_identity_missing_or_ambiguous')
    identity=identities[0]
    bars=sorted((r for r in records if r.data.kind=='candle'),key=lambda r:r.data.ends_at)
    check(len({r.data.ends_at for r in bars})==len(bars),'ambiguous_price_sources')
    check(len(bars)<=5000,'price_read_limit')
    # Never chart mixed back-adjustment observation batches or legacy raw labels.
    anchors=[r.fetched_at for r in bars if r.source_id=='upstox' and r.data.adjustment_basis=='split_bonus_adjusted']
    latest_anchor=max(anchors) if anchors else None
    bars=[r for r in bars if r.source_id!='upstox' or (r.data.adjustment_basis=='split_bonus_adjusted' and r.fetched_at==latest_anchor)]
    documents=[];facts=[];events=[];evidence_bundles=[]
    for r in records:
        if r.data.kind!='document':continue
        item=read_evidence(conn,r.revision_id,access=access,cutoff=cutoff,mode='live_paper')
        documents.append({k:v for k,v in item['document'].items() if k!='body'});evidence_bundles.append(item)
        facts.extend(item['facts']);events.extend(item['events'])
    history=[]
    # Immutable RAG results are analysis history, never prospective publication.
    rows=conn.execute("""SELECT r.run_id,r.payload,b.payload,r.arm FROM (
          SELECT run_id,payload,bundle_hash,'quant_rag' AS arm FROM discovery.rag_results
          UNION ALL SELECT run_id,payload,coalesce(final_bundle_hash,baseline_hash),'quant_agent' AS arm FROM discovery.agent_results
        ) r JOIN discovery.rag_bundles b USING(bundle_hash)
        WHERE b.payload->'query'->>'listing_id'=%s AND b.payload->'query'->>'mode'='live_paper'
        ORDER BY b.payload->'query'->>'cutoff_at' DESC, r.payload->>'reviewed_at' DESC NULLS LAST, r.run_id DESC LIMIT 30""",(listing,)).fetchall()
    for run_id,result,raw_bundle,arm in rows:
        bundle=Bundle.model_validate_json(json.dumps(raw_bundle))
        if at(bundle.query.cutoff_at)>at(cutoff):continue
        recheck(conn,bundle,access)
        history.append(dict(run_id=run_id,cohort=arm,cutoff_at=bundle.query.cutoff_at,horizon=bundle.query.horizon,
            result=result,citations=[c.model_dump(mode='json') for h in bundle.hits for c in h.citations]
                +[f.citation.model_dump(mode='json') for f in bundle.facts]))
    def provenance(r):
        return Provenance(source_ref=r.source_id,source_version=r.source_revision,
            published_at=at(r.published_at).replace(tzinfo=timezone.utc),available_at=at(r.available_at).replace(tzinfo=timezone.utc),
            fetched_at=at(r.fetched_at).replace(tzinfo=timezone.utc),availability_basis='observed_live')
    candles=tuple(Candle(instrument_id=listing,starts_at=at(r.data.starts_at).replace(tzinfo=timezone.utc),
        ends_at=at(r.data.ends_at).replace(tzinfo=timezone.utc),open=Decimal(r.data.open),high=Decimal(r.data.high),
        low=Decimal(r.data.low),close=Decimal(r.data.close),volume=r.data.volume,provenance=provenance(r)) for r in bars
        if r.data.adjustment_basis == 'raw' and r.source_id != 'upstox')
    # Descriptive indicators may use one current provider-adjusted observation
    # batch. They never become raw execution inputs or historical PIT evidence.
    observed_features={}; feature_reason='no_coherent_adjusted_observation_batch'
    adjusted=[r for r in bars if r.source_id=='upstox' and r.data.adjustment_basis=='split_bonus_adjusted']
    if adjusted and len(adjusted)==len(bars) and len({r.fetched_at for r in adjusted})==1:
        from .indicators import features
        series=tuple(Candle(instrument_id=listing,starts_at=at(r.data.starts_at).replace(tzinfo=timezone.utc),
            ends_at=at(r.data.ends_at).replace(tzinfo=timezone.utc),open=Decimal(r.data.open),high=Decimal(r.data.high),
            low=Decimal(r.data.low),close=Decimal(r.data.close),volume=r.data.volume,provenance=provenance(r),
            adjustment_version='upstox-split-bonus-observed:'+r.fetched_at) for r in adjusted)
        observed_features={k:format(v,'f') if v is not None else None for k,v in features(series).items()}
        observed_features['relative_volume20']=None  # Provider volume adjustment not established.
        feature_reason='descriptive_only_action_coverage_and_volume_basis_unqualified'
    sessions=sorted((r for r in records if r.data.kind=='session'),key=lambda r:r.data.opens_at)
    readiness=market_readiness(bars,sessions,cutoff)
    if any(day<=readiness['latest_bar'] for day in readiness['missing_sessions'] if readiness['latest_bar']) or readiness['unverified_bar_sessions'] or readiness['duplicate_bars']:
        observed_features={k:None for k in observed_features}
        feature_reason='descriptive_indicators_blocked_by_session_coverage'
    calendar=None
    if sessions:
        check(len({r.data.opens_at for r in sessions})==len(sessions),'ambiguous_calendar_sources')
        calendar=Calendar(version=digest([r.revision_id for r in sessions]),
            sessions=tuple(Session(at(r.data.opens_at).replace(tzinfo=timezone.utc),at(r.data.closes_at).replace(tzinfo=timezone.utc)) for r in sessions),
            provenance=provenance(max(sessions,key=lambda r:r.fetched_at)))
    statements=[]
    for item in evidence_bundles:
        if item['document']['category'] not in ('annual_report','quarterly_report'):continue
        periods=sorted({(f['period_start_at'],f['period_end_at'],f['period_kind'],f['scope']) for f in item['facts'] if f['period_kind'] in ('annual','quarter')})
        for start,end,kind,scope in periods:
            statements.append(statement_from_evidence(item,period_start_at=start,period_end_at=end,period_kind=kind,scope=scope))
    registry=PolicyRegistry();policies={}
    if config.policy_file:
        for raw in json.loads(Path(config.policy_file).read_text()):
            p=Policy.model_validate_json(json.dumps(raw))
            if p.kind!='strategy':continue
            registry.register(p)
            check(p.profile not in policies,'ambiguous_strategy_policy');policies[p.profile]=p
    quantitative={};inputs={}
    for horizon in ('swing','short_term','long_term'):
        ref=policies[horizon].ref if horizon in policies else Ref(id='unconfigured-real-'+horizon,version='1',content_hash=digest(['missing',horizon]))
        # Coverage, eligibility and instrument risk remain unknown until separately
        # verified. Complete filing parsing alone cannot attest feed completeness.
        inputs[horizon]=dict(profile=horizon,instrument_id=listing,cutoff=cutoff,mode='live_paper',
            calendar=calendar,bars=candles,statements=tuple(statements),coverage=(),eligible=None,risk_prohibited=None)
        quantitative[horizon]=assess(registry,ref,**inputs[horizon])
    # Final recheck so a mid-read revocation never returns cached content.
    for r in records:access.require(stored_stream(conn,r.revision_id),('derive',))
    for doc in documents:read_evidence(conn,doc['revision']['revision_id'],access=access,cutoff=cutoff,mode='live_paper')
    detail=dict(mode='real_research',listing_id=listing,symbol=identity.data.symbol,isin=identity.data.isin,
        cutoff_at=cutoff,actionable=False,qualified=False,price_series=[dict(time=r.data.ends_at[:10],
            open=r.data.open,high=r.data.high,low=r.data.low,close=r.data.close,volume=r.data.volume,
            revision_id=r.revision_id,fetched_at=r.fetched_at,adjustment_basis=r.data.adjustment_basis,
            adjustment_observed_at=r.fetched_at,volume_adjustment='unverified' if r.source_id=='upstox' else 'raw') for r in bars],documents=documents,financial_facts=facts,
        events=events,quantitative=quantitative,market_readiness=readiness,
        policy_states={h:dict(ref=p.ref.model_dump(),status=p.status,approval_ref=p.approval_ref) for h,p in policies.items()},
        assessment_state='RESEARCH_ONLY_ASSESSMENT',paper_position_status='not_created',price_features=dict(metrics=observed_features,reason=feature_reason,actionable=False),analysis_history=history,recommendations=[],
        publication_status='not_published',prospective_status='not_configured',
        publication_blockers=['real_policies_required','financial_publication_timestamps_unknown',
            'cash_flow_reconciliation_unresolved','balance_sheet_and_valuation_fields_unverified',
            'official_event_coverage_missing','price_action_and_volume_basis_unqualified',
            'eligibility_and_instrument_risk_unknown','semantic_financial_research_unqualified'],
        limitations=['Analysis history is not a published prediction.','Source and corporate-action coverage is not qualified.',
            'Provider-adjusted and legacy Upstox prices are display-only until action/basis coverage is verified; raw-price quantitative inputs exclude them.',
            'Original financial publication timestamps are unknown; observation clocks are not filing dates.',
            'Cash-flow lines do not reconcile to observed cash-balance movements; no balancing item is inferred.',
            'Debt, equity, EPS units, capex, diluted shares and valuation inputs are missing or unverified.',
            'Company name is unavailable in the current stored identity contract.','Paper position admission remains blocked.'])

    if publication_inputs:
        return detail,inputs,records
    from .publication_store import read_artifact
    from .shadow_tracking import history as tracking_history
    published=[]
    for rid, in conn.execute("SELECT recommendation_id FROM discovery.recommendations WHERE listing_id=%s AND payload->>'mode'='live_paper' ORDER BY payload->>'decision_available_at' DESC LIMIT 30",(listing,)):
        artifact=read_artifact(conn,rid,access)
        published.append(dict(recommendation=artifact['recommendation'],quantitative=artifact['quantitative'],
            research=artifact['research'],citations=artifact['citations'],tracking=tracking_history(conn,rid,access)))
    detail['recommendations']=published
    if published:
        detail['publication_status']='published_shadow'
        detail['prospective_status']='configured_shadow'
    return detail
