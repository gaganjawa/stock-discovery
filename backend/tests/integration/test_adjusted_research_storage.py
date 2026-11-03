"""Synthetic PostgreSQL acceptance: no actual Upstox data or requests."""
import json,os,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from test_real_market import grant, NOW
from stock_discovery_analysis.real_views import company,ViewConfig
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.revisions import InstrumentData,SessionData,CandleData
from stock_discovery_analysis.revision_storage import Stream,ingest_next
from worker.providers.upstox import observed_revision,RevisionPages
from stock_discovery_contracts.rights import UseRequest

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')
@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()


def setup(conn,tmp_path,*,mixed=False,missing=False,boundary=None):
    g=grant();path=tmp_path/'grants.json';path.write_text(json.dumps([g.model_dump(mode='json')]))
    def save(scope,rows,suffix=''):
        s=Stream(stream_id='adjusted-test-'+scope+suffix,source_id='upstox',account_ref='test',scope=scope)
        req=UseRequest(source_id='upstox',account_ref='test',scope=scope,uses=('acquire','store'),region='IN',destination_region=None,processor_ref=None,
            requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
        r=ingest_next(conn,s,RevisionPages(tuple(rows)),load_grant=lambda:g,request=req,audit=lambda d:None,clock=lambda:NOW)
        assert not r['quarantined']
    listing='NSE:INE009A01021'
    identity=observed_revision(InstrumentData(kind='instrument',issuer_id='TEST',symbol='TEST',isin='INE009A01021',series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at='2026-01-01T00:00:00Z'),listing=listing,fetched=NOW)
    save('universe',[identity]);sessions=[];bars=[]
    for i in range(30):
        day=datetime(2026,9,20,tzinfo=timezone.utc)+timedelta(days=i)
        stamp=lambda h:day.replace(hour=h).strftime('%Y-%m-%dT%H:%M:%SZ')
        sessions.append(observed_revision(SessionData(kind='session',calendar_version='invented',opens_at=stamp(4),closes_at=stamp(10)),listing='NSE',fetched=NOW))
        bars.append(observed_revision(CandleData(kind='candle',interval='1d',starts_at=stamp(4),ends_at=stamp(10),open='100',high='110',low='90',close='105',volume=1000,adjustment_basis='split_bonus_adjusted'),listing=listing,fetched=NOW,parent=identity.revision_id))
    if boundary:
        if boundary in ('late_open','early_open','early_close','late_close'):
            data=bars[0].data.model_dump();field='starts_at' if 'open' in boundary else 'ends_at'
            stamp=datetime.fromisoformat(data[field].replace('Z','+00:00'))+timedelta(hours=1 if boundary.startswith('late') else -1)
            data[field]=stamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            bars[0]=observed_revision(CandleData.model_validate(data),listing=listing,fetched=NOW,parent=identity.revision_id)
        elif boundary=='missing':sessions.pop(10)
        elif boundary=='extra':
            data=bars[0].data.model_dump()
            for field in ('starts_at','ends_at'):
                data[field]=(datetime.fromisoformat(data[field].replace('Z','+00:00'))-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            bars.insert(0,observed_revision(CandleData.model_validate(data),listing=listing,fetched=NOW,parent=identity.revision_id))
        else:
            data=sessions[0].data.model_dump();data['calendar_version']='competing-calendar'
            if boundary=='ambiguous':data['opens_at']='2026-09-20T05:00:00Z'
            sessions.append(observed_revision(SessionData.model_validate(data),listing='NSE',fetched=NOW))
    save('calendar',sessions)
    if missing:bars.pop(10)
    if mixed:
        save('prices',bars[:15],'A');save('prices',bars[15:],'B')
    else:save('prices',bars)
    return ViewConfig(sources=SourceConfig(grant_file=str(path),retention_days=365),listing_ids=(listing,)),listing

@pytest.mark.parametrize('mode',['valid','mixed','missing','historical','fenced','revoked','missing_grant'])
def test_adjusted_company_read_and_denials(isolated_url,tmp_path,mode):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,mixed=mode=='mixed',missing=mode=='missing')
        before=conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()
        if mode=='fenced':
            assert company(conn,config,listing,clock=lambda:NOW)['adjusted_research']['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
            from stock_discovery_analysis.grant_fences import restrict
            restrict(conn,request_id=uuid.uuid4(),kind='provider',source_id='upstox',reason='revoked')
        if mode in ('revoked','missing_grant'):
            rows=[] if mode=='missing_grant' else [grant().model_copy(update={'status':'revoked','revoked_at':NOW}).model_dump(mode='json')]
            Path(config.sources.grant_file).write_text(json.dumps(rows))
        if mode in ('fenced','revoked','missing_grant'):
            with pytest.raises(PermissionError):company(conn,config,listing,clock=lambda:NOW)
            return
        kw={'cutoff_at':NOW} if mode=='historical' else {}
        result=company(conn,config,listing,clock=lambda:NOW,**kw);research=result['adjusted_research']
        assert research['status']==('AVAILABLE_DESCRIPTIVE_ONLY' if mode=='valid' else 'UNAVAILABLE')
        assert research['metrics'].get('relative_volume20') is None
        assert not research['execution_qualified'] and not research['paper_admission_authorized']
        assert not research['historical_pit_qualified'] and not research['actionable']
        assert result['recommendations']==[] and result['paper_position_status']=='not_created'
        assert all(q['action']=='INSUFFICIENT_EVIDENCE' for q in result['quantitative'].values())
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==before
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()==(0,)
        if mode=='valid':
            assert research['batch']['identity_basis']=='verified_ingestion_pages'
            assert len(research['observations'])==30 and research['metrics']['sma20']=='105'
            assert company(conn,config,listing,clock=lambda:NOW)['adjusted_research']==research
        else:assert not research['metrics'] and not result['price_series']

@pytest.mark.parametrize('boundary',['late_open','early_open','early_close','late_close','missing','extra','duplicate','ambiguous'])
def test_company_rejects_invalid_daily_boundaries(isolated_url,tmp_path,boundary):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,boundary=boundary)
        result=company(conn,config,listing,clock=lambda:NOW)
        research=result['adjusted_research']
        assert research['status']=='UNAVAILABLE'
        assert 'session_boundaries_unverified' in research['unavailable_reasons']
        assert not research['metrics'] and not result['price_series']
        assert not research['execution_qualified'] and not research['paper_admission_authorized']
