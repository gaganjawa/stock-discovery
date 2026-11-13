"""STK-095 D3-03/04/09: private Mac candidate supervisor; never installs itself.

Native Python shares the existing owner's file permissions. Only a fixed,
credential-free environment is inherited by the stored-only candidate worker.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import plistlib
import shlex
import signal
import subprocess
import sys
import threading
import time

LABEL = 'local.stock-discovery.chartink-consumer'
SCOPES = {'receive', 'store', 'derive', 'operational_replay'}


def private_file(path):
    p = Path(path)
    if not p.is_absolute() or not p.is_file() or p.stat().st_mode & 0o077:
        raise ValueError('private_file_required')
    return p


def environment(config):
    # Parse data, never source an arbitrary shell script or expand shell commands.
    values = {}
    for line in private_file(config['environment_file']).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, value = line.removeprefix('export ').split('=', 1)
        if key not in {'CHARTINK_RECEIVER_URL', 'CHARTINK_PULL_SECRET_FILE', 'CHARTINK_SCANNER_CONFIG'}:
            raise ValueError('unexpected_environment_key')
        parts = shlex.split(value)
        if len(parts) != 1 or key in values:
            raise ValueError('invalid_environment')
        values[key] = parts[0].replace('$HOME', str(Path.home()))
    if set(values) != {'CHARTINK_RECEIVER_URL', 'CHARTINK_PULL_SECRET_FILE', 'CHARTINK_SCANNER_CONFIG'}:
        raise ValueError('missing_environment_key')
    repo = Path(config['repo'])
    if not repo.is_absolute() or not (repo/'worker/worker/main.py').is_file():
        raise ValueError('release_path_invalid')
    values.update(DATABASE_URL_FILE=str(private_file(config['database_file'])),
                  REAL_RESEARCH_VIEW_CONFIG=str(private_file(config['view_file'])),
                  PYTHONPATH=os.pathsep.join(str(repo/x) for x in ('shared','worker','backend')),
                  PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
                  PATH='/usr/bin:/bin', HOME=str(Path.home()))
    private_file(values['CHARTINK_PULL_SECRET_FILE'])
    private_file(values['CHARTINK_SCANNER_CONFIG'])
    return values


def preflight(config, *, connect=None, clock=lambda: datetime.now(timezone.utc)):
    import psycopg
    from stock_discovery_analysis.chartink import Scanner
    from stock_discovery_analysis.candidate_store import digest
    from stock_discovery_analysis.real_views import ViewConfig
    from stock_discovery_contracts.rights import Grant
    from stock_discovery_contracts.v2 import Policy
    from urllib.parse import urlsplit
    env = environment(config)
    url = urlsplit(env['CHARTINK_RECEIVER_URL'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('receiver_url_invalid')
    scanner = Scanner.model_validate_json(Path(env['CHARTINK_SCANNER_CONFIG']).read_text())
    now = clock()
    if scanner.mode != 'provider_alert' or scanner.enabled_until <= now:
        raise ValueError('scanner_authorization_invalid')
    approval = json.loads(private_file(config['authorization_file']).read_text())
    if (approval['scanner_key'] != scanner.key or approval['rights_reference'] != scanner.rights_reference
        or not SCOPES <= set(approval['scopes']) or not approval.get('evidence_reference')
        or datetime.fromisoformat(approval['enabled_until']) <= now):
        raise ValueError('use_specific_approval_required')
    # A pending marker is never promoted to permission by an unattended launcher.
    if 'pending' in scanner.rights_reference.lower():
        raise ValueError('scanner_rights_review_pending')
    if len(Path(env['CHARTINK_PULL_SECRET_FILE']).read_text().strip()) < 32:
        raise ValueError('pull_secret_invalid')
    view = ViewConfig.model_validate_json(Path(env['REAL_RESEARCH_VIEW_CONFIG']).read_text())
    grants = json.loads(Path(view.sources.grant_file).read_text())
    if not isinstance(grants, list):
        raise ValueError('grant_list_required')
    for raw in grants:
        Grant.model_validate_json(json.dumps(raw))
    if view.policy_file:
        policies = json.loads(Path(view.policy_file).read_text())
        if not isinstance(policies, list):
            raise ValueError('policy_list_required')
        for raw in policies:
            Policy.model_validate_json(json.dumps(raw))
    with (connect or psycopg.connect)(Path(env['DATABASE_URL_FILE']).read_text().strip(),
            connect_timeout=5, options='-c default_transaction_read_only=on -c statement_timeout=15000 -c lock_timeout=2000') as conn:
        database, user = conn.execute('SELECT current_database(),current_user').fetchone()
        if database != config['database'] or user != 'stk_candidate_worker':
            raise ValueError('database_identity_mismatch')
        role = conn.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone()
        if any(role):
            raise ValueError('restricted_role_required')
        if conn.execute('SELECT version_num FROM alembic_version').fetchone() != ('0017',):
            raise ValueError('schema_0017_required')
        receiver_id = digest(env['CHARTINK_RECEIVER_URL'])
        if receiver_id != config['receiver_id']:
            raise ValueError('receiver_identity_mismatch')
        cursor = conn.execute('SELECT cursor FROM discovery.candidate_receivers WHERE receiver_id=%s', (receiver_id,)).fetchone()
        if cursor is None:
            raise ValueError('existing_cursor_required')
        for table, privileges in {
            'candidate_events': 'SELECT,INSERT', 'candidate_matches': 'SELECT,INSERT',
            'candidate_research_runs': 'SELECT,INSERT', 'candidate_receivers': 'SELECT,INSERT,UPDATE',
            'candidate_event_state': 'SELECT,INSERT,UPDATE', 'candidate_sessions': 'SELECT,INSERT,UPDATE',
            'candidates': 'SELECT,INSERT,UPDATE', 'revisions': 'SELECT',
        }.items():
            for privilege in privileges.split(','):
                if not conn.execute('SELECT has_table_privilege(current_user,%s,%s)', ('discovery.'+table, privilege)).fetchone()[0]:
                    raise ValueError('required_grant_missing')
        for privilege in ('USAGE', 'SELECT'):
            if not conn.execute("SELECT has_sequence_privilege(current_user,'discovery.candidate_events_sequence_seq',%s)", (privilege,)).fetchone()[0]:
                raise ValueError('required_sequence_grant_missing')
    return env, cursor[0]


def state(directory, status, **values):
    try:
        previous = json.loads((directory/'health.json').read_text())
        completed = datetime.fromisoformat(previous['completed_at']).isoformat()
        values['completed_at'] = completed
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if status == 'cycle_completed':
        values['completed_at'] = datetime.now(timezone.utc).isoformat()
    temporary = directory/'health.tmp'
    temporary.write_text(json.dumps(dict(status=status, at=datetime.now(timezone.utc).isoformat(), **values)))
    temporary.chmod(0o600)
    temporary.replace(directory/'health.json')


def supervise(config, *, check=preflight, stop=None, interval=5, cycle_timeout=180):
    directory = Path(config['state_directory'])
    if not directory.is_absolute() or not directory.is_dir() or directory.stat().st_mode & 0o077:
        raise ValueError('private_state_directory_required')
    stop = stop or threading.Event()
    with (directory/'consumer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while not stop.is_set():
            # Recheck expiration, grants and identity before every bounded cycle.
            env, cursor = check(config)
            if stop.is_set():
                break
            state(directory, 'running', cursor=cursor)
            child = subprocess.Popen([config['python'], '-m', 'worker.main', '--candidate-intake', '--once'],
                cwd=config['repo'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True, pass_fds=(lock.fileno(),))
            deadline = time.monotonic() + cycle_timeout
            timed_out = False
            while child.poll() is None:
                if stop.wait(0.1) or time.monotonic() >= deadline:
                    timed_out = not stop.is_set()
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL); child.wait()
                    break
            if timed_out:
                state(directory, 'cycle_timed_out')
            elif child.returncode and not stop.is_set():
                state(directory, 'cycle_failed')
            elif not stop.is_set():
                state(directory, 'cycle_completed')
            stop.wait(interval)
        state(directory, 'stopped')


def definition(manifest, config):
    return dict(Label=LABEL, ProgramArguments=[config['python'], str(Path(__file__).resolve()), 'run', str(manifest)],
        WorkingDirectory=config['repo'], EnvironmentVariables={'PYTHONPATH':str(Path(config['repo'])/'shared')},
        RunAtLoad=True, KeepAlive=True, ThrottleInterval=60, ExitTimeOut=40, Umask=63,
        StandardOutPath='/dev/null', StandardErrorPath='/dev/null')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check','run','prepare-plist'])
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    os.umask(0o077)
    config=json.loads(private_file(args.manifest).read_text())
    if args.action=='prepare-plist':
        if not args.output or 'LaunchAgents' in args.output.parts:
            raise ValueError('inactive_output_required')
        with args.output.open('xb') as out:plistlib.dump(definition(args.manifest.resolve(),config),out)
        print('Prepared inactive plist; not installed or started')
    elif args.action=='check':
        _,cursor=preflight(config);print(json.dumps(dict(status='ready',cursor=cursor)))
    else:
        stop=threading.Event()
        for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
        try:supervise(config,stop=stop)
        except BlockingIOError:
            raise
        except Exception:
            state(Path(config['state_directory']), 'preflight_or_runtime_failed')
            raise


if __name__=='__main__':
    try:main()
    except Exception:
        # Never include exception strings, paths, URLs or database errors.
        raise SystemExit('candidate_consumer_failed') from None
