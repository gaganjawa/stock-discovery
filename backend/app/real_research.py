"""Authenticated REAL-001 readiness. Never falls back to synthetic records."""
from fastapi import APIRouter,Depends,Response
from typing import Literal
from stock_discovery_contracts.v2 import Timestamp
from .auth import require_auth

router=APIRouter(prefix='/v1/real-research',dependencies=[Depends(require_auth)])
REQUIRED_SCHEMA='0015'
MIGRATION_REQUIRED='Database migration required: the retained schema is older than this application, so permitted reads fail closed. No data was read or changed.'


def schema_state():
    """STK-074/079: distinguish an unmigrated database from a source permission denial."""
    try:
        import psycopg
        from stock_discovery_analysis.runtime import setting
        with psycopg.connect(setting('DATABASE_URL'),connect_timeout=5) as conn:
            version=conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    except Exception:
        return dict(state='unavailable')
    return dict(state='current' if version==REQUIRED_SCHEMA else 'migration_required')


def denied():
    from fastapi import HTTPException
    if schema_state()['state']=='migration_required':
        return HTTPException(503,MIGRATION_REQUIRED)
    return HTTPException(403,'Source permission denied')


@router.get('/status')
def status():
    # These are implementation gates, not inferred from the presence of a token
    # or a model. Only a demonstrated complete pipeline may clear them.
    result=dict(mode='real_research',status='blocked',actionable=False,qualified=False,
        default_mode='synthetic',recommendations=[],price_series=[],analysis_history=[],
        providers=[dict(id='upstox',adapter='implemented_unactivated',coverage='NSE EQ instruments and daily candles',
            blockers=['credential_and_use_specific_grant_required','observed_calendar_required']),
            dict(id='issuer_filings',adapter='pdf_html_extractor_unactivated',coverage='No activated financial filing source',
                 blockers=['approved_source_and_extraction_qualification_required']),
            dict(id='company_events',adapter='unavailable',coverage='No activated official announcements or independent news',
                 blockers=['approved_event_feed_required'])],
        models=dict(adapter='ollama',status='qualification_pending',note='Local inference smoke is recorded in the acceptance report. It is not financial qualification.'),
        blockers=['Real provider activation and end-to-end company acceptance are pending.',
                  'Real publication and shadow observation handlers require permitted inputs and explicit policies.',
                  'Real filing and event coverage requires source-specific acceptance.'],
        publication_blockers=['real_policies_required','financial_publication_timestamps_unknown',
            'cash_flow_reconciliation_unresolved','balance_sheet_and_valuation_fields_unverified',
            'official_event_coverage_missing','price_action_and_volume_basis_unqualified',
            'eligibility_and_instrument_risk_unknown','semantic_financial_research_unqualified'],
        scheduler=dict(status='partial',prices='D3-04 handler available with explicit real configuration',
                       research='blocked',events='blocked',outcomes='blocked'),
        forward_paper=dict(status='blocked',reason='Existing D3-10 admission gates remain in force; research cannot create a position.'),
        limitations=['No prices or financial values are substituted from synthetic data.',
                     'No performance results exist for this feature.'],
        database=schema_state(),
        readiness=dict(level='none',today=['Browse the synthetic workflows; no permitted real company inputs are readable yet.'],
            next=['Level 1: permitted adjusted prices, charts and descriptive indicators for configured companies.',
                  'Level 2: qualified original prices, filings, approved policies and independent AI review.',
                  'Level 3: measured forward paper outcomes for each horizon.']))

    import os
    if os.getenv('REAL_RESEARCH_VIEW_CONFIG'):
        # Configuration alone is not activation: inspect currently permitted rows.
        try:
            import psycopg
            from stock_discovery_analysis.runtime import setting
            from stock_discovery_analysis.real_views import company
            config=view_config()
            with psycopg.connect(setting('DATABASE_URL'),connect_timeout=5) as conn:
                detail=company(conn,config,config.listing_ids[0])
            if detail['price_series'] or detail['financial_facts']:
                result['publication_blockers']=detail['publication_blockers']
                result['status']='partial'
                result['providers'][0].update(adapter='observations_available',
                    coverage='Permitted observed prices and structured numerical financial APIs',
                    blockers=['corporate_action_and_volume_basis_unqualified'])
                result['blockers'][0]='Observed company inputs are available; full research acceptance remains incomplete.'
                result['models']['note']='Actual local research attempts and validation outcomes appear in company history. Model financial qualification remains pending.'
            if detail['adjusted_research']['status']=='AVAILABLE_DESCRIPTIVE_ONLY':
                result['readiness'].update(level='level_1_descriptive',today=[
                    'Inspect permitted split/bonus-adjusted daily charts and descriptive indicators (SMA, EMA, ATR, breakout, support).',
                    'Review stored financial facts, citations and local research history for configured companies.',
                    'All three horizons remain research-only: no BUY decision, execution-grade P&L, backtest or paper position.'])
        except Exception:
            # Never leak a private configuration path, provider data or secret.
            result['blockers'][0]='Configured company inputs cannot currently be read with verified permissions.'
    if result['database']['state']=='migration_required':
        result['blockers'].insert(0,MIGRATION_REQUIRED)
    return result


def view_config():
    import os
    from pathlib import Path
    from fastapi import HTTPException
    from stock_discovery_analysis.real_views import ViewConfig
    path=os.getenv('REAL_RESEARCH_VIEW_CONFIG')
    if not path:raise HTTPException(503,'Real data sources are not configured')
    try:return ViewConfig.model_validate_json(Path(path).read_text())
    except (OSError,ValueError):raise HTTPException(503,'Real source configuration is unavailable') from None


@router.get('/companies')
def companies():
    config=view_config()
    return dict(listing_ids=config.listing_ids,qualified=False,actionable=False)


from .research import db
@router.get('/companies/{listing}')
def company_detail(listing:str,response:Response,conn=Depends(db),analysis:Literal['company','swing','combined']='company',cutoff_at:Timestamp|None=None):
    from fastapi import HTTPException
    from stock_discovery_analysis.real_views import company
    config=view_config()
    if listing not in config.listing_ids:raise HTTPException(404,'Company is not configured')
    try:
        if analysis=='combined':
            from stock_discovery_analysis.combined_research import research
            response.headers['Cache-Control']='no-store'
            return research(conn,config,listing,cutoff_at=cutoff_at)
        if analysis=='swing':
            from stock_discovery_analysis.swing_research import research
            response.headers['Cache-Control']='no-store'
            return research(conn,config,listing,cutoff_at=cutoff_at)
        return company(conn,config,listing)
    except PermissionError:raise denied() from None
    except (ValueError,OSError,KeyError):raise HTTPException(503,'Real company inputs are unavailable or ambiguous') from None


def coverage_row(conn,config,listing):
    from stock_discovery_analysis.real_views import company
    try:detail=company(conn,config,listing)
    except PermissionError:return dict(listing_id=listing,state='denied',reasons=['source_permission_denied'])
    except (ValueError,OSError,KeyError) as error:
        code=str(error) if str(error).replace('_','').isalnum() else 'inputs_unavailable'
        return dict(listing_id=listing,state='unavailable',reasons=[code])
    research=detail['adjusted_research'];series=detail['price_series']
    available=research['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
    return dict(listing_id=listing,symbol=detail['symbol'],state='available' if available else 'unavailable',
        reasons=list(research['unavailable_reasons']),sessions=len(series),last_session=series[-1]['time'] if series else None,
        indicators=sorted(k for k,v in (research['metrics'] or {}).items() if v is not None))


@router.get('/coverage')
def pilot_coverage(response:Response,conn=Depends(db)):
    """STK-079: per-company Level 1 readiness for the configured pilot; descriptive only."""
    from fastapi import HTTPException
    config=view_config()
    if schema_state()['state']=='migration_required':raise HTTPException(503,MIGRATION_REQUIRED)
    response.headers['Cache-Control']='no-store'
    rows=[coverage_row(conn,config,listing) for listing in config.listing_ids]
    return dict(rows=rows,available=sum(r['state']=='available' for r in rows),total=len(rows),
                actionable=False,qualified=False,execution_qualified=False)


@router.get('/scan')
def latest_scan(conn=Depends(db)):
    from fastapi import HTTPException
    from stock_discovery_analysis.real_scan_view import scan_view
    try:return scan_view(conn,view_config())
    except PermissionError:raise denied() from None
    except (ValueError,OSError,KeyError):raise HTTPException(503,'Real scan inputs are unavailable') from None
