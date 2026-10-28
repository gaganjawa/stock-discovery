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
            (legacy / 'versions/0015_grant_fences.py').unlink()
            for name in ('0012_real_shadow.py', '0013_pilot_maintenance_audit.py'):
                path = legacy / 'versions' / name
                path.write_text(path.read_text().replace("'real_0012'", "'0012'"))
            old = Config(str(ROOT / 'backend/alembic.ini'))
            old.set_main_option('script_location', str(legacy))
            command.upgrade(old, 'head')
            assert conn.execute('SELECT version_num FROM alembic_version').fetchone() == ('0013',)
            # Seed the historical schema directly. Current ingestion deliberately
            # requires 0015 and must not grow a fail-open pre-migration fallback.
            conn.execute("INSERT INTO discovery.publication_runs(run_id,request_key,request_hash,request) VALUES ('legacy-run','legacy-key','legacy-hash','{}')")
            conn.execute("INSERT INTO discovery.publication_batches(run_id,horizon,mode,payload) VALUES ('legacy-run','swing','live_paper','{}')")
            conn.execute("""INSERT INTO discovery.recommendations VALUES
                ('legacy-rec','legacy-run','SYN-listing','swing','quant',
                 '{"schema_version":"2.0.0","cohort":{"shadow":true},"paper_admission":{"status":"blocked"}}',
                 '{}','legacy-rec')""")
            conn.execute("""INSERT INTO paper.shadow_references VALUES
                ('legacy-ref','legacy-rec','{"mode":"live_paper","actionable":false}')""")
            conn.execute("INSERT INTO paper.shadow_outcomes VALUES ('legacy-outcome','legacy-ref',1,'legacy-input',now(),'{}')")
            conn.execute("INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (NULL,now(),'pilot_request:migration-sentinel')")
        before = snapshot(conn)
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        after = snapshot(conn)
        assert all(after[table] == rows for table, rows in before.items())
        assert conn.execute('SELECT version_num FROM alembic_version').fetchall() == [('0015',)]
        assert conn.execute("SELECT to_regclass('discovery.experiments'),to_regclass('paper.shadow_references')").fetchone() == ('discovery.experiments', 'paper.shadow_references')
        if origin == 'real_0013':
            assert conn.execute('SELECT count(*) FROM paper.shadow_outcomes').fetchone()[0] == 1
            assert conn.execute('SELECT count(*) FROM discovery.schedule_audit WHERE job_id IS NULL').fetchone()[0] == 1
            # The existing audit-preservation rollback guard remains effective.
            with pytest.raises(IntegrityError, match='null values'):
                command.downgrade(config, 'base')
            assert conn.execute('SELECT version_num FROM alembic_version').fetchall() == [('0015',)]
            assert snapshot(conn) == after


def test_fence_upgrade_initializes_scopes_without_rewriting_legacy_acquisitions(migration_database):
    from psycopg.types.json import Jsonb
    from stock_discovery_analysis.revision_fixtures import fixture_grant,fixture_stream,fixture_request,fixture_adapter
    from stock_discovery_analysis.revision_storage import ingest_page
    from stock_discovery_analysis.grant_fences import restrict
    from sqlalchemy.exc import DBAPIError
    config=Config(str(ROOT/'backend/alembic.ini'))
    command.upgrade(config,'0014')
    g=fixture_grant();s=fixture_stream('universe')
    with psycopg.connect(migration_database,autocommit=True) as conn:
        conn.execute('INSERT INTO discovery.grants VALUES(%s,%s,%s)',(g.grant_id,g.version,Jsonb(g.model_dump(mode='json'))))
        conn.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,%s,%s,%s)',(s.stream_id,s.source_id,s.account_ref,s.scope))
        conn.execute('INSERT INTO discovery.pages VALUES(%s,\'legacy\',\'legacy-hash\',NULL,true,0,0)',(s.stream_id,))
        before=snapshot(conn)
        command.upgrade(config,'head');command.upgrade(config,'head')
        assert conn.execute('SELECT state,generation FROM discovery.grant_fences').fetchall()==[('OPEN',0)]*3
        assert all(snapshot(conn)[t]==rows for t,rows in before.items())
        with pytest.raises(psycopg.errors.InsufficientPrivilege,match='page_grant_unattributed'):
            conn.execute('SELECT discovery.check_ingestion_page(%s,\'legacy\')',(s.stream_id,))
        # Empty restriction history supports schema rollback without deleting data.
        command.downgrade(config,'0014');command.upgrade(config,'head')
        assert all(snapshot(conn)[t]==rows for t,rows in before.items())
        assert ingest_page(conn,s.model_copy(update={'stream_id':'SYN-post-migration'}),fixture_adapter('universe').fetch(None,100),
            load_grant=lambda:g,request=fixture_request('universe'),audit=lambda d:None)['accepted']==1
        restrict(conn,request_id=uuid4(),kind='grant',source_id=g.source_id,account_ref=g.account_ref,
            grant_id=g.grant_id,grant_version=g.version,reason='deletion_pending')
        saved=snapshot(conn)
        with pytest.raises(DBAPIError,match='grant_fence_history_present'):command.downgrade(config,'0014')
        assert snapshot(conn)==saved
        assert conn.execute('SELECT version_num FROM alembic_version').fetchone()==('0015',)
