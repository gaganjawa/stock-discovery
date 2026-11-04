"""STK-083: deterministic, guarded projection of existing research. No acquisition/inference."""
from decimal import Decimal, localcontext, Context
from stock_discovery_contracts.v2 import at, check, digest
from .publication_store import now
from .real_views import ViewConfig, _company
from .real_access import source_access
from .read_fences import guarded_read
from .combined_research import research as combined

VERSION='infy-daily-insight-1'
LISTING='NSE:INE009A01021'
ACQUISITION=dict(status='disabled',last_attempt_at=None,provider_requests=0,
    reason='recurring_acquisition_owner_activation_not_established')


def interpret(close, metrics):
    """Describe exact existing indicator values; no return forecasts or signal approval."""
    with localcontext(Context(prec=28)):
        price=Decimal(close);m={k:Decimal(v) for k,v in metrics.items() if v is not None}
        check(price>0 and price.is_finite() and all(v.is_finite() for v in m.values()),'invalid_indicator')
        bullish=[];bearish=[];neutral=[]
        for key in ('sma20','ema10','ema30'):
            (bullish if price>m[key] else bearish if price<m[key] else neutral).append(
                dict(code='price_'+('above' if price>m[key] else 'below' if price<m[key] else 'at')+'_'+key,
                     text=f'Close {price:.2f} is '+('above' if price>m[key] else 'below' if price<m[key] else 'at')+f' {key.upper()} {m[key]:.2f}.'))
        (bullish if m['ema10']>m['ema30'] else bearish if m['ema10']<m['ema30'] else neutral).append(
            dict(code='ema_alignment',text=f"EMA10 {m['ema10']:.2f} is "+('above' if m['ema10']>m['ema30'] else 'below' if m['ema10']<m['ema30'] else 'equal to')+f" EMA30 {m['ema30']:.2f}."))
        neutral.extend([
            dict(code='volatility',text=f"ATR14 is {m['atr14']:.2f} ({m['atr14']/price*100:.2f}% of the latest close); it measures recent range, not predicted return."),
            dict(code='support_distance',text=f"Close is {(price-m['support20'])/price*100:.2f}% of close above the 20-session support {m['support20']}."),
            dict(code='breakout_condition',text=f"A close above the existing 20-session high {m['breakout20']} would exceed that descriptive level. Current close {price}; distance {(m['breakout20']-price)/price*100:.2f}% of close. No trading signal is authorized.")])
        return dict(bullish=bullish,bearish=bearish,neutral=neutral)


def compose(detail, financial, *, evaluated_at):
    adjusted=detail['adjusted_research'];available=adjusted['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
    bars=detail['price_series'];latest=bars[-1] if available and bars else None
    observations=interpret(latest['close'],adjusted['metrics']) if latest else dict(bullish=[],bearish=[],neutral=[])
    facts=[]
    for fact in detail['financial_facts']:
        # Retain the existing validated fact and locator, never synthesize ratios.
        facts.append(dict(fact,source_url=next((d['revision']['data']['url'] for d in detail['documents'] if d['revision']['revision_id']==fact.get('document_revision_id')),None),age_days=max(0,(at(evaluated_at)-at(fact['period_end_at'])).days),
            age_basis='reporting_period_end_not_publication'))
    ai=financial.get('financial')
    report=dict(version=VERSION,listing_id=detail['listing_id'],symbol=detail['symbol'],evaluated_at=evaluated_at,
        state=('current_descriptive' if adjusted['freshness']['status']=='current' else 'delayed_descriptive') if available else 'unavailable_data',
        market=dict(latest_candle=latest,chart_points=len(bars),freshness=adjusted['freshness'],coverage=adjusted['session_coverage'],
            batch=adjusted['batch'],source='upstox',price_basis=adjusted['price_basis'],limitations=adjusted['limitations']),
        technical=dict(status=adjusted['status'],metrics=adjusted['metrics'],interpretation=observations,
            input_revision_ids=[o['revision_id'] for o in adjusted['observations']]),
        fundamentals=dict(status='reported_facts_available' if facts else 'unavailable',facts=facts,
            sources=detail['documents'],missing=detail['publication_blockers'],conflict_validation='verified_stored_report' if ai else 'unavailable',
            conflicts=(ai or {}).get('conflicts',[]),limitations=['Reporting period age is not disclosure age.','Secondary reported facts do not qualify valuation or investment conclusions.']),
        ai=dict(status='STORED_VERIFIED_FACTUAL_RESEARCH' if ai else 'AI_RESEARCH_UNAVAILABLE',
            reason='stored_claims_revalidated_no_new_inference' if ai else ','.join(financial.get('gaps',[])) or 'qualified_stored_factual_evidence_missing',
            research=ai,new_model_calls=0,quality_acceptance='BLOCKED'),
        conclusion=dict(bullish_observations=observations['bullish'],bearish_observations=observations['bearish'],
            uncertainties=sorted(set(adjusted['limitations'])|set(adjusted['unavailable_reasons'])|set(financial.get('gaps',[]))),
            missing_qualification=detail['publication_blockers'],summary='Descriptive evidence for investigation only; return prediction and investment suitability are unqualified.'),
        news=dict(status='UNAVAILABLE',reason='permitted_complete_news_event_coverage_missing',coverage='unverified'),
        hypothetical_levels=dict(status='unavailable',reason='qualified_raw_price_strategy_and_approved_policy_required',entry=None,stop=None,target=None),
        acquisition=dict(ACQUISITION),research_only=True,actionable=False,publication_authorized=False,
        paper_admission_authorized=False,trading_authorized=False)
    report['evidence_hash']=digest([detail['market_readiness']['input_revision_ids'],detail['financial_facts'],ai,adjusted['freshness'],adjusted['unavailable_reasons']])
    report['report_id']=digest(report)
    return report


def run_status(conn, config):
    """Metadata only; stored report bodies never bypass a fresh guarded read."""
    rows=conn.execute("""SELECT job_id,status,error_code,updated_at,result,payload->>'catch_up'
        FROM discovery.schedule_jobs WHERE payload->>'scope_id'=%s AND stage='ingest'
        AND payload->>'input_hash'=%s ORDER BY updated_at DESC,job_id DESC LIMIT 20""",
        (config.pilot_scope_id,digest(config.model_dump(mode='json')))).fetchall() if config.pilot_scope_id else []
    latest=rows[0] if rows else None
    successful=conn.execute("""SELECT result FROM discovery.schedule_jobs
        WHERE payload->>'scope_id'=%s AND payload->>'input_hash'=%s AND stage='ingest'
        AND status='completed' AND result->>'version'=%s
        AND result->>'report_state' IN ('current_descriptive','delayed_descriptive')
        ORDER BY updated_at DESC,job_id DESC LIMIT 1""",
        (config.pilot_scope_id,digest(config.model_dump(mode='json')),VERSION)).fetchone() if config.pilot_scope_id else None
    return dict(automation='configured_not_proof_of_running' if rows else 'not_activated',
        latest_run=None if latest is None else dict(job_id=latest[0],status=latest[1],error=latest[2],at=str(latest[3]),catch_up=latest[5]=='true'),
        latest_successful_analysis_at=(successful[0] or {}).get('evaluated_at') if successful else None,
        previous_evidence_hash=(successful[0] or {}).get('evidence_hash') if successful else None,
        acquisition=dict(ACQUISITION))


def research(conn, config, listing, *, clock=now):
    config=ViewConfig.model_validate(config);check(listing==LISTING and listing in config.listing_ids,'infy_insight_only')
    cutoff=clock()
    financial=combined(conn,config,listing,clock=lambda:cutoff)
    access=source_access(config.sources,clock)
    with guarded_read(conn,access) as guard:
        detail=_company(conn,config,listing,clock=clock,publication_inputs=False,cutoff_at=None,access=access)
        report=compose(detail,financial,evaluated_at=detail['cutoff_at'])
        status=run_status(conn,config)
        report['automation']=status
        previous=status['previous_evidence_hash']
        report['changes_since_scheduled_run']='no_previous_successful_run' if previous is None else 'evidence_unchanged' if previous==report['evidence_hash'] else 'evidence_or_freshness_changed'
        guard.collect(report)
    return report
