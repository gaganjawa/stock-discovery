"""STK-094: rolling synthetic acquisition must remain readable after opening research."""
import os
from pathlib import Path
import psycopg
import pytest
from test_candidates import isolated_url
from test_candidate_price_refresh import prepare,Provider,run
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.candidate_research import analyze
from stock_discovery_analysis.real_views import company,ViewConfig
from stock_discovery_analysis.real_access import SourceConfig

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='disposable PostgreSQL required')
LATER='2026-10-20T12:00:00Z'
LISTING='NSE:INE009A01021'


@pytest.mark.parametrize('raw_intake',[False,True])
def test_rolling_refresh_keeps_candidate_and_open_research_on_same_batch(isolated_url,tmp_path,monkeypatch,raw_intake):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path,raw_intake=raw_intake,monkeypatch=monkeypatch);provider=Provider()
        view=ViewConfig(sources=SourceConfig(grant_file=config.market.grant_file,retention_days=365),listing_ids=(LISTING,))
        assert run(conn,config,provider)['status']=='ingested'
        assert run(conn,config,provider,LATER)['status']=='ingested'
        assert store.research_one(conn,lambda c,s,d:analyze(c,view,s,d,clock=lambda:LATER))
        candidate=store.rows(conn)['rows'][0]['research']
        assert candidate['status']=='completed'
        detail=company(conn,view,LISTING,clock=lambda:LATER)
        assert detail['adjusted_research']['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
        assert detail['adjusted_research']['batch']==candidate['technical']['batch']
        assert len(detail['price_series'])==41
        assert detail['adjusted_research']['metrics']['relative_volume20'] is None
        assert not detail['adjusted_research']['actionable']
        # A later receipt must not alter an earlier current-clock observation.
        earlier=company(conn,view,LISTING,clock=lambda:'2026-10-19T12:00:00Z')
        assert earlier['adjusted_research']['status']=='AVAILABLE_DESCRIPTIVE_ONLY'
        assert earlier['adjusted_research']['batch']!=detail['adjusted_research']['batch']
        # Historical/publication reads keep their existing full evidence selection.
        historical=company(conn,view,LISTING,clock=lambda:LATER,cutoff_at=LATER)
        publication=company(conn,view,LISTING,clock=lambda:LATER,publication_inputs=True)[0]
        for result in (historical,publication):
            assert result['market_readiness']['observed_bars']==42
            assert result['adjusted_research']['status']=='UNAVAILABLE'
        before=conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()
        calls=len(provider.requests)
    from app.main import app
    from app.research import db
    from app import candidates,real_research
    from fastapi.testclient import TestClient
    from stock_discovery_analysis import real_views,candidate_swing
    monkeypatch.setenv('AUTH_TOKEN','o'*40)
    monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'watchlist'))
    monkeypatch.setattr(candidates,'view_config',lambda:view)
    monkeypatch.setattr(real_research,'view_config',lambda:view)
    original=real_views.company
    def current(*args,**kwargs):
        kwargs.setdefault('clock',lambda:LATER)
        return original(*args,**kwargs)
    monkeypatch.setattr(real_views,'company',current)
    page=candidate_swing.page
    monkeypatch.setattr(candidate_swing,'page',lambda *a,**k:page(*a,**k,clock=lambda:LATER))
    def connection():
        with psycopg.connect(isolated_url,autocommit=True) as c:yield c
    app.dependency_overrides[db]=connection
    try:
        client=TestClient(app);headers={'Authorization':'Bearer '+'o'*40}
        base='/v1/real-research/'
        for endpoint in ('companies/'+LISTING,'workbench','candidates/swing-review'):
            assert client.get(base+endpoint).status_code==401
        response=client.get(base+'companies/'+LISTING,headers=headers)
        assert response.status_code==200 and response.headers['cache-control']=='no-store'
        assert response.json()['adjusted_research']['batch']==candidate['technical']['batch']
        reviewed=client.get(base+'candidates/swing-review',headers=headers).json()
        assert reviewed['ranking_scope']=='displayed_page_only'
        assert reviewed['rows'][0]['swing_review']['rank']==1
        q=reviewed['rows'][0]['qualification']
        assert q['identity']=='verified_nse_eq' and q['source_permission']=='permitted_stored_research'
        assert q['research_state']=='completed' and q['refresh_state']=='completed'
        assert q['latest_qualified_price_session']==candidate['market_data']['latest_session']
        assert q['signal']=='unqualified' and not q['actionable']
        cached=client.get(base+'candidates',headers=headers).json()['rows'][0]['qualification']
        assert cached['evidence_basis']=='last_stored_analysis'
        assert cached['latest_qualified_price_session'] is None
        if os.getenv('STK094_CONTINUITY_BROWSER')=='1':
            import sys
            sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
            from candidate_price_browser_acceptance import verify
            monkeypatch.setenv('COOKIE_SECURE','false')
            verify(app,continuity=True)
        assert client.put(base+'watchlist/'+LISTING,headers=headers,json={'status':'Researching','note':'','review_date':None}).status_code==200
        workbench=client.get(base+'workbench',headers=headers).json()
        row=next(r for r in workbench['rows'] if r['listing_id']==LISTING)
        assert row['state']=='readable'
        assert row['detail']['adjusted_research']['batch']==candidate['technical']['batch']
        assert client.post(base+'watchlist/'+LISTING+'/review',headers=headers).status_code==200
        assert client.get(base+'watchlist',headers=headers).json()['entries'][LISTING]['reviewed_observation']
        # Revocation is rechecked across all views even after a successful save.
        Path(config.market.grant_file).write_text('[]')
        assert client.get(base+'companies/'+LISTING,headers=headers).status_code==403
        denied=client.get(base+'candidates/swing-review',headers=headers).json()['rows'][0]
        assert denied['swing_review']['rank'] is None and 'technical' not in denied['research']
        assert denied['qualification']['source_permission']=='denied'
        assert denied['qualification']['latest_qualified_price_session'] is None
        denied=client.get(base+'workbench',headers=headers).json()['rows'][0]
        assert denied['state']=='denied' and 'detail' not in denied
        with psycopg.connect(isolated_url,autocommit=True) as conn:
            assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==before
            assert conn.execute('SELECT count(*) FROM discovery.candidate_research_runs').fetchone()==(1,)
            assert conn.execute('SELECT count(*) FROM discovery.candidates').fetchone()==(1,)
        assert len(provider.requests)==calls  # Reading/saving never acquires prices.
    finally:app.dependency_overrides.clear()


@pytest.mark.parametrize('failure',['partial','missing_stream','wrong_scope'])
def test_incomplete_or_invalid_batch_cannot_fall_back_to_ranked_old_history(isolated_url,tmp_path,failure):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,_=prepare(conn,tmp_path);provider=Provider()
        view=ViewConfig(sources=SourceConfig(grant_file=config.market.grant_file,retention_days=365),listing_ids=(LISTING,))
        assert run(conn,config,provider)['status']=='ingested'
        clock=LATER
        if failure=='partial':
            provider.partial=True
            assert run(conn,config,provider,LATER)['status']=='partial'
        else:
            stream='absent-test-stream'
            if failure=='wrong_scope':
                # A real complete calendar stream cannot masquerade as prices.
                stream=conn.execute("SELECT stream_id FROM discovery.streams WHERE scope='calendar' LIMIT 1").fetchone()[0]
            conn.execute("UPDATE discovery.schedule_jobs SET result=jsonb_set(result,'{price_stream_id}',to_jsonb(%s::text)) WHERE status='completed'",(stream,))
        detail=company(conn,view,LISTING,clock=lambda:clock)
        assert detail['price_series']==[]
        assert detail['adjusted_research']['status']=='UNAVAILABLE'
        assert list(detail['adjusted_research']['unavailable_reasons'])==['price_batch_superseded_or_unavailable']
        from stock_discovery_analysis.candidate_swing import review
        assert review(analyze(conn,view,'INFY','2026-10-19',clock=lambda:clock))['rank'] is None
