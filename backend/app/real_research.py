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
    return dict(state='current' if version in (REQUIRED_SCHEMA,'0016') else 'migration_required')


def safe_code(error):
    """STK-079: only internal snake_case reason codes leave the server; anything else is generic."""
    import re
    text=str(error)
    return text if re.fullmatch(r'[a-z][a-z0-9_]{2,80}',text) else 'inputs_unavailable'


def denied(error=None):
    from fastapi import HTTPException
    if schema_state()['state']=='migration_required':
        return HTTPException(503,MIGRATION_REQUIRED)
    # The fenced-read contract keeps denials generic; reasons stay in the private audit.
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
    if result['database']['state']=='unavailable':
        result['blockers'].insert(0,'Database is not reachable: check that DATABASE_URL_FILE points to an existing file and the database container is running.')
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


def candidate_config(conn,config,listing):
    if listing in config.listing_ids:return config
    if conn is not None and conn.execute("SELECT 1 FROM discovery.candidates WHERE listing_id=%s LIMIT 1",(listing,)).fetchone():
        return config.model_copy(update={'listing_ids':(listing,)})
    from fastapi import HTTPException
    raise HTTPException(404,'Company is not configured or resolved from candidates')


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
    response.headers['Cache-Control']='no-store'
    config=candidate_config(conn,config,listing)
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
    except PermissionError as error:raise denied(error) from None
    except (ValueError,OSError,KeyError) as error:
        raise HTTPException(503,'Real company inputs are unavailable: '+safe_code(error)) from None


def coverage_row(conn,config,listing):
    from stock_discovery_analysis.real_views import company
    try:detail=company(conn,config,listing)
    except PermissionError:return dict(listing_id=listing,state='denied',reasons=['source_permission_denied'])
    except (ValueError,OSError,KeyError) as error:
        return dict(listing_id=listing,state='unavailable',reasons=[safe_code(error)])
    except Exception as error:
        # One unreadable company must not hide the others; only the class name is reported.
        return dict(listing_id=listing,state='unavailable',reasons=['unexpected_'+type(error).__name__.lower()[:40]])
    research=detail['adjusted_research'];series=detail['price_series'];readiness=detail.get('market_readiness') or {}
    available=research['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
    return dict(listing_id=listing,symbol=detail['symbol'],state='available' if available else 'unavailable',
        reasons=list(research['unavailable_reasons']),sessions=len(series),last_session=series[-1]['time'] if series else None,
        indicators=sorted(k for k,v in (research['metrics'] or {}).items() if v is not None),
        descriptive_freshness=readiness.get('descriptive_freshness'),
        refresh=dict(current=bool(readiness.get('latest_session_present')),latest_session=readiness.get('latest_verified_session'),
            latest_bar=readiness.get('latest_bar'),missing_sessions=len(readiness.get('missing_sessions') or ())))


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


@router.get('/rules')
def owner_rules(response:Response):
    """STK-079: versioned starting rules and their gates; nothing here activates a rule."""
    import os
    from pathlib import Path
    from stock_discovery_analysis.owner_rules import Decisions, evaluate, load_ruleset, private_gates
    decisions_file=os.environ.get('REAL_RESEARCH_RULE_DECISIONS')
    decisions=Decisions.model_validate_json(Path(decisions_file).read_text()) if decisions_file else None
    gates=private_gates(os.environ.get('REAL_RESEARCH_RULE_GATES'))
    gates['database_current']=schema_state()['state']=='current'
    response.headers['Cache-Control']='no-store'
    return evaluate(load_ruleset(),decisions,gates)


@router.get('/scan')
def latest_scan(conn=Depends(db)):
    from fastapi import HTTPException
    from stock_discovery_analysis.real_scan_view import scan_view
    try:return scan_view(conn,view_config())
    except PermissionError as error:raise denied(error) from None
    except (ValueError,OSError,KeyError) as error:raise HTTPException(503,'Real scan inputs are unavailable: '+safe_code(error)) from None


@router.get('/companies/{listing}/insight')
def daily_insight(listing:str,response:Response,conn=Depends(db)):
    from fastapi import HTTPException
    from stock_discovery_analysis.daily_insight import research,LISTING
    config=view_config()
    if listing!=LISTING or listing not in config.listing_ids:raise HTTPException(404,'INFY research is not configured')
    response.headers['Cache-Control']='no-store'
    try:return research(conn,config,listing)
    except PermissionError as error:raise denied(error) from None
    except (ValueError,OSError,KeyError):raise HTTPException(503,'Analysis unavailable: verified inputs are incomplete') from None


from .watchlist import Entry

@router.get('/watchlist')
def get_watchlist(response:Response):
    from .watchlist import store
    response.headers['Cache-Control']='no-store'
    return store()

@router.put('/watchlist/{listing}')
def save_watchlist(listing:str, entry:Entry, response:Response,conn=Depends(db)):
    from fastapi import HTTPException
    from .watchlist import store
    if listing.startswith('CHARTINK:'):
        parts=listing.split(':')
        if len(parts)!=3 or conn is None or not conn.execute('SELECT 1 FROM discovery.candidates WHERE scanner_key=%s AND symbol=%s LIMIT 1',tuple(parts[1:])).fetchone():
            raise HTTPException(404,'Candidate is not known')
    else:candidate_config(conn,view_config(),listing)
    response.headers['Cache-Control']='no-store'
    return store(listing,entry)

@router.delete('/watchlist/{listing}')
def remove_watchlist(listing:str,response:Response):
    from .watchlist import store
    response.headers['Cache-Control']='no-store'
    return store(listing,remove=True)

@router.get('/workbench')
def workbench(response:Response,conn=Depends(db)):
    from stock_discovery_analysis.real_views import company
    from stock_discovery_analysis.real_scan_view import scan_view
    from fastapi import HTTPException
    try:config=view_config()
    except HTTPException:config=None
    response.headers['Cache-Control']='no-store'
    try:scan=scan_view(conn,config).get('scan') or {}
    except Exception:scan={}
    saved={r['listing_id']:r for r in scan.get('rows',[])}
    rows=[]
    from .watchlist import store
    listings=list(config.listing_ids) if config else []
    if conn is not None:
        for listing in list(store()['entries'])[:500]:
            if listing.startswith('CHARTINK:'):
                parts=listing.split(':')
                if len(parts)==3 and conn.execute('SELECT 1 FROM discovery.candidates WHERE scanner_key=%s AND symbol=%s LIMIT 1',tuple(parts[1:])).fetchone():
                    rows.append(dict(listing_id=listing,symbol=parts[2],name='Chartink candidate; company identity unverified',state='unresolved',reasons=['nse_identity_missing_or_ambiguous'],screening={},unresolved_candidate=True))
                continue
            if config and listing not in listings and conn.execute('SELECT 1 FROM discovery.candidates WHERE listing_id=%s LIMIT 1',(listing,)).fetchone():
                listings.append(listing)
    for listing in listings:
        scoped=config if listing in config.listing_ids else config.model_copy(update={'listing_ids':(listing,)})
        prior=saved.get(listing,{})
        row=dict(listing_id=listing,symbol=prior.get('symbol',listing),name=prior.get('name','Name unavailable'),state='unavailable',reasons=[],screening=prior.get('screening',{}),assessment_at=scan.get('completed_at'))
        try:
            detail=company(conn,scoped,listing)
            research=detail['adjusted_research']
            row.update(symbol=detail['symbol'],state='readable' if detail['price_series'] else 'unavailable',detail=detail,reasons=research['unavailable_reasons'])
        except PermissionError:
            row.update(state='denied',reasons=['source_permission_denied'],screening={})
        except Exception as error:row['reasons']=[safe_code(error)]
        rows.append(row)
    return dict(rows=rows,actionable=False,qualified=False)


@router.post('/watchlist/{listing}/review')
def review_watchlist(listing:str,response:Response,conn=Depends(db)):
    from stock_discovery_analysis.real_views import company
    from .watchlist import store
    from fastapi import HTTPException
    config=view_config()
    response.headers['Cache-Control']='no-store'
    config=candidate_config(conn,config,listing)
    try:detail=company(conn,config,listing)
    except PermissionError as error:raise denied(error) from None
    except Exception:raise HTTPException(503,'Verified observations unavailable') from None
    observed=max((b['fetched_at'] for b in detail['price_series']),default=None)
    if not observed:raise HTTPException(409,'No readable price observation to mark reviewed')
    response.headers['Cache-Control']='no-store'
    return store(listing,reviewed_observation=observed)
