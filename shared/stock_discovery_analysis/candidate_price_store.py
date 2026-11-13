"""STK-014: candidate refresh jobs in existing D3-04 durable storage."""
from datetime import timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import digest
from .scheduling import utc, stamp
from .schedule_store import finish, fenced_row

VERSION='candidate-price-refresh-v1'


def enqueue(conn, config_hash, symbols, day, now, target_session=None):
    ids=[]
    with conn.transaction():
        for symbol in sorted(set(symbols)):
            payload=dict(code_version=VERSION,schedule_hash=config_hash,symbol=symbol,
                         refresh_day=day,target_session=target_session,scope_id=VERSION,mode='live_paper')
            jid=digest(payload)
            conn.execute('INSERT INTO discovery.occurrences VALUES (%s,%s) ON CONFLICT DO NOTHING',
                         (jid,Jsonb(dict(occurrence_id=jid,kind=VERSION,**payload))))
            conn.execute('''INSERT INTO discovery.schedule_jobs
                (job_id,occurrence_id,stage,priority,payload,status,due_at,updated_at)
                VALUES (%s,%s,'ingest',2,%s,'queued',%s,%s) ON CONFLICT DO NOTHING''',
                (jid,jid,Jsonb(payload),now,now))
            ids.append(jid)
    return ids



def supersede(conn, config_hash, day, now):
    # Current observation jobs are not historical requests. A missed day is never
    # relabelled as its original session; today's candidate set gets today's jobs.
    conn.execute("""UPDATE discovery.schedule_jobs SET status='missed',error_code='refresh_day_elapsed',
        token=NULL,lease_until=NULL,updated_at=%s WHERE payload->>'code_version'=%s
        AND payload->>'schedule_hash'=%s AND payload->>'refresh_day'<%s
        AND status IN ('queued','running','retry_wait')""",(now,VERSION,config_hash,day))


def claim(conn, config_hash, now):
    # Caller holds the existing account session lock. Never maintain other queues.
    with conn.transaction():
        conn.execute('''UPDATE discovery.schedule_jobs SET status='failed',error_code='retry_exhausted',
            token=NULL,lease_until=NULL,updated_at=%s WHERE payload->>'schedule_hash'=%s
            AND payload->>'code_version'=%s AND status='running' AND lease_until<=%s AND attempts>=3''',
            (now,config_hash,VERSION,now))
        row=conn.execute('''SELECT job_id,payload,attempts FROM discovery.schedule_jobs
            WHERE payload->>'code_version'=%s AND payload->>'schedule_hash'=%s AND attempts<3
            AND ((status IN ('queued','retry_wait') AND due_at<=%s) OR (status='running' AND lease_until<=%s))
            ORDER BY due_at,job_id FOR UPDATE SKIP LOCKED LIMIT 1''',(VERSION,config_hash,now,now)).fetchone()
        if row is None:return None
        jid,payload,attempts=row;token=str(uuid4());until=stamp(utc(now)+timedelta(seconds=900))
        conn.execute('''UPDATE discovery.schedule_jobs SET status='running',attempts=attempts+1,
            token=%s,lease_until=%s,updated_at=%s WHERE job_id=%s''',(token,until,now,jid))
        return dict(job_id=jid,payload=payload,token=token,attempts=attempts+1)


def complete(conn, job, result, scanner_keys, since, now):
    # Receipt and re-analysis trigger commit together; replay cannot reset twice.
    with conn.transaction():
        fenced_row(conn,job,now)
        conn.execute('''UPDATE discovery.candidates SET research_status='pending',attempts=0,
            retry_at=%s,error_code=NULL,result=NULL WHERE symbol=%s AND scanner_key=ANY(%s)
            AND session_date>=%s AND first_observed_at<=%s''',(now,job['payload']['symbol'],list(scanner_keys),since,now))
        finish(conn,job,now,status='completed',result=result)


def status(conn, config_hash):
    return dict(conn.execute('''SELECT status,count(*) FROM discovery.schedule_jobs
        WHERE payload->>'code_version'=%s AND payload->>'schedule_hash'=%s GROUP BY status''',
        (VERSION,config_hash)).fetchall())
