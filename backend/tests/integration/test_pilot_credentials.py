"""STK-075 recovery: mocked HTTP, real worker processes and disposable PG.

These controlled regressions do not approve operational acceptance. No provider or model is contacted.
"""
import gzip
import json
import multiprocessing
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import count
from threading import Barrier

import httpx
import psycopg
import pytest

from test_real_pilot_recovery import isolated_url, pilot_case
from worker import main as worker_main, pilot_operations as operations, real_market, real_pilot as pilot
from worker.providers import upstox_financials
from worker.providers.upstox import Upstox, observed_revision, RevisionPages
from worker.providers.upstox_financials import ingest_financials
from stock_discovery_analysis.revisions import SessionData
from stock_discovery_analysis.revision_storage import Stream, ingest_next
from stock_discovery_analysis.scheduling import resolve_occurrences
from stock_discovery_analysis.schedule_store import materialize, resume_blocked

NOW = '2026-10-15T15:00:00Z'  # After the event polling window; exercise scheduled ingestion.


def history(conn):
    return conn.execute('SELECT revision_id,payload FROM discovery.revisions ORDER BY revision_id').fetchall()


def evidence(conn):
    tables = ('evidence_documents', 'evidence_blobs', 'evidence_chunks', 'financial_facts')
    return {table: conn.execute('SELECT to_jsonb(t) FROM discovery.'+table+' t ORDER BY to_jsonb(t)::text').fetchall() for table in tables}


def receipts(conn):
    return conn.execute('SELECT event_key,payload FROM discovery.schedule_outbox ORDER BY event_key').fetchall()


@pytest.fixture
def credential_case(pilot_case, monkeypatch, tmp_path):
    c = pilot_case
    c.current[0] = NOW
    # Explicit fabricated permissions, never an amendment to a private grant.
    c.g = c.g.model_copy(update={'version': 'credential-test-2', 'attribution': 'Upstox', 'scopes': (*c.g.scopes, 'financial_facts', 'filings'),
                                'allowed_uses': (*c.g.allowed_uses, 'extract')})
    c.gf.write_text(json.dumps([c.g.model_dump(mode='json')]))
    c.schedule = c.schedule.model_copy(update={'horizons': ('swing',)})
    c.ops = tmp_path/'operations'
    c.ops.mkdir(mode=0o700)
    c.schedule_file = tmp_path/'schedule.json'
    c.pilot_file = tmp_path/'pilot.json'
    c.schedule_file.write_text(c.schedule.model_dump_json())
    c.pilot_file.write_text(c.config.model_dump_json())
    operations.atomic(c.ops/'health.json', {'calendar_checked_at': NOW})
    session = observed_revision(SessionData(kind='session', calendar_version='upstox-dated-NSE-v1',
        opens_at='2026-10-15T03:45:00Z', closes_at='2026-10-15T10:00:00Z'), listing='NSE', fetched=NOW)
    stream = Stream(stream_id=session.revision_id, source_id='upstox', account_ref='test', scope='calendar')
    access = real_market.access_for(c.config.market, lambda: c.current[0])
    _, request = access.require(stream, ('store',))
    ingest_next(c.conn, stream, RevisionPages((session,)), load_grant=lambda: c.g,
                request=request, audit=lambda d: None, clock=lambda: c.current[0])
    other = c.schedule.model_copy(update={'schedule_id': 'unrelated', 'code_version': 'unrelated-worker'})
    c.other_id = materialize(c.conn, resolve_occurrences(other, NOW), NOW)[0]
    c.other = c.conn.execute('SELECT * FROM discovery.schedule_jobs WHERE job_id=%s', (c.other_id,)).fetchone()
    c.initial_history = history(c.conn)
    c.pids = []
    c.http = []
    c.endpoint = None
    c.code = None
    c.rejected_token = 'Bearer fabricated-token'

    def transport(request):
        path = request.url.path
        if path.endswith('.gz'):
            body = [dict(segment='NSE_EQ', exchange='NSE', instrument_type='EQ',
                         trading_symbol=m['symbol'], isin=m['isin'], instrument_key='NSE_EQ|'+m['isin'],
                         name='FABRICATED '+m['symbol'], lot_size=1, tick_size=5) for m in c.members]
            c.http.append(('universe', 200))
            return httpx.Response(200, content=gzip.compress(json.dumps(body).encode()))
        endpoint = 'calendar' if '/market/timings/' in path else 'prices' if '/historical-candle/' in path else path.rsplit('/', 1)[-1]
        assert endpoint in ('calendar', 'prices', 'income-statement', 'balance-sheet', 'cash-flow'), path
        token = request.headers.get('Authorization')
        assert token in ('Bearer fabricated-token', 'Bearer corrected-mock-token')
        code = c.code if endpoint == c.endpoint and token == c.rejected_token else 200
        c.http.append((endpoint, code))
        if code != 200:
            return httpx.Response(code, text='DO-NOT-RETAIN mock secret rejection body')
        if endpoint == 'calendar':
            day = path.rsplit('/', 1)[-1]
            def millis(time):
                return int(datetime.fromisoformat(day+'T'+time+'+00:00').timestamp()*1000)
            return httpx.Response(200, json={'status': 'success', 'data': [dict(
                exchange='NSE', start_time=millis('03:45:00'), end_time=millis('10:00:00'))]})
        if endpoint == 'prices':
            return httpx.Response(200, json={'status': 'success', 'data': {'candles': [
                ['2026-10-15T00:00:00+05:30', 100, 110, 90, 105, 100, 0]]}})
        lines = {'income-statement': {'Revenue': 100, 'Profit After Tax': 25},
                 'balance-sheet': {'Total Assets': 100},
                 'cash-flow': {'Cash flow from Operations': 20}}[endpoint]
        return httpx.Response(200, json={'status': 'success', 'data': {
            'type': 'consolidated', 'time_period': 'yearly', 'units_in': 'crore',
            'full_statement': [{'particular': k, 'history': [{'period': 'Mar 2026', 'value': v}]} for k, v in lines.items()]}})

    class MockHTTP(Upstox):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(transport), monotonic=lambda: next(ticks))
    ticks = count(0, 1)
    original_client_init = httpx.Client.__init__
    def only_mock_http(self, *args, **kwargs):
        assert isinstance(kwargs.get('transport'), httpx.MockTransport), 'external HTTP forbidden'
        original_client_init(self, *args, **kwargs)
    monkeypatch.setattr(httpx.Client, '__init__', only_mock_http)
    monkeypatch.setattr(pilot, 'Upstox', MockHTTP)
    monkeypatch.setattr(pilot, 'ingest_prices', real_market.ingest_prices)
    def rank(rows):
        if 'screening' in rows[0]:
            rows[0]['screening'] = {'long_term': {'rank': 1}}
    monkeypatch.setattr(pilot, 'rank_rows', rank)
    monkeypatch.setattr(upstox_financials, 'ingest_financials', ingest_financials)
    # Keep real rights, parsing, storage, leases and accounting. Only HTTP, AI,
    # ranking/view fixtures, elapsed pacing and the controlled wall clock are mocked.
    monkeypatch.setattr(pilot.time, 'sleep', lambda seconds: None)
    original_renew = operations.renew_calendar
    monkeypatch.setattr(operations, 'renew_calendar', lambda *a, **kw:
        original_renew(*a, **kw, factory=MockHTTP, pause=lambda seconds: None))
    original_ops = operations.Operations
    monkeypatch.setattr(operations, 'Operations', lambda *a: original_ops(*a, clock=lambda: c.current[0]))
    class Clock:
        @staticmethod
        def now(tz):
            return datetime.fromisoformat(c.current[0].replace('Z', '+00:00'))
    monkeypatch.setattr(worker_main, 'datetime', Clock)
    monkeypatch.setattr(sys, 'argv', ['worker', '--once', '--schedule-config', str(c.schedule_file),
        '--real-pilot-config', str(c.pilot_file), '--pilot-operations-directory', str(c.ops)])
    monkeypatch.delenv('DEPLOYMENT_MODE', raising=False)

    def run(expected_error=None):
        # A fresh OS process opens fresh DB connections and reloads token/state.
        # Fork inherits only the controlled test doubles; no daemon is installed.
        context = multiprocessing.get_context('fork')
        reader, writer = context.Pipe(duplex=False)
        def child():
            try:
                # Let any higher-priority event-poll slot finish normally.
                for _ in range(16):
                    worker_main.main()
                    health = json.loads((c.ops/'health.json').read_text())
                    if health.get('last_tick', {}).get('stage') != 'event_poll':
                        break
                else:
                    raise AssertionError('scheduled ingestion starved')
                writer.send(dict(http=c.http, inference=len(c.model_calls)))
            except BaseException:
                writer.send(dict(error=traceback.format_exc(), http=c.http, inference=len(c.model_calls)))
            finally:
                writer.close()
        process = context.Process(target=child)
        process.start()
        assert process.pid not in c.pids
        c.pids.append(process.pid)
        writer.close()
        try:
            assert reader.poll(30), 'bounded worker did not finish'
            result = reader.recv()
            process.join(5)
            assert process.exitcode == 0
            if expected_error:
                assert expected_error in result.get('error', ''), result
            else:
                assert 'error' not in result, result.get('error', result)
            return result, json.loads((c.ops/'health.json').read_text())
        finally:
            if process.is_alive():
                process.terminate(); process.join(5)
            reader.close()
    c.run = run
    yield c


def assert_preserved(c):
    assert all(row in history(c.conn) for row in c.initial_history)
    assert c.conn.execute('SELECT * FROM discovery.schedule_jobs WHERE job_id=%s', (c.other_id,)).fetchone() == c.other
    for table in ('discovery.publication_runs', 'paper.shadow_references', 'paper.shadow_outcomes', 'paper.portfolios'):
        assert c.conn.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    assert 'DO-NOT-RETAIN' not in json.dumps(receipts(c.conn))


@pytest.mark.parametrize('code', [401, 403])
@pytest.mark.parametrize('endpoint', ['prices', 'income-statement', 'balance-sheet', 'cash-flow'])
def test_rejected_scan_blocks_and_audited_restart_recovers_same_cutoff(credential_case, code, endpoint):
    c = credential_case; c.endpoint = endpoint; c.code = code
    first, health = c.run()
    assert first['http'].count((endpoint, code)) == 1
    assert first['http'][-1] == (endpoint, code)
    assert len(first['http']) == {'prices': 2, 'income-statement': 3, 'balance-sheet': 4, 'cash-flow': 5}[endpoint]
    assert first['inference'] == 0 and health['last_tick']['status'] == 'blocked'
    jid = health['last_tick']['job_id']
    reason = 'credentials' if code == 401 else 'rights'
    error = 'upstox_authentication_rejected' if code == 401 else 'upstox_authorization_rejected'
    rejection = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_upstream_rejection' AND job_id=%s", (jid,)).fetchone()[0]
    assert rejection['error'] == error and rejection['http_status'] == code
    assert rejection['reason'] == reason and rejection['attempt'] == 1 and not rejection['actionable']
    stock = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_stock' AND job_id=%s", (jid,)).fetchone()[0]
    assert stock['errors'] == [('' if endpoint == 'prices' else endpoint+':')+error]
    assert c.conn.execute('SELECT status,attempts,error_code FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == ('blocked', 1, reason)
    before_history, before_receipts, before_evidence = history(c.conn), receipts(c.conn), evidence(c.conn)
    reservations = c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0]
    assert reservations == len(first['http'])
    c.tf.write_text('corrected-mock-token')
    c.current[0] = '2026-10-15T16:00:00Z'
    second, restarted = c.run()
    assert second == dict(http=[], inference=0)  # Correction/restart alone is not approval to resume.
    assert restarted['last_tick']['status'] == 'idle'
    assert history(c.conn) == before_history and receipts(c.conn) == before_receipts
    assert evidence(c.conn) == before_evidence
    with pytest.raises(ValueError, match='resolution evidence required'):
        resume_blocked(c.conn, jid, c.current[0], '', expected_attempt=1)
    assert resume_blocked(c.conn, jid, c.current[0], 'fixture://corrected-access', expected_attempt=1) is True
    assert resume_blocked(c.conn, jid, c.current[0], 'fixture://corrected-access', expected_attempt=1) is False
    assert c.conn.execute('SELECT attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone()[0] == 1
    recovered, health = c.run()
    assert health['last_tick']['job_id'] == jid and health['last_tick']['status'] == 'completed'
    assert all(status == 200 for _, status in recovered['http']) and len(recovered['http']) == 41
    assert recovered['inference'] == 1
    assert c.conn.execute('SELECT status,attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == ('completed', 2)
    scan = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan' AND job_id=%s", (jid,)).fetchone()[0]
    assert scan['attempt'] == 2 and scan['scheduled_cutoff'] == rejection['scheduled_cutoff']
    assert scan['publication'] == 'blocked_existing_qualification_gates'
    assert scan['positions'] == scan['prospective_references'] == 0 and not scan['actionable']
    assert all(row in history(c.conn) for row in before_history)
    assert all(row in receipts(c.conn) for row in before_receipts)
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0] == reservations+41
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE job_id=%s AND code LIKE 'upstream_gate_resolved:%%'", (jid,)).fetchone()[0] == 1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_stock' AND job_id=%s", (jid,)).fetchone()[0] == 11
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0] == 1
    assert c.conn.execute("SELECT count(*) FROM discovery.evidence_documents").fetchone()[0] == 30
    assert c.conn.execute("SELECT count(*) FROM discovery.financial_facts").fetchone()[0] == 50
    saved = history(c.conn), receipts(c.conn), evidence(c.conn)
    assert resume_blocked(c.conn, jid, c.current[0], 'fixture://corrected-access', expected_attempt=1) is False
    duplicate, _ = c.run()
    assert duplicate == dict(http=[], inference=0)
    assert (history(c.conn), receipts(c.conn), evidence(c.conn)) == saved
    assert_preserved(c)


@pytest.mark.parametrize('code', [401, 403])
def test_calendar_rejection_backoff_survives_restart_and_same_cutoff_recovers(credential_case, code):
    c = credential_case; c.endpoint = 'calendar'; c.code = code
    operations.atomic(c.ops/'health.json', {})
    first, health = c.run()
    assert first == dict(http=[('calendar', code)], inference=0)
    assert health['status'] == 'blocked' and health['last_tick']['error'] == 'upstox_credentials_rejected'
    assert health['calendar_retry_at'] == '2026-10-15T16:00:00Z'
    assert not (c.ops/'schedule.json').exists()
    assert history(c.conn) == c.initial_history
    reservations = c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0]
    assert reservations == 1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_jobs WHERE payload->>'code_version'=%s", (c.schedule.code_version,)).fetchone()[0] == 0
    first_audit = c.conn.execute('SELECT * FROM discovery.schedule_audit ORDER BY audit_id').fetchall()
    c.tf.write_text('corrected-mock-token')
    c.current[0] = '2026-10-15T15:30:00Z'
    early, waiting = c.run()
    assert early == dict(http=[], inference=0)
    assert waiting['status'] == 'blocked' and waiting['last_tick']['error'] == 'calendar_refresh_required'
    assert c.conn.execute('SELECT * FROM discovery.schedule_audit ORDER BY audit_id').fetchall() == first_audit
    c.current[0] = '2026-10-15T16:00:00Z'
    recovered, health = c.run()
    assert recovered['http'].count(('calendar', 200)) == 15
    assert recovered['inference'] == 1 and health['last_tick']['status'] == 'completed'
    scan = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan'").fetchone()[0]
    assert scan['scheduled_cutoff'] == '2026-10-15T10:00:00Z'
    assert scan['status'] == 'completed' and not scan['actionable']
    assert scan['publication'] == 'blocked_existing_qualification_gates'
    saved_history, saved_receipts, saved_evidence = history(c.conn), receipts(c.conn), evidence(c.conn)
    duplicate, _ = c.run()
    assert duplicate == dict(http=[], inference=0)
    assert history(c.conn) == saved_history and receipts(c.conn) == saved_receipts
    assert evidence(c.conn) == saved_evidence
    assert c.conn.execute("SELECT count(*) FROM discovery.revisions WHERE kind='document'").fetchone()[0] == 30
    assert c.conn.execute('SELECT count(*) FROM discovery.financial_facts').fetchone()[0] == 50  # Four reported facts + derived net margin per issuer.
    assert_preserved(c)


@pytest.mark.parametrize('code', [401, 403])
def test_repeated_rejection_never_resets_attempt_limit(credential_case, code):
    c = credential_case; c.endpoint = 'prices'; c.code = code
    prior = []
    for attempt in range(1, 4):
        result, health = c.run()
        jid = health['last_tick']['job_id']
        assert result == dict(http=[('universe', 200), ('prices', code)], inference=0)
        assert health['last_tick']['status'] == 'blocked'
        assert c.conn.execute('SELECT attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone()[0] == attempt
        assert all(row in receipts(c.conn) for row in prior)
        prior = receipts(c.conn)
        if attempt < 3:
            assert resume_blocked(c.conn, jid, c.current[0], f'fixture://access-reviewed/{attempt}', expected_attempt=attempt) is True
    with pytest.raises(ValueError, match='retry budget exhausted'):
        resume_blocked(c.conn, jid, c.current[0], f'fixture://access-reviewed/{attempt}', expected_attempt=attempt)
    unchanged, _ = c.run()
    assert unchanged == dict(http=[], inference=0) and receipts(c.conn) == prior
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_upstream_rejection'").fetchone()[0] == 3
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0] == 6
    assert_preserved(c)


def test_expired_rejection_cannot_resume_as_forward_work(credential_case):
    c = credential_case; c.endpoint = 'prices'; c.code = 401
    _, health = c.run(); jid = health['last_tick']['job_id']
    saved = receipts(c.conn)
    with pytest.raises(ValueError, match='expired job must remain historical'):
        resume_blocked(c.conn, jid, '2026-10-16T03:00:00Z', 'fixture://corrected-access', expected_attempt=1)
    assert c.conn.execute('SELECT status,attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == ('blocked', 1)
    assert receipts(c.conn) == saved


def test_crash_after_rejection_receipt_blocks_reclaimed_worker_before_requests(credential_case, monkeypatch):
    from stock_discovery_analysis import schedule_runner
    c = credential_case; c.endpoint = 'prices'; c.code = 401
    real_retry = schedule_runner.retry
    def crash(*args, **kwargs):
        raise KeyboardInterrupt('fixture crash before scheduler block')
    monkeypatch.setattr(schedule_runner, 'retry', crash)
    first, _ = c.run(expected_error='fixture crash before scheduler block')
    assert first['http'] == [('universe', 200), ('prices', 401)] and first['inference'] == 0
    saved = receipts(c.conn)
    monkeypatch.setattr(schedule_runner, 'retry', real_retry)
    c.tf.write_text('corrected-mock-token')
    c.current[0] = '2026-10-15T15:16:00Z'  # Expired 900-second lease, same session cutoff.
    restarted, health = c.run()
    assert restarted == dict(http=[], inference=0) and health['last_tick']['status'] == 'blocked'
    jid = health['last_tick']['job_id']
    assert c.conn.execute('SELECT attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone()[0] == 2
    assert all(row in receipts(c.conn) for row in saved)
    resume_blocked(c.conn, jid, c.current[0], 'fixture://corrected-access', expected_attempt=2)
    recovered, health = c.run()
    assert recovered['inference'] == 1 and health['last_tick']['status'] == 'completed'
    assert c.conn.execute('SELECT attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone()[0] == 3
    assert_preserved(c)


def test_access_recovery_preserves_preexisting_ambiguous_inference_budget(credential_case):
    c = credential_case; c.endpoint = 'prices'; c.code = 401
    jid = materialize(c.conn, resolve_occurrences(c.schedule, NOW), NOW)[0]
    # A prior unresolved intent for this cutoff must still consume its budget,
    # even if its model fingerprint differs from the current research request.
    pilot.receipt(c.conn, {'job_id': jid}, 'pilot_research_intent', 'prior-intent',
                  dict(fingerprint='prior-ambiguous-fingerprint', status='reserved'), lambda: NOW)
    existing = receipts(c.conn)
    rejected, health = c.run()
    assert health['last_tick']['job_id'] == jid and rejected['inference'] == 0
    c.tf.write_text('corrected-mock-token')
    c.current[0] = '2026-10-15T16:00:00Z'
    resume_blocked(c.conn, jid, c.current[0], 'fixture://corrected-access', expected_attempt=1)
    recovered, health = c.run()
    assert health['last_tick']['status'] == 'partial' and recovered['inference'] == 0
    scan = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan'").fetchone()[0]
    assert scan['rows'][0]['research']['status'] == 'occurrence_research_budget_exhausted'
    assert all(row in receipts(c.conn) for row in existing)
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0] == 1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research'").fetchone()[0] == 0
    assert_preserved(c)


@pytest.mark.parametrize('second_gate', ['http_403', 'local_permission'])
def test_sequential_gates_bind_resolution_to_attempt_and_serialize_recovery(credential_case, monkeypatch, second_gate):
    c = credential_case; c.endpoint = 'prices'; c.code = 401
    first, health = c.run(); jid = health['last_tick']['job_id']
    assert first == dict(http=[('universe', 200), ('prices', 401)], inference=0)
    first_receipts = receipts(c.conn)
    first_history = history(c.conn)
    with pytest.raises(ValueError, match='recovery attempt required'):
        resume_blocked(c.conn, jid, NOW, 'fixture://credential-resolution')
    with pytest.raises(ValueError, match='stale recovery attempt'):
        resume_blocked(c.conn, jid, NOW, 'fixture://credential-resolution', expected_attempt=99)

    def resolve_concurrently(attempt, reference):
        barrier = Barrier(2)
        def resolve():
            with psycopg.connect(c.isolated_url, autocommit=True) as conn:
                barrier.wait(timeout=5)
                return resume_blocked(conn, jid, c.current[0], reference, expected_attempt=attempt)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(resolve) for _ in range(2)]
            assert sorted(f.result(timeout=10) for f in futures) == [False, True]

    resolve_concurrently(1, 'fixture://credential-resolution')
    assert c.conn.execute('SELECT status,attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == ('queued', 1)
    c.tf.write_text('corrected-mock-token')
    c.current[0] = '2026-10-15T15:10:00Z'
    c.code = 403; c.rejected_token = 'Bearer corrected-mock-token'
    original_access = pilot.access_for
    if second_gate == 'local_permission':
        # A local grant is denied after operational preflight; unlike HTTP 403,
        # this creates no new upstream-rejection receipt.
        def denied(*args, **kwargs):
            raise PermissionError('fixture_permission_revoked')
        monkeypatch.setattr(pilot, 'access_for', denied)
    second, health = c.run()
    assert health['last_tick']['job_id'] == jid and health['last_tick']['status'] == 'blocked'
    assert second == dict(http=[('universe', 200), ('prices', 403)] if second_gate == 'http_403' else [], inference=0)
    assert c.conn.execute('SELECT attempts,error_code FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == (2, 'rights')
    if second_gate == 'http_403':
        failures = c.conn.execute("SELECT payload->>'http_status',payload->>'attempt' FROM discovery.schedule_outbox WHERE kind='pilot_upstream_rejection' ORDER BY payload->>'attempt'").fetchall()
        assert failures == [('401', '1'), ('403', '2')]
    saved = history(c.conn), receipts(c.conn), evidence(c.conn)
    audit_before = c.conn.execute('SELECT * FROM discovery.schedule_audit ORDER BY audit_id').fetchall()
    # Replaying the first approval cannot resolve the second failure, even if
    # the caller changes only its expected attempt to the new value.
    for attempt, reference, error in ((1, 'fixture://credential-resolution', 'stale recovery attempt'),
                                      (1, 'fixture://permission-resolution', 'stale recovery attempt'),
                                      (2, 'fixture://credential-resolution', 'stale recovery evidence')):
        with pytest.raises(ValueError, match=error):
            resume_blocked(c.conn, jid, c.current[0], reference, expected_attempt=attempt)
    assert c.conn.execute('SELECT * FROM discovery.schedule_audit ORDER BY audit_id').fetchall() == audit_before
    assert (history(c.conn), receipts(c.conn), evidence(c.conn)) == saved
    assert all(row in receipts(c.conn) for row in first_receipts)
    assert all(row in history(c.conn) for row in first_history)

    monkeypatch.setattr(pilot, 'access_for', original_access)
    c.code = 200  # Provider permission restored, with the corrected token unchanged.
    waiting, _ = c.run()
    assert waiting == dict(http=[], inference=0)
    resolve_concurrently(2, 'fixture://permission-resolution')
    assert resume_blocked(c.conn, jid, c.current[0], 'fixture://permission-resolution', expected_attempt=2) is False
    assert c.conn.execute('SELECT attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone()[0] == 2
    final, health = c.run()
    assert health['last_tick']['status'] == 'completed' and final['inference'] == 1
    assert len(final['http']) == 41 and all(code == 200 for _, code in final['http'])
    assert c.conn.execute('SELECT status,attempts FROM discovery.schedule_jobs WHERE job_id=%s', (jid,)).fetchone() == ('completed', 3)
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE job_id=%s AND code LIKE 'pilot_gate_resolved:%%'", (jid,)).fetchone()[0] == 2
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code LIKE 'pilot_request:%'").fetchone()[0] == 2+len(second['http'])+41
    scan = c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan'").fetchone()[0]
    assert scan['attempt'] == 3 and scan['scheduled_cutoff'] == '2026-10-15T10:00:00Z'
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0] == 1
    final_state = history(c.conn), receipts(c.conn), evidence(c.conn)
    assert resume_blocked(c.conn, jid, c.current[0], 'fixture://permission-resolution', expected_attempt=2) is False
    duplicate, _ = c.run()
    assert duplicate == dict(http=[], inference=0)
    assert (history(c.conn), receipts(c.conn), evidence(c.conn)) == final_state
    assert all(row in receipts(c.conn) for row in saved[1])
    assert_preserved(c)
