import os
import secrets
import sys
from pathlib import Path
from datetime import timedelta
import pytest
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg import sql
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from deploy.roles import configure
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest
from stock_discovery_analysis.service import freeze, reveal
from stock_discovery_analysis.jobs import run_job
URL = os.getenv("STK_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requires disposable migrated database")


def test_runtime_grants_preserve_functionality_and_prevent_bypass():
    assert conninfo_to_dict(URL)["dbname"] == "stk013_test"
    password = secrets.token_hex(32)
    role = "stk_test_" + secrets.token_hex(6)
    with psycopg.connect(URL) as owner:
        configure(owner, password, role)
    params = conninfo_to_dict(URL)
    params.update(user=role, password=password)
    try:
        with psycopg.connect(make_conninfo(**params), autocommit=True) as db:
            dataset = demo_dataset()
            ingest(db, dataset)
            result = freeze(db, dataset, "SYN-ALPHA",
                            dataset.calendar.sessions[39].closes_at + timedelta(minutes=1), "runtime-test")
            reveal(db, result["recommendation"]["recommendation_id"])
            for statement in ("CREATE TABLE research.forbidden(id int)", "TRUNCATE research.decisions",
                              "ALTER TABLE research.decisions DISABLE TRIGGER ALL", "DELETE FROM research.decisions",
                              "SET session_replication_role='replica'", "CREATE ROLE forbidden"):
                with pytest.raises(psycopg.errors.InsufficientPrivilege): db.execute(statement)
            assert not any(db.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone())
    finally:
        with psycopg.connect(URL, autocommit=True) as owner:
            owner.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role)))
            owner.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


def test_active_worker_session_cannot_be_reclaimed():
    assert conninfo_to_dict(URL)["dbname"] == "stk013_test"
    with psycopg.connect(URL, autocommit=True) as first, psycopg.connect(URL, autocommit=True) as second:
        first.execute("SELECT pg_advisory_lock(170017)")
        assert run_job(second, "test") is None
        first.execute("SELECT pg_advisory_unlock(170017)")
        assert second.execute("SELECT pg_try_advisory_lock(170017)").fetchone()[0]
        second.execute("SELECT pg_advisory_unlock(170017)")
