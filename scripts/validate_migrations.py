"""Migration lifecycle checks, restricted to an explicitly disposable database."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import psycopg
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def main():
    url = os.environ['STK_TEST_DATABASE_URL']
    if psycopg.conninfo.conninfo_to_dict(url).get('dbname') != 'stk013_test':
        raise ValueError('Only the disposable stk013_test database is allowed')
    os.environ['DATABASE_URL'] = url
    os.environ['PYTHONPATH'] = os.pathsep.join(str(ROOT / part) for part in ('backend','shared','worker'))
    config = Config(str(ROOT / 'backend/alembic.ini'))
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    subprocess.run([sys.executable, '-m', 'pytest', str(ROOT / 'backend/tests/integration'), '-q'], check=True)
    with psycopg.connect(url, autocommit=True) as db:
        db.execute('CREATE TABLE public.migration_test_sentinel (id integer)')
    command.downgrade(config, 'base')
    with psycopg.connect(url) as db:
        assert db.execute("SELECT count(*) FROM pg_namespace WHERE nspname='research'").fetchone()[0] == 0
        assert db.execute("SELECT to_regclass('public.migration_test_sentinel')").fetchone()[0] is not None
    command.upgrade(config, 'head')
    with tempfile.TemporaryDirectory() as temp:
        migrations = Path(temp) / 'migrations'
        shutil.copytree(ROOT / 'backend/migrations', migrations)
        (migrations / 'versions/9999_failure.py').write_text('''from alembic import op
revision = '9999'
down_revision = '0003'
def upgrade():
    op.execute('CREATE TABLE research.should_rollback (id integer)')
    op.execute('SELECT 1 / 0')
def downgrade():
    pass
''')
        broken = Config(str(ROOT / 'backend/alembic.ini'))
        broken.set_main_option('script_location', str(migrations))
        from sqlalchemy.exc import DBAPIError
        try:
            command.upgrade(broken, 'head')
        except DBAPIError:
            pass
        else:
            raise AssertionError('Intentional migration failure did not fail')
    with psycopg.connect(url, autocommit=True) as db:
        assert db.execute("SELECT to_regclass('research.should_rollback')").fetchone()[0] is None
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0] == '0003'
        db.execute('DROP TABLE public.migration_test_sentinel')
    print('PASS: upgrade, repeat upgrade, constraints, downgrade, re-upgrade and atomic failure rollback')


if __name__ == '__main__':
    main()
