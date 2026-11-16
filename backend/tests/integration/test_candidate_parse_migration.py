"""STK-095 additive parse state preserves immutable receipts and cursors."""
import json,os
from pathlib import Path
from datetime import datetime,timezone
import psycopg,pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from test_candidates import isolated_url,event,scanner
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.chartink_intake import capture

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='disposable PostgreSQL required')


def test_additive_parse_state_preserves_history_and_guards_rollback(isolated_url,monkeypatch):
    info=psycopg.conninfo.conninfo_to_dict(isolated_url)
    url=URL.create('postgresql+psycopg',username=info.get('user'),password=info.get('password'),host=info.get('host'),port=int(info['port']),database=info['dbname']).render_as_string(hide_password=False)
    monkeypatch.delenv('DATABASE_URL_FILE',raising=False);monkeypatch.setenv('DATABASE_URL',url)
    config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'))
    command.downgrade(config,'0017')
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        legacy=event(['LEGACY']);store.accept(conn,legacy)
        raw=capture(json.dumps(event(['NEW'])['payload']).encode(),scanner(),datetime.now(timezone.utc))
        store.accept(conn,raw)
        conn.execute("INSERT INTO discovery.candidate_receivers VALUES ('existing-cursor',3)")
        before=conn.execute('SELECT * FROM discovery.candidate_events ORDER BY sequence').fetchall()
        sequence=conn.execute('SELECT last_value FROM discovery.candidate_events_sequence_seq').fetchone()
        command.upgrade(config,'head');command.upgrade(config,'head')
        assert conn.execute('SELECT * FROM discovery.candidate_events ORDER BY sequence').fetchall()==before
        assert conn.execute('SELECT last_value FROM discovery.candidate_events_sequence_seq').fetchone()==sequence
        assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(3,)
        # Empty parse state can roll back without deleting receipt history.
        command.downgrade(config,'0017');command.upgrade(config,'head')
        assert store.materialize_one(conn)==legacy['event_id']
        assert store.materialize_one(conn)==raw['event_id']
        assert store.rows(conn)['total']==1  # latest receipt date; legacy session retained
        with pytest.raises(DBAPIError,match='candidate_parse_evidence_present'):command.downgrade(config,'0017')
        assert conn.execute('SELECT version_num FROM alembic_version').fetchone()==('0018',)
        assert conn.execute('SELECT * FROM discovery.candidate_events ORDER BY sequence').fetchall()==before
        assert conn.execute('SELECT cursor FROM discovery.candidate_receivers').fetchone()==(3,)
