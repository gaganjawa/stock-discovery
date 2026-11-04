"""STK-082 invented records; no provider requests or historical fixture edits."""
from datetime import timedelta,timezone
import pytest
from test_adjusted_research import fixture,Conn,NOW
from stock_discovery_analysis.adjusted_research import describe,AdjustedResearch
from stock_discovery_analysis.real_views import market_readiness
from stock_discovery_analysis.revisions import Revision,SessionData
from stock_discovery_analysis.revision_storage import Page
from stock_discovery_analysis.data import Provenance
from stock_discovery_contracts.v2 import at,digest


def delayed(*,lag=1,policy='one_trailing_session_v1',fault=None,historical=False):
    bars,_,stream,_=fixture()
    # 43 valid sessions ensure an interior hole is rejected independently of warmup.
    earlier=[]
    for i in range(13):
        raw=bars[0].model_dump();raw['revision_id']=f'EARLY-{i}'
        for k in ('starts_at','ends_at'):
            raw['data'][k]=(at(raw['data'][k])-timedelta(days=13-i)).strftime('%Y-%m-%dT%H:%M:%SZ')
        earlier.append(Revision.model_validate(raw))
    bars=earlier+bars
    sessions=[Revision.model_validate({**r.model_dump(),'revision_id':'s-'+r.revision_id,'listing_id':'NSE','instrument_revision_id':None,
        'data':SessionData(kind='session',calendar_version='invented',opens_at=r.data.starts_at,closes_at=r.data.ends_at)}) for r in bars]
    for i,b in enumerate(bars):
        raw=b.model_dump()
        for k in ('starts_at','ends_at'):raw['data'][k]=(at(raw['data'][k])-timedelta(days=lag)).strftime('%Y-%m-%dT%H:%M:%SZ')
        bars[i]=Revision.model_validate(raw)
    for b in bars[:lag]:sessions.insert(0,sessions[0].model_copy(update={'revision_id':'early-'+b.revision_id,'data':SessionData(kind='session',calendar_version='invented',opens_at=b.data.starts_at,closes_at=b.data.ends_at)}))
    if fault=='interior':bars.pop(10)
    if fault=='warmup':bars=bars[14:]
    if fault=='duplicate':bars.append(bars[-1])
    if fault=='calendar':sessions.append(sessions[-1])
    if fault=='boundary':bars[0]=bars[0].model_copy(update={'data':bars[0].data.model_copy(update={'starts_at':'2026-09-19T05:00:00Z'})})
    if fault=='vintage':bars[0]=bars[0].model_copy(update={'fetched_at':'2026-10-19T11:59:00Z','available_at':'2026-10-19T11:59:00Z','published_at':'2026-10-19T11:59:00Z'})
    rows=[(r.model_dump(mode='json'),'test-grant','1') for r in bars]
    page=Page(cursor=None,next_cursor=None,complete=True,records=tuple(r[0] for r in rows))
    pages=[('',digest(page.model_dump(mode='json')),None,True,len(rows),0)]
    if fault=='pages':pages=[]
    if fault=='incomplete':stream=(*stream[:3],False)
    if fault=='provenance':rows[0]=(rows[0][0],'', '1')
    def provenance(r):return Provenance(r.source_id,r.source_revision,*(at(t).replace(tzinfo=timezone.utc) for t in (r.published_at,r.available_at,r.fetched_at)),'observed_live')
    readiness=market_readiness(bars,sessions,NOW)
    result=describe(Conn(rows,stream,pages),'NSE:TEST',bars,sessions,readiness,NOW,historical_request=historical,provenance=provenance,freshness_policy=policy)
    return result,readiness


@pytest.mark.parametrize('lag,policy,available',[(0,'strict',True),(0,'one_trailing_session_v1',True),(1,'one_trailing_session_v1',True),(2,'one_trailing_session_v1',False),(1,'strict',False)])
def test_explicit_policy_and_session_lag(lag,policy,available):
    r,ready=delayed(lag=lag,policy=policy)
    assert (r.status=='AVAILABLE_DESCRIPTIVE_ONLY')==available
    assert r.freshness.trailing_missing_sessions==lag
    assert ready['latest_session_present']==(lag==0)
    assert r.session_coverage.latest_session_present==(lag==0)
    assert not r.actionable and not r.execution_qualified and not r.paper_admission_authorized and not r.publication_authorized
    if available:
        assert r.metrics['sma20']=='105' and r.metrics['relative_volume20'] is None
        assert r.freshness.status==('current' if lag==0 else 'delayed_one_session')
        assert r==AdjustedResearch.model_validate_json(r.model_dump_json())


@pytest.mark.parametrize('fault',['interior','warmup','duplicate','calendar','boundary','vintage','pages','incomplete','provenance'])
def test_delay_does_not_relax_other_checks(fault):
    r,_=delayed(fault=fault)
    assert r.status=='UNAVAILABLE' and not r.metrics
    assert r.freshness.status=='unavailable'


def test_no_historical_cutoff_reuse():
    r,_=delayed(historical=True)
    assert r.status=='UNAVAILABLE' and 'historical_adjusted_research_not_supported' in r.unavailable_reasons


@pytest.mark.parametrize('field,value',[('policy','strict'),('trailing_missing_sessions',2),('status','current'),('latest_available_price_session',NOW)])
def test_delayed_contract_rejects_contradictions(field,value):
    r,_=delayed();raw=r.model_dump();raw['freshness'][field]=value
    with pytest.raises(ValueError):AdjustedResearch.model_validate(raw)


@pytest.mark.parametrize('flag',['actionable','execution_qualified','historical_pit_qualified','publication_authorized','paper_admission_authorized'])
def test_delayed_contract_cannot_enable_execution(flag):
    r,_=delayed();raw=r.model_dump();raw[flag]=True
    with pytest.raises(ValueError):AdjustedResearch.model_validate(raw)
