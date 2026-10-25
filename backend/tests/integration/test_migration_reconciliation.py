"""Upgrade both deployed histories using new, disposable databases only."""
import os
from pathlib import Path
import shutil
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[3]
URL = os.getenv('STK_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='requires disposable PostgreSQL')


@pytest.fixture
def migration_database(monkeypatch):
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname'] == 'stk013_test'
    name = 'stk013_test_migration_' + uuid4().hex[:12]
    admin = psycopg.conninfo.make_conninfo(URL, dbname='postgres')
    url = psycopg.conninfo.make_conninfo(URL, dbname=name)
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    from sqlalchemy.engine import URL as DatabaseURL
    info = psycopg.conninfo.conninfo_to_dict(url)
    monkeypatch.delenv('DATABASE_URL_FILE', raising=False)
    monkeypatch.setenv('DATABASE_URL', DatabaseURL.create(
        'postgresql+psycopg', username=info.get('user'), password=info.get('password'),
        host=info.get('host'), port=int(info['port']), database=name,
    ).render_as_string(hide_password=False))
    try:
        yield url
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


def snapshot(conn):
    tables = conn.execute("""SELECT schemaname, tablename FROM pg_tables
        WHERE schemaname IN ('research','discovery','paper') ORDER BY 1,2""").fetchall()
    return {(schema, table): conn.execute(sql.SQL(
        'SELECT to_jsonb(t)::text FROM {}.{} t ORDER BY to_jsonb(t)::text'
    ).format(sql.Identifier(schema), sql.Identifier(table))).fetchall() for schema, table in tables}


@pytest.mark.parametrize('origin', ['clean', 'main_0012', 'real_0013'])
def test_combined_upgrade_preserves_both_histories(migration_database, tmp_path, origin):
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with psycopg.connect(migration_database, autocommit=True) as conn:
        if origin == 'main_0012':
            command.upgrade(config, '0012')
            # Immutable governance history must survive the REAL branch upgrade.
            conn.execute("""INSERT INTO discovery.experiments
                (experiment_id,manifest_hash,manifest,split_audit)
                VALUES ('migration-sentinel','migration-sentinel','{}','{}')""")
        elif origin == 'real_0013':
            # Reconstruct the actual old graph, including its conflicting 0012 ID.
            legacy = tmp_path / 'legacy'
            shutil.copytree(ROOT / 'backend/migrations', legacy)
            (legacy / 'versions/0012_experiment_governance.py').unlink()
            (legacy / 'versions/0014_reconcile_real_governance.py').unlink()
            for name in ('0012_real_shadow.py', '0013_pilot_maintenance_audit.py'):
                path = legacy / 'versions' / name
                path.write_text(path.read_text().replace("'real_0012'", "'0012'"))
            old = Config(str(ROOT / 'backend/alembic.ini'))
            old.set_main_option('script_location', str(legacy))
            command.upgrade(old, 'head')
            assert conn.execute('SELECT version_num FROM alembic_version').fetchone() == ('0013',)
            from test_real_publication_flow import prepared, insert, bar, CLOCK
            from stock_discovery_analysis.real_publication import publish
            from stock_discovery_analysis.real_access import source_access
            from stock_discovery_analysis.shadow_tracking import observe, history
            view = prepared(conn, tmp_path)
            artifact = publish(conn, view, 'NSE:test', 'swing', 'migration-sentinel', 'test', clock=lambda: CLOCK)
            access = source_access(view.sources, lambda: '2026-10-21T13:00:00Z')
            reference = history(conn, artifact['recommendation']['recommendation_id'], access)['reference']['reference_id']
            insert(conn, view, bar('2026-10-21'), 'migration-later-bar', '2026-10-21T12:00:00Z')
            observe(conn, reference, access, clock=lambda: '2026-10-21T13:00:00Z')
            conn.execute("INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (NULL,now(),'pilot_request:migration-sentinel')")
        before = snapshot(conn)
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        after = snapshot(conn)
        assert all(after[table] == rows for table, rows in before.items())
        assert conn.execute('SELECT version_num FROM alembic_version').fetchall() == [('0014',)]
        assert conn.execute("SELECT to_regclass('discovery.experiments'),to_regclass('paper.shadow_references')").fetchone() == ('discovery.experiments', 'paper.shadow_references')
        if origin == 'real_0013':
            assert conn.execute('SELECT count(*) FROM paper.shadow_outcomes').fetchone()[0] == 1
            assert conn.execute('SELECT count(*) FROM discovery.schedule_audit WHERE job_id IS NULL').fetchone()[0] == 1
            # The existing audit-preservation rollback guard remains effective.
            with pytest.raises(IntegrityError, match='null values'):
                command.downgrade(config, 'base')
            assert conn.execute('SELECT version_num FROM alembic_version').fetchall() == [('0014',)]
            assert snapshot(conn) == after
