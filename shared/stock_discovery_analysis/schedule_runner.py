"""One bounded scheduler tick; production adapters remain explicitly unavailable."""
from datetime import timedelta

from stock_discovery_contracts.v2 import check, digest
from .scheduling import calendar_issues, event_poll_slots, monitoring_active, resolve_occurrences, stamp, utc
from .schedule_store import StaleLease, claim, finish, materialize, retry


class JobFailure(Exception):
    def __init__(self, reason, retry_after_seconds=0):
        self.reason, self.retry_after_seconds = reason, retry_after_seconds
        super().__init__(reason)


def tick(conn, config, *, clock, handlers=None, lease_seconds=120):
    """Materialize durable slots and execute at most one job. No hidden paid calls.

    Handlers are trusted installed code, not configuration imports. They receive
    immutable job inputs and must use D3-03 rights-gated operations. A fresh clock
    is read when committing so an expired lease cannot publish a slow result.
    """
    now = clock()
    issues = calendar_issues(config, now)
    if 'calendar_not_available' in issues:
        return dict(status='blocked', issues=issues, monitoring_active=False)
    slots = resolve_occurrences(config, now)
    # Commit checkpoint and occurrence creation together; catch up at most 31 days per tick.
    schedule_hash = digest(config.model_dump(mode='json'))
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('polls:'+schedule_hash,))
        row = conn.execute('SELECT polled_through FROM discovery.schedule_cursors WHERE schedule_hash=%s', (schedule_hash,)).fetchone()
        start = row[0] if row else utc(config.calendar.available_at)-timedelta(seconds=1)
        end = min(utc(now), start+timedelta(days=31))
        polls = event_poll_slots(config, stamp(start), stamp(end))
        materialize(conn, slots+polls, now)
        conn.execute('INSERT INTO discovery.schedule_cursors VALUES (%s,%s) ON CONFLICT(schedule_hash) DO UPDATE SET polled_through=EXCLUDED.polled_through', (schedule_hash,stamp(end)))
    job = claim(conn, now, config.code_version, lease_seconds=lease_seconds, schedule_hash=digest(config.model_dump(mode='json')))
    if job is None:
        return dict(status='idle', issues=issues, monitoring_active=monitoring_active(config,now))
    handlers = handlers or {}
    handler = handlers.get(job['stage'])
    try:
        check(job['payload']['schedule_hash'] == digest(config.model_dump(mode='json')), 'worker schedule mismatch')
        if handler is None:
            reason = 'policy' if job['stage'] in ('screen','reassess') else 'credentials'
            raise JobFailure(reason)
        with conn.transaction():
            result, next_stage = handler(conn, job, clock)
            status = 'partial' if result.get('status')=='partial' else 'completed'
            finish(conn,job,clock(),status=status,result=result,next_stage=next_stage)
    except JobFailure as exc:
        try:
            status = retry(conn,job,clock(),reason=exc.reason,retry_after_seconds=exc.retry_after_seconds)
        except StaleLease:
            status = 'lease_lost'
    except PermissionError:
        try:
            status = retry(conn,job,clock(),reason='rights')
        except StaleLease:
            status = 'lease_lost'
    except StaleLease:
        status = 'lease_lost'
    except Exception:
        # Unknown errors may include ambiguous side effects: require investigation.
        try:
            status = retry(conn,job,clock(),reason='permanent')
        except StaleLease:
            status = 'lease_lost'
    return dict(job_id=job['job_id'], stage=job['stage'],status=status,issues=issues,
                monitoring_active=monitoring_active(config,clock()))
