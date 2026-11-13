"""Stored-only candidate adapter over D3-03 identity and STK-093 research.

Current descriptive analysis has its own clock; a historical match does not
turn current observations into point-in-time evidence or a frozen prediction.
"""
import re
from datetime import datetime
from .real_views import company, ViewConfig
from .real_access import source_access
from .read_fences import guarded_read
from .evidence_storage import stored_stream
from .revisions import Revision
from .publication_store import now


def resolve(conn, config, symbol, session, *, clock=now):
    access=source_access(config.sources,clock)
    with guarded_read(conn,access) as guard:
        records=conn.execute('''SELECT payload FROM (
          SELECT DISTINCT ON(source_id,listing_id) payload FROM discovery.revisions
          WHERE kind='instrument' AND available_at<=%s AND (payload->>'fetched_at')::timestamptz<=%s
          ORDER BY source_id,listing_id,sequence DESC) latest
          WHERE payload->'data'->>'symbol'=%s LIMIT 3''',(clock(),clock(),symbol)).fetchall()
        eligible=[]
        for raw, in records:
            r=Revision.model_validate(raw)
            if (r.availability_basis!='observed' or not r.listing_id.startswith('NSE:')
                or r.data.series!='EQ' or r.data.status!='active'
                or not re.fullmatch(r'IN[A-Z0-9]{10}',r.data.isin or '')
                or r.data.effective_at[:10]>str(session)):
                continue
            access.require(stored_stream(conn,r.revision_id),('derive',))
            guard.add(r.revision_id)
            eligible.append(r)
    if len(eligible)!=1: raise ValueError('nse_identity_missing_or_ambiguous')
    return eligible[0]


def analyze(conn, config, symbol, session, *, clock=now):
    base=dict(status='blocked',listing_id=None,identity_status='unverified',company_name='Name unavailable in stored identity',
        reasons=[],source_revision_ids=[],analyzed_at=clock(),analysis_version='existing-adjusted-research-v1',
        research_priority='not_rankable',actionable=False,evaluation_eligible=False,
        acquisition=dict(permitted=False,reason='no_approved_live_request_budget',provider_requests=0,model_requests=0))
    if config is None:
        return {**base,'reasons':['real_source_configuration_required']}
    try:
        identity=resolve(conn,config,symbol,session,clock=clock)
        base.update(listing_id=identity.listing_id,identity_status='verified_stored_nse_eq',
                    source_revision_ids=[identity.revision_id])
        # Candidate admission expands ONLY the identity list, never source rights.
        scoped=config.model_copy(update={'listing_ids':(identity.listing_id,)})
        receipt=conn.execute("""SELECT result->>'price_stream_id' FROM discovery.schedule_jobs
            WHERE payload->>'code_version'='candidate-price-refresh-v1' AND payload->>'symbol'=%s
            AND status='completed' AND updated_at<=%s AND result->>'price_stream_id' IS NOT NULL
            ORDER BY updated_at DESC,job_id LIMIT 1""",(symbol,clock())).fetchone()
        detail=company(conn,scoped,identity.listing_id,clock=clock,
                       price_stream_id=receipt[0] if receipt else None)
        adjusted=detail['adjusted_research']
        ids=set(base['source_revision_ids'])|set(detail['market_readiness']['input_revision_ids'])
        base.update(source_revision_ids=sorted(ids),market_data=dict(bars=len(detail['price_series']),
            latest_close=detail['price_series'][-1]['close'] if detail['price_series'] else None,
            latest_session=detail['market_readiness']['latest_bar'],warmup_complete=detail['market_readiness']['warmup_complete'],
            freshness=adjusted['freshness']),technical=adjusted,
            reasons=adjusted['unavailable_reasons'],qualification_limitations=detail['publication_blockers'],
            financial_fact_count=len(detail['financial_facts']),permitted_event_count=len(detail['events']),
            grounded_research_count=len(detail['analysis_history']))
        if adjusted['status']=='AVAILABLE_DESCRIPTIVE_ONLY':
            base.update(status='completed',research_priority='descriptive_evidence_available_not_a_signal')
        return base
    except PermissionError:
        return {**base,'listing_id':None,'identity_status':'unverified','source_revision_ids':[],
                'reasons':['source_permission_denied']}
    except ValueError as exc:
        code=str(exc)
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,80}',code):code='verified_inputs_unavailable'
        return {**base,'reasons':[code]}


def permitted_result(conn, config, result, *, clock=now):
    """Cached results retain original grant fences; revoked data is never served."""
    if not result:return None
    if not result.get('source_revision_ids'):return result
    if config is None:return dict(status='blocked',reasons=['real_source_configuration_required'])
    access=source_access(config.sources,clock)
    try:
        with guarded_read(conn,access) as guard:
            guard.collect(result)
        return result
    except (PermissionError,ValueError,OSError):
        return dict(status='blocked',identity_status='unverified',reasons=['source_permission_denied'],actionable=False)
