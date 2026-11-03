"""STK-079: activate, check or stop the reviewed pilot LaunchAgent on the owner's Mac.

Activation needs the explicit approval phrase and refuses unless the target
database is already at the required schema. It never migrates, never changes
power settings and never calls a provider itself; the worker's own grants apply.
"""
import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

LABEL = 'local.stock-discovery.research'
APPROVAL = 'I approve unattended local research refresh'
REQUIRED_SCHEMA = '0015'


def agent_path(home=None):
    return Path(home or Path.home()) / 'Library/LaunchAgents' / (LABEL + '.plist')


def schema_version(database_url_file):
    import psycopg
    url = Path(database_url_file).read_text().strip()
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        conn.execute('SET default_transaction_read_only = on')
        return conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]


def preflight(reviewed, *, schema=schema_version):
    data = plistlib.loads(Path(reviewed).read_bytes())
    if data.get('Label') != LABEL:raise ValueError('unexpected_launch_label')
    args = data['ProgramArguments']
    if args[1:3] != ['-m', 'worker.main'] or '--real-pilot-config' not in args:raise ValueError('unexpected_launch_program')
    paths = [args[0], data['WorkingDirectory'], data['EnvironmentVariables']['DATABASE_URL_FILE'],
             args[args.index('--schedule-config') + 1], args[args.index('--real-pilot-config') + 1]]
    if not all(Path(p).exists() for p in paths):raise ValueError('launch_path_missing')
    if 'DATABASE_URL' in data['EnvironmentVariables']:raise ValueError('inline_database_secret_forbidden')
    version = schema(data['EnvironmentVariables']['DATABASE_URL_FILE'])
    if version != REQUIRED_SCHEMA:raise ValueError('database_migration_required')
    return data


def activate(reviewed, approval, *, home=None, run=subprocess.run, schema=schema_version, uid=None):
    if approval != APPROVAL:raise PermissionError('owner_approval_phrase_required')
    preflight(reviewed, schema=schema)
    target = agent_path(home)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'xb') as out, open(reviewed, 'rb') as source:
        os.chmod(target, 0o600);shutil.copyfileobj(source, out)
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'bootstrap', domain, str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        target.unlink()
        raise RuntimeError('launchctl_bootstrap_failed')
    return dict(status='active', label=LABEL, plist=str(target))


def deactivate(*, home=None, run=subprocess.run, uid=None):
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'bootout', f'{domain}/{LABEL}'], capture_output=True, text=True)
    target = agent_path(home)
    if target.exists():target.unlink()
    return dict(status='inactive', label=LABEL, was_loaded=result.returncode == 0)


def status(*, run=subprocess.run, uid=None):
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'print', f'{domain}/{LABEL}'], capture_output=True, text=True)
    if result.returncode != 0:return dict(status='inactive', label=LABEL)
    fields = dict(line.strip().split(' = ', 1) for line in result.stdout.splitlines() if ' = ' in line)
    return dict(status='active', label=LABEL, state=fields.get('state'), runs=fields.get('runs'),
                last_exit=fields.get('last exit code'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('activate');a.add_argument('--reviewed-plist', type=Path, required=True);a.add_argument('--approval', required=True)
    sub.add_parser('deactivate');sub.add_parser('status')
    args = p.parse_args()
    if sys.platform != 'darwin':raise SystemExit('macOS launchd only')
    result = activate(args.reviewed_plist, args.approval) if args.action == 'activate' else deactivate() if args.action == 'deactivate' else status()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':main()
