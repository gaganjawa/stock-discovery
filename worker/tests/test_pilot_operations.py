import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from worker.pilot_operations import singleton, atomic, Operations, next_occurrence
from stock_discovery_analysis.schedule_fixtures import fixture_config


def test_singleton_prevents_duplicate_even_without_same_state_directory():
    with singleton('unit-operations'):
        with pytest.raises(RuntimeError,match='already_running'):singleton('unit-operations')
    with singleton('unit-operations'):pass


def test_atomic_private_state_and_next_completed_session(tmp_path):
    p=tmp_path/'state.json';atomic(p,{'ok':True})
    assert json.loads(p.read_text())=={'ok':True} and p.stat().st_mode&0o077==0
    c=fixture_config();n=next_occurrence(c,c.calendar.available_at)
    assert n is not None
    assert next_occurrence(c,'2027-01-01T00:00:00Z') is None


def test_log_cleanup_only_owned_diagnostics(tmp_path):
    tmp_path.chmod(0o700);c=fixture_config()
    ops=Operations(tmp_path,c,None,clock=lambda:c.calendar.available_at)
    original=tmp_path/'original-document.json';original.write_text('never delete')
    for _ in range(6):
        (tmp_path/'operations.jsonl').write_text('x'*(256*1024+1));ops.event('rotation')
    assert original.read_text()=='never delete'
    assert len(list(tmp_path.glob('operations.*.jsonl')))==3
    assert not (tmp_path/'operations.4.jsonl').exists()


def test_operations_refuses_wrong_scope_and_insecure_directory(tmp_path):
    tmp_path.chmod(0o755)
    with pytest.raises(ValueError,match='private_operations'):Operations(tmp_path,fixture_config(),None)
    tmp_path.chmod(0o700);c=fixture_config();saved=c.model_dump(mode='json');saved['scope_id']='different'
    atomic(tmp_path/'schedule.json',saved)
    with pytest.raises(ValueError,match='configuration_mismatch'):Operations(tmp_path,c,None)


def test_calendar_failure_keeps_previous_file_and_persists_retry(tmp_path,monkeypatch):
    from worker import pilot_operations as module
    tmp_path.chmod(0o700);c=fixture_config();clock=lambda:c.calendar.available_at
    grant=NS(retention_days=30)
    access=NS(load_grant=lambda s:grant,require=lambda *a:None)
    monkeypatch.setattr(module,'cleanup_plan',lambda *a:None)
    monkeypatch.setattr(module,'access_for',lambda *a:access)
    monkeypatch.setattr(module,'renew_calendar',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('provider_unavailable')))
    class DB:
        def execute(self,sql,*args):return NS(fetchone=lambda:(1000 if 'pg_database_size' in sql else None,))
    pilot=NS(market=NS(account_ref='test'))
    ops=Operations(tmp_path,c,pilot,clock=clock)
    with pytest.raises(RuntimeError):ops.preflight(DB())
    assert ops.schedule==c and not (tmp_path/'schedule.json').exists()
    assert ops.read('health.json',{})['calendar_retry_at']
    with pytest.raises(ValueError,match='calendar_refresh_required'):ops.preflight(DB())


def test_revocation_stops_before_provider_or_original_deletion(tmp_path,monkeypatch):
    from worker import pilot_operations as module
    tmp_path.chmod(0o700);c=fixture_config()
    original=tmp_path/'original.json';original.write_text('preserve')
    monkeypatch.setattr(module,'access_for',lambda *a:NS(load_grant=lambda s:None))
    class DB:
        def execute(self,*a):return NS(fetchone=lambda:(1000,))
    ops=Operations(tmp_path,c,NS(market=NS(account_ref='test')),clock=lambda:c.calendar.available_at)
    with pytest.raises(PermissionError,match='retention_review'):ops.preflight(DB())
    assert original.read_text()=='preserve' and ops.state['retention']['original_data_deleted'] is False


def test_sleep_or_pause_gap_is_reported(tmp_path,monkeypatch):
    from worker import pilot_operations as module
    tmp_path.chmod(0o700);c=fixture_config();ops=Operations(tmp_path,c,None,clock=lambda:c.calendar.available_at)
    ops.last-=600
    class DB:
        def execute(self,*a):return NS(fetchone=lambda:(3*1024**3,))
    with pytest.raises(ValueError,match='resource_high_water_stop'):ops.preflight(DB())
    assert ops.state['last_resume_gap_seconds']>=600
