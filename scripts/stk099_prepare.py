"""STK-099 create NEW private app credentials and reviewable role SQL, never apply.

Run on the approved host after review. Does not read or change receiver secrets.
Keep this directory outside Git; apply bootstrap.sql explicitly as cluster owner.
"""
import argparse
import os
from pathlib import Path
import secrets


def prepare(directory):
    os.umask(0o077)
    directory.mkdir(mode=0o700,parents=False,exist_ok=False)
    roles={'stk_runtime':'app_url','stk_candidate_worker':'worker_url','stk_inbox_reader':'source_url'}
    statements=['-- STK-099: new roles only; fail rather than alter existing credentials.',
                'BEGIN;', 'CREATE ROLE stk_app_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;']
    for role,name in roles.items():
        password=secrets.token_hex(32)
        database='chartink_inbox' if role=='stk_inbox_reader' else 'stk_real001_private'
        (directory/name).write_text(f'postgresql://{role}:{password}@database/{database}\n')
        statements.append(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{password}';")
    statements.append('COMMIT;')
    (directory/'bootstrap.sql').write_text('\n'.join(statements)+'\n')
    (directory/'owner_access').write_text(secrets.token_hex(32)+'\n')
    print('Prepared private files. No database or service changed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    prepare(parser.parse_args().directory)
