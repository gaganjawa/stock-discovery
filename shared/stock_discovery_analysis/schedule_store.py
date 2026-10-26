"""D3-04 durable scheduler. Trusted worker supplies clocks and validated outputs."""
from datetime import timedelta
import uuid
import json

from psycopg.types.json import Jsonb

from stock_discovery_contracts.v2 import check, digest
from .scheduling import Coverage, Occurrence, coverage_label, stamp, utc


class StaleLease(ValueError):
    pass


def put_occurrence(conn, item):
    payload=item.model_dump(mode='json')
    conn.execute('INSERT INTO discovery.occurrences VALUES (%s,%s) ON CONFLICT DO NOTHING',
                 (item.occurrence_id,Jsonb(payload)))
    check(conn.execute('SELECT payload FROM discovery.occurrences WHERE occurrence_id=%s',
                       (item.occurrence_id,)).fetchone()[0]==payload, 'occurrence identity conflict')


def enqueue(conn, item, stage, now, *, catch_up=False, parent_id=None, extra=None):
    mode='historical_reconstructed' if catch_up and item.mode=='live_paper' else item.mode
    payload=dict(occurrence_id=item.occurrence_id,schedule_hash=item.schedule_hash,
                 scope_id=item.scope_id,input_hash=item.input_hash,code_version=item.code_version,
                 policy_hash=item.policy_hash,horizon=item.horizon,mode=mode,catch_up=catch_up,
                 information_cutoff_at=item.information_cutoff_at,extra=extra or {})
    jid=digest([stage,payload,parent_id])
    priority=20 if stage=='replay' else 0 if stage in ('event_poll','reassess') else 1 if stage=='outcome' else 10 if catch_up else 2
    expires=None if catch_up else item.expires_at
    conn.execute('''INSERT INTO discovery.schedule_jobs
        (job_id,occurrence_id,stage,parent_id,priority,payload,status,due_at,expires_at,updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,'queued',%s,%s,%s) ON CONFLICT DO NOTHING''',
        (jid,item.occurrence_id,stage,parent_id,priority,Jsonb(payload),item.due_at,expires,now))
    return jid


def materialize(conn, occurrences, now):
    """Idempotent due slots. Historical catch-up never becomes a forward signal."""
    result=[]
    with conn.transaction():
        for item in occurrences:
            check(utc(item.due_at)<=utc(now), 'occurrence not due')
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('schedule:'+item.occurrence_id,))
            put_occurrence(conn,item)
            late=utc(now)>=utc(item.expires_at)
            if late and conn.execute("SELECT 1 FROM discovery.schedule_jobs WHERE occurrence_id=%s AND stage='screen' AND status='completed'",(item.occurrence_id,)).fetchone():
                continue
            stage='event_poll' if item.kind=='event_poll' else 'ingest'
            # Missed polling is never reconstructed with today's news.
            catch_up=late and stage!='event_poll'
            jid=enqueue(conn,item,stage,now,catch_up=catch_up)
            if late and stage=='event_poll':
                conn.execute("UPDATE discovery.schedule_jobs SET status='missed',error_code='missed_poll_window',updated_at=%s WHERE job_id=%s AND status='queued'",(now,jid))
            result.append(jid)
    return tuple(result)


def claim(conn, now, code_version, lease_seconds=120, *, schedule_hash=None):
    check(type(lease_seconds) is int and 1<=lease_seconds<=900,'lease bound')
    token=str(uuid.uuid4())
    with conn.transaction():
        # Expired workers lose publication authority even before another worker claims.
        conn.execute("""UPDATE discovery.schedule_jobs SET status='missed',error_code='publication_window_elapsed',token=NULL,lease_until=NULL,updated_at=%s
            WHERE expires_at<=%s AND status IN ('queued','running','retry_wait')""",(now,now))
        conn.execute("""UPDATE discovery.schedule_jobs SET status='failed',error_code='retry_exhausted',token=NULL,lease_until=NULL,updated_at=%s
            WHERE status='running' AND lease_until<=%s AND attempts>=3""",(now,now))
        conn.execute("""UPDATE discovery.schedule_jobs j SET status='blocked',error_code='prerequisite_unavailable',updated_at=%s
            FROM discovery.schedule_jobs p WHERE j.parent_id=p.job_id AND j.status IN ('queued','retry_wait')
            AND p.status IN ('partial','blocked','failed','missed')""",(now,))
        row=conn.execute("""SELECT j.job_id,j.stage,j.payload,j.attempts FROM discovery.schedule_jobs j
            WHERE j.attempts<3 AND j.payload->>'code_version'=%s
            AND (%s::text IS NULL OR j.payload->>'schedule_hash'=%s)
            AND ((j.status IN ('queued','retry_wait') AND j.due_at<=%s) OR (j.status='running' AND j.lease_until<=%s))
            AND (j.parent_id IS NULL OR EXISTS(SELECT 1 FROM discovery.schedule_jobs p WHERE p.job_id=j.parent_id AND p.status='completed'))
            ORDER BY j.priority,j.due_at,j.job_id FOR UPDATE OF j SKIP LOCKED LIMIT 1""",(code_version,schedule_hash,schedule_hash,now,now)).fetchone()
        if row is None:
            return None
        jid,stage,payload,attempts=row
        until=stamp(utc(now)+timedelta(seconds=lease_seconds))
        conn.execute("""UPDATE discovery.schedule_jobs SET status='running',attempts=attempts+1,
            token=%s,lease_until=%s,updated_at=%s WHERE job_id=%s""",(token,until,now,jid))
        conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(jid,now,'claimed'))
        return dict(job_id=jid,stage=stage,payload=payload,attempts=attempts+1,token=token,lease_until=until)


def fenced_row(conn, job, now):
    row=conn.execute('''SELECT occurrence_id,status,token,lease_until,expires_at,attempts,payload,stage
        FROM discovery.schedule_jobs WHERE job_id=%s FOR UPDATE''',(job['job_id'],)).fetchone()
    if row is None or row[1]!='running' or row[2]!=job['token'] or row[3]<=utc(now) or (row[4] is not None and row[4]<=utc(now)):
        raise StaleLease('worker no longer owns publication lease')
    return row


def finish(conn, job, now, *, status, result, error_code=None, next_stage=None):
    check(status in ('completed','partial','blocked','failed'),'terminal status')
    check(not next_stage or status=='completed','dependencies need complete input')
    with conn.transaction():
        row=fenced_row(conn,job,now)
        if row[7]=='screen' and status=='completed':
            coverage=Coverage.model_validate_json(json.dumps(result['coverage']))
            check(coverage_label(coverage,status) in ('complete','no_qualifying_picks'),'incomplete screen publication')
        if next_stage:
            check((row[7],next_stage) in (('ingest','snapshot'),('snapshot','screen')),'invalid stage transition')
        conn.execute('''UPDATE discovery.schedule_jobs SET status=%s,result=%s,error_code=%s,token=NULL,lease_until=NULL,updated_at=%s WHERE job_id=%s''',
                     (status,Jsonb(result),error_code,now,job['job_id']))
        conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(job['job_id'],now,status))
        if status in ('completed','partial'):
            # Internal notification only. There is no email/chat sender.
            conn.execute('INSERT INTO discovery.schedule_outbox VALUES (%s,%s,%s,%s,%s)',
                         (digest([job['job_id'],status]),job['job_id'],status,Jsonb(result),now))
        if next_stage:
            item=Occurrence.model_validate(conn.execute('SELECT payload FROM discovery.occurrences WHERE occurrence_id=%s',(row[0],)).fetchone()[0])
            enqueue(conn,item,next_stage,now,catch_up=row[6]['catch_up'],parent_id=job['job_id'],extra=result)


def retry(conn, job, now, *, reason, retry_after_seconds=0):
    check(reason in ('transient','readiness','rights','credentials','budget','policy','ambiguous_billing','permanent'),'failure classification')
    check(type(retry_after_seconds) is int and 0<=retry_after_seconds<=604800,'Retry-After bound')
    with conn.transaction():
        row=fenced_row(conn,job,now)
        blocked=reason in ('rights','credentials','budget','policy','ambiguous_billing')
        status='blocked' if blocked else 'failed' if reason=='permanent' or row[5]>=3 else 'retry_wait'
        # Reproducible bounded jitter; Retry-After is a lower bound, never shortened.
        jitter=int(job['job_id'][:4],16)%11
        delay=900 if reason=='readiness' else 10*2**(row[5]-1)+jitter
        due=stamp(utc(now)+timedelta(seconds=max(delay,retry_after_seconds)))
        conn.execute('''UPDATE discovery.schedule_jobs SET status=%s,due_at=%s,error_code=%s,
            token=NULL,lease_until=NULL,updated_at=%s WHERE job_id=%s''',(status,due,reason,now,job['job_id']))
        conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(job['job_id'],now,reason))
        return status


def unresolved_upstream_rejection(conn, job_id):
    """An independently committed pilot rejection survives a lease/worker crash."""
    row=conn.execute("""SELECT payload FROM discovery.schedule_outbox
        WHERE job_id=%s AND kind='pilot_upstream_rejection'
        ORDER BY (payload->>'attempt')::integer DESC LIMIT 1""",(job_id,)).fetchone()
    if row and not conn.execute('SELECT 1 FROM discovery.schedule_audit WHERE job_id=%s AND code LIKE %s',
        (job_id,'upstream_gate_resolved:'+str(row[0]['attempt'])+':%')).fetchone():return row[0]
    return None


def resume_blocked(conn, job_id, now, evidence_ref, *, expected_attempt=None):
    """Pilot recovery requires an explicit attempt and a fresh resolution reference."""
    check(isinstance(evidence_ref,str) and evidence_ref.strip(),'resolution evidence required')
    with conn.transaction():
        row=conn.execute('SELECT status,expires_at,attempts,error_code FROM discovery.schedule_jobs WHERE job_id=%s FOR UPDATE',(job_id,)).fetchone()
        upstream=conn.execute("SELECT 1 FROM discovery.schedule_outbox WHERE job_id=%s AND kind='pilot_upstream_rejection'",(job_id,)).fetchone()
        if upstream:
            check(type(expected_attempt) is int and expected_attempt>0,'recovery attempt required')
            reference_hash=digest(evidence_ref.strip())
            audit_code='pilot_gate_resolved:'+str(expected_attempt)+':'+reference_hash
            # An old authorization must not resolve a new blocked attempt. Exact
            # repeats after queuing/running/completion are harmless acknowledgments.
            if row[0]=='blocked':
                check(row[2]==expected_attempt,'stale recovery attempt')
            elif conn.execute('SELECT 1 FROM discovery.schedule_audit WHERE job_id=%s AND code=%s',(job_id,audit_code)).fetchone():
                return False
            check(row[0]=='blocked','only blocked jobs can resume')
            check(not conn.execute('SELECT 1 FROM discovery.schedule_audit WHERE job_id=%s AND code LIKE %s',
                (job_id,'pilot_gate_resolved:%:'+reference_hash)).fetchone(),'stale recovery evidence')
            rejection=unresolved_upstream_rejection(conn,job_id)
            if rejection:check(row[3]==rejection['reason'],'upstream rejection reason mismatch')
            check(row[1] is None or utc(now)<row[1],'expired job must remain historical')
            check(row[2]<3,'retry budget exhausted')
            conn.execute("UPDATE discovery.schedule_jobs SET status='queued',due_at=%s,error_code=NULL,updated_at=%s WHERE job_id=%s",(now,now,job_id))
            conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(job_id,now,audit_code))
            if rejection:
                conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',
                    (job_id,now,'upstream_gate_resolved:'+str(rejection['attempt'])+':'+reference_hash))
            return True
        check(row is not None and row[0]=='blocked','only blocked jobs can resume')
        check(row[1] is None or utc(now)<row[1],'expired job must remain historical')
        conn.execute("UPDATE discovery.schedule_jobs SET status='queued',attempts=0,due_at=%s,error_code=NULL,updated_at=%s WHERE job_id=%s",(now,now,job_id))
        conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(job_id,now,'gate_resolved:'+evidence_ref))


def operations(conn, now, *, scope_id, mode, horizon):
    """Never mix modes/horizons/scopes. Retain true publication AND input age."""
    where = "payload->>'scope_id'=%s AND payload->>'mode'=%s AND payload->>'horizon' IS NOT DISTINCT FROM %s"
    args = (scope_id, mode, horizon)
    statuses = dict(conn.execute('SELECT status,count(*) FROM discovery.schedule_jobs WHERE '+where+' GROUP BY status', args).fetchall())
    completed = conn.execute("SELECT job_id,payload,result,updated_at FROM discovery.schedule_jobs WHERE "+where+" AND stage='screen' AND status='completed' ORDER BY updated_at DESC,job_id LIMIT 1", args).fetchone()
    latest = conn.execute('SELECT job_id,status,error_code,updated_at FROM discovery.schedule_jobs WHERE '+where+' ORDER BY updated_at DESC,job_id LIMIT 1', args).fetchone()
    return dict(counts=statuses,
        latest_attempt=None if latest is None else dict(job_id=latest[0],status=latest[1],error_code=latest[2],at=stamp(latest[3])),
        last_complete=None if completed is None else dict(job_id=completed[0],mode=mode,horizon=horizon,
            coverage=completed[2]['coverage'],published_at=stamp(completed[3]),
            information_cutoff_at=completed[1]['information_cutoff_at'],
            age_seconds=max(0,int((utc(now)-completed[3]).total_seconds())),
            input_age_seconds=max(0,int((utc(now)-utc(completed[1]['information_cutoff_at'])).total_seconds()))))
