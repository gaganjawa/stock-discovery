"""STK-086 lifecycle acceptance on disposable DBs. Invented sessions only."""
import json
import os
import uuid
from pathlib import Path
import psycopg
import pytest
from test_adjusted_research_storage import setup, isolated_url, NOW
from test_real_market import grant
from stock_discovery_analysis.revisions import SessionData
from stock_discovery_analysis.revision_storage import Stream, ingest_next, ingest_page, Page
from stock_discovery_analysis.scheduling import ScheduleConfig
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.grant_fences import restrict
from stock_discovery_contracts.rights import UseRequest
from stock_discovery_contracts.v2 import digest
from worker.providers.upstox import observed_revision, RevisionPages
from worker.stored_operations import inspect

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def setup_readiness(conn,tmp_path,*,incomplete=False,conflict=False):
    view,_=setup(conn,tmp_path,boundary='duplicate' if conflict else None,lag=1)
    view=view.model_copy(update={'pilot_scope_id':'STK-083-INFY-test','descriptive_freshness_policy':'one_trailing_session_v1'})
    records=[observed_revision(SessionData(kind='session',calendar_version='invented',
        opens_at=f'2026-10-{day}T04:00:00Z',closes_at=f'2026-10-{day}T10:00:00Z'),listing='NSE',fetched=NOW)
        for day in ('20','21','22')]
    stream=Stream(stream_id='test-future-calendar',source_id='upstox',account_ref='test',scope='calendar')
    request=UseRequest(source_id='upstox',account_ref='test',scope='calendar',uses=('acquire','store'),region='IN',
        destination_region=None,processor_ref=None,requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
    if incomplete:
        ingest_page(conn,stream,Page(cursor=None,next_cursor='next',complete=False,records=tuple(r.model_dump(mode='json') for r in records)),
            load_grant=grant,request=request,audit=lambda d:None)
    else:
        ingest_next(conn,stream,RevisionPages(tuple(records)),load_grant=grant,request=request,audit=lambda d:None,clock=lambda:NOW)
    sessions=conn.execute("SELECT DISTINCT payload->'data'->>'opens_at',payload->'data'->>'closes_at' FROM discovery.revisions WHERE kind='session' ORDER BY 1").fetchall()
    raw=fixture_config().model_dump(mode='json')
    raw['calendar'].update(starts_on=sessions[0][0][:10],ends_on='2026-10-24',available_at=NOW,
        sessions=[dict(opens_at=o,closes_at=c) for o,c in sessions])
    raw['calendar']['ref']['content_hash']=digest(raw['calendar']['sessions'])
    raw.update(mode='live_paper',scope_id=view.pilot_scope_id,input_hash=digest(view.model_dump(mode='json')),
        horizons=['swing'],starts_on='2026-10-19')
    return ScheduleConfig.model_validate_json(json.dumps(raw)),view


def test_permitted_sessions_corroborate_but_do_not_invent_closed_day_coverage(isolated_url,tmp_path,monkeypatch):
    import httpx
    from worker.providers.ollama import Ollama
    def forbidden(*a,**kw):pytest.fail('provider/model request forbidden')
    monkeypatch.setattr(httpx.Client,'send',forbidden);monkeypatch.setattr(Ollama,'__init__',forbidden)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        s,v=setup_readiness(conn,tmp_path)
        before=conn.execute('SELECT revision_id,payload FROM discovery.revisions ORDER BY 1').fetchall()
        report=inspect(conn,s,v,clock=lambda:NOW,include_analysis=True)
        assert report['status']=='READY_WITH_LIMITATIONS'
        assert report['calendar']['next_verified_opening']=='2026-10-20T04:00:00Z'
        assert report['calendar']['next_scheduled_execution']=='2026-10-20T10:30:00Z'
        assert report['calendar']['renewal']['stored_sessions_available']
        assert report['calendar']['renewal']['status']=='RENEWAL_BLOCKED'
        assert 'closed_date_coverage_not_in_session_revisions' in report['calendar']['renewal']['reasons']
        assert report['analysis']['state']=='delayed_descriptive'
        assert report['provider_requests']==report['model_requests']==0 and not report['actionable']
        assert conn.execute('SELECT revision_id,payload FROM discovery.revisions ORDER BY 1').fetchall()==before
        assert conn.execute('SELECT count(*) FROM discovery.schedule_jobs').fetchone()[0]==0
        assert all({'source_id','revision_id','content_hash','available_at','supersedes_id'}<=r.keys() for r in report['revision_evidence'])


@pytest.mark.parametrize('case,reason',[
    ('incomplete','stored_revision_incomplete_or_invalid'),
    ('conflict','calendar_revision_missing_or_conflicting'),
    ('missing','calendar_revision_missing_or_conflicting'),
    ('grant_missing','source_authorization_missing'),
    ('grant_expired','source_grant_expired'),
    ('grant_revoked','source_grant_inactive_or_revoked'),
    ('durable_revoked','stored_source_authorization_or_evidence_denied'),
])
def test_calendar_and_rights_fail_closed(isolated_url,tmp_path,case,reason):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        s,v=setup_readiness(conn,tmp_path,incomplete=case=='incomplete',conflict=case=='conflict')
        if case=='missing':
            raw=s.model_dump(mode='json');raw['calendar']['sessions'][-1]['opens_at']='2026-10-23T04:00:00Z';raw['calendar']['sessions'][-1]['closes_at']='2026-10-23T10:00:00Z'
            raw['calendar']['ref']['content_hash']=digest(raw['calendar']['sessions']);s=ScheduleConfig.model_validate_json(json.dumps(raw))
        path=Path(v.sources.grant_file);grants=json.loads(path.read_text())
        if case=='grant_missing':grants=[]
        if case=='grant_expired':grants[0]['expires_at']='2026-10-18T00:00:00Z'
        if case=='grant_revoked':grants[0]['status']='revoked';grants[0]['revoked_at']='2026-10-18T00:00:00Z'
        path.write_text(json.dumps(grants))
        if case=='durable_revoked':restrict(conn,request_id=uuid.uuid4(),kind='provider',source_id='upstox',reason='revoked')
        result=inspect(conn,s,v,clock=lambda:NOW)
        assert result['status']=='BLOCKED' and not result['recurring_activation_safe']
        assert reason in result['reasons']
        assert 'analysis' not in result


def test_expiring_grant_and_last_session_cannot_claim_readiness(isolated_url,tmp_path,monkeypatch):
    from stock_discovery_analysis import read_fences
    # Test both application and durable-check clocks at the same fictional instant.
    monkeypatch.setattr(read_fences,'database_request',lambda conn,request,uses:request.model_copy(update={'uses':tuple(uses)}))
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        s,v=setup_readiness(conn,tmp_path)
        p=Path(v.sources.grant_file);gs=json.loads(p.read_text());gs[0]['expires_at']='2026-10-20T09:00:00Z';p.write_text(json.dumps(gs))
        result=inspect(conn,s,v,clock=lambda:NOW)
        assert 'source_grant_expiring_soon' in result['warnings']
        assert 'source_grant_expires_before_next_execution' in result['reasons']
        p.write_text(json.dumps([grant().model_dump(mode='json')]))
        result=inspect(conn,s,v,clock=lambda:'2026-10-22T02:00:00Z')
        assert result['status']=='BLOCKED'
        assert 'next_execution_opening_unverified' in result['reasons']
        result=inspect(conn,s,v,clock=lambda:'2026-10-25T02:00:00Z')
        assert 'calendar_expired' in result['reasons']


def test_supervised_cycle_reuses_tick_and_catchup_without_duplicate_completion(isolated_url,tmp_path,monkeypatch):
    from worker import stored_operations as ops
    from worker.stored_research import handlers
    import httpx
    monkeypatch.setattr(httpx.Client,'send',lambda *a,**kw:pytest.fail('no network providers'))
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        s,v=setup_readiness(conn,tmp_path)
        # Oct19 is missed; analysis runs at Oct20 noon, with two missing bars.
        clock=lambda:'2026-10-20T12:00:00Z'
        directory=tmp_path/'ops';directory.mkdir(mode=0o700)
        database=directory/'db';database.write_text(isolated_url)
        manifest=directory/'deployment.json'
        view_file=directory/'view.json';schedule_file=directory/'schedule.json'
        data=dict(repo=str(Path(ops.__file__).resolve().parents[2]),database_file=str(database),
            view_file=str(view_file),schedule_file=str(schedule_file))
        monkeypatch.setattr(ops,'validate_deployment',lambda p:(data,s,v))
        before=conn.execute('SELECT revision_id,payload FROM discovery.revisions ORDER BY 1').fetchall()
        for _ in range(4):
            result=ops.cycle(manifest,s,v,schedule_file,view_file,isolated_url,handlers(s,v),clock=clock)
            assert result['status']=='READY_WITH_LIMITATIONS'
        rows=conn.execute("SELECT job_id,status,result FROM discovery.schedule_jobs WHERE stage='ingest' ORDER BY 1").fetchall()
        assert len(rows)==2 and all(r[1]=='partial' for r in rows)
        assert any(r[2]['catch_up'] for r in rows)
        assert all(r[2]['evaluated_at']==clock() and r[2]['report_state']=='unavailable_data' for r in rows)
        for _ in range(2):ops.cycle(manifest,s,v,schedule_file,view_file,isolated_url,handlers(s,v),clock=clock)
        assert conn.execute("SELECT job_id,status,result FROM discovery.schedule_jobs WHERE stage='ingest' ORDER BY 1").fetchall()==rows
        assert conn.execute('SELECT revision_id,payload FROM discovery.revisions ORDER BY 1').fetchall()==before
        health=json.loads((directory/'health.json').read_text())
        assert health['latest_failed_or_partial']['status']=='partial'
        assert health['provider_requests']==health['model_requests']==0
