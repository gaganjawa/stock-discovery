"""STK-099: same-host durable bridge; LISTEN is a hint, never a queue.

Separate inbox/research databases preserve receiver isolation. The destination
transaction commits events and cursor together. Source events are immutable.
LISTEN precedes draining so a commit during catch-up cannot be lost; a bounded
fallback scan also recovers missed hints, retries and older receiver versions.
"""
import json
import os
import time
from urllib.parse import urlsplit
from pathlib import Path
import psycopg
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.runtime import setting
from .candidates import cycle, validate_page


def bridge(destination, source, receiver_url):
    # Retain the old HTTPS identity so migrated Mac cursors are reused.
    parts = urlsplit(receiver_url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('receiver_identity_required')
    receiver_id = store.digest(receiver_url)
    with destination.transaction():
        if not destination.execute('SELECT pg_try_advisory_xact_lock(94004)').fetchone()[0]:
            return 0
        destination.execute('INSERT INTO discovery.candidate_receivers(receiver_id) VALUES (%s) ON CONFLICT DO NOTHING', (receiver_id,))
        cursor = destination.execute('SELECT cursor FROM discovery.candidate_receivers WHERE receiver_id=%s FOR UPDATE', (receiver_id,)).fetchone()[0]
        high = source.execute('SELECT coalesce(max(sequence),0) FROM discovery.candidate_events').fetchone()[0]
        if cursor > high:
            raise ValueError('receiver_cursor_ahead_restore_required')
        page = store.feed(source, cursor)
        expected = validate_page(destination, page, cursor)
        destination.execute('UPDATE discovery.candidate_receivers SET cursor=%s WHERE receiver_id=%s', (expected, receiver_id))
        return len(page['events'])


def connect(url, *, source=False):
    options = '-c statement_timeout=15000 -c lock_timeout=2000'
    if source:
        options += ' -c default_transaction_read_only=on'
    return psycopg.connect(url, autocommit=True, connect_timeout=5, options=options,
                          application_name='stk099-candidate-worker')


def save_health(status, **counts):
    filename = os.getenv('CANDIDATE_HEALTH_FILE')
    if filename:
        target = Path(filename)
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(status=status, at=time.time(), **counts)))
        temp.replace(target)


def validate_hosted():
    if os.getenv('DEPLOYMENT_MODE') != 'private':
        return
    from psycopg.conninfo import conninfo_to_dict
    if not os.getenv('CANDIDATE_SOURCE_DATABASE_URL_FILE'):
        raise ValueError('source_secret_file_required')
    source = conninfo_to_dict(setting('CANDIDATE_SOURCE_DATABASE_URL'))
    target = conninfo_to_dict(setting('DATABASE_URL'))
    if (source.get('user') != 'stk_inbox_reader' or source.get('dbname') != 'chartink_inbox'
            or target.get('user') != 'stk_candidate_worker' or target.get('dbname') != 'stk_real001_private'
            or len(source.get('password', '')) < 32
            or not source.get('host') or source.get('host') != target.get('host')
            or source.get('port', '5432') != target.get('port', '5432')):
        raise ValueError('hosted_database_identity_configuration_mismatch')


def serve(*, once=False, stop=None, recovery_seconds=30):
    validate_hosted()
    while stop is None or not stop.is_set():
        try:
            with connect(setting('CANDIDATE_SOURCE_DATABASE_URL'), source=True) as source, connect(setting('DATABASE_URL')) as destination:
                source.execute('LISTEN stk_candidates')
                # Only one recurring consumer, including during overlapping restarts.
                if not destination.execute('SELECT pg_try_advisory_lock(99001)').fetchone()[0]:
                    raise RuntimeError('candidate_worker_already_running')
                while stop is None or not stop.is_set():
                    received = bridge(destination, source, os.environ['CHARTINK_RECEIVER_URL'])
                    result = cycle(destination, remote_pull=False)
                    save_health('healthy', received=received, **result)
                    if once:
                        return
                    if received or result['events'] or result['research']:
                        continue
                    # A notification's payload is deliberately empty and ignored.
                    for _ in source.notifies(timeout=recovery_seconds, stop_after=1):
                        break
        except Exception as exc:
            save_health('blocked', error_type=type(exc).__name__)
            print(json.dumps(dict(event='candidate_worker_blocked', error_type=type(exc).__name__)), flush=True)
            if once:
                raise SystemExit(1) from None
            if stop is not None:
                stop.wait(5)
            else:
                time.sleep(5)
