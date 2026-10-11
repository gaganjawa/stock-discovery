"""Back up the local database and optionally verify into a new disposable database."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import uuid

COMPOSE=['docker-compose'] if shutil.which('docker-compose') else ['docker','compose']


def command(script,*args,input=None):
    return subprocess.run([*COMPOSE,'exec','-T','database','sh','-c',script,'backup',*args],
                          input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout


def fingerprint(db=None):
    script='psql -X -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" -At -v ON_ERROR_STOP=1'
    tables=command(script,db or '',input=b"SELECT tablename FROM pg_tables WHERE schemaname='research' ORDER BY tablename;").decode().splitlines()
    result={}
    for table in tables:
        # Names are read from this application's schema; validate before SQL interpolation.
        if not table.replace('_','').isalnum(): raise ValueError('unexpected table name')
        sql=f'SELECT row_to_json(t)::text FROM research.{table} t ORDER BY row_to_json(t)::text;'
        result[table]=hashlib.sha256(command(script,db or '',input=sql.encode())).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('destination',type=Path)
    parser.add_argument('--verify-restore',action='store_true')
    args=parser.parse_args()
    if args.destination.exists(): raise ValueError('refusing to overwrite an existing backup')
    before=fingerprint()
    dump=command('exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc')
    args.destination.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(args.destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f: f.write(dump)
    if fingerprint()!=before: raise ValueError('source changed during backup; quiesce writes before verification')
    if args.verify_restore:
        name='stk_restore_'+uuid.uuid4().hex[:12]
        command('createdb -U "$POSTGRES_USER" "$1"',name)
        try:
            command('pg_restore -U "$POSTGRES_USER" -d "$1" --single-transaction --exit-on-error',name,input=dump)
            if fingerprint(name)!=before: raise AssertionError('restored research records differ')
        finally:
            command('dropdb -U "$POSTGRES_USER" "$1"',name)
        print('PASS: backup restored into disposable database; every research table hash matches')
    print('Backup created with owner-only permissions; encrypt before off-host storage.')


if __name__=='__main__': main()
