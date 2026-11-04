"""STK-086: read-only readiness and local health for the existing stored worker.

No provider adapter, new scheduler, grant registration or evidence mutation.
The scheduler alone owns job/lease/receipt writes after this gate passes.
"""
import json
import os
import subprocess
from hashlib import sha256
from datetime import timedelta
from pathlib import Path

from stock_discovery_contracts.v2 import check, digest, at
from stock_discovery_analysis.calendar_lifecycle import lifecycle
from stock_discovery_analysis.daily_insight import LISTING, research, run_status
from stock_discovery_analysis.real_access import source_access
from stock_discovery_analysis.real_views import ViewConfig, eligible_revisions
from stock_discovery_analysis.read_fences import guarded_read, authorize_revision_dependencies
from stock_discovery_analysis.revisions import Revision
from stock_discovery_analysis.scheduling import ScheduleConfig, IST, utc
from stock_discovery_analysis.publication_store import now

ENV = 'STK_STORED_DEPLOYMENT_FILE'
DEPLOYMENT_ERRORS = frozenset({'deployment_code_mismatch', 'deployment_code_dirty',
    'deployment_runtime_preflight_missing', 'deployment_configuration_mismatch', 'deployment_code_not_merged',
    'private_file_permissions', 'private_directory_permissions', 'private_file_required',
    'deployment_path_missing', 'stored_execution_mode_required', 'deployment_loaded_code_mismatch',
    'policy_file_unsafe'})


def safe_failure(exc, fallback):
    return str(exc) if str(exc) in DEPLOYMENT_ERRORS else fallback


class CalendarEvidenceError(RuntimeError):
    pass


def evidence_check(condition, code):
    if not condition: raise CalendarEvidenceError(code)


def private_file(path):
    path = Path(path)
    check(path.is_absolute() and not path.is_symlink() and path.is_file(), 'private_file_required')
    stat = path.stat()
    check(stat.st_uid == os.getuid() and not stat.st_mode & 0o077, 'private_file_permissions')
    return path


def private_directory(path):
    path = Path(path)
    check(path.is_absolute() and not path.is_symlink() and path.is_dir(), 'private_directory_required')
    stat = path.stat()
    check(stat.st_uid == os.getuid() and not stat.st_mode & 0o077, 'private_directory_permissions')
    return path


def policy_hash(path):
    if path is None: return None
    path=Path(path)
    check(path.is_absolute() and path.is_file() and not path.is_symlink()
          and path.stat().st_uid==os.getuid() and not path.stat().st_mode & 0o022, 'policy_file_unsafe')
    return sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    check(result.returncode == 0, 'deployment_git_unavailable')
    return result.stdout.strip()


def deployment(repo, python, database, view, schedule, output):
    """Bind immutable input hashes and code; keep credentials in existing files."""
    repo = Path(repo).absolute(); python = Path(python).absolute()
    check(repo.is_dir() and python.is_file() and os.access(python, os.X_OK), 'deployment_path_missing')
    check(not git(repo, 'status', '--porcelain', '--untracked-files=no'), 'deployment_code_dirty')
    sha = git(repo, 'rev-parse', 'HEAD')
    check(schedule.code_version == sha, 'deployment_code_mismatch')
    private_file(database); private_file(view.sources.grant_file)
    return dict(version='stored-deployment-v1', code_sha=sha, repo=str(repo), python=str(python),
                database_file=str(Path(database).absolute()),
                view_file=str(Path(output).absolute() / 'view.json'),
                schedule_file=str(Path(output).absolute() / 'schedule.json'),
                view_hash=digest(view.model_dump(mode='json')), schedule_hash=digest(schedule.model_dump(mode='json')),
                policy_hash=policy_hash(view.policy_file),
                acquisition='disabled', model_execution='disabled', required_schema='0015')


def validate_deployment(path):
    path = private_file(path); private_directory(path.parent)
    data = json.loads(path.read_text())
    check(data['version'] == 'stored-deployment-v1' and data['required_schema'] == '0015', 'deployment_version_mismatch')
    check(data['acquisition'] == data['model_execution'] == 'disabled', 'stored_execution_mode_required')
    repo = Path(data['repo'])
    check(repo.is_absolute() and repo.is_dir() and Path(data['python']).is_absolute()
          and os.access(data['python'], os.X_OK), 'deployment_path_missing')
    check(git(repo, 'rev-parse', 'HEAD') == data['code_sha'], 'deployment_code_mismatch')
    check(not git(repo, 'status', '--porcelain', '--untracked-files=no'), 'deployment_code_dirty')
    check(not git(repo, 'rev-list', '--max-count=1', data['code_sha'], '--not', 'refs/remotes/origin/main'),
          'deployment_code_not_merged')
    # Older merged code does not enforce this manifest. Never call that deployment ready.
    check(ENV in (repo / 'worker/worker/main.py').read_text(), 'deployment_runtime_preflight_missing')
    private_file(data['database_file'])
    view = ViewConfig.model_validate_json(private_file(data['view_file']).read_text())
    schedule = ScheduleConfig.model_validate_json(private_file(data['schedule_file']).read_text())
    private_file(view.sources.grant_file)
    check(policy_hash(view.policy_file)==data['policy_hash'], 'deployment_configuration_mismatch')
    check(schedule.code_version == data['code_sha'] and digest(schedule.model_dump(mode='json')) == data['schedule_hash']
          and digest(view.model_dump(mode='json')) == data['view_hash'], 'deployment_configuration_mismatch')
    from .stored_research import handlers
    handlers(schedule, view)  # Existing scope/mode/input-hash contract; no execution.
    return data, schedule, view


def calendar_evidence(conn, schedule, view, clock):
    """Authorize original revisions and durable restrictions before returning metadata.

    Even a complete ingestion stream contains only positive sessions. It cannot
    attest the closed days needed to expand ScheduleCalendar.ends_on.
    """
    access = source_access(view.sources, clock)
    with guarded_read(conn, access) as guard:
        records = eligible_revisions(conn, LISTING, clock(), access)
        sessions = [r for r in records if r.data.kind == 'session']
        evidence_check(bool(sessions), 'calendar_revisions_missing')
        # Validate and authorize all selected inputs and revision lineage. Reuse
        # existing original-grant fences, including parents of candle evidence.
        ids = {r.revision_id for r in records}
        pending = list(records); seen = set(); grants = {}; evidence = []; streams = set()
        while pending:
            revision = pending.pop()
            if revision.revision_id in seen: continue
            seen.add(revision.revision_id)
            row = conn.execute('''SELECT r.content_hash, s.complete, r.stream_id
                FROM discovery.revisions r JOIN discovery.streams s USING(stream_id)
                WHERE r.revision_id=%s''', (revision.revision_id,)).fetchone()
            evidence_check(row and row[0] == revision.content_hash and row[1], 'stored_revision_incomplete_or_invalid')
            if row[2] not in streams:
                streams.add(row[2])
                pages = conn.execute('SELECT cursor_key,next_cursor,complete,quarantined FROM discovery.pages WHERE stream_id=%s', (row[2],)).fetchall()
                complete_pages(pages)
            if revision.supersedes_id:
                raw = conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s', (revision.supersedes_id,)).fetchone()
                evidence_check(bool(raw), 'revision_lineage_missing')
                parent = Revision.model_validate(raw[0])
                evidence_check(parent.source_id == revision.source_id and parent.logical_key == revision.logical_key
                      and parent.sequence + 1 == revision.sequence, 'revision_lineage_conflict')
                ids.add(parent.revision_id); pending.append(parent)
            if revision.data.kind == 'session':
                evidence.append(dict(revision_id=revision.revision_id, source_id=revision.source_id,
                    content_hash=revision.content_hash, available_at=revision.available_at,
                    fetched_at=revision.fetched_at, supersedes_id=revision.supersedes_id))
        authorize_revision_dependencies(conn, sorted(ids), clock())
        for grant, stream, scopes in guard.dependencies().values():
            current = access.load_grant(stream)
            for g in (grant, current):
                evidence_check(g is not None, 'source_authorization_missing')
                key=(g.grant_id, g.version)
                prior=grants.get(key)
                grants[key] = dict(grant_id=g.grant_id, version=g.version,
                    source_id=g.source_id, status=g.status, expires_at=g.expires_at,
                    retention_days=g.retention_days)
                if prior:
                    # A later date in the current file never extends original rights.
                    grants[key]['expires_at']=min(prior['expires_at'],g.expires_at)
            # Retention covers original fetch dates, not the latest run time.
        retention_until = []
        for rid in guard.dependencies():
            raw = conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s', (rid,)).fetchone()[0]
            deadline = at(raw['fetched_at']) + timedelta(days=view.sources.retention_days)
            evidence_check(at(clock()) < deadline, 'stored_retention_expired')
            retention_until.append(deadline)
        by_day = {}
        for revision in sessions:
            day = utc(revision.data.opens_at).astimezone(IST).date().isoformat()
            by_day.setdefault(day, []).append(revision)
        for session in schedule.calendar.sessions:
            day = utc(session.opens_at).astimezone(IST).date().isoformat()
            matches = by_day.get(day, [])
            evidence_check(len(matches) == 1, 'calendar_revision_missing_or_conflicting')
            evidence_check((matches[0].data.opens_at, matches[0].data.closes_at) == (session.opens_at, session.closes_at), 'calendar_revision_conflict')
        configured = {s.opens_at for s in schedule.calendar.sessions}
        evidence_check(all(r.data.opens_at in configured for r in sessions
                  if schedule.calendar.starts_on <= utc(r.data.opens_at).astimezone(IST).date().isoformat() <= schedule.calendar.ends_on),
              'calendar_coverage_conflict')
        future = [r for r in sessions if at(r.data.opens_at) > at(clock())]
        return dict(session_revision_count=len(sessions), revision_evidence=evidence,
                    future_revision_count=len(future), grants=list(grants.values()),
                    earliest_retention_expiry=min(retention_until).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    latest_stored_candle=max((r.data.ends_at for r in records if r.data.kind == 'candle'), default=None))


def inspect(conn, schedule, view, *, clock=now, include_analysis=False):
    from .stored_research import handlers
    handlers(schedule, view)
    observed = clock(); clock = lambda: observed
    calendar = lifecycle(schedule, observed)
    reasons = list(calendar['reasons']); warnings = list(calendar['warnings'])
    result = dict(evaluated_at=observed, code_sha=schedule.code_version, scope=list(view.listing_ids),
        acquisition='disabled', model_execution='disabled', provider_requests=0, model_requests=0,
        actionable=False, calendar=calendar, reasons=reasons, warnings=warnings)
    result['database'] = conn.execute('SELECT current_database()').fetchone()[0]
    result['schema'] = conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    if result['schema'] != '0015':
        reasons.append('database_schema_incompatible')
    else:
        from stock_discovery_contracts.rights import Grant
        try:
            configured_grants = [Grant.model_validate_json(json.dumps(g)) for g in json.loads(Path(view.sources.grant_file).read_text())]
            identities=set(conn.execute('''SELECT DISTINCT s.source_id,s.account_ref
                FROM discovery.revisions r JOIN discovery.streams s USING(stream_id)
                WHERE (r.listing_id=%s OR (r.kind='session' AND r.listing_id='NSE'))
                AND r.available_at<=%s AND r.payload->>'availability_basis'='observed'
                AND (r.payload->>'fetched_at')::timestamptz<=%s''',(LISTING,observed,observed)).fetchall())
            configured_grants=[g for g in configured_grants if (g.source_id,g.account_ref) in identities]
            if not configured_grants: reasons.append('source_authorization_missing')
            result['configured_grants'] = [dict(source_id=g.source_id, status=g.status, expires_at=g.expires_at) for g in configured_grants]
            for g in configured_grants:
                if g.status != 'active' or g.revoked_at: reasons.append('source_grant_inactive_or_revoked')
                if at(g.expires_at) <= at(observed): reasons.append('source_grant_expired')
        except (ValueError, OSError): reasons.append('source_authorization_missing_or_invalid')
        try:
            evidence = calendar_evidence(conn, schedule, view, clock)
            result.update(evidence)
            calendar['renewal']['stored_sessions_available'] = evidence['future_revision_count'] > 0
            if not evidence['future_revision_count']:
                calendar['renewal']['reasons'].append('verified_future_session_revisions_missing')
            if (calendar['next_scheduled_execution']
                and at(evidence['earliest_retention_expiry']) <= at(calendar['next_scheduled_execution'])):
                reasons.append('retention_expires_before_next_execution')
            for grant in evidence['grants']:
                expiry = at(grant['expires_at'])
                if expiry <= at(observed) + timedelta(days=7): warnings.append('source_grant_expiring_soon')
                if calendar['next_scheduled_execution'] and expiry <= at(calendar['next_scheduled_execution']):
                    reasons.append('source_grant_expires_before_next_execution')
        except PermissionError:
            reasons.append('stored_source_authorization_or_evidence_denied')
            calendar['renewal']['reasons'].append('stored_source_authorization_or_evidence_denied')
        except CalendarEvidenceError as exc:
            reasons.append(str(exc))
            calendar['renewal']['reasons'].append(str(exc))
        except ValueError:
            # guarded_read deliberately sanitizes evidence/rights failures.
            reasons.append('stored_calendar_evidence_invalid')
        result['receipts'] = run_status(conn, view)
        result['latest_failed_or_partial'] = failed_receipt(conn, schedule)
        if result['latest_failed_or_partial']: warnings.append('failed_or_partial_research_receipt')
        if include_analysis and not reasons:
            try:
                report = research(conn, view, LISTING, clock=clock)
                result['analysis'] = dict(state=report['state'], freshness=report['market']['freshness'],
                    chart_points=report['market']['chart_points'], evidence_hash=report['evidence_hash'])
                if report['state'] != 'current_descriptive': warnings.append('research_not_current')
            except PermissionError: reasons.append('stored_analysis_access_denied')
    # Even a valid calendar has a finite horizon and cannot renew in this mode.
    warnings.append('calendar_renewal_requires_verified_coverage_and_owner_authorization')
    result['reasons'] = sorted(set(reasons)); result['warnings'] = sorted(set(warnings))
    result['status'] = 'BLOCKED' if reasons else 'READY_WITH_LIMITATIONS' if warnings else 'READY'
    result['recurring_activation_safe'] = not reasons
    return result


def check_deployment(path, *, include_analysis=True):
    """Private CLI/activation check. Errors never include DSNs or source payloads."""
    import psycopg
    try:
        data, schedule, view = validate_deployment(path)
        with psycopg.connect(Path(data['database_file']).read_text().strip(), autocommit=True, connect_timeout=5) as conn:
            return inspect(conn, schedule, view, include_analysis=include_analysis)
    except (ValueError, KeyError, OSError, PermissionError, psycopg.Error) as exc:
        safe = safe_failure(exc, 'deployment_or_database_preflight_failed')
        return dict(status='BLOCKED', recurring_activation_safe=False,
                    reasons=[safe], provider_requests=0, model_requests=0)


def failed_receipt(conn, schedule):
    row = conn.execute('''SELECT job_id,status,error_code,updated_at,result->>'report_state'
        FROM discovery.schedule_jobs WHERE stage='ingest' AND payload->>'scope_id'=%s
        AND payload->>'input_hash'=%s AND status IN ('failed','partial')
        ORDER BY updated_at DESC,job_id DESC LIMIT 1''', (schedule.scope_id, schedule.input_hash)).fetchone()
    return None if row is None else dict(job_id=row[0], status=row[1], error=row[2], at=str(row[3]), analysis_state=row[4])


def complete_pages(pages):
    """Read-side structural check, including pre-0015 accepted streams.

    Original revision grants are authorized by ReadGuard. The ingestion helper
    requires acquire rights and newer page attribution, so is not a read gate.
    """
    evidence_check(pages and all(p[3] == 0 for p in pages), 'stored_pages_missing_or_quarantined')
    by_cursor = {p[0]: p for p in pages}; visited = set(); cursor = ''
    while True:
        evidence_check(cursor in by_cursor and cursor not in visited, 'stored_page_chain_incomplete')
        visited.add(cursor); _, following, complete, _ = by_cursor[cursor]
        evidence_check(complete == (following is None), 'stored_page_chain_incomplete')
        if complete: break
        cursor = following
    evidence_check(len(visited) == len(pages), 'stored_page_chain_incomplete')


def cycle(path, schedule, view, schedule_file, view_file, database_url, handlers, *, clock=now):
    """One supervised iteration; same tick, singleton and receipt fencing as before."""
    import psycopg
    from stock_discovery_analysis.schedule_runner import tick
    from .pilot_operations import atomic
    # Fail before choosing a diagnostic destination if its ownership is unsafe.
    directory = private_directory(Path(path).absolute().parent)
    try:
        data, checked_schedule, checked_view = validate_deployment(path)
        check(schedule == checked_schedule and view == checked_view
              and Path(schedule_file).absolute() == Path(data['schedule_file'])
              and Path(view_file).absolute() == Path(data['view_file'])
              and database_url == Path(data['database_file']).read_text().strip(), 'deployment_configuration_mismatch')
        check(Path(__file__).resolve().parents[2] == Path(data['repo']).resolve(), 'deployment_loaded_code_mismatch')
        with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as conn:
            result = inspect(conn, schedule, view, clock=clock)
            if result['status'] != 'BLOCKED':
                result['worker_result'] = tick(conn, schedule, handlers=handlers, clock=clock, lease_seconds=120)
                # Refresh receipt metadata after the existing scheduler commits.
                result['receipts'] = run_status(conn, view)
                result['latest_failed_or_partial'] = failed_receipt(conn, schedule)
                if result['latest_failed_or_partial']:
                    result['warnings'] = sorted(set(result['warnings']) | {'failed_or_partial_research_receipt'})
    except Exception as exc:
        # Never persist an exception containing connection strings/source content.
        result = dict(status='BLOCKED', reasons=[safe_failure(exc, 'stored_worker_preflight_or_execution_failed')],
                      evaluated_at=clock(), provider_requests=0, model_requests=0)
    health = directory / 'health.json'
    check(not health.is_symlink() and not health.with_suffix('.json.tmp').is_symlink(), 'diagnostic_symlink_refused')
    atomic(health, result)  # One bounded latest snapshot, not an unbounded log.
    return result
