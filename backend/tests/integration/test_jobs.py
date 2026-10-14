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


def test_versioned_experiments_preserve_old_results_and_reject_wrong_worker(monkeypatch):
    from app.research import Batch, experiments, job_detail
    from stock_discovery_analysis.dataset import demo_dataset
    from stock_discovery_analysis.storage import ingest
    from stock_discovery_analysis.service import read_frozen
    assert URL.rsplit('/',1)[-1]=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as db:
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
