"""D3-03 PostgreSQL atomicity, identity, rights and snapshot tests."""
import json
import os

import psycopg
import pytest

from stock_discovery_analysis.revision_fixtures import (
    CUTOFF, NOW, fixture_adapter, fixture_grant, fixture_records, fixture_request, fixture_stream,
)
from stock_discovery_analysis.revision_storage import (
    Page, freeze_snapshot, ingest_next, ingest_page, read_snapshot,
)

URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated PostgreSQL database')


@pytest.fixture
def db():
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname']=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            yield conn


def ingest(conn,scope,page):
    return ingest_page(conn,fixture_stream(scope),page,load_grant=fixture_grant,
                       request=fixture_request(scope),audit=lambda d: None)


def seed(conn):
    for scope in ('universe','calendar','prices','corporate_actions','filings'):
        adapter=fixture_adapter(scope)
        for _ in adapter.pages:
            ingest_next(conn,fixture_stream(scope),adapter,clock=lambda:NOW,load_grant=fixture_grant,
                        request=fixture_request(scope),audit=lambda d: None)


def freeze(conn,**changes):
    scopes=('universe','calendar','prices','corporate_actions','filings')
    args=dict(streams=tuple(fixture_stream(s) for s in scopes),load_grant=lambda s: fixture_grant(),
              requests={fixture_stream(s).stream_id:fixture_request(s) for s in scopes},
              audit=lambda d:None,mode='synthetic',cutoff=CUTOFF,created_at=NOW,
              universe_version='SYN-universe-1',calendar_version='SYN-calendar-1')
    args.update(changes)
    return freeze_snapshot(conn,**args)


def read(conn, snapshot_id, load_grant=lambda s: fixture_grant()):
    scopes=('universe','calendar','prices','corporate_actions','filings')
    return read_snapshot(conn,snapshot_id,load_grant=load_grant,
                         requests={fixture_stream(s).stream_id:fixture_request(s) for s in scopes},
                         audit=lambda d:None)


def test_paged_automatic_ingestion_restart_snapshot_roundtrip(db):
    adapter=fixture_adapter('universe')
    stream=fixture_stream('universe')
    options=dict(load_grant=fixture_grant,request=fixture_request('universe'),audit=lambda d:None)
    ingest_next(db,stream,adapter,clock=lambda:NOW,**options)
    assert db.execute('SELECT cursor FROM discovery.streams').fetchone()[0]=='1'
    # New adapter instance resumes the persisted checkpoint rather than restarting.
    ingest_next(db,stream,fixture_adapter('universe'),clock=lambda:NOW,**options)
    assert ingest_next(db,stream,adapter,clock=lambda:NOW,**options)=={'complete':True}
    seed(db)
    snapshot=freeze(db)
    assert snapshot.complete and snapshot.eligible_count==1
    assert read(db,snapshot.snapshot_id)==snapshot
    assert freeze(db).snapshot_id==snapshot.snapshot_id
    assert db.execute('SELECT count(*) FROM discovery.snapshot_items').fetchone()[0]==6


def test_replay_page_idempotent_but_changed_page_rejected(db):
    page=fixture_adapter('universe').fetch(None,100)
    assert not ingest(db,'universe',page)['reused']
    assert ingest(db,'universe',page)['reused']
    changed=page.model_dump()
    changed['records'][0]['data']['symbol']='DIFFERENT'
    with pytest.raises(ValueError,match='changed page'):
        ingest(db,'universe',Page.model_validate(changed))
    assert db.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==1


def test_invalid_rows_quarantined_without_raw_payload_or_silent_zero(db):
    seed(db)
    # Overlapping batches reuse identical revisions and quarantine malformed rows.
    stream=fixture_stream('prices').model_copy(update={'stream_id':'SYN-new-prices'})
    good=fixture_records()[3].model_dump(mode='json')
    bad=json.loads(json.dumps(good)); bad['data']['low']='NaN'
    page=Page(cursor=None,next_cursor=None,complete=True,records=(bad,good))
    result=ingest_page(db,stream,page,load_grant=fixture_grant,request=fixture_request('prices'),audit=lambda d:None)
    assert result['quarantined']==1 and result['accepted']==1
    rows=db.execute('SELECT content_hash,reason FROM discovery.quarantine').fetchall()
    assert {r[1] for r in rows}=={'invalid_record'}
    assert all(len(r[0])==64 for r in rows)


def test_page_failure_rolls_back_rows_and_checkpoint(db):
    class FailCheckpoint:
        def transaction(self): return db.transaction()
        def execute(self,sql,args=None):
            if sql.startswith('UPDATE discovery.streams'):
                raise RuntimeError('injected checkpoint failure')
            return db.execute(sql,args)
    with pytest.raises(RuntimeError,match='checkpoint failure'):
        ingest(FailCheckpoint(),'universe',fixture_adapter('universe').fetch(None,100))
    assert db.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM discovery.streams').fetchone()[0]==0
    assert ingest(db,'universe',fixture_adapter('universe').fetch(None,100))['accepted']==1


def test_revocation_stops_fetch_and_post_fetch_storage(db):
    calls=[]
    class Adapter:
        def fetch(self,cursor,limit):
            calls.append('fetch')
            return fixture_adapter('universe').fetch(cursor,limit)
    revoked=fixture_grant(status='revoked',revoked_at='2026-10-15T11:00:00Z')
    options=dict(request=fixture_request('universe'),audit=lambda d:None)
    with pytest.raises(PermissionError):
        ingest_next(db,fixture_stream('universe'),Adapter(),clock=lambda:NOW,load_grant=lambda:revoked,**options)
    assert calls==[]
    grants=iter((fixture_grant(),revoked))
    with pytest.raises(PermissionError):
        ingest_next(db,fixture_stream('universe'),Adapter(),clock=lambda:NOW,load_grant=lambda:next(grants),**options)
    assert calls==['fetch'] and db.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==0


def test_missing_instrument_quarantine_and_partial_snapshot(db):
    r=fixture_records()[3].model_dump(mode='json')
    result=ingest(db,'prices',Page(cursor=None,next_cursor=None,complete=True,records=(r,)))
    assert result['quarantined']==1
    assert db.execute('SELECT reason FROM discovery.quarantine').fetchone()[0]=='instrument_reference_missing'
    snapshot=freeze(db)
    assert not snapshot.complete and 'quarantined_records' in snapshot.issues
    assert 'universe_unavailable' in snapshot.issues
    assert read(db,snapshot.snapshot_id)==snapshot


def test_snapshot_rechecks_grants(db):
    seed(db)
    with pytest.raises(PermissionError):
        freeze(db,load_grant=lambda s: fixture_grant(status='revoked',revoked_at='2026-10-15T11:00:00Z'))
    assert db.execute('SELECT count(*) FROM discovery.snapshots').fetchone()[0]==0


@pytest.mark.parametrize('table', ['grants','revisions','stream_revisions','pages','quarantine','snapshots','snapshot_items'])
def test_persisted_records_are_immutable(db,table):
    seed(db)
    freeze(db)
    # Ensure the quarantine table has a row too.
    stream=fixture_stream('filings').model_copy(update={'stream_id':'SYN-invalid'})
    ingest_page(db,stream,Page(cursor=None,next_cursor=None,complete=True,records=({'invalid':True},)),load_grant=fixture_grant,request=fixture_request('filings'),audit=lambda d:None)
    with pytest.raises(psycopg.errors.CheckViolation),db.transaction():
        db.execute(f'DELETE FROM discovery.{table}')


def test_out_of_order_cursor_and_foreign_account_denied(db):
    page=fixture_adapter('universe').fetch('1',100)
    with pytest.raises(ValueError,match='cursor'):
        ingest(db,'universe',page)
    with pytest.raises(ValueError,match='stream request'):
        ingest_page(db,fixture_stream('universe'),page,load_grant=fixture_grant,
                    request=fixture_request('universe',account_ref='OTHER'),audit=lambda d:None)


def test_new_revisions_append_without_changing_frozen_snapshot(db):
    # Keep price stream open so a later provider correction can arrive.
    for scope in ('universe','calendar','corporate_actions','filings'):
        adapter=fixture_adapter(scope)
        for _ in adapter.pages:
            ingest_next(db,fixture_stream(scope),adapter,clock=lambda:NOW,load_grant=fixture_grant,request=fixture_request(scope),audit=lambda d:None)
    old=fixture_records()[3].model_dump(mode='json')
    ingest(db,'prices',Page(cursor=None,next_cursor='next',complete=False,records=(old,)))
    before=freeze(db)
    correction=json.loads(json.dumps(old))
    correction.update(revision_id='SYN-correction',source_revision='price-v2',sequence=2,
                      supersedes_id=old['revision_id'],available_at='2026-10-15T10:00:00Z')
    correction['data']['close']='106'
    result=ingest(db,'prices',Page(cursor='next',next_cursor=None,complete=True,records=(correction,)))
    assert result['accepted']==1
    after=freeze(db)
    assert after.snapshot_id!=before.snapshot_id
    assert read(db,before.snapshot_id)==before
    assert next(r for r in after.revisions if r.data.kind=='candle').data.close=='106'
    assert db.execute("SELECT count(*) FROM discovery.revisions WHERE kind='candle'").fetchone()[0]==2


def test_reused_source_revision_is_quarantined(db):
    adapter=fixture_adapter('universe')
    for _ in adapter.pages:
        ingest_next(db,fixture_stream('universe'),adapter,clock=lambda:NOW,load_grant=fixture_grant,request=fixture_request('universe'),audit=lambda d:None)
    original=fixture_records()[3].model_dump(mode='json')
    ingest(db,'prices',Page(cursor=None,next_cursor='next',complete=False,records=(original,)))
    bad=json.loads(json.dumps(original))
    bad.update(revision_id='SYN-conflict',sequence=2,supersedes_id=original['revision_id'])
    bad['data']['close']='106'
    result=ingest(db,'prices',Page(cursor='next',next_cursor=None,complete=True,records=(bad,)))
    assert result['quarantined']==1
    assert db.execute('SELECT reason FROM discovery.quarantine').fetchone()[0]=='source_revision_conflict'


def test_overlapping_batch_deduplicates_revision_but_keeps_membership(db):
    seed(db)
    stream=fixture_stream('prices').model_copy(update={'stream_id':'SYN-prices-next-batch'})
    raw=fixture_records()[3].model_dump(mode='json')
    page=Page(cursor=None,next_cursor=None,complete=True,records=(raw,))
    assert ingest_page(db,stream,page,load_grant=fixture_grant,request=fixture_request('prices'),audit=lambda d:None)['accepted']==1
    assert db.execute("SELECT count(*) FROM discovery.revisions WHERE kind='candle'").fetchone()[0]==1
    assert db.execute("SELECT count(*) FROM discovery.stream_revisions WHERE revision_id='SYN-candle'").fetchone()[0]==2
    scopes=('universe','calendar','corporate_actions','filings')
    streams=tuple(fixture_stream(s) for s in scopes)+(stream,)
    requests={s.stream_id:fixture_request(s.scope) for s in streams}
    snap=freeze(db,streams=streams,requests=requests)
    assert snap.complete and any(r.revision_id=='SYN-candle' for r in snap.revisions)



def test_revoked_grant_blocks_reading_existing_snapshot(db):
    seed(db)
    snapshot=freeze(db)
    with pytest.raises(PermissionError):
        read(db,snapshot.snapshot_id,load_grant=lambda s:fixture_grant(status='revoked',revoked_at='2026-10-15T11:00:00Z'))



def test_snapshot_foreign_keys_reject_unresolved_items(db):
    seed(db)
    snapshot=freeze(db)
    with pytest.raises(psycopg.errors.ForeignKeyViolation),db.transaction():
        db.execute('INSERT INTO discovery.snapshot_items VALUES (%s,%s)',(snapshot.snapshot_id,'missing'))



def test_expiry_during_fetch_is_checked_at_storage_time(db):
    clocks=iter(('2026-10-15T11:59:59Z','2026-10-15T12:00:00Z'))
    g=fixture_grant(expires_at='2026-10-15T12:00:00Z')
    with pytest.raises(PermissionError,match='grant_expired'):
        ingest_next(db,fixture_stream('universe'),fixture_adapter('universe'),
                    load_grant=lambda:g,request=fixture_request('universe'),
                    audit=lambda d:None,clock=lambda:next(clocks))
    assert db.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==0
