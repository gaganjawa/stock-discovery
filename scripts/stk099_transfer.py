"""STK-099: non-destructive Docker PostgreSQL backup/restore with full fingerprints.

No URL/password arguments. Uses the container's local owner socket. Restoration
requires a new database; never cleans, drops, truncates or migrates a target.
Stop source writers first. Private manifests contain only counts and hashes.
"""
import argparse
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

    def snapshot(self):
        tables = self.sql("SELECT schemaname||'.'||tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1").splitlines()
        result = {}
        for table in tables:
            schema, name = map(identifier, table.split('.'))
            digest, count = hashlib.sha256(), 0
            command = ['psql', '-X', '-U', self.owner, '-d', self.name, '-At', '-v', 'ON_ERROR_STOP=1', '-c',
                       f'COPY (SELECT to_jsonb(t)::text FROM {schema}.{name} t ORDER BY 1) TO STDOUT']
            with subprocess.Popen(self.command + command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
                for line in proc.stdout:
                    digest.update(line)
                    count += 1
                if proc.wait():
                    raise RuntimeError('fingerprint_failed')
            result[table] = dict(rows=count, sha256=digest.hexdigest())
        sequences = {}
        for sequence in self.sql("SELECT schemaname||'.'||sequencename FROM pg_sequences WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1").splitlines():
            schema, name = map(identifier, sequence.split('.'))
            sequences[sequence] = self.sql(f'SELECT last_value,is_called FROM {schema}.{name}')
        return dict(revision=self.sql('SELECT version_num FROM public.alembic_version'), tables=result, sequences=sequences)


def checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


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


def restore(db, dump, manifest, owner):
    if checksum(dump) != manifest['sha256']:
        raise ValueError('backup_checksum_mismatch')
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
    p.add_argument('--restore-owner')
    args = p.parse_args()
    os.umask(0o077)
    db = Database(args.container, args.owner, args.database, args.context)
    if args.action == 'backup':
        if not args.expected_cluster: p.error('--expected-cluster required')
        backup(db, args.dump, args.expected_cluster)
    else:
        manifest = json.loads(args.dump.with_suffix('.manifest.json').read_text())
        if args.action == 'restore':
            if not args.restore_owner: p.error('--restore-owner required')
            restore(db, args.dump, manifest, args.restore_owner)
        elif db.snapshot() != manifest['snapshot']:
            raise ValueError('verification_mismatch')
    print(json.dumps(dict(action=args.action, database=args.database, verified=True)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not expose subprocess stderr, DSNs, row content or credentials.
        raise SystemExit('STK-099 transfer failed: '+type(exc).__name__) from None
