"""STK-095 migration preservation and exact PostgreSQL jsonb size boundaries."""
import json
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import psycopg
from psycopg.types.json import Jsonb
import pytest
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from stock_discovery_analysis import candidate_store as store
from test_candidates import isolated_url, event

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


def size(conn,envelope):
    return conn.execute('SELECT octet_length(%s::jsonb::text)',(Jsonb(envelope),)).fetchone()[0]


def sized_event(conn,target):
    envelope=event(['SYNBOUND'])
    # Exercise Unicode bytes, escaped text, and PostgreSQL exponent expansion.
    envelope['boundary_fixture']={'text':'é漢😀"\\\n','number':1e20,'padding':''}
    envelope['boundary_fixture']['padding']='x'*(target-size(conn,envelope))
    assert size(conn,envelope)==target
    assert len(json.dumps(envelope).encode())!=target
    return envelope


@pytest.mark.parametrize('offset',[-1,0,1])
def test_python_and_database_agree_at_exact_jsonb_limit(isolated_url,offset):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        envelope=sized_event(conn,store.MAX_EVENT_BYTES+offset)
        if offset<=0:
            assert not store.accept(conn,envelope)['duplicate']
            assert store.accept(conn,envelope)['duplicate']
            assert conn.execute('SELECT octet_length(envelope::text) FROM discovery.candidate_events').fetchone()==(store.MAX_EVENT_BYTES+offset,)
        else:
            with pytest.raises(ValueError,match='^event_too_large$'):store.accept(conn,envelope)
            with pytest.raises(psycopg.errors.CheckViolation) as failure:
                conn.execute('INSERT INTO discovery.candidate_events(event_id,received_at,envelope) VALUES (%s,%s,%s)',
                    (envelope['event_id'],envelope['received_at'],Jsonb(envelope)))
            assert failure.value.diag.constraint_name=='candidate_events_envelope_check'
            assert conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()==(0,)
            assert conn.execute('SELECT count(*) FROM discovery.candidate_event_state').fetchone()==(0,)


def test_0017_preserves_events_sequences_references_and_state(isolated_url,monkeypatch):
    info=psycopg.conninfo.conninfo_to_dict(isolated_url)
    url=URL.create('postgresql+psycopg',username=info.get('user'),password=info.get('password'),
        host=info.get('host'),port=int(info['port']) if info.get('port') else None,
        database=info['dbname']).render_as_string(hide_password=False)
    monkeypatch.delenv('DATABASE_URL_FILE',raising=False)
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'))
    command.downgrade(config,'0016')
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        old=event(['SYNOLD']);store.accept(conn,old);store.accept(conn,old)
        assert store.materialize_one(conn)==old['event_id']
        candidate=conn.execute('SELECT candidate_id FROM discovery.candidates').fetchone()[0]
        conn.execute("INSERT INTO discovery.candidate_research_runs(run_id,candidate_id,result) VALUES ('migration-fixture',%s,'{}')",(candidate,))
        sequence=conn.execute('SELECT sequence FROM discovery.candidate_events').fetchone()[0]
        conn.execute("INSERT INTO discovery.candidate_receivers VALUES ('migration-fixture',%s)",(sequence,))
        tables=('candidate_events','candidate_event_state','candidate_sessions','candidates',
            'candidate_matches','candidate_research_runs','candidate_receivers')
        def snapshot():
            return {table:conn.execute('SELECT * FROM discovery.'+table+' ORDER BY 1').fetchall() for table in tables}
        before=snapshot()
        seq_before=conn.execute('SELECT last_value,is_called FROM discovery.candidate_events_sequence_seq').fetchone()
        for action,target in [(command.upgrade,'0017'),(command.upgrade,'head'),
                              (command.downgrade,'0016'),(command.upgrade,'head')]:
            action(config,target)
            assert snapshot()==before
            assert conn.execute('SELECT last_value,is_called FROM discovery.candidate_events_sequence_seq').fetchone()==seq_before
        for mutation in ('UPDATE discovery.candidate_events SET received_at=now()',
                         'DELETE FROM discovery.candidate_events'):
            with pytest.raises(psycopg.Error):conn.execute(mutation)
        large=sized_event(conn,65537);store.accept(conn,large)
        assert conn.execute('SELECT sequence FROM discovery.candidate_events WHERE event_id=%s',(large['event_id'],)).fetchone()[0]>sequence
        retained=snapshot()
        # Reinstating the smaller bound must fail, never delete/rewrite retained data.
        with pytest.raises(DBAPIError):command.downgrade(config,'0016')
        assert snapshot()==retained
        assert conn.execute('SELECT version_num FROM alembic_version').fetchone()==('0017',)
        constraint=conn.execute("SELECT pg_get_constraintdef(oid),convalidated FROM pg_constraint WHERE conrelid='discovery.candidate_events'::regclass AND conname='candidate_events_envelope_check'").fetchone()
        assert '1048576' in constraint[0] and constraint[1]
        assert store.accept(conn,large)['duplicate']
        assert len(store.feed(conn)['events'])==2
