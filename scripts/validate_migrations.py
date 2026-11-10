"""Migration lifecycle checks, restricted to an explicitly disposable database."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from time import perf_counter
import xml.etree.ElementTree as ET

import psycopg
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def verify_integration_report(path):
    """Database acceptance must execute tests, never silently skip them."""
    cases = ET.parse(path).getroot().findall(".//testcase")
    if not cases:
        raise AssertionError("No database integration tests executed")
    skipped = [case.get("name") for case in cases if case.find("skipped") is not None]
    if skipped:
        raise AssertionError(f"Database integration tests skipped: {skipped}")
    print(f"PASS: all {len(cases)} database integration tests executed; zero skipped")


def main():
    total_started = perf_counter()
    timings = {}
    url = os.environ['STK_TEST_DATABASE_URL']
    if psycopg.conninfo.conninfo_to_dict(url).get('dbname') != 'stk013_test':
        raise ValueError('Only the disposable stk013_test database is allowed')
    os.environ.pop('DATABASE_URL_FILE', None)
    os.environ['DATABASE_URL'] = url
    os.environ['PYTHONPATH'] = os.pathsep.join(str(ROOT / part) for part in ('backend','shared','worker'))
    config = Config(str(ROOT / 'backend/alembic.ini'))
    started = perf_counter()
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    timings['Initial database migrations'] = perf_counter() - started
    with tempfile.TemporaryDirectory() as reports:
        report = Path(reports) / 'integration.xml'
        started = perf_counter()
        subprocess.run([sys.executable, '-m', 'pytest', str(ROOT / 'backend/tests/integration'), '-q', '-p', 'no:cacheprovider', '--durations=25', f'--junitxml={report}'], check=True)
        verify_integration_report(report)
        timings['PostgreSQL integration tests'] = perf_counter() - started
    started = perf_counter()
    with psycopg.connect(url, autocommit=True) as db:
        db.execute('CREATE TABLE public.migration_test_sentinel (id integer)')
    command.downgrade(config, 'base')
    with psycopg.connect(url) as db:
        assert db.execute("SELECT count(*) FROM pg_namespace WHERE nspname IN ('research','discovery','paper')").fetchone()[0] == 0
        assert db.execute("SELECT to_regclass('public.migration_test_sentinel')").fetchone()[0] is not None
    command.upgrade(config, 'head')
    timings['Downgrade and re-upgrade validation'] = perf_counter() - started
    started = perf_counter()
    with tempfile.TemporaryDirectory() as temp:
        migrations = Path(temp) / 'migrations'
        shutil.copytree(ROOT / 'backend/migrations', migrations)
        (migrations / 'versions/9999_failure.py').write_text('''from alembic import op
revision = '9999'
down_revision = '0016'
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
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0] == '0016'
        db.execute('DROP TABLE public.migration_test_sentinel')
    timings['Migration rollback verification'] = perf_counter() - started
    print('PASS: upgrade, repeat upgrade, constraints, downgrade, re-upgrade and atomic failure rollback')
    timings['Total execution'] = perf_counter() - total_started
    print('Timing summary:')
    for phase, elapsed in timings.items():
        print(f'  {phase}: {elapsed:.2f}s')


if __name__ == '__main__':
    main()
