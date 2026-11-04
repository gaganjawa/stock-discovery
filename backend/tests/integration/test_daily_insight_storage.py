"""STK-083 disposable stored research; no real provider/model calls."""
import os,uuid
import psycopg,pytest
from test_adjusted_research_storage import setup,isolated_url,NOW
from stock_discovery_analysis.daily_insight import research,LISTING
from stock_discovery_analysis.grant_fences import restrict
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.scheduling import ScheduleConfig,resolve_occurrences
from stock_discovery_analysis.schedule_store import materialize
from stock_discovery_analysis.schedule_runner import tick
from stock_discovery_contracts.v2 import digest
from worker.stored_research import handlers
pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def cfg(conn,tmp_path,**kw):
 v,l=setup(conn,tmp_path,**kw)
 return v.model_copy(update={'descriptive_freshness_policy':'one_trailing_session_v1','pilot_scope_id':'STK-083-INFY-test'}),l


@pytest.mark.parametrize('lag,mixed,available',[(0,False,True),(1,False,True),(2,False,False),(0,True,False)])
def test_guarded_report(isolated_url,tmp_path,lag,mixed,available,monkeypatch):
 from worker.providers.upstox import Upstox
 def forbidden(*a,**kw):raise AssertionError('provider call forbidden')
 monkeypatch.setattr(Upstox,'_get',forbidden)
 with psycopg.connect(isolated_url,autocommit=True) as c:
  v,l=cfg(c,tmp_path,lag=lag,mixed=mixed)
  before=c.execute('select revision_id,payload from discovery.revisions order by revision_id').fetchall()
  r=research(c,v,l,clock=lambda:NOW)
  assert (r['state'] in ('current_descriptive','delayed_descriptive'))==available
  assert r['ai']['status']=='AI_RESEARCH_UNAVAILABLE'
  assert not r['actionable'] and not r['paper_admission_authorized']
  assert r['automation']['latest_successful_analysis_at'] is None
  assert c.execute('select revision_id,payload from discovery.revisions order by revision_id').fetchall()==before
  restrict(c,request_id=uuid.uuid4(),kind='provider',source_id='upstox',reason='revoked')
  with pytest.raises(PermissionError):research(c,v,l,clock=lambda:NOW)


def schedule(v):
 raw=fixture_config().model_dump()
 raw['calendar']['sessions']+=({'opens_at':'2026-10-20T03:45:00Z','closes_at':'2026-10-20T10:00:00Z'},)
 raw['calendar']['ref']['content_hash']=digest(list(raw['calendar']['sessions']))
 raw.update(mode='live_paper',scope_id=v.pilot_scope_id,input_hash=digest(v.model_dump(mode='json')),horizons=('swing',),starts_on='2026-10-16')
 return ScheduleConfig.model_validate(raw)


def test_scheduled_idempotent_stored_analysis_and_missed_run(isolated_url,tmp_path):
 with psycopg.connect(isolated_url,autocommit=True) as c:
  v,l=cfg(c,tmp_path,lag=1);s=schedule(v)
  # Oct16 post-market window has expired at Oct19 noon: catch-up remains descriptive NOW.
  materialize(c,resolve_occurrences(s,NOW),NOW)
  h=handlers(s,v)
  for _ in range(4):tick(c,s,clock=lambda:NOW,handlers=h)
  rows=c.execute("select result from discovery.schedule_jobs where stage='ingest' and status='completed'").fetchall()
  assert len(rows)==2 and any(r[0]['catch_up'] for r in rows)
  assert rows[0][0]['evaluated_at']==NOW
  assert rows[0][0]['acquisition']['provider_requests']==0 and rows[0][0]['model_requests']==0
  assert all(r[0]['original_scheduled_cutoff']!=NOW for r in rows)
  for _ in range(2):tick(c,s,clock=lambda:NOW,handlers=h)
  assert c.execute("select count(*) from discovery.schedule_jobs where stage='ingest' and status='completed'").fetchone()[0]==2
  r=research(c,v,l,clock=lambda:NOW)
  assert r['automation']['latest_successful_analysis_at']==NOW
  assert r['changes_since_scheduled_run']=='evidence_unchanged'


def test_failure_is_durable_and_not_retried_unbounded(isolated_url,tmp_path,monkeypatch):
 import worker.stored_research as module
 with psycopg.connect(isolated_url,autocommit=True) as c:
  v,l=cfg(c,tmp_path);s=schedule(v)
  def fail(*a,**kw):raise RuntimeError('simulated processing failure')
  monkeypatch.setattr(module,'research',fail)
  for _ in range(4):tick(c,s,clock=lambda:NOW,handlers=handlers(s,v))
  assert c.execute("select status,error_code,attempts from discovery.schedule_jobs where stage='ingest'").fetchall()==[('failed','permanent',1)]*2



def test_navigation_reads_only_and_denial_clears_api(isolated_url,tmp_path,monkeypatch):
 import httpx
 from fastapi.testclient import TestClient
 from app.main import app
 from app import real_research as routes,research as legacy
 from worker.providers.ollama import Ollama
 original=httpx.Client.send
 def send(self,request,*a,**kw):
  assert request.url.host=='testserver','unexpected provider request'
  return original(self,request,*a,**kw)
 monkeypatch.setattr(httpx.Client,'send',send)
 def no_model(*a,**kw):raise AssertionError('model execution forbidden')
 monkeypatch.setattr(Ollama,'__init__',no_model)
 monkeypatch.setenv('AUTH_TOKEN','test-only-'+'x'*40)
 monkeypatch.delenv('AUTH_TOKEN_FILE',raising=False)
 with psycopg.connect(isolated_url,autocommit=True) as c:
  v,l=cfg(c,tmp_path,lag=1);monkeypatch.setattr(routes,'view_config',lambda:v)
  app.dependency_overrides[legacy.db]=lambda:c
  try:
   client=TestClient(app);headers={'Authorization':'Bearer '+'test-only-'+'x'*40}
   r=client.get('/v1/real-research/companies/'+l+'/insight',headers=headers)
   assert r.status_code==200 and r.json()['state']=='delayed_descriptive'
   assert r.headers['cache-control']=='no-store'
   restrict(c,request_id=uuid.uuid4(),kind='provider',source_id='upstox',reason='revoked')
   r=client.get('/v1/real-research/companies/'+l+'/insight',headers=headers)
   assert r.status_code==403 and 'technical' not in r.json()
  finally:app.dependency_overrides.clear()
