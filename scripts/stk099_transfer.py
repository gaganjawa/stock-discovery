"""STK-099: non-destructive Docker PostgreSQL backup/restore with full fingerprints.

No URL/password arguments. Uses the container's local owner socket. Restoration
requires a new database; never cleans, drops, truncates or migrates a target.
Stop source writers first. Private manifests contain only counts and hashes.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def identifier(value):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', value):
        raise ValueError('invalid_identifier')
    return value


class Database:
    def __init__(self, container, owner, name, context=None):
        self.name = identifier(name)
        self.owner = identifier(owner)
        self.command = ['docker'] + (['--context', context] if context else []) + ['exec', '-i', container]

    def run(self, args, **kwargs):
        return subprocess.run(self.command + args, check=True, stderr=subprocess.PIPE, **kwargs)

    def sql(self, query, database=None):
        return self.run(['psql', '-X', '-U', self.owner, '-d', database or self.name,
                         '-At', '-v', 'ON_ERROR_STOP=1'], input=query.encode(), stdout=subprocess.PIPE).stdout.decode().strip()

    @contextmanager
    def exported_snapshot(self):
        # Keep the exporting transaction alive until pg_dump and fingerprints finish.
        command=self.command+['psql','-X','-qAt','-U',self.owner,'-d',self.name,'-v','ON_ERROR_STOP=1']
        with subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True) as proc:
            try:
                proc.stdin.write('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT pg_export_snapshot();\n');proc.stdin.flush()
                snapshot=proc.stdout.readline().strip()
                if not re.fullmatch(r'[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+',snapshot):
                    raise RuntimeError('snapshot_export_failed')
                yield snapshot
            finally:
                if proc.poll() is None:
                    proc.stdin.write('ROLLBACK;\n');proc.stdin.close()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)

    def snapshot(self, snapshot_id=None):
        if snapshot_id and not re.fullmatch(r'[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+',snapshot_id):
            raise ValueError('invalid_exported_snapshot')
        def wrap(query):
            return ("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET TRANSACTION SNAPSHOT '"+snapshot_id+"'; "+query+'; COMMIT') if snapshot_id else query
        def query(statement):
            if not snapshot_id:return self.sql(statement)
            return self.run(['psql','-X','-qAt','-U',self.owner,'-d',self.name,'-v','ON_ERROR_STOP=1','-c',wrap(statement)],stdout=subprocess.PIPE).stdout.decode().strip()
        tables = query("SELECT schemaname||'.'||tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1").splitlines()
        result = {}
        for table in tables:
            schema, name = map(identifier, table.split('.'))
            digest, count = hashlib.sha256(), 0
            command = ['psql', '-X', '-U', self.owner, '-d', self.name, '-qAt', '-v', 'ON_ERROR_STOP=1', '-c',
                       wrap(f'COPY (SELECT to_jsonb(t)::text FROM {schema}.{name} t ORDER BY 1) TO STDOUT')]
            with subprocess.Popen(self.command + command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
                for line in proc.stdout:
                    digest.update(line)
                    count += 1
                if proc.wait():
                    raise RuntimeError('fingerprint_failed')
            result[table] = dict(rows=count, sha256=digest.hexdigest())
        sequences = {}
        for sequence in query("SELECT schemaname||'.'||sequencename FROM pg_sequences WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1").splitlines():
            schema, name = map(identifier, sequence.split('.'))
            sequences[sequence] = query(f'SELECT last_value,is_called FROM {schema}.{name}')
        return dict(revision=query('SELECT version_num FROM public.alembic_version'), tables=result, sequences=sequences)


def checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def backup_online(db, destination, expected_cluster):
    if db.sql('SELECT system_identifier FROM pg_control_system()') != expected_cluster:
        raise ValueError('source_cluster_mismatch')
    with db.exported_snapshot() as snapshot:
        before=db.snapshot(snapshot)
        if before['revision'] not in ('0016','0017'):raise ValueError('supported_schema_0016_or_0017_required')
        with destination.open('xb') as output:
            db.run(['pg_dump','-U',db.owner,'-d',db.name,'-Fc','--snapshot',snapshot],stdout=output)
            output.flush();os.fsync(output.fileno())
        # Sequences are not MVCC: reject concurrent allocations rather than claim
        # a consistent restore. Row-only writes may proceed under the snapshot.
        if before != db.snapshot(snapshot):raise ValueError('sequence_or_schema_changed_retry_new_path')
    manifest=dict(source=db.name,cluster=expected_cluster,snapshot=before,sha256=checksum(destination),backup_mode='exported_read_only_snapshot')
    destination.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def backup(db, destination, expected_cluster):
    if db.sql('SELECT system_identifier FROM pg_control_system()') != expected_cluster:
        raise ValueError('source_cluster_mismatch')
    before = db.snapshot()
    if before['revision'] not in ('0016','0017'):
        raise ValueError('supported_schema_0016_or_0017_required')
    with destination.open('xb') as output:
        db.run(['pg_dump', '-U', db.owner, '-d', db.name, '-Fc'], stdout=output)
        output.flush(); os.fsync(output.fileno())
    if before != db.snapshot():
        raise ValueError('source_changed_quiesce_writers_and_retry_new_path')
    manifest = dict(source=db.name, cluster=expected_cluster, snapshot=before,
                    sha256=checksum(destination))
    destination.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def restore(db, dump, manifest, owner, *, expected_source=None, expected_source_cluster=None):
    if checksum(dump) != manifest['sha256']:
        raise ValueError('backup_checksum_mismatch')
    if not expected_source or not expected_source_cluster:
        raise ValueError('expected_source_identity_required')
    if manifest.get('source') != expected_source:
        raise ValueError('source_database_mismatch')
    if manifest.get('cluster') != expected_source_cluster:
        raise ValueError('source_cluster_mismatch')
    if db.name in ('postgres', 'template0', 'template1', 'chartink_inbox', 'stock_discovery'):
        raise ValueError('protected_destination')
    # CREATE DATABASE fails if present; no overwrite path exists.
    db.sql(f'CREATE DATABASE {identifier(db.name)} OWNER {identifier(owner)} TEMPLATE template0', 'postgres')
    with dump.open('rb') as data:
        db.run(['pg_restore', '-U', db.owner, '-d', db.name, '--role', owner,
                '--no-owner', '--exit-on-error', '--single-transaction'], stdin=data, stdout=subprocess.DEVNULL)
    actual = db.snapshot()
    if actual != manifest['snapshot']:
        raise ValueError('restore_fingerprint_mismatch_leave_target_for_investigation')
    return actual


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['backup', 'restore', 'verify'])
    p.add_argument('--container', required=True)
    p.add_argument('--context')
    p.add_argument('--owner', required=True)
    p.add_argument('--database', required=True)
    p.add_argument('--dump', type=Path, required=True)
    p.add_argument('--expected-cluster')
    p.add_argument('--online',action='store_true',help='Consistent exported snapshot; sequence changes still fail closed')
    p.add_argument('--restore-owner')
    p.add_argument('--expected-source-database')
    p.add_argument('--expected-source-cluster')
    args = p.parse_args()
    os.umask(0o077)
    db = Database(args.container, args.owner, args.database, args.context)
    if args.action == 'backup':
        if not args.expected_cluster: p.error('--expected-cluster required')
        (backup_online if args.online else backup)(db, args.dump, args.expected_cluster)
    else:
        manifest = json.loads(args.dump.with_suffix('.manifest.json').read_text())
        if args.action == 'restore':
            if not args.restore_owner: p.error('--restore-owner required')
            if not args.expected_source_database or not args.expected_source_cluster:
                p.error('--expected-source-database and --expected-source-cluster required')
            restore(db, args.dump, manifest, args.restore_owner,
                    expected_source=args.expected_source_database, expected_source_cluster=args.expected_source_cluster)
        elif db.snapshot() != manifest['snapshot']:
            raise ValueError('verification_mismatch')
    print(json.dumps(dict(action=args.action, database=args.database, verified=True)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not expose subprocess stderr, DSNs, row content or credentials.
        raise SystemExit('STK-099 transfer failed: '+type(exc).__name__) from None
