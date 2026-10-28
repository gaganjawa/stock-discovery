import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
import psycopg
from psycopg import sql
from stock_discovery_analysis.jobs import enqueue,run_job
URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated database')


@pytest.fixture
def db():
    # Each test owns its database; deterministic job IDs must never reuse a
    # previous invocation's completed jobs or another test's pending work.
    info=psycopg.conninfo.conninfo_to_dict(URL)
    assert info['dbname']=='stk013_test'
    name='stk013_test_jobs_'+uuid4().hex
    owner=psycopg.conninfo.make_conninfo(URL,dbname='postgres')
    uri=psycopg.conninfo.make_conninfo(URL,dbname=name)
    with psycopg.connect(owner,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        from sqlalchemy.engine import URL as DatabaseURL
        migration_url=DatabaseURL.create('postgresql',username=info.get('user'),password=info.get('password'),
            host=info.get('host'),port=int(info['port']) if info.get('port') else None,database=name).render_as_string(hide_password=False)
        env={**os.environ,'DATABASE_URL':migration_url}
        env.pop('DATABASE_URL_FILE',None)
        subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],
            cwd=Path(__file__).resolve().parents[3],env=env,check=True,capture_output=True)
        with psycopg.connect(uri,autocommit=True) as conn:
            yield conn
    finally:
        # Only the UUID database successfully created above is eligible for cleanup.
        with psycopg.connect(owner,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


def test_job_idempotency_failure_and_retry(db):
    key=enqueue(db,'ingest',{'fixture_version':'test'})
    assert enqueue(db,'ingest',{'fixture_version':'test'})==key
    result=run_job(db,'test')
    assert result['status']=='completed'
    assert db.execute('SELECT status FROM research.jobs WHERE job_id=%s',(key,)).fetchone()[0]=='completed'
    bad=enqueue(db,'replay',{'dataset_version':'does-not-exist'})
    for _ in range(3):
        db.execute("UPDATE research.jobs SET next_attempt_at=now() WHERE job_id=%s",(bad,))
        run_job(db,'test')
    state=db.execute('SELECT status,attempts,error_code FROM research.jobs WHERE job_id=%s',(bad,)).fetchone()
    assert state==('failed',3,'KeyError')
    from app.research import job_detail, export
    detail=job_detail(bad,db)
    assert detail['status']=='failed' and detail['error_code']=='KeyError'
    assert detail['payload']['dataset_version']=='does-not-exist'
    assert next(j for j in export(db)['jobs'] if j['job_id']==bad)==detail
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as missing:
        job_detail('unknown-job',db)
    assert missing.value.status_code==404
    assert run_job(db,'test') is None


def test_versioned_experiments_preserve_old_results_and_reject_wrong_worker(monkeypatch,db):
    from app.research import Batch, experiments, job_detail
    from stock_discovery_analysis.dataset import demo_dataset
    from stock_discovery_analysis.storage import ingest
    from stock_discovery_analysis.service import read_frozen
    d=demo_dataset()
    ingest(db,d)
    body=Batch(dataset_version=d.version,dates=[d.calendar.sessions[39].closes_at.date().isoformat()])
    monkeypatch.setenv('CODE_VERSION','revision-a')
    first=experiments(body,db)['job_ids']
    assert experiments(body,db)['job_ids']==first
    for _ in first: run_job(db,'revision-a')
    originals=[job_detail(j,db) for j in first]
    assert all(j['status']=='completed' for j in originals)
    monkeypatch.setenv('CODE_VERSION','revision-b')
    second=experiments(body,db)['job_ids']
    assert set(first).isdisjoint(second)
    wrong=run_job(db,'revision-a')
    assert wrong['error_code']=='ExecutionVersionMismatch'
    assert job_detail(wrong['job_id'],db)['result'] is None
    db.execute("UPDATE research.jobs SET next_attempt_at=now() WHERE job_id=ANY(%s)",(second,))
    for _ in second: run_job(db,'revision-b')
    for jid in second:
        job=job_detail(jid,db)
        assert job['status']=='completed'
        for rid in job['result']['recommendation_ids']:
            assert read_frozen(db,rid)['recommendation']['versions']['code']=='revision-b'
    assert [job_detail(j,db) for j in first]==originals
