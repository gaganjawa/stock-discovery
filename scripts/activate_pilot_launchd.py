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
STORED_LABEL = 'local.stock-discovery.infy-stored-research'
APPROVAL = 'I approve unattended local research refresh'
REQUIRED_SCHEMA = '0015'


def agent_path(home=None, *, label=LABEL):
    if label not in (LABEL,STORED_LABEL):raise ValueError('unexpected_launch_label')
    return Path(home or Path.home()) / 'Library/LaunchAgents' / (label + '.plist')


def schema_version(database_url_file):
    import psycopg
    url = Path(database_url_file).read_text().strip()
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        conn.execute('SET default_transaction_read_only = on')
        return conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]


def preflight(reviewed, *, schema=schema_version, stored_check=None):
    data = plistlib.loads(Path(reviewed).read_bytes())
    label=data.get('Label')
    if label not in (LABEL,STORED_LABEL):raise ValueError('unexpected_launch_label')
    flag='--stored-research-view' if label==STORED_LABEL else '--real-pilot-config'
    args = data['ProgramArguments']
    if args[1:3] != ['-m', 'worker.main'] or flag not in args:raise ValueError('unexpected_launch_program')
    if label==STORED_LABEL and any(x in args for x in ('--real-pilot-config','--real-market-config','--synthetic-schedule','--pilot-operations-directory')):raise ValueError('mixed_stored_research_mode')
    paths = [args[0], data['WorkingDirectory'], data['EnvironmentVariables']['DATABASE_URL_FILE'],
             args[args.index('--schedule-config') + 1], args[args.index(flag) + 1]]
    if not all(Path(p).exists() for p in paths):raise ValueError('launch_path_missing')
    if 'DATABASE_URL' in data['EnvironmentVariables']:raise ValueError('inline_database_secret_forbidden')
    version = schema(data['EnvironmentVariables']['DATABASE_URL_FILE'])
    if version not in (REQUIRED_SCHEMA,'0016'):raise ValueError('database_migration_required')
    if label==STORED_LABEL:
        from worker.stored_operations import check_deployment
        manifest=data['EnvironmentVariables'].get('STK_STORED_DEPLOYMENT_FILE')
        if not manifest:raise ValueError('stored_deployment_manifest_required')
        readiness=(stored_check or check_deployment)(manifest)
        if readiness['status']=='BLOCKED':raise ValueError('stored_deployment_not_ready:'+','.join(readiness['reasons']))
        # Manifest paths must describe exactly the reviewed launch program.
        bound=json.loads(Path(manifest).read_text())
        if (bound['repo']!=data['WorkingDirectory'] or bound['python']!=args[0]
            or bound['database_file']!=paths[2] or bound['schedule_file']!=paths[3] or bound['view_file']!=paths[4]):
            raise ValueError('launch_deployment_mismatch')
        expected=':'.join(str(Path(bound['repo'])/x) for x in ('backend','shared','worker'))
        if data['EnvironmentVariables'].get('PYTHONPATH')!=expected:raise ValueError('launch_deployment_mismatch')
    return data


def activate(reviewed, approval, *, home=None, run=subprocess.run, schema=schema_version, uid=None, stored_check=None):
    if approval != APPROVAL:raise PermissionError('owner_approval_phrase_required')
    data=preflight(reviewed, schema=schema,stored_check=stored_check);label=data['Label']
    target = agent_path(home,label=label)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'xb') as out, open(reviewed, 'rb') as source:
        os.chmod(target, 0o600);shutil.copyfileobj(source, out)
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'bootstrap', domain, str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        target.unlink()
        raise RuntimeError('launchctl_bootstrap_failed')
    return dict(status='active', label=label, plist=str(target))


def deactivate(*, home=None, run=subprocess.run, uid=None, label=LABEL):
    target=agent_path(home,label=label)
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'bootout', f'{domain}/{label}'], capture_output=True, text=True)
    # ESRCH (3) means no service; other errors do not establish shutdown.
    if result.returncode not in (0,3):raise RuntimeError('launchctl_shutdown_failed')
    stopped = run(['launchctl', 'print', f'{domain}/{label}'], capture_output=True, text=True)
    if stopped.returncode != 113:raise RuntimeError('launchctl_shutdown_unverified')
    if target.exists():target.unlink()
    return dict(status='inactive', label=label, was_loaded=result.returncode == 0)


def status(*, run=subprocess.run, uid=None, label=LABEL):
    agent_path(label=label)
    domain = f'gui/{uid if uid is not None else os.getuid()}'
    result = run(['launchctl', 'print', f'{domain}/{label}'], capture_output=True, text=True)
    if result.returncode == 113:return dict(status='inactive', label=label)
    if result.returncode != 0:raise RuntimeError('launchctl_status_unverified')
    fields = dict(line.strip().split(' = ', 1) for line in result.stdout.splitlines() if ' = ' in line)
    return dict(status='active', label=label, state=fields.get('state'), runs=fields.get('runs'),
                last_exit=fields.get('last exit code'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('activate');a.add_argument('--reviewed-plist', type=Path, required=True);a.add_argument('--approval', required=True)
    sub.add_parser('deactivate').add_argument('--stored-research',action='store_true');sub.add_parser('status').add_argument('--stored-research',action='store_true')
    args = p.parse_args()
    if sys.platform != 'darwin':raise SystemExit('macOS launchd only')
    result = activate(args.reviewed_plist, args.approval) if args.action == 'activate' else deactivate(label=STORED_LABEL if args.stored_research else LABEL) if args.action == 'deactivate' else status(label=STORED_LABEL if args.stored_research else LABEL)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':main()
