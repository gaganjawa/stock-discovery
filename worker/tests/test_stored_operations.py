"""STK-086 offline deployment/lifecycle tests; no providers or services."""
import json
import os
from pathlib import Path
import pytest
from stock_discovery_analysis.calendar_lifecycle import lifecycle
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.scheduling import ScheduleConfig
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.daily_insight import LISTING
from stock_discovery_contracts.v2 import digest
from worker import stored_operations as ops


@pytest.mark.parametrize('now,end,state,reason',[
    ('2026-10-15T09:00:00Z','2026-10-31','valid',None),
    ('2026-10-15T09:00:00Z','2026-10-19','expiring_soon',None),
    ('2026-10-19T02:00:00Z','2026-10-31','blocked','next_execution_opening_unverified'),
    ('2026-10-19T11:00:00Z','2026-10-31','blocked','next_execution_unverified'),
    ('2026-11-01T00:00:00Z','2026-10-31','expired','calendar_expired'),
])
def test_calendar_lifecycle_never_extends_or_infers(now,end,state,reason):
    raw=fixture_config().model_dump();raw['calendar']['ends_on']=end
    schedule=ScheduleConfig.model_validate(raw);before=schedule.model_dump()
    result=lifecycle(schedule,now)
    assert result['state']==state
    if reason:assert reason in result['reasons']
    assert result['renewal']['status']=='RENEWAL_BLOCKED'
    assert result['renewal']['provider_requests']==0
    assert schedule.model_dump()==before


def files(tmp_path,monkeypatch):
    root=tmp_path/'deploy';root.mkdir(mode=0o700)
    repo=tmp_path/'repo';(repo/'worker/worker').mkdir(parents=True)
    (repo/'worker/worker/main.py').write_text(ops.ENV)
    python=tmp_path/'python';python.write_text('test');python.chmod(0o700)
    db=tmp_path/'db';db.write_text('test-secret');db.chmod(0o600)
    grant=tmp_path/'grants';grant.write_text('[]');grant.chmod(0o600)
    view=ViewConfig(sources=SourceConfig(grant_file=str(grant),retention_days=30),
        listing_ids=(LISTING,),pilot_scope_id='STK-083-INFY-test')
    raw=fixture_config().model_dump();raw.update(code_version='a'*40,mode='live_paper',scope_id=view.pilot_scope_id,
        input_hash=digest(view.model_dump(mode='json')),horizons=('swing',))
    schedule=ScheduleConfig.model_validate(raw)
    monkeypatch.setattr(ops,'git',lambda repo,*args:'a'*40 if args[0]=='rev-parse' else '')
    data=ops.deployment(repo,python,db,view,schedule,root)
    for name,obj in [('deployment.json',data),('view.json',view.model_dump(mode='json')),('schedule.json',schedule.model_dump(mode='json'))]:
        path=root/name;path.write_text(json.dumps(obj));path.chmod(0o600)
    return root/'deployment.json',data


def test_deployment_hashes_and_secret_references(tmp_path,monkeypatch):
    path,data=files(tmp_path,monkeypatch)
    assert ops.validate_deployment(path)[0]==data
    assert 'test-secret' not in path.read_text()
    view=Path(data['view_file']);v=json.loads(view.read_text());v['descriptive_freshness_policy']='one_trailing_session_v1';view.write_text(json.dumps(v))
    with pytest.raises(ValueError,match='configuration_mismatch'):ops.validate_deployment(path)


@pytest.mark.parametrize('change,reason',[
    ('sha','code_mismatch'),('dirty','code_dirty'),('permissions','file_permissions'),
    ('missing_runtime','runtime_preflight_missing'),('enabled','execution_mode_required')])
def test_stale_or_unsafe_deployment_rejected(tmp_path,monkeypatch,change,reason):
    path,data=files(tmp_path,monkeypatch)
    if change=='sha':monkeypatch.setattr(ops,'git',lambda *a:'b'*40)
    if change=='dirty':monkeypatch.setattr(ops,'git',lambda repo,*a:'a'*40 if a[0]=='rev-parse' else ' M worker.py')
    if change=='permissions':Path(data['database_file']).chmod(0o644)
    if change=='missing_runtime':(Path(data['repo'])/'worker/worker/main.py').write_text('legacy')
    if change=='enabled':data['acquisition']='enabled';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match=reason):ops.validate_deployment(path)


def test_unmerged_code_is_not_activation_ready(tmp_path,monkeypatch):
    path,data=files(tmp_path,monkeypatch)
    monkeypatch.setattr(ops,'git',lambda repo,*a:'a'*40 if a[0] in ('rev-parse','rev-list') else '')
    assert ops.check_deployment(path)['reasons']==['deployment_code_not_merged']


@pytest.mark.parametrize('pages',[
    [],[('',None,True,1)],[('orphan',None,True,0)],
    [('', 'missing',False,0)],[('', '',False,0)],
    [('',None,False,0)],[('',None,True,0),('extra',None,True,0)]])
def test_incomplete_or_conflicting_pages_block(pages):
    with pytest.raises(ops.CalendarEvidenceError):ops.complete_pages(pages)


def test_complete_page_chain():
    ops.complete_pages([('', 'second',False,0),('second',None,True,0)])


def test_blocked_worker_writes_private_health_without_tick(tmp_path,monkeypatch):
    import stock_discovery_analysis.schedule_runner as runner
    path,data=files(tmp_path,monkeypatch)
    # A changed executable tree fails before connecting or claiming a job.
    monkeypatch.setattr(ops,'git',lambda *a:'changed')
    monkeypatch.setattr(runner,'tick',lambda *a,**k:pytest.fail('scheduler must not run'))
    result=ops.cycle(path,None,None,'unused','unused','must-not-connect',{},clock=lambda:'2026-10-15T00:00:00Z')
    assert result['status']=='BLOCKED'
    health=path.parent/'health.json'
    assert health.stat().st_mode&0o777==0o600
    assert 'must-not-connect' not in health.read_text()
    assert result['provider_requests']==result['model_requests']==0
