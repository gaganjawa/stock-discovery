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

EARLIER='2026-10-19T11:00:00Z'
pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')
@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()


def setup(conn,tmp_path,*,mixed=False,missing=False,boundary=None,rolling=None,approved=False, hidden=False, parent_only=False):
    g=grant();path=tmp_path/'grants.json';path.write_text(json.dumps([g.model_dump(mode='json')]))
    def save(scope,rows,suffix=''):
        s=Stream(stream_id='adjusted-test-'+scope+suffix,source_id='upstox',account_ref='test',scope=scope)
        req=UseRequest(source_id='upstox',account_ref='test',scope=scope,uses=('acquire','store'),region='IN',destination_region=None,processor_ref=None,
            requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
        r=ingest_next(conn,s,RevisionPages(tuple(rows)),load_grant=lambda:g,request=req,audit=lambda d:None,clock=lambda:NOW)
        assert not r['quarantined']
    listing='NSE:INE009A01021'
    identity=observed_revision(InstrumentData(kind='instrument',issuer_id='TEST',symbol='TEST',isin='INE009A01021',series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at='2026-01-01T00:00:00Z'),listing=listing,fetched=EARLIER if rolling else NOW)
    old_parent=None
    if parent_only:
        old_grant=g.model_copy(update={'account_ref':'parent-only','grant_id':'parent-only-grant'})
        path.write_text(json.dumps([g.model_dump(mode='json'),old_grant.model_dump(mode='json')]))
        old_parent=observed_revision(identity.data.model_copy(update={'symbol':'OLD'}),listing=listing,fetched='2026-10-18T11:00:00Z')
        stream=Stream(stream_id='parent-only',source_id='upstox',account_ref='parent-only',scope='universe')
        req=UseRequest(source_id='upstox',account_ref='parent-only',scope='universe',uses=('acquire','store'),region='IN',destination_region=None,processor_ref=None,
            requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
        ingest_next(conn,stream,RevisionPages((old_parent,)),load_grant=lambda:old_grant,request=req,audit=lambda d:None,clock=lambda:NOW)
        identity=observed_revision(identity.data,listing=listing,fetched=EARLIER,previous=old_parent)
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
    if rolling:
        # Rolling daily refreshes: an earlier window, then a later overlapping re-fetch.
        first=[observed_revision(b.data,listing=listing,fetched=EARLIER,parent=old_parent.revision_id if parent_only and i>=10 else identity.revision_id) for i,b in enumerate(bars[:20])]
        if hidden:
            from stock_discovery_analysis.revision_storage import Page,ingest_page
            stream=Stream(stream_id='adjusted-test-pricesA',source_id='upstox',account_ref='test',scope='prices')
            req=UseRequest(source_id='upstox',account_ref='test',scope='prices',uses=('acquire','store'),region='IN',destination_region=None,processor_ref=None,
                requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
            old=g.model_copy(update={'grant_id':'overlap-only-grant'})
            for index,rows in enumerate((first[:10],first[10:])):
                page=Page(cursor=None if index==0 else '10',next_cursor='10' if index==0 else None,complete=index==1,records=tuple(r.model_dump(mode='json') for r in rows))
                ingest_page(conn,stream,page,load_grant=lambda:g if index==0 else old,request=req,audit=lambda d:None)
        else:save('prices',first,'A')
        later=[]
        for i,b in enumerate(bars[10:],10):
            data=b.data
            if rolling=='conflict' and i==12:data=data.model_copy(update={'close':'104'})
            later.append(observed_revision(data,listing=listing,fetched=NOW,parent=identity.revision_id,previous=first[i] if i<20 else None))
        save('prices',later if rolling!='gap' else later[10:],'B')
    elif mixed:
        save('prices',bars[:15],'A');save('prices',bars[15:],'B')
    else:save('prices',bars)
    return ViewConfig(sources=SourceConfig(grant_file=str(path),retention_days=365),listing_ids=(listing,),
                      adjusted_multi_stream='approved_v1' if approved else 'disabled'),listing

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


@pytest.mark.parametrize('rolling,approved,expected',[
    ('agree',False,'batch_identity_missing_or_ambiguous'),('agree',True,'adjusted_vintage_unverified'),
    ('conflict',True,'adjusted_stream_conflict'),('gap',True,'adjusted_stream_continuity_unverified')])
def test_owner_approved_multi_stream_rule(isolated_url,tmp_path,rolling,approved,expected):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,rolling=rolling,approved=approved)
        before=conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()
        result=company(conn,config,listing,clock=lambda:NOW);research=result['adjusted_research']
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==before
        assert not research['execution_qualified'] and not research['actionable'] and not research['paper_admission_authorized']
        if expected:
            assert research['status']=='UNAVAILABLE' and expected in research['unavailable_reasons']
            assert not research['metrics'] and not result['price_series']
            return
        assert research['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
        assert research['batch']['identity_basis']=='verified_ingestion_pages_multi_stream_v1'
        assert len(research['batch']['stream_batches'])==2 and 'owner_approved_multi_stream_rule_v1' in research['limitations']
        clocks={o['acquired_at'] for o in research['observations']}
        assert len(research['observations'])==30 and len(clocks)==2 and research['metrics']['sma20']=='105'
        assert len(result['price_series'])==30


@pytest.mark.parametrize('restricted',[False,True])
def test_superseded_overlap_original_grant_is_required(isolated_url,tmp_path,restricted):
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,rolling='agree',approved=True,hidden=True)
        if restricted:restrict(conn,request_id=uuid.uuid4(),kind='grant',source_id='upstox',account_ref='test',grant_id='overlap-only-grant',grant_version='1',reason='revoked')
        # Selected observations all use the current grant; superseded overlap does not.
        # Even without an explicit fence its original grant must match current authority.
        with pytest.raises(PermissionError,match='real_read_access_denied'):
            company(conn,config,listing,clock=lambda:NOW)


def test_multi_stream_dependencies_include_every_overlap_and_parent(isolated_url,tmp_path,monkeypatch):
    from stock_discovery_analysis import read_fences
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,rolling='agree',approved=True)
        original=read_fences.authorize_revision_dependencies;seen=[]
        def capture(db,ids,cutoff):
            seen.extend(ids);original(db,ids,cutoff)
            deps=read_fences._active.get().dependencies()
            assert set(ids)<=set(deps)
            assert any(stream.scope=='universe' for _,stream,_ in deps.values())
        monkeypatch.setattr(read_fences,'authorize_revision_dependencies',capture)
        result=company(conn,config,listing,clock=lambda:NOW)
        assert len(set(seen))==40
        assert result['adjusted_research']['unavailable_reasons']==['adjusted_vintage_unverified']
        assert not result['price_series'] and not result['adjusted_research']['metrics']


def test_full_stream_locks_hold_until_guarded_read_finishes(isolated_url,tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from stock_discovery_analysis import read_fences
    from stock_discovery_analysis.grant_fences import restrict
    from test_read_fences import wait_blocked
    locked=Event();release=Event();ready=Event();pids=[]
    original=read_fences.authorize_revision_dependencies
    def pause(conn,ids,cutoff):
        original(conn,ids,cutoff);locked.set();assert release.wait(5)
    monkeypatch.setattr(read_fences,'authorize_revision_dependencies',pause)
    with psycopg.connect(isolated_url,autocommit=True) as admin:
        config,listing=setup(admin,tmp_path,rolling='agree',approved=True)
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as conn:return company(conn,config,listing,clock=lambda:NOW)
        def revoke():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                pids.append(conn.info.backend_pid);ready.set()
                return restrict(conn,request_id=uuid.uuid4(),kind='account',source_id='upstox',account_ref='test',reason='revoked')
        with ThreadPoolExecutor(2) as pool:
            reading=pool.submit(read);assert locked.wait(5)
            writing=pool.submit(revoke);assert ready.wait(5)
            try:wait_blocked(admin,pids[0]);assert not writing.done()
            finally:release.set()
            assert reading.result(timeout=5)['adjusted_research']['status']=='UNAVAILABLE'
            assert writing.result(timeout=5)==1
        with pytest.raises(PermissionError):company(admin,config,listing,clock=lambda:NOW)


def test_rehearsal_target_challenge_distinguishes_databases(isolated_url):
    import importlib.util
    spec=importlib.util.spec_from_file_location('rehearse',Path(__file__).resolve().parents[3]/'scripts/rehearse_migration.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def runner(url):
        def run(command,source,challenge):
            with psycopg.connect(url,autocommit=True) as conn:
                locked=conn.execute('SELECT NOT pg_try_advisory_lock(%s)',(int(challenge),)).fetchone()[0]
                return b't\n' if locked else b'f\n'
        return run
    module.verify_target(isolated_url,run=runner(isolated_url))
    other=psycopg.conninfo.make_conninfo(isolated_url,dbname='stk013_test')
    with pytest.raises(ValueError,match='database_target_mismatch'):
        module.verify_target(isolated_url,run=runner(other))



def test_superseded_overlap_parent_restriction_denies_company(isolated_url,tmp_path):
    from stock_discovery_analysis.grant_fences import restrict
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,rolling='agree',approved=True,parent_only=True)
        assert company(conn,config,listing,clock=lambda:NOW)['adjusted_research']['status']=='UNAVAILABLE'
        restrict(conn,request_id=uuid.uuid4(),kind='account',source_id='upstox',account_ref='parent-only',reason='revoked')
        with pytest.raises(PermissionError,match='real_read_access_denied'):
            company(conn,config,listing,clock=lambda:NOW)


def test_recent_overlap_cannot_prove_pre_action_adjustment(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,listing=setup(conn,tmp_path,rolling='agree',approved=True)
        # A split effective Sep 30 changes Sep 20-29 only. B re-fetches Sep 30 onward:
        # every overlapping value matches, but A's older 100-price rows could now be 50.
        older=conn.execute("SELECT payload->'data'->>'open' FROM discovery.revisions WHERE stream_id='adjusted-test-pricesA' AND payload->'data'->>'starts_at'<'2026-09-30' ").fetchall()
        assert older==[('100',)]*10
        result=company(conn,config,listing,clock=lambda:NOW)
        assert result['adjusted_research']['status']=='UNAVAILABLE'
        assert 'adjusted_vintage_unverified' in result['adjusted_research']['unavailable_reasons']
        assert not result['adjusted_research']['metrics'] and not result['price_series']


def test_full_dependency_temporal_eligibility(isolated_url,tmp_path):
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.read_fences import guarded_read,authorize_revision_dependencies
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=setup(conn,tmp_path,rolling='agree',approved=True)
        ids=[r[0] for r in conn.execute("SELECT revision_id FROM discovery.revisions WHERE stream_id='adjusted-test-pricesA'")]
        with pytest.raises(PermissionError,match='real_read_access_denied'):
            with guarded_read(conn,source_access(config.sources,lambda:NOW)):
                authorize_revision_dependencies(conn,ids,'2026-10-19T10:59:59Z')
