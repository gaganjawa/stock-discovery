"""One PostgreSQL-backed worker; idempotent operations and bounded retry leases."""
import hashlib
import uuid
from datetime import timedelta
from psycopg.types.json import Jsonb
from .dataset import canonical,demo_dataset
from .storage import ingest
from .service import freeze,reveal,json_value,load_dataset
from .replay import dt
from .strategy import STRATEGY_VERSION, CONFIG_VERSION


class ExecutionVersionMismatch(ValueError):
    pass


def execution_versions(code_version):
    return dict(code_version=code_version,strategy_version=STRATEGY_VERSION,config_version=CONFIG_VERSION)


def enqueue(conn,kind,payload):
    if kind not in ('ingest','scan','replay'): raise ValueError('unknown job kind')
    key='JOB-'+hashlib.sha256(canonical([kind,payload]).encode()).hexdigest()
    conn.execute('INSERT INTO research.jobs(job_id,kind,payload) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                 (key,kind,Jsonb(payload)))
    return key


def run_job(conn,code_version):
    # A session lock prevents a second worker reclaiming a long-running job
    # merely because its persisted recovery lease expired. A crash releases it.
    if not conn.execute("SELECT pg_try_advisory_lock(170017)").fetchone()[0]:
        return None
    try:
        return _run_job(conn,code_version)
    finally:
        conn.execute("SELECT pg_advisory_unlock(170017)")


def _run_job(conn,code_version):
    token=str(uuid.uuid4())
    with conn.transaction():
        conn.execute("""UPDATE research.jobs SET status='failed',error_code='retry_exhausted',updated_at=now()
            WHERE status='running' AND lease_until<now() AND attempts>=3""")
        row=conn.execute("""SELECT job_id,kind,payload FROM research.jobs WHERE attempts<3 AND
            ((status='queued' AND next_attempt_at<=now()) OR (status='running' AND lease_until<now()))
            ORDER BY CASE WHEN kind='ingest' THEN 0 ELSE 1 END,created_at
            FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if row is None: return None
        jid,kind,payload=row
        conn.execute("""UPDATE research.jobs SET status='running',attempts=attempts+1,
            lease_until=now()+interval '5 minutes',lease_token=%s,updated_at=now() WHERE job_id=%s""",(token,jid))
    try:
        if kind=='ingest':
            result={'dataset_version':ingest(conn,demo_dataset())}
        else:
            if any(payload.get(key, value)!=value for key,value in execution_versions(code_version).items()):
                raise ExecutionVersionMismatch('Queued execution versions do not match this worker')
            d=load_dataset(conn,payload['dataset_version'])
            cutoff=dt(payload['cutoff'])
            instruments=[payload['instrument_id']] if kind=='replay' else [i.instrument_id for i in d.instruments]
            recs=[]
            for instrument in instruments:
                a=freeze(conn,d,instrument,cutoff,code_version)
                rid=a['recommendation']['recommendation_id']; recs.append(rid)
                if kind=='replay': reveal(conn,rid)
            result={'recommendation_ids':recs}
        with conn.transaction():
            conn.execute("""UPDATE research.jobs SET status='completed',result=%s,lease_until=NULL,
                updated_at=now(),error_code=NULL WHERE job_id=%s AND lease_token=%s""",(Jsonb(json_value(result)),jid,token))
    except Exception as exc:
        with conn.transaction():
            conn.execute("""UPDATE research.jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'queued' END,
                next_attempt_at=now()+attempts*interval '10 seconds',lease_until=NULL,
                error_code=%s,updated_at=now() WHERE job_id=%s AND lease_token=%s""",(type(exc).__name__,jid,token))
        return {'job_id':jid,'status':'retry_or_failed','error_code':type(exc).__name__}
    return {'job_id':jid,'status':'completed','result':result}
