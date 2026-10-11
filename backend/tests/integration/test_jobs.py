import os
import pytest
import psycopg
from stock_discovery_analysis.jobs import enqueue,run_job
URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated database')


def test_job_idempotency_failure_and_retry():
    assert URL.rsplit('/',1)[-1]=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as db:
        key=enqueue(db,'ingest',{'fixture_version':'test'})
        assert enqueue(db,'ingest',{'fixture_version':'test'})==key
        result=run_job(db,'test')
        # Repeat test invocations preserve completed jobs.
        if result: assert result['status']=='completed'
        assert db.execute('SELECT status FROM research.jobs WHERE job_id=%s',(key,)).fetchone()[0]=='completed'
        bad=enqueue(db,'replay',{'dataset_version':'does-not-exist'})
        for _ in range(3):
            db.execute("UPDATE research.jobs SET next_attempt_at=now() WHERE job_id=%s",(bad,))
            run_job(db,'test')
        state=db.execute('SELECT status,attempts,error_code FROM research.jobs WHERE job_id=%s',(bad,)).fetchone()
        assert state==('failed',3,'KeyError')
        assert run_job(db,'test') is None
