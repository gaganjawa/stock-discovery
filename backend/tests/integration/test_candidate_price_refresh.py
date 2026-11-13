"""Invented provider responses through the real Upstox adapter; disposable DB."""
import gzip,json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx,psycopg,pytest
from test_candidates import isolated_url
from test_real_market import grant,NOW
from test_candidates import scanner,drain
from worker.candidate_prices import RefreshConfig,cycle,identity
from worker.providers.upstox import Upstox
from stock_discovery_analysis import candidate_store as store,candidate_price_store as jobs
from stock_discovery_analysis.chartink import fixture_snapshot
from stock_discovery_analysis.candidate_research import analyze
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.real_access import SourceConfig

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='disposable PostgreSQL required')


def prepare(conn,path):
    gf=path/'grants';gf.write_text(json.dumps([grant().model_dump(mode='json')]))
    token=path/'token';token.write_text('invented-token')
    scan=scanner();day=NOW[:10]
    event=fixture_snapshot(scan,['INFY'],day,datetime.fromisoformat(NOW.replace('Z','+00:00')))
    store.accept(conn,event);store.accept(conn,event);drain(conn)
    conn.execute("UPDATE discovery.candidates SET research_status='blocked',result='{}'")
    config=RefreshConfig(market=dict(account_ref='test',grant_file=str(gf),token_file=str(token),
        symbols=('INFY',),retention_days=365,lookback_days=40),scanner_keys=(scan.key,))
    return config,event


class Provider:
    def __init__(self):self.requests=[];self.partial=False;self.interrupt=False;self.fail_calendar=False
    def response(self,request):
        self.requests.append(str(request.url));url=str(request.url)
        if 'NSE.json.gz' in url:
            rows=[dict(segment='NSE_EQ',exchange='NSE',instrument_type='EQ',trading_symbol='INFY',
                isin='INE009A01021',instrument_key='NSE_EQ|INE009A01021',name='Invented identity',lot_size=1,tick_size=5)]
            return httpx.Response(200,content=gzip.compress(json.dumps(rows).encode()))
        if '/timings/' in url:
            if self.fail_calendar:return httpx.Response(503)
            day=url.rsplit('/',1)[1]
            millis=lambda h:int(datetime.fromisoformat(day).replace(hour=h,tzinfo=timezone.utc).timestamp()*1000)
            return httpx.Response(200,json={'status':'success','data':[dict(exchange='NSE',start_time=millis(4),end_time=millis(10))]})
        assert '/historical-candle/' in url
        if self.interrupt:self.interrupt=False;raise KeyboardInterrupt('simulated process loss')
        end,start=[datetime.fromisoformat(s) for s in url.split('/')[-2:]]
        days=(end-start).days+1
        rows=[[(start+timedelta(days=i)).date().isoformat()+'T00:00:00+05:30',100,110,90,105,1000,0] for i in range(days)]
        if self.partial:rows=rows[:-1]  # latest known closed session absent
        return httpx.Response(200,json={'status':'success','data':{'candles':rows}})
    def factory(self):
        transport=httpx.MockTransport(self.response);ticks=iter(range(100000))
        class Client(Upstox):
            def __init__(self,**kw):super().__init__(**kw,transport=transport,monotonic=lambda:next(ticks))
        return Client


def run(conn,config,provider,at=NOW):return cycle(conn,config,clock=lambda:at,factory=provider.factory(),pause=lambda _:None)


def test_duplicate_refresh_reanalysis_and_current_api(isolated_url,tmp_path,monkeypatch):
    from app.main import app
    from app.research import db
    from app import candidates
    from stock_discovery_analysis import candidate_swing
    from fastapi.testclient import TestClient
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,event=prepare(conn,tmp_path);provider=Provider()
        view=ViewConfig(sources=SourceConfig(grant_file=config.market.grant_file,retention_days=365),listing_ids=('NSE:INE009A01021',))
        # Missing history has no invented values before refresh.
        assert analyze(conn,view,'INFY',NOW[:10],clock=lambda:NOW)['status']=='blocked'
        result=run(conn,config,provider)
        assert result['status']=='ingested' and result['research_status']=='queued'
        assert conn.execute('SELECT research_status FROM discovery.candidates').fetchone()==('pending',)
        requests=len(provider.requests)
        store.accept(conn,event);drain(conn)
        assert run(conn,config,provider)['status']=='idle' and len(provider.requests)==requests
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()==(1,)
        assert store.research_one(conn,lambda c,s,d:analyze(c,view,s,d,clock=lambda:NOW))
        row=store.rows(conn)['rows'][0]
        assert row['research_status']=='completed'
        assert row['research']['technical']['metrics']['sma20']=='105'
        assert conn.execute('SELECT count(*) FROM discovery.candidate_receivers').fetchone()==(0,)
    monkeypatch.setenv('AUTH_TOKEN','o'*40);monkeypatch.setattr(candidates,'view_config',lambda:view)
    original=candidate_swing.page
    monkeypatch.setattr(candidate_swing,'page',lambda *a,**k:original(*a,**k,clock=lambda:NOW))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as c:yield c
    app.dependency_overrides[db]=connection
    try:
        response=TestClient(app).get('/v1/real-research/candidates/swing-review',headers={'Authorization':'Bearer '+'o'*40})
        assert response.status_code==200
        assert response.json()['rows'][0]['swing_review']['rank']==1
        if os.getenv('STK014_PRICE_BROWSER')=='1':
            import sys
            sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
            from candidate_price_browser_acceptance import verify
            monkeypatch.setenv('COOKIE_SECURE','false')
            monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'watchlist'))
            verify(app)
    finally:app.dependency_overrides.clear()


def test_partial_stale_response_then_recovery(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();p.partial=True
        result=run(conn,config,p)
        assert result['status']=='partial' and result['missing_sessions']==[NOW[:10]]
        assert conn.execute('SELECT research_status FROM discovery.candidates').fetchone()==('blocked',)
        assert jobs.status(conn,identity(config))=={'retry_wait':1}
        calendar_calls=sum('/timings/' in u for u in p.requests)
        p.partial=False
        later=(datetime.fromisoformat(NOW.replace('Z','+00:00'))+timedelta(minutes=16)).strftime('%Y-%m-%dT%H:%M:%SZ')
        assert run(conn,config,p,later)['status']=='ingested'
        assert sum('/timings/' in u for u in p.requests)==calendar_calls
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(1,)


def test_interrupted_job_retains_quota_and_recovers_after_lease(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();p.interrupt=True
        with pytest.raises(KeyboardInterrupt):run(conn,config,p)
        charged=conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0]
        assert charged==len(p.requests) and charged>40
        assert jobs.status(conn,identity(config))=={'running':1}
        assert run(conn,config,p)['status']=='idle'
        later=(datetime.fromisoformat(NOW.replace('Z','+00:00'))+timedelta(minutes=16)).strftime('%Y-%m-%dT%H:%M:%SZ')
        assert run(conn,config,p,later)['status']=='ingested'
        assert conn.execute('SELECT attempts FROM discovery.schedule_jobs').fetchone()==(2,)
        assert conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0]==charged+2


def test_rights_and_account_lock_deny_requests(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn,psycopg.connect(isolated_url,autocommit=True) as other:
        config,_=prepare(conn,tmp_path);p=Provider()
        other.execute("SELECT pg_advisory_lock(hashtextextended('REAL-001:test',0))")
        assert run(conn,config,p)['status']=='busy' and not p.requests
        other.execute("SELECT pg_advisory_unlock(hashtextextended('REAL-001:test',0))")
        Path(config.market.grant_file).write_text('[]')
        assert run(conn,config,p)['status']=='blocked' and not p.requests
        assert jobs.status(conn,identity(config))=={'blocked':1}


def test_cross_scanner_duplicates_use_one_price_job(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path)
        scan=scanner().model_copy(update={'scan_name':'Another synthetic scanner','scan_url':'another-synthetic'})
        e=fixture_snapshot(scan,['INFY'],NOW[:10],datetime.fromisoformat(NOW.replace('Z','+00:00')))
        store.accept(conn,e);drain(conn)
        config=config.model_copy(update={'scanner_keys':(*config.scanner_keys,scan.key)})
        p=Provider();assert run(conn,config,p)['status']=='ingested'
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(2,)
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()==(1,)
        assert sum('/historical-candle/' in u for u in p.requests)==1


def test_after_ingestion_crash_replays_without_duplicate_reanalysis(isolated_url,tmp_path,monkeypatch):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();original=jobs.complete
        def crash(*args,**kwargs):
            with conn.transaction():
                original(*args,**kwargs)
                raise KeyboardInterrupt('crash before completion commit')
        monkeypatch.setattr(jobs,'complete',crash)
        with pytest.raises(KeyboardInterrupt):run(conn,config,p)
        assert conn.execute('SELECT research_status FROM discovery.candidates').fetchone()==('blocked',)
        assert jobs.status(conn,identity(config))=={'running':1}
        monkeypatch.setattr(jobs,'complete',original)
        assert run(conn,config,p,'2026-10-19T12:16:00Z')['status']=='ingested'
        assert jobs.status(conn,identity(config))=={'completed':1}
        assert run(conn,config,p,'2026-10-19T12:17:00Z')['status']=='idle'
        assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(1,)


def test_partial_retry_exhaustion_is_explicit(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();p.partial=True
        for clock in (NOW,'2026-10-19T12:16:00Z','2026-10-19T12:32:00Z'):
            assert run(conn,config,p,clock)['status']=='partial'
        assert jobs.status(conn,identity(config))=={'partial':1}
        calls=len(p.requests)
        assert run(conn,config,p,'2026-10-19T12:50:00Z')['status']=='idle'
        assert len(p.requests)==calls
        assert conn.execute('SELECT research_status FROM discovery.candidates').fetchone()==('blocked',)


def test_calendar_failure_and_durable_quota_stop_before_http(isolated_url,tmp_path):
    from stock_discovery_contracts.v2 import digest
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();p.fail_calendar=True
        assert run(conn,config,p)['status']=='retry_wait'
        assert conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='candidate_calendar'").fetchone()==(0,)
        p.fail_calendar=False
        # Existing account requests made by another acquisition path remain charged.
        code='pilot_request:'+digest('test')
        for _ in range(90):conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES(NULL,%s,%s)',('2026-10-19T12:01:00Z',code))
        calls=len(p.requests)
        assert run(conn,config,p,'2026-10-19T12:01:00Z')['status']=='retry_wait'
        assert len(p.requests)==calls


def test_morning_success_refreshes_again_after_verified_close(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider()
        # A prior-day observed candidate can refresh before today's session closes;
        # today's fixture has not yet been received at the morning test clock.
        old=fixture_snapshot(scanner(),['INFY'],'2026-10-18',datetime(2026,10,18,12,tzinfo=timezone.utc))
        store.accept(conn,old);drain(conn)
        assert run(conn,config,p,'2026-10-19T09:00:00Z')['latest_session']=='2026-10-18'
        calls=len(p.requests)
        assert run(conn,config,p,'2026-10-19T09:05:00Z')['status']=='idle'
        assert len(p.requests)==calls
        assert run(conn,config,p,NOW)['latest_session']=='2026-10-19'
        assert jobs.status(conn,identity(config))=={'completed':2}


def test_abandoned_previous_day_job_is_not_backdated(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider();p.interrupt=True
        with pytest.raises(KeyboardInterrupt):run(conn,config,p)
        assert run(conn,config,p,'2026-10-20T12:00:00Z')['status']=='ingested'
        assert jobs.status(conn,identity(config))=={'missed':1,'completed':1}
        assert conn.execute("SELECT result->>'latest_session' FROM discovery.schedule_jobs WHERE status='completed'").fetchone()==('2026-10-20',)


def test_bounded_selection_advances_and_unknown_mapping_is_explicit(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider()
        e=fixture_snapshot(scanner(),['ZZZ','OUTSIDE'],NOW[:10],datetime.fromisoformat(NOW.replace('Z','+00:00')))
        store.accept(conn,e);drain(conn)
        config=config.model_copy(update={'market':config.market.model_copy(update={'symbols':('INFY','ZZZ')}),'max_symbols':1})
        result=run(conn,config,p)
        assert result['status']=='ingested'
        assert result['selection']=={'eligible_symbols':2,'outside_configured_universe':1}
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()==(1,)
        result=run(conn,config,p)
        assert result['status']=='retry_wait' and result['reason']=='readiness'
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()==(2,)
        assert conn.execute("SELECT listing_id FROM discovery.candidates WHERE symbol='ZZZ'").fetchone()==(None,)


def test_new_candidate_after_clock_never_triggers_early_acquisition(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);p=Provider()
        result=run(conn,config,p,'2026-10-19T11:00:00Z')
        assert result['status']=='idle' and result['selection']['eligible_symbols']==0
        assert not p.requests
