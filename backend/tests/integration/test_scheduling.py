import json
import os
from datetime import timedelta
import psycopg
import pytest

from stock_discovery_analysis.schedule_fixtures import fixture_config, handlers
from stock_discovery_analysis.scheduling import Coverage, resolve_occurrences, stamp, utc
from stock_discovery_analysis.schedule_store import (StaleLease, claim, enqueue, finish, materialize,
    operations, put_occurrence, resume_blocked, retry)
from stock_discovery_analysis.schedule_runner import tick, JobFailure

URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated PostgreSQL')
NOW='2026-10-15T12:00:00Z'


@pytest.fixture
def db():
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname']=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            yield conn


def setup(conn):
    c=fixture_config()
    slot=resolve_occurrences(c,NOW)[0]
    jid=materialize(conn,(slot,),NOW)[0]
    return c,slot,jid


def test_idempotent_dependency_and_atomic_outbox(db):
    c,slot,jid=setup(db)
    assert materialize(db,(slot,),NOW)==(jid,)
    job=claim(db,NOW,c.code_version)
    with pytest.raises(RuntimeError):
        with db.transaction():
            finish(db,job,NOW,status='completed',result={'ready':True},next_stage='snapshot')
            raise RuntimeError('crash before commit')
    assert db.execute('SELECT count(*) FROM discovery.schedule_outbox').fetchone()[0]==0
    finish(db,job,NOW,status='completed',result={'ready':True},next_stage='snapshot')
    assert claim(db,NOW,c.code_version)['stage']=='snapshot'
    assert db.execute('SELECT count(*) FROM discovery.schedule_outbox').fetchone()[0]==1
    with pytest.raises(StaleLease):
        finish(db,job,NOW,status='completed',result={})


def test_crash_reclaim_fencing_and_max_attempts(db):
    c,_,_=setup(db)
    first=claim(db,NOW,c.code_version,lease_seconds=1)
    later=stamp(utc(NOW)+timedelta(seconds=2))
    second=claim(db,later,c.code_version,lease_seconds=1)
    with pytest.raises(StaleLease):
        finish(db,first,later,status='completed',result={})
    third=claim(db,stamp(utc(NOW)+timedelta(seconds=4)),c.code_version,lease_seconds=1)
    assert third['attempts']==3 and second['attempts']==2
    assert claim(db,stamp(utc(NOW)+timedelta(seconds=6)),c.code_version) is None
    assert db.execute('SELECT status FROM discovery.schedule_jobs').fetchone()[0]=='failed'


@pytest.mark.parametrize('reason',['rights','credentials','budget','policy','ambiguous_billing'])
def test_blocks_do_not_retry_without_resolution(db,reason):
    c,_,jid=setup(db)
    job=claim(db,NOW,c.code_version)
    assert retry(db,job,NOW,reason=reason)=='blocked'
    assert claim(db,NOW,c.code_version) is None
    with pytest.raises(ValueError):
        resume_blocked(db,jid,NOW,'')
    resume_blocked(db,jid,NOW,'fixture://resolution')
    assert claim(db,NOW,c.code_version)['job_id']==jid


@pytest.mark.parametrize('reason,seconds',[('transient',1200),('readiness',900)])
def test_backoff_respects_retry_after(db,reason,seconds):
    c,_,_=setup(db)
    job=claim(db,NOW,c.code_version)
    assert retry(db,job,NOW,reason=reason,retry_after_seconds=seconds)=='retry_wait'
    assert claim(db,stamp(utc(NOW)+timedelta(seconds=seconds-1)),c.code_version) is None
    assert claim(db,stamp(utc(NOW)+timedelta(seconds=seconds)),c.code_version)['attempts']==2


def test_missed_forward_window_is_historical(db):
    c=fixture_config().model_copy(update={'mode':'live_paper'})
    slot=resolve_occurrences(c,NOW)[0]
    materialize(db,(slot,),NOW)
    late='2026-10-16T03:00:00Z'
    materialize(db,(slot,),late)
    job=claim(db,late,c.code_version)
    assert job['payload']['mode']=='historical_reconstructed' and job['payload']['catch_up']
    assert db.execute("SELECT count(*) FROM discovery.schedule_jobs WHERE status='missed'").fetchone()[0]==1


def test_safety_priority_and_code_scope(db):
    c,slot,_=setup(db)
    enqueue(db,slot,'outcome',NOW)
    enqueue(db,slot,'replay',NOW)
    enqueue(db,slot,'reassess',NOW)
    assert claim(db,NOW,'other-code') is None
    assert claim(db,NOW,c.code_version)['stage']=='reassess'
    assert claim(db,NOW,c.code_version)['stage']=='outcome'
    assert claim(db,NOW,c.code_version)['stage']=='ingest'
    assert claim(db,NOW,c.code_version)['stage']=='replay'


def test_unattended_fixture_pipeline_and_last_complete(db):
    c=fixture_config()
    for _ in range(12):
        tick(db,c,clock=lambda:NOW,handlers=handlers(c))
    report=operations(db,NOW,scope_id=c.scope_id,mode='synthetic',horizon='swing')
    assert report['last_complete']['coverage']['universe_total']==1
    assert report['last_complete']['input_age_seconds']==7200
    later='2026-10-16T12:00:00Z'
    # Unconfigured next-day jobs block; prior complete result remains visible.
    for _ in range(8):
        tick(db,c,clock=lambda:later)
    report=operations(db,later,scope_id=c.scope_id,mode='synthetic',horizon='swing')
    assert report['last_complete']['age_seconds']==86400
    assert report['counts']['blocked']>=1
    assert operations(db,later,scope_id=c.scope_id,mode='live_paper',horizon='swing')['last_complete'] is None


def test_slow_handler_cannot_publish(db):
    c,_,_=setup(db)
    # Direct finish simulates a handler returning after its lease.
    job=claim(db,NOW,c.code_version)
    with pytest.raises(StaleLease):
        finish(db,job,'2026-10-15T12:03:00Z',status='completed',result={})
    assert db.execute('SELECT count(*) FROM discovery.schedule_outbox').fetchone()[0]==0


def test_event_dedup_coalescing_adverse_pause_and_universe_guard(db):
    from stock_discovery_analysis.schedule_events import MaterialEvent, nominate, admission_paused
    from stock_discovery_analysis.revision_storage import read_snapshot
    from stock_discovery_analysis.revision_fixtures import fixture_grant, fixture_request, fixture_stream
    from stock_discovery_analysis.schedule_fixtures import SCOPES
    c,_,_=setup(db)
    installed=handlers(c)
    for stage in ('ingest','snapshot','screen'):
        job=claim(db,NOW,c.code_version)
        result,next_stage=installed[stage](db,job,lambda:NOW)
        finish(db,job,NOW,status='completed',result=result,next_stage=next_stage)
    sid=result['snapshot_id']
    def read():
        return read_snapshot(db,sid,load_grant=lambda s:fixture_grant(),
            requests={fixture_stream(s).stream_id:fixture_request(s,requested_at=NOW) for s in SCOPES},audit=lambda d:None)
    event=MaterialEvent(listing_id='SYN-listing',source_revision_id='SYN-doc',event_type='earnings',observed_at=NOW)
    jobids=nominate(db,c,(event,),NOW,read_authorized_snapshot=read)
    assert len(jobids)==1
    assert nominate(db,c,(event,),NOW,read_authorized_snapshot=read)==()
    adverse=event.model_copy(update={'event_type':'restatement'})
    assert nominate(db,c,(adverse,),NOW,read_authorized_snapshot=read)==jobids
    assert admission_paused(db,'SYN-listing')
    assert db.execute('SELECT count(*) FROM discovery.material_events WHERE job_id=%s',jobids).fetchone()[0]==2
    assert claim(db,NOW,c.code_version)['stage']=='reassess'
    # New source event while earlier work is running cannot disappear into that work.
    third=event.model_copy(update={'event_type':'default'})
    assert nominate(db,c,(third,),NOW,read_authorized_snapshot=read)!=jobids
    for invalid in (event.model_copy(update={'listing_id':'SYN-outsider'}),
                    event.model_copy(update={'source_revision_id':'missing'}),
                    event.model_copy(update={'observed_at':'2027-01-01T00:00:00Z'})):
        with pytest.raises(ValueError):
            nominate(db,c,(invalid,),NOW,read_authorized_snapshot=read)
    with pytest.raises(ValueError,match='limit'):
        nominate(db,c,(event,)*21,NOW,read_authorized_snapshot=read)
    def denied():
        raise PermissionError('revoked')
    with pytest.raises(PermissionError):
        nominate(db,c,(third,),NOW,read_authorized_snapshot=denied)


def test_incomplete_screen_cannot_publish(db):
    c,slot,_=setup(db)
    enqueue(db,slot,'screen',NOW)
    # Ingest is claimed first, screen then; incomplete totals must not publish no-picks.
    claim(db,NOW,c.code_version)
    job=claim(db,NOW,c.code_version)
    cov=dict(universe_total=1,ineligible=0,eligible=1,screened=0,unscreened=1,candidate=0,noncandidate=0,
        research_complete=0,research_pending=0,research_failed=0,research_not_selected=0,data_complete=0,exclusion_reasons=[])
    with pytest.raises(ValueError,match='incomplete'):
        finish(db,job,NOW,status='completed',result={'coverage':cov})


def test_handler_writes_rollback_with_failed_completion(db):
    c,_,_=setup(db)
    # Tick prioritizes a due event poll. A failed handler must leave no checkpoint write.
    def broken(conn,job,clock):
        conn.execute("INSERT INTO discovery.schedule_cursors VALUES ('handler-sentinel',%s)",(NOW,))
        raise JobFailure('transient')
    result=tick(db,c,clock=lambda:NOW,handlers={'event_poll':broken})
    assert result['status']=='retry_wait'
    assert db.execute("SELECT 1 FROM discovery.schedule_cursors WHERE schedule_hash='handler-sentinel'").fetchone() is None
