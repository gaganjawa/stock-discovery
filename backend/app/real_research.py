"""Authenticated REAL-001 readiness. Never falls back to synthetic records."""
from fastapi import APIRouter,Depends
from .auth import require_auth

router=APIRouter(prefix='/v1/real-research',dependencies=[Depends(require_auth)])


@router.get('/status')
def status():
    # These are implementation gates, not inferred from the presence of a token
    # or a model. Only a demonstrated complete pipeline may clear them.
    return dict(mode='real_research',status='blocked',actionable=False,qualified=False,
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
        scheduler=dict(status='partial',prices='D3-04 handler available with explicit real configuration',
                       research='blocked',events='blocked',outcomes='blocked'),
        forward_paper=dict(status='blocked',reason='Existing D3-10 admission gates remain in force; research cannot create a position.'),
        limitations=['No prices or financial values are substituted from synthetic data.',
                     'No performance results exist for this feature.'])


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
def company_detail(listing:str,conn=Depends(db)):
    from fastapi import HTTPException
    from stock_discovery_analysis.real_views import company
    config=view_config()
    if listing not in config.listing_ids:raise HTTPException(404,'Company is not configured')
    try:return company(conn,config,listing)
    except PermissionError:raise HTTPException(403,'Source permission denied') from None
    except (ValueError,OSError,KeyError):raise HTTPException(503,'Real company inputs are unavailable or ambiguous') from None
