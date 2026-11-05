"""STK-014/074/079: rehearse the retained-database upgrade on a restored copy only.

1. Fingerprint the original (read-only), stream a verified custom-format dump.
2. Restore it into a new database, prove every table fingerprint is identical.
3. Upgrade only the copy to head twice, prove every pre-existing row is unchanged,
   and that each stored grant received OPEN provider/account/grant fences.
The original is never migrated, written or dropped. Prints a sanitized JSON report.
Usage (owner, on the Mac, writers stopped):
  DATABASE_URL_FILE=<private file> python scripts/rehearse_migration.py backups/<name>.dump [--keep-copy]
"""
import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_retained_database import database_url, fingerprints  # noqa: E402
from backup_restore import command  # noqa: E402


def verify_target(url, *, run=command, connect=None):
    """Prove URL and Compose reach the same database/lock manager, before any copy.

    A random session advisory lock also distinguishes byte-identical cloned
    clusters. No row/schema writes, credentials, or provider calls are involved.
    """
    import psycopg
    connect=connect or psycopg.connect
    source=psycopg.conninfo.conninfo_to_dict(url)['dbname']
    challenge=uuid.uuid4().int & ((1<<63)-1)
    with connect(url,autocommit=True,connect_timeout=5,options='-c default_transaction_read_only=on') as conn:
        conn.execute('SELECT pg_advisory_lock(%s)',(challenge,))
        try:
            result=run('psql -X -U "$POSTGRES_USER" -d "$1" -At -v ON_ERROR_STOP=1 -c "SELECT NOT pg_try_advisory_lock($2::bigint)"',source,str(challenge))
            if result.strip()!=b't':raise ValueError('database_target_mismatch')
        finally:
            conn.execute('SELECT pg_advisory_unlock(%s)',(challenge,))


def compare(before, after):
    changed = sorted(t for t in before if after.get(t) != before[t])
    return dict(unchanged=not changed, changed=changed, added=sorted(set(after) - set(before)))


def upgrade(url):
    from alembic import command as alembic
    from alembic.config import Config
    from psycopg.conninfo import conninfo_to_dict
    from sqlalchemy.engine import URL
    info = conninfo_to_dict(url)
    os.environ.pop('DATABASE_URL_FILE', None)
    os.environ['DATABASE_URL'] = URL.create('postgresql+psycopg', username=info.get('user'), password=info.get('password'),
        host=info.get('host'), port=int(info.get('port', 5432)), database=info['dbname']).render_as_string(hide_password=False)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    alembic.upgrade(config, 'head')
    alembic.upgrade(config, 'head')


def fence_check(conn):
    expected = {(k, s, a, g, v) for s, a, g, v in conn.execute(
        "SELECT payload->>'source_id',payload->>'account_ref',grant_id,version FROM discovery.grants")
        for k, a, g, v in (('provider', '', '', ''), ('account', a, '', ''), ('grant', a, g, v))}
    stored = set(conn.execute("SELECT kind,source_id,account_ref,grant_id,grant_version FROM discovery.grant_fences WHERE state='OPEN' AND generation=0").fetchall())
    return dict(expected=len(expected), open_registered=len(stored), all_registered=expected <= stored,
                restriction_requests=conn.execute('SELECT count(*) FROM discovery.restriction_requests').fetchone()[0],
                legacy_pages_unattributed=conn.execute('SELECT count(*) FROM discovery.pages p WHERE NOT EXISTS (SELECT FROM discovery.ingestion_grants i WHERE (i.stream_id,i.cursor_key)=(p.stream_id,p.cursor_key))').fetchone()[0])


def main():
    import psycopg
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--keep-copy', action='store_true', help='leave the upgraded copy for browser acceptance')
    args = parser.parse_args()
    url = database_url()
    source = psycopg.conninfo.conninfo_to_dict(url)['dbname']
    copy = 'stk_rehearsal_' + uuid.uuid4().hex[:12]
    copy_url = psycopg.conninfo.make_conninfo(url, dbname=copy)

    def snapshot(target):
        with psycopg.connect(target, connect_timeout=5) as conn:
            conn.read_only = True
            version = [v[0] for v in conn.execute('SELECT version_num FROM alembic_version')]
            return version, fingerprints(conn)

    verify_target(url)
    version, before = snapshot(url)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        command('exec pg_dump -U "$POSTGRES_USER" -d "$1" -Fc', source, stdout=out)
        out.flush()
        os.fsync(out.fileno())
    if snapshot(url)[1] != before:
        raise SystemExit('FAIL: original changed during backup; stop writers and retry')
    with args.destination.open('rb') as dump:
        checksum = hashlib.file_digest(dump, 'sha256').hexdigest()
    report = dict(original=dict(version=version, tables=len(before), rows=sum(t['rows'] for t in before.values())),
                  dump=dict(file=args.destination.name, sha256=checksum), copy=copy if args.keep_copy else 'dropped')
    command('createdb -U "$POSTGRES_USER" "$1"', copy)
    try:
        with args.destination.open('rb') as dump:
            command('pg_restore -U "$POSTGRES_USER" -d "$1" --single-transaction --exit-on-error', copy, stdin=dump)
        restored = snapshot(copy_url)
        report['restore'] = dict(version=restored[0], **compare(before, restored[1]))
        if not report['restore']['unchanged'] or restored[1].keys() != before.keys():
            raise AssertionError('restored copy differs from original')
        upgrade(copy_url)
        version_after, after = snapshot(copy_url)
        report['upgrade'] = dict(version=version_after, **compare(before, after))
        with psycopg.connect(copy_url, connect_timeout=5) as conn:
            report['fences'] = fence_check(conn)
        report['pass'] = (version_after in (['0015'],['0016']) and report['upgrade']['unchanged']
                          and report['fences']['all_registered'] and report['fences']['restriction_requests'] == 0)
        if snapshot(url)[1] != before:
            raise AssertionError('original changed during rehearsal')
        report['original_unchanged'] = True
    finally:
        if not args.keep_copy:
            command('dropdb -U "$POSTGRES_USER" "$1"', copy)
    print(json.dumps(report, indent=1))
    if not report.get('pass'):
        raise SystemExit('FAIL: rehearsal did not meet every gate; do not migrate the original')


if __name__ == '__main__':
    main()
