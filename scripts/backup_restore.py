"""Streaming PostgreSQL backup and verification into a disposable database."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import uuid

COMPOSE = shlex.split(os.environ.get("STK_COMPOSE_COMMAND", "docker-compose" if shutil.which("docker-compose") else "docker compose"))


def command(script, *args, input=None, stdin=None, stdout=subprocess.PIPE):
    return subprocess.run([*COMPOSE, "exec", "-T", "database", "sh", "-c", script, "backup", *args],
                          input=input, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, check=True).stdout


def fingerprint(db=None):
    script = 'psql -X -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" -At -v ON_ERROR_STOP=1'
    tables = command(script, db or "", input=b"SELECT tablename FROM pg_tables WHERE schemaname='research' ORDER BY tablename;").decode().splitlines()
    result = {}
    for table in tables:
        if not table.replace("_", "").isalnum():
            raise ValueError("Unexpected table name")
        sql = f'SELECT row_to_json(t)::text FROM research.{table} t ORDER BY row_to_json(t)::text;'
        # Stream rows; never buffer the dataset or dump in the Python process.
        with subprocess.Popen([*COMPOSE, "exec", "-T", "database", "sh", "-c", script,
                               "backup", db or ""], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL) as proc:
            proc.stdin.write(sql.encode()); proc.stdin.close()
            digest = hashlib.sha256()
            while block := proc.stdout.read(1024 * 1024):
                digest.update(block)
            if proc.wait():
                raise RuntimeError("Fingerprint query failed")
            result[table] = digest.hexdigest()
    return result


def verify_restore(dump, expected):
    name = "stk_restore_" + uuid.uuid4().hex[:12]
    command('createdb -U "$POSTGRES_USER" "$1"', name)
    try:
        with Path(dump).open("rb") as source:
            command('pg_restore -U "$POSTGRES_USER" -d "$1" --single-transaction --exit-on-error',
                    name, stdin=source)
        if fingerprint(name) != expected:
            raise AssertionError("Restored research records differ")
        return command('psql -X -U "$POSTGRES_USER" -d "$1" -At -c "SELECT version_num FROM alembic_version"', name).decode().strip()
    finally:
        command('dropdb -U "$POSTGRES_USER" "$1"', name)


def backup(destination, verify=False):
    destination = Path(destination)
    before = fingerprint()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        command('exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc', stdout=out)
        out.flush(); os.fsync(out.fileno())
    if fingerprint() != before:
        raise ValueError("Source changed during backup; quiesce writers")
    schema = verify_restore(destination, before) if verify else None
    with destination.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    return {"research_tables": before, "sha256": checksum, "schema": schema}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--verify-restore", action="store_true")
    args = parser.parse_args()
    backup(args.destination, args.verify_restore)
    print("PASS: backup created" + (" and disposable restore verified" if args.verify_restore else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("FAIL: backup/restore did not complete; do not trust an incomplete dump")
