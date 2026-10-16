"""D3-05 arbitrary engineering fixtures; no approved investment settings."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from stock_discovery_contracts.v2 import Evidence, Parameter, Policy, Ref, digest
from .calendar import Calendar, Session
from .dataset import demo_dataset
from .quant_policies import CoverageCheck, PolicyRegistry, Statement, SUPPORTED


def fixture_policy(profile, **overrides):
    # These values exercise branches only. They are not investment recommendations.
    settings=dict(report_months='12',duration='3' if profile=='swing' else '1',entry_sessions='2',max_price_age_days='5',
        max_evidence_age_days='30',forecast_sessions='5',max_statement_age_days='500',
        min_revenue_growth='0.01',min_earnings_growth='0.01',min_price_to_sma='0.5',
        bear_pe='50',base_pe='60',bull_pe='70',min_margin_of_safety='0.1',min_ocf_margin='0.01',
        min_roe='0.01',max_net_debt_to_ocf='10',durability_years='2',min_fcf_yield='0.001')
    settings.update(overrides)
    parameters=[Parameter(name=k,value=settings[k],unit=u,unavailable_reason=None) for k,u in sorted(SUPPORTED[profile].items())]
    return Policy(schema_version='2.0.0',ref=Ref(id='SYN-'+profile,version='fixture-1',content_hash=digest([p.model_dump() for p in parameters])),
        kind='strategy',profile=profile,status='fixture',effective_at='2020-01-01T00:00:00Z',parameters=parameters,approval_ref=None)


def fixture_inputs(profile):
    dataset=demo_dataset()
    cutoff=dataset.calendar.sessions[39].closes_at+timedelta(minutes=1)
    stamp=lambda t:t.strftime('%Y-%m-%dT%H:%M:%SZ')
    # Extend only the fictional calendar so multi-year endpoints are resolvable.
    sessions=list(dataset.calendar.sessions)
    day=sessions[-1].opens_at
    through=cutoff.replace(year=cutoff.year+6)
    while day < through:
        day+=timedelta(days=1)
        if day.weekday()<5:
            sessions.append(Session(day,day+timedelta(hours=6,minutes=15)))
    calendar=replace(dataset.calendar,sessions=tuple(sessions))
    def evidence(rid,kind,published,period=None):
        return Evidence(evidence_id=rid,revision_id=rid,instrument_id='SYN-ALPHA',kind=kind,
            source_ref='SYN-primary',source_version='1',locator='fixture:'+rid,published_at=published,available_at=published,
            fetched_at=published,period_end_at=period,availability_basis='fictional_fixture',archive_verification_ref=None,summary='Fictional engineering evidence')
    statements=[]
    for offset in (3,2,1):
        year=cutoff.year-offset
        end=f'{year}-12-31T00:00:00Z'
        published=f'{year+1}-01-01T00:00:00Z'
        scale=4-offset
        statements.append(Statement(revision_id='SYN-annual-'+str(year),instrument_id='SYN-ALPHA',
            period_start_at=f'{year}-01-01T00:00:00Z',period_end_at=end,period_kind='annual',scope='consolidated',currency='INR',monetary_unit='INR',
            evidence=evidence('SYN-annual-'+str(year),'filing',published,end),revenue=str(1000*scale),earnings=str(100*scale),
            operating_cash_flow=str(150*scale),capital_expenditure='20',debt='100',cash='20',equity='1000',diluted_shares='100'))
    coverage=tuple(CoverageCheck(requirement=r,evidence=evidence('SYN-'+r,'fact',stamp(cutoff)),complete=True,adverse=False)
                   for r in ('actions','material_events','filings','governance','business'))
    return dict(profile=profile,instrument_id='SYN-ALPHA',cutoff=stamp(cutoff),mode='synthetic',calendar=calendar,
                bars=dataset.candles,statements=tuple(statements),coverage=coverage,sector='non_financial',eligible=True,risk_prohibited=False)


def fixture_assessment(profile, **settings):
    from .quant_policies import assess
    policy=fixture_policy(profile,**settings)
    registry=PolicyRegistry()
    registry.register(policy)
    return assess(registry,policy.ref,**fixture_inputs(profile))
