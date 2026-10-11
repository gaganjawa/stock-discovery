"""Real PostgreSQL constraints and unchanged STK-001 fixture round trips."""
import json
import os
from pathlib import Path
from decimal import Decimal
import pytest
import psycopg
from psycopg.types.json import Jsonb

URL = os.getenv('STK_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='requires disposable migrated PostgreSQL database')
FIXTURES = Path(__file__).resolve().parents[3] / 'docs/contracts/examples'


@pytest.fixture
def db():
    assert URL.rsplit('/', 1)[-1] == 'stk013_test', 'test database must be explicitly disposable'
    with psycopg.connect(URL) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


def seed(conn):
    conn.execute("INSERT INTO research.instruments VALUES ('SYN-I',NULL,'SYNTHETIC_NSE','EQ','INR','Asia/Kolkata',true)")
    conn.execute("INSERT INTO research.accounts VALUES ('SYN-A',true,'INR')")
    conn.execute("INSERT INTO research.capital_buckets VALUES ('SYN-U','SYN-A','unallocated'),('SYN-T','SYN-A','active_trading')")


def test_original_nine_scenarios_roundtrip(db):
    recommendations = json.loads((FIXTURES / 'recommendations.synthetic.json').read_text())
    db.execute("INSERT INTO research.accounts VALUES ('SYN-A',true,'INR')")
    db.execute("INSERT INTO research.capital_buckets VALUES ('SYN-T','SYN-A','active_trading')")
    for r in recommendations:
        i = r['instrument']
        db.execute('INSERT INTO research.instruments VALUES (%s,%s,%s,%s,%s,%s,%s)',
                   (i['instrument_id'],i['isin'],i['exchange'],i['series'],i['currency'],i['exchange_timezone'],r['synthetic']))
        db.execute('''INSERT INTO research.runs (run_id,mode,information_cutoff_at,started_at,status,
                      dataset_version,code_version,strategy_version,manifest)
                      VALUES (%s,%s,%s,%s,'completed',%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                   (r['run_id'],r['mode'],r['information_cutoff_at'],r['generated_at'],
                    r['versions']['dataset'],r['versions']['code'],r['strategy']['version'],Jsonb(r['versions'])))
        holding_id = r['holding']['holding_ref'] if r['holding'] else None
        if holding_id:
            db.execute('''INSERT INTO research.holdings
                (holding_id,account_ref,bucket_id,instrument_id,observed_at,recorded_at,quantity,source_ref,source_version)
                VALUES (%s,'SYN-A','SYN-T',%s,%s,%s,%s,'fixture','v1')''',
                (holding_id,i['instrument_id'],r['information_cutoff_at'],r['generated_at'],r['holding']['available_quantity']))
        db.execute('''INSERT INTO research.decisions
            (recommendation_id,instrument_id,run_id,schema_version,information_cutoff_at,generated_at,
             decision_available_at,action,position_effect,holding_id,revises_id,revision_reason,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (r['recommendation_id'],i['instrument_id'],r['run_id'],r['schema_version'],r['information_cutoff_at'],
             r['generated_at'],r['decision_available_at'],r['action'],r['position_effect'],holding_id,
             r['revises_id'],r['revision_reason'],Jsonb(r)))
    for name in ('forecast','trade'):
        outcomes = json.loads((FIXTURES / f'{name}-outcomes.synthetic.json').read_text())
        for o in outcomes:
            db.execute(f'''INSERT INTO research.{name}_outcomes VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                (o['outcome_id'],o['recommendation_id'],o['evaluated_at'],o['evaluator_version'],
                 o['observation_dataset'],o['status'],o['supersedes_outcome_id'],Jsonb(o)))
        actual = dict(db.execute(f'SELECT outcome_id,payload FROM research.{name}_outcomes'))
        assert actual == {o['outcome_id']:o for o in outcomes}
    assert dict(db.execute('SELECT recommendation_id,payload FROM research.decisions')) == {r['recommendation_id']:r for r in recommendations}
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.decisions SET position_effect='OPEN_SHORT' WHERE action='SELL'")
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.decisions SET payload=jsonb_set(payload,'{action}','null') WHERE recommendation_id='SYN-stop'")
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.decisions SET revises_id='SYN-target',revision_reason='test' WHERE recommendation_id='SYN-stop'")


    original = next(r for r in recommendations if r['recommendation_id'] == 'SYN-stop')
    correction = dict(original, recommendation_id='SYN-stop-correction',
                      revises_id='SYN-stop', revision_reason='synthetic correction test')
    def append(payload, instrument=None):
        db.execute("""INSERT INTO research.decisions
            SELECT %s,COALESCE(%s,instrument_id),run_id,schema_version,information_cutoff_at,
                   generated_at,decision_available_at,action,position_effect,holding_id,
                   %s,%s,%s FROM research.decisions WHERE recommendation_id='SYN-stop'""",
                   (payload['recommendation_id'], instrument, payload['revises_id'],
                    payload['revision_reason'], Jsonb(payload)))
    append(correction)
    assert db.execute("SELECT revises_id FROM research.decisions WHERE recommendation_id='SYN-stop-correction'").fetchone()[0] == 'SYN-stop'
    invalid = dict(correction, recommendation_id='SYN-invalid', versions=dict(correction['versions'], dataset='wrong'))
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        append(invalid)
    cross = dict(correction, recommendation_id='SYN-cross',
                 instrument=next(r['instrument'] for r in recommendations if r['recommendation_id']=='SYN-target'))
    with pytest.raises(psycopg.errors.ForeignKeyViolation), db.transaction():
        append(cross, cross['instrument']['instrument_id'])

    for table in ('decisions', 'forecast_outcomes', 'trade_outcomes'):
        with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
            db.execute(f'DELETE FROM research.{table}')
        with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
            db.execute(f'UPDATE research.{table} SET payload=payload')
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.runs SET dataset_version='changed'")
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("DELETE FROM research.runs")


def test_candle_revisions_and_constraints(db):
    seed(db)
    insert = '''INSERT INTO research.candles VALUES (%s,'SYN-I','fixture',%s,'1d',
        '2025-08-06 03:45Z','2025-08-06 10:00Z',%s,'2026-10-09 10:00Z',
        'verified_archive','raw','v1',100,110,%s,105,1000)'''
    db.execute(insert,('bar1','v1','2025-08-06 10:01Z',90))
    db.execute(insert,('bar2','v2','2025-08-07 10:01Z',91))
    assert db.execute("SELECT candle_id FROM research.candles WHERE instrument_id='SYN-I' AND available_at <= '2025-08-06 12:00Z'").fetchall() == [('bar1',)]
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        db.execute(insert,('bar3','v1','2025-08-06 10:01Z',90))
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute(insert,('bad','v3','2025-08-06 10:01Z',106))
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute(insert,('future','v3','2025-08-06 09:00Z',90))


def test_documents_facts_and_holdings(db):
    seed(db)
    db.execute("""INSERT INTO research.documents VALUES
        ('doc','SYN-I','fixture','v1','section1','filing','2025-08-06 07:00Z',
         '2025-08-06 08:00Z','2026-10-09 10:00Z','verified_archive','synthetic-only',NULL,NULL)""")
    db.execute("""INSERT INTO research.facts VALUES ('fact','SYN-I','doc','revenue','\"123.45\"','INR',
        '2025-01-01','2025-03-31','2025-08-06 08:00Z','v1','section1',NULL)""")
    assert db.execute("SELECT value FROM research.facts").fetchone()[0] == '123.45'
    with pytest.raises(psycopg.errors.ForeignKeyViolation), db.transaction():
        db.execute("UPDATE research.facts SET document_id='missing'")
    db.execute("""INSERT INTO research.holdings (holding_id,account_ref,bucket_id,instrument_id,
        observed_at,recorded_at,quantity,cost_basis,source_ref,source_version)
        VALUES ('holding','SYN-A','SYN-T','SYN-I',now(),now(),2,123.45678901,'fixture','v1')""")
    assert db.execute('SELECT cost_basis FROM research.holdings').fetchone()[0] == Decimal('123.45678901')
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute('UPDATE research.holdings SET reserved_sell_quantity=3')


def test_contributions_transfers_and_idempotency(db):
    seed(db)
    insert = '''INSERT INTO research.contribution_ledger
        (event_id,account_ref,kind,from_bucket_id,to_bucket_id,amount,effective_at,recorded_at,status,source_ref,source_event_id)
        VALUES (%s,'SYN-A',%s,%s,%s,%s,'2025-01-01 00:00Z',now(),%s,'fixture',%s)'''
    db.execute(insert,('jan','deposit',None,'SYN-U','50000','posted','jan'))
    db.execute(insert,('mar','deposit',None,'SYN-U','30000','posted','mar'))
    db.execute(insert,('pending','deposit',None,'SYN-U','7000','pending','pending'))
    db.execute(insert,('transfer','transfer','SYN-U','SYN-T','10000','posted','transfer'))
    assert db.execute("SELECT sum(amount) FROM research.contribution_ledger WHERE kind='deposit' AND status='posted'").fetchone()[0] == Decimal('80000')
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        db.execute(insert,('duplicate','deposit',None,'SYN-U','50000','posted','jan'))
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute(insert,('unpaired','transfer',None,'SYN-T','10000','posted','unpaired'))
    db.execute("INSERT INTO research.accounts VALUES ('OTHER',true,'INR')")
    db.execute("INSERT INTO research.capital_buckets VALUES ('OTHER-B','OTHER','unallocated')")
    with pytest.raises(psycopg.errors.ForeignKeyViolation), db.transaction():
        db.execute(insert,('cross','transfer','SYN-U','OTHER-B','10000','posted','cross'))

    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.contribution_ledger SET amount='NaN' WHERE event_id='jan'")
    db.execute("""INSERT INTO research.contribution_ledger
        (event_id,account_ref,kind,to_bucket_id,amount,effective_at,recorded_at,status,source_ref,source_event_id,reverses_id,correction_reason)
        VALUES ('reverse','SYN-A','deposit','SYN-U',50000,now(),now(),'posted','fixture','reverse','jan','correction')""")
    assert db.execute("""SELECT sum(CASE WHEN reverses_id IS NULL THEN amount ELSE -amount END)
        FROM research.contribution_ledger WHERE kind='deposit' AND status='posted'""").fetchone()[0] == Decimal('30000')
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE research.contribution_ledger SET amount=1 WHERE event_id='reverse'")
