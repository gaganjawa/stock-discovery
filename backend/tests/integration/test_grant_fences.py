"""STK-014/074: synthetic PostgreSQL barriers, no provider/model execution."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4
import os

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import pytest

from stock_discovery_analysis.grant_fences import capture, enforce, restrict
from stock_discovery_analysis.revision_fixtures import fixture_grant, fixture_request, fixture_stream, fixture_adapter
from stock_discovery_analysis.revision_storage import ingest_page, ingest_next
from stock_discovery_analysis.evidence_fixtures import seed_identity, evidence_access, evidence_stream, adapter_fixture
from stock_discovery_analysis.evidence_storage import ingest_next_evidence

URL = os.getenv('STK_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='disposable PostgreSQL required')


@pytest.fixture
def case():
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname'] == 'stk013_test'
    name = 'stk013_test_fence_' + uuid4().hex[:10]
    # Every race uses separate connections to an isolated, migrated synthetic clone.
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE stk013_test').format(sql.Identifier(name)))
    url = psycopg.conninfo.make_conninfo(URL, dbname=name)
    with psycopg.connect(url, autocommit=True) as conn:
        yield conn, url
    # The task-owned disposable cluster is removed after validation, never real data.


def ingest(conn, grant=None, permit=None, stream=None):
    grant = grant or fixture_grant()
    stream = stream or fixture_stream('universe')
    return ingest_page(conn, stream, fixture_adapter('universe').fetch(None,100),
        load_grant=lambda:grant, request=fixture_request('universe'), audit=lambda d:None, permit=permit)


def fence(conn, kind='grant', grant=None, request_id=None, **changes):
    g = grant or fixture_grant()
    args = dict(request_id=request_id or uuid4(), kind=kind, source_id=g.source_id,
        account_ref=g.account_ref if kind!='provider' else '', grant_id=g.grant_id if kind=='grant' else '',
        grant_version=g.version if kind=='grant' else '', reason='revoked')
    args.update(changes)
    return restrict(conn, **args)


@pytest.mark.parametrize('kind', ['provider','account','grant'])
def test_fenced_before_ingestion_and_restart(case,kind):
    conn,url=case
    assert fence(conn,kind)==1
    with pytest.raises(PermissionError):ingest(conn)
    with psycopg.connect(url,autocommit=True) as restarted:
        with pytest.raises(PermissionError):ingest(restarted)
        assert fence(restarted,kind)==1
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==0
    assert conn.execute('SELECT generation,state FROM discovery.grant_fences WHERE state=\'FENCED\'').fetchall()==[(1,'FENCED')]


def test_preflight_then_restriction_blocks_final_persistence(case):
    conn,url=case
    permit=capture(conn,fixture_grant(),fixture_request('universe'))
    with psycopg.connect(url,autocommit=True) as operator:fence(operator)
    with pytest.raises(PermissionError):ingest(conn,permit=permit)
    assert conn.execute('SELECT count(*) FROM discovery.pages').fetchone()[0]==0


@pytest.mark.parametrize('evidence',[False,True])
def test_restriction_between_fetch_and_store(case,evidence):
    conn,url=case
    if evidence:seed_identity(conn)
    class Adapter:
        def fetch(self,cursor,limit):
            with psycopg.connect(url,autocommit=True) as operator:fence(operator,'provider')
            return adapter_fixture().fetch(cursor,limit) if evidence else fixture_adapter('universe').fetch(cursor,limit)
    with pytest.raises(PermissionError):
        if evidence:ingest_next_evidence(conn,evidence_stream(),Adapter(),access=evidence_access())
        else:ingest_next(conn,fixture_stream('universe'),Adapter(),load_grant=fixture_grant,
            request=fixture_request('universe'),audit=lambda d:None,clock=lambda:'2026-10-15T12:00:00Z')
    assert conn.execute('SELECT count(*) FROM discovery.evidence_blobs').fetchone()[0]==0


def test_writer_linearizes_before_waiting_fence(case):
    conn,url=case
    permit=capture(conn,fixture_grant(),fixture_request('universe'))
    ready=Event();pid=[]
    def restrict_other():
        with psycopg.connect(url,autocommit=True) as operator:
            pid.append(operator.info.backend_pid);ready.set()
            return fence(operator)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with conn.transaction():
            ingest(conn,permit=permit)
            future=pool.submit(restrict_other)
            assert ready.wait(5)
            # Observe the database wait, rather than assuming a scheduling delay.
            with psycopg.connect(url,autocommit=True) as observer:
                deadline=monotonic()+5
                while True:
                    blocking=observer.execute('SELECT pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]
                    if conn.info.backend_pid in blocking:break
                    assert monotonic()<deadline,'restriction did not wait on writer'
            assert not future.done()
        assert future.result(timeout=5)==1
    assert conn.execute('SELECT grant_id,grant_version FROM discovery.revisions').fetchall()==[(fixture_grant().grant_id,fixture_grant().version)]
    with pytest.raises(PermissionError):ingest(conn)


def test_concurrent_duplicate_requests_and_conflicting_scopes(case):
    conn,url=case;barrier=Barrier(2);key=uuid4()
    def activate():
        with psycopg.connect(url,autocommit=True) as operator:
            barrier.wait(timeout=5);return fence(operator,request_id=key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(activate) for _ in range(2)]
        assert [f.result(timeout=10) for f in futures]==[1,1]
    assert conn.execute('SELECT count(*) FROM discovery.restriction_requests').fetchone()[0]==1
    with pytest.raises(ValueError,match='restriction_request_failed'):fence(conn,'provider',request_id=key)
    fence(conn,'account');fence(conn,'provider')
    assert conn.execute('SELECT generation FROM discovery.grant_fences').fetchall()==[(1,),(1,),(1,)]


def test_database_time_expiry_and_registration_is_not_permission(case):
    conn,_=case
    now=conn.execute('SELECT clock_timestamp()').fetchone()[0]
    expired=fixture_grant(expires_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    conn.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)',(expired.source_id,expired.account_ref,expired.grant_id,expired.version))
    with pytest.raises(PermissionError,match='grant_expired'):ingest(conn,expired)
    denied=fixture_grant(allowed_uses=['derive'])
    with pytest.raises(PermissionError,match='use_denied'):ingest(conn,denied)
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==0


def test_expiry_after_capture_even_with_old_application_clock(case):
    conn,_=case
    permit=capture(conn,fixture_grant(),fixture_request('universe'))
    now=conn.execute('SELECT clock_timestamp()').fetchone()[0]
    expired=fixture_grant(expires_at=(now-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    with pytest.raises(PermissionError,match='grant_expired'):ingest(conn,expired,permit)


def test_renewal_does_not_reauthorize_old_acquisition(case):
    conn,_=case;ingest(conn);fence(conn)
    new=fixture_grant(version='renewed-2')
    capture(conn,new,fixture_request('universe'))
    # Both an old page and identical revision on a new stream remain restricted.
    with pytest.raises(PermissionError):ingest(conn,new)
    with pytest.raises(PermissionError):ingest(conn,new,stream=fixture_stream('universe').model_copy(update={'stream_id':'SYN-renewed'}))
    assert conn.execute('SELECT grant_version FROM discovery.revisions').fetchall()==[('fixture-1',)]


def test_scope_isolation_and_unrelated_provider(case):
    conn,_=case
    fence(conn,'account')
    for changes in ({'account_ref':'SYN-other-account'}, {'source_id':'SYN-other-provider'}):
        g=fixture_grant(grant_id='SYN-'+uuid4().hex,**changes)
        assert capture(conn,g,fixture_request('universe',source_id=g.source_id,account_ref=g.account_ref))
    # A fresh exact version is allowed only when its parents are OPEN.
    other=fixture_grant(source_id='SYN-other-provider',grant_id='SYN-other-grant')
    from stock_discovery_analysis.revision_storage import Page
    stream=fixture_stream('universe').model_copy(update={'source_id':other.source_id,'stream_id':'SYN-other-stream'})
    raw=fixture_adapter('universe').fetch(None,100).model_dump();raw['records'][0]['source_id']=other.source_id
    result=ingest_page(conn,stream,Page.model_validate(raw),load_grant=lambda:other,
        request=fixture_request('universe',source_id=other.source_id),audit=lambda d:None)
    assert result['accepted']==1


def test_atomic_fence_rollback_and_audit_no_content(case):
    conn,_=case;key=uuid4()
    with pytest.raises(RuntimeError):
        with conn.transaction():
            fence(conn,request_id=key,reason='policy_unverified');raise RuntimeError('injected')
    assert conn.execute('SELECT count(*) FROM discovery.restriction_requests').fetchone()[0]==0
    ingest(conn)
    assert fence(conn,request_id=key,reason='policy_unverified')==1
    row=conn.execute('SELECT reason,deletion_authorized,decision,generation FROM discovery.restriction_requests').fetchone()
    assert row==('policy_unverified',False,'fenced',1)
    with pytest.raises(ValueError,match='invalid_restriction_request'):fence(conn,reason='SECRET provider body')
    assert 'SECRET' not in str(conn.execute('SELECT * FROM discovery.restriction_requests').fetchall())


def test_operator_authority_cannot_be_claimed_by_caller(case):
    conn,url=case;name='stk_fence_test_'+uuid4().hex[:8]
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD 'synthetic-only'").format(sql.Identifier(name)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA discovery TO {}').format(sql.Identifier(name)))
    with psycopg.connect(psycopg.conninfo.make_conninfo(url,user=name,password='synthetic-only'),autocommit=True) as worker:
        with pytest.raises(PermissionError):fence(worker)
        worker.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)',('SYN-source','SYN-account','SYN-D303-grant','fixture-1'))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):worker.execute("UPDATE discovery.grant_fences SET state='OPEN'")
    assert conn.execute('SELECT count(*) FROM discovery.restriction_requests').fetchone()[0]==0


def test_missing_scope_direct_sql_and_failed_writer_roll_back(case):
    conn,_=case;g=fixture_grant()
    conn.execute('INSERT INTO discovery.grants VALUES(%s,%s,%s)',(g.grant_id,g.version,Jsonb(g.model_dump(mode='json'))))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):conn.execute('SELECT discovery.check_ingestion_grant(%s,%s)',(g.grant_id,g.version))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with conn.transaction():conn.execute("INSERT INTO discovery.evidence_blobs VALUES('SYN-orphan','source text')")
    assert conn.execute('SELECT count(*) FROM discovery.evidence_blobs').fetchone()[0]==0
    with pytest.raises(RuntimeError):
        with conn.transaction():ingest(conn);raise RuntimeError('writer crash')
    assert conn.execute('SELECT count(*) FROM discovery.ingestion_grants').fetchone()[0]==0
    assert ingest(conn)['accepted']==1
    assert ingest(conn)['reused']
    for table in ('schedule_outbox','rag_reservations','publication_runs','recommendations'):
        assert conn.execute(sql.SQL('SELECT count(*) FROM discovery.{}').format(sql.Identifier(table))).fetchone()[0]==0
    assert conn.execute('SELECT count(*) FROM paper.portfolios').fetchone()[0]==0


def test_direct_revision_insert_cannot_bypass_fence(case):
    conn,_=case;ingest(conn);fence(conn)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with conn.transaction():
            conn.execute("""INSERT INTO discovery.revisions
                SELECT 'SYN-bypass',stream_id,source_id,'SYN-bypass',logical_key||'-bypass',1,kind,listing_id,
                  available_at,grant_id,grant_version,instrument_revision_id,supersedes_id,content_hash,
                  jsonb_set(jsonb_set(payload,'{revision_id}','"SYN-bypass"'),'{source_revision}','"SYN-bypass"')
                FROM discovery.revisions WHERE revision_id='SYN-instrument'""")
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()[0]==1


def test_shared_blob_cannot_hide_restricted_owner(case):
    conn,_=case
    seed_identity(conn);ingest_next_evidence(conn,evidence_stream(),adapter_fixture(),access=evidence_access())
    from stock_discovery_analysis.evidence_fixtures import evidence_grant,document_fixture
    fence(conn,grant=evidence_grant())
    # A distinct authorized grant cannot launder the same stored source body.
    renewed=evidence_grant(version='renewed-2')
    from stock_discovery_analysis.revision_storage import Page
    identity_page=fixture_adapter('universe').fetch(None,100).model_dump()
    identity_page['records'][0].update(revision_id='SYN-new-instrument',source_revision='SYN-new-instrument',listing_id='SYN-other-listing')
    ingest_page(conn,fixture_stream('universe').model_copy(update={'stream_id':'SYN-new-identity'}),Page.model_validate(identity_page),
        load_grant=lambda:renewed,request=fixture_request('universe'),audit=lambda d:None)
    doc=document_fixture(rid='SYN-new-owner')
    doc=doc.model_copy(update={'revision':doc.revision.model_copy(update={
        'source_revision':'SYN-new-owner','instrument_revision_id':'SYN-new-instrument','listing_id':'SYN-other-listing',
        'data':doc.revision.data.model_copy(update={'document_id':'SYN-new-body-owner'})})})
    with pytest.raises((PermissionError,psycopg.errors.InsufficientPrivilege)):
        outcome=ingest_next_evidence(conn,evidence_stream().model_copy(update={'stream_id':'SYN-new-owner-stream'}),adapter_fixture(doc),
            access=evidence_access(load_grant=lambda s:renewed))
        assert outcome['accepted']==1, outcome.get('rejections')
    assert conn.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==1


def test_explicit_operator_membership_and_immutable_decisions(case):
    conn,url=case;name='stk_fence_operator_'+uuid4().hex[:8]
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD 'synthetic-only'").format(sql.Identifier(name)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA discovery TO {}').format(sql.Identifier(name)))
    conn.execute(sql.SQL('GRANT stk_restriction_operator TO {}').format(sql.Identifier(name)))
    with psycopg.connect(psycopg.conninfo.make_conninfo(url,user=name,password='synthetic-only'),autocommit=True) as operator:
        assert fence(operator)==1
    assert conn.execute('SELECT operator_name FROM discovery.restriction_requests').fetchone()[0]==name
    with pytest.raises(psycopg.errors.CheckViolation):conn.execute("UPDATE discovery.restriction_requests SET reason='expired'")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):conn.execute("UPDATE discovery.grant_fences SET state='OPEN',generation=0")


def test_restriction_does_not_reset_existing_budget(case):
    conn,_=case
    conn.execute("INSERT INTO discovery.rag_reservations VALUES('SYN-prior-intent','SYN-hash','SYN-account',now(),100,0)")
    before=conn.execute('SELECT * FROM discovery.rag_reservations').fetchall()
    fence(conn)
    for _ in range(2):
        with pytest.raises(PermissionError):ingest(conn)
    assert conn.execute('SELECT * FROM discovery.rag_reservations').fetchall()==before
    assert conn.execute('SELECT count(*) FROM discovery.schedule_outbox').fetchone()[0]==0


def test_bound_ingestion_access_checks_every_acquisition(case):
    conn,url=case
    from stock_discovery_analysis.grant_fences import ingestion_access
    access=ingestion_access(conn,evidence_access())
    access.require(evidence_stream(),('acquire',))
    with psycopg.connect(url,autocommit=True) as operator:fence(operator,'provider')
    with pytest.raises(PermissionError):access.require(evidence_stream(),('acquire',))
    with pytest.raises(PermissionError):access.require(evidence_stream(),('store',))


@pytest.fixture
def membership_writer(case):
    conn,url=case
    ingest(conn)
    role='stk_membership_'+uuid4().hex[:12]
    conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA discovery TO {}').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT INSERT ON discovery.streams,discovery.stream_revisions TO {}').format(sql.Identifier(role)))
    try:
        with psycopg.connect(url,autocommit=True) as writer:
            writer.execute(sql.SQL('SET SESSION AUTHORIZATION {}').format(sql.Identifier(role)))
            assert writer.execute('SELECT rolsuper FROM pg_roles WHERE rolname=session_user').fetchone()==(False,)
            yield conn,url,writer
    finally:
        conn.execute(sql.SQL('REVOKE INSERT ON discovery.streams,discovery.stream_revisions FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('REVOKE USAGE ON SCHEMA discovery FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def membership_destination(conn,writer,*,source='SYN-source',account='SYN-destination',registered=True):
    sid='SYN-destination-'+uuid4().hex
    if registered:
        conn.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)',
            (source,account,'SYN-destination-grant','1'))
    writer.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,%s,%s,\'universe\')',
        (sid,source,account))
    return sid


def insert_membership(writer,sid):
    writer.execute('INSERT INTO discovery.stream_revisions VALUES(%s,\'SYN-instrument\')',(sid,))


def test_membership_rejects_fenced_destination_insert_only(membership_writer):
    conn,_,writer=membership_writer
    sid=membership_destination(conn,writer)
    restrict(conn,request_id=uuid4(),kind='account',source_id='SYN-source',account_ref='SYN-destination',reason='revoked')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):insert_membership(writer,sid)
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(0,)
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)


@pytest.mark.parametrize('blocked',['provider','missing_account','missing_provider','source_grant'])
def test_membership_checks_both_ends_and_missing_scopes(membership_writer,blocked):
    conn,_,writer=membership_writer
    source='SYN-other-provider' if blocked in ('provider','missing_provider') else 'SYN-source'
    sid=membership_destination(conn,writer,source=source,registered=not blocked.startswith('missing'))
    if blocked=='provider':restrict(conn,request_id=uuid4(),kind='provider',source_id=source,reason='revoked')
    if blocked=='source_grant':fence(conn)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):insert_membership(writer,sid)
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(0,)


@pytest.mark.parametrize('account',['SYN-account','SYN-destination'])
def test_membership_permits_registered_unfenced_cross_stream(membership_writer,account):
    conn,_,writer=membership_writer
    sid=membership_destination(conn,writer,account=account)
    insert_membership(writer,sid)
    assert conn.execute('SELECT revision_id FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchall()==[('SYN-instrument',)]
    assert conn.execute('SELECT grant_id,grant_version FROM discovery.revisions').fetchall()==[('SYN-D303-grant','fixture-1')]


def test_destination_fence_commits_before_deferred_membership_check(membership_writer):
    conn,url,writer=membership_writer
    sid=membership_destination(conn,writer)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with writer.transaction():
            insert_membership(writer,sid)
            # Separate transaction commits the fence before the INSERT's deferred check.
            with psycopg.connect(url,autocommit=True) as operator:
                restrict(operator,request_id=uuid4(),kind='account',source_id='SYN-source',
                    account_ref='SYN-destination',reason='revoked')
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(0,)


def test_destination_fence_waits_for_checked_membership_commit(membership_writer):
    conn,url,writer=membership_writer
    sid=membership_destination(conn,writer);ready=Event();pid=[]
    def activate():
        with psycopg.connect(url,autocommit=True) as operator:
            operator.execute("SET statement_timeout='8s'")
            pid.append(operator.info.backend_pid);ready.set()
            return restrict(operator,request_id=uuid4(),kind='account',source_id='SYN-source',
                account_ref='SYN-destination',reason='revoked')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with writer.transaction():
            insert_membership(writer,sid)
            writer.execute('SET CONSTRAINTS discovery.ingestion_fence_stream_revisions IMMEDIATE')
            future=pool.submit(activate)
            assert ready.wait(5)
            deadline=monotonic()+5
            while writer.info.backend_pid not in conn.execute('SELECT pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]:
                assert monotonic()<deadline,'destination fence did not wait on membership writer'
            assert not future.done()
        assert future.result(timeout=10)==1
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(1,)
    later=membership_destination(conn,writer)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):insert_membership(writer,later)


@pytest.fixture
def membership_updater(membership_writer):
    conn,url,writer=membership_writer
    role=writer.execute('SELECT session_user').fetchone()[0]
    conn.execute(sql.SQL('GRANT SELECT,UPDATE ON discovery.streams TO {}').format(sql.Identifier(role)))
    try:
        yield conn,url,writer,role
    finally:
        conn.execute(sql.SQL('REVOKE SELECT,UPDATE ON discovery.streams FROM {}').format(sql.Identifier(role)))


@pytest.mark.parametrize('column,value',[
    ('account_ref','SYN-restricted'),('source_id','SYN-restricted'),('scope','prices'),
    ('stream_id','SYN-renamed'),
])
def test_stream_identity_update_rejected_for_non_owner(membership_updater,column,value):
    conn,_,writer,_=membership_updater
    sid=membership_destination(conn,writer)
    # Test the primary key before membership, so the FK cannot mask this guard.
    if column!='stream_id':insert_membership(writer,sid)
    restrict(conn,request_id=uuid4(),kind='account',source_id='SYN-source',
        account_ref='SYN-restricted',reason='revoked')
    restrict(conn,request_id=uuid4(),kind='provider',source_id='SYN-restricted',reason='revoked')
    before=conn.execute('SELECT * FROM discovery.streams WHERE stream_id=%s',(sid,)).fetchone()
    with pytest.raises(psycopg.errors.InsufficientPrivilege,match='stream_identity_immutable'):
        writer.execute(sql.SQL('UPDATE discovery.streams SET {}=%s WHERE stream_id=%s').format(sql.Identifier(column)),(value,sid))
    assert conn.execute('SELECT * FROM discovery.streams WHERE stream_id=%s',(sid,)).fetchone()==before
    writer.execute('UPDATE discovery.streams SET cursor=%s,complete=true,source_id=source_id WHERE stream_id=%s',('next',sid))
    assert conn.execute('SELECT cursor,complete FROM discovery.streams WHERE stream_id=%s',(sid,)).fetchone()==('next',True)


def wait_for_blocker(observer,waiter,blocker):
    deadline=monotonic()+5
    while blocker not in observer.execute('SELECT pg_blocking_pids(%s)',(waiter,)).fetchone()[0]:
        assert monotonic()<deadline,'expected database lock wait was not observed'


def test_membership_insert_then_concurrent_identity_update(membership_updater):
    conn,url,writer,role=membership_updater
    sid=membership_destination(conn,writer);ready=Event();pid=[]
    def change_identity():
        with psycopg.connect(url,autocommit=True) as updater:
            updater.execute(sql.SQL('SET SESSION AUTHORIZATION {}').format(sql.Identifier(role)))
            updater.execute("SET statement_timeout='10s'")
            pid.append(updater.info.backend_pid);ready.set()
            with pytest.raises(psycopg.errors.InsufficientPrivilege,match='stream_identity_immutable'):
                updater.execute("UPDATE discovery.streams SET account_ref='SYN-restricted' WHERE stream_id=%s",(sid,))
    with ThreadPoolExecutor(max_workers=1) as pool:
        with writer.transaction():
            insert_membership(writer,sid)
            writer.execute('SET CONSTRAINTS discovery.ingestion_fence_stream_revisions IMMEDIATE')
            future=pool.submit(change_identity)
            assert ready.wait(5)
            wait_for_blocker(conn,pid[0],writer.info.backend_pid)
        future.result(timeout=10)
    assert conn.execute('SELECT account_ref FROM discovery.streams WHERE stream_id=%s',(sid,)).fetchone()==('SYN-destination',)
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(1,)


@pytest.mark.parametrize('completed',[False,True])
def test_reuse_checks_original_grant_after_overlapping_renewal(case,completed):
    conn,_=case;ingest(conn)
    renewed=fixture_grant(version='renewed-2')
    stream=fixture_stream('universe').model_copy(update={'stream_id':'SYN-overlap'})
    page=fixture_adapter('universe').fetch(None,100).model_copy(update={'complete':True,'next_cursor':None})
    def retry_page():
        return ingest_page(conn,stream,page,load_grant=lambda:renewed,
            request=fixture_request('universe'),audit=lambda d:None)
    assert retry_page()['accepted']==1
    def reuse():
        if completed:
            class NoFetch:
                def fetch(self,*args):raise AssertionError('completed stream fetched again')
            return ingest_next(conn,stream,NoFetch(),load_grant=lambda:renewed,
                request=fixture_request('universe'),audit=lambda d:None,clock=lambda:'2026-10-15T12:00:00Z')
        return retry_page()
    assert reuse().get('complete' if completed else 'reused') is True
    before=conn.execute('SELECT to_jsonb(r) FROM discovery.revisions r ORDER BY revision_id').fetchall()
    dependencies=conn.execute('SELECT * FROM discovery.ingestion_grants ORDER BY stream_id').fetchall()
    fence(conn)
    with pytest.raises((PermissionError,psycopg.errors.InsufficientPrivilege)):reuse()
    assert conn.execute('SELECT to_jsonb(r) FROM discovery.revisions r ORDER BY revision_id').fetchall()==before
    assert conn.execute('SELECT * FROM discovery.ingestion_grants ORDER BY stream_id').fetchall()==dependencies
    assert conn.execute('SELECT count(*) FROM discovery.pages').fetchone()==(2,)


@pytest.mark.parametrize('path',['sql','capture','enforce'])
def test_expiry_during_fence_lock_wait_rejects_work(case,path):
    conn,url=case;ingest(conn)
    now=conn.execute('SELECT clock_timestamp()').fetchone()[0]
    grant=fixture_grant(version='expiring',expires_at=(now+timedelta(seconds=4)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    request=fixture_request('universe')
    permit=capture(conn,grant,request)
    conn.execute('INSERT INTO discovery.grants VALUES(%s,%s,%s)',
        (grant.grant_id,grant.version,Jsonb(grant.model_dump(mode='json'))))
    ready=Event();pid=[]
    def write():
        with psycopg.connect(url,autocommit=True) as writer:
            writer.execute("SET statement_timeout='12s'")
            pid.append(writer.info.backend_pid);ready.set()
            with pytest.raises((PermissionError,psycopg.errors.InsufficientPrivilege)):
                with writer.transaction():
                    if path=='capture':capture(writer,grant,request)
                    elif path=='enforce':enforce(writer,permit,grant,request)
                    else:
                        writer.execute("""INSERT INTO discovery.revisions
                            SELECT 'SYN-expiring',stream_id,source_id,'SYN-expiring',logical_key||'-expiring',1,kind,listing_id,
                              available_at,%s,%s,instrument_revision_id,supersedes_id,content_hash,
                              jsonb_set(jsonb_set(payload,'{revision_id}','"SYN-expiring"'),'{source_revision}','"SYN-expiring"')
                            FROM discovery.revisions WHERE revision_id='SYN-instrument'""",(grant.grant_id,grant.version))
    with psycopg.connect(url,autocommit=True) as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute('BEGIN')
        try:
            holder.execute("SELECT scope_id FROM discovery.grant_fences WHERE kind='grant' AND grant_version='expiring' FOR UPDATE")
            future=pool.submit(write)
            assert ready.wait(5)
            wait_for_blocker(conn,pid[0],holder.info.backend_pid)
            # Lock ordering is observed above. Wait only for the actual DB expiry,
            # not an assumed thread scheduling delay; no stale transaction clock.
            conn.execute('SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM %s::timestamptz-clock_timestamp())))',(grant.expires_at,))
            assert conn.execute('SELECT clock_timestamp()>=%s::timestamptz',(grant.expires_at,)).fetchone()==(True,)
        finally:
            holder.execute('ROLLBACK')
        future.result(timeout=10)
    assert conn.execute("SELECT count(*) FROM discovery.revisions WHERE revision_id='SYN-expiring'").fetchone()==(0,)
    assert conn.execute("SELECT state,generation FROM discovery.grant_fences WHERE kind='grant' AND grant_version='expiring'").fetchone()==('OPEN',0)


@pytest.fixture
def scoped_writer(case):
    conn,url=case;role='stk_scope_'+uuid4().hex[:12]
    tables='discovery.streams,discovery.revisions,discovery.stream_revisions,discovery.pages,discovery.ingestion_grants,discovery.evidence_batches,discovery.evidence_blobs,discovery.evidence_documents,discovery.financial_facts'
    conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA discovery TO {}').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT INSERT ON '+tables+' TO {}').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT SELECT ON discovery.pages TO {}').format(sql.Identifier(role)))
    try:
        with psycopg.connect(url,autocommit=True) as writer:
            writer.execute(sql.SQL('SET SESSION AUTHORIZATION {}').format(sql.Identifier(role)))
            assert writer.execute('SELECT rolsuper FROM pg_roles WHERE rolname=session_user').fetchone()==(False,)
            yield conn,url,writer,role
    finally:
        conn.execute(sql.SQL('REVOKE SELECT ON discovery.pages FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('REVOKE INSERT ON '+tables+' FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('REVOKE USAGE ON SCHEMA discovery FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def register_test_grant(conn,grant):
    conn.execute('INSERT INTO discovery.grants VALUES(%s,%s,%s)',
        (grant.grant_id,grant.version,Jsonb(grant.model_dump(mode='json'))))
    conn.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)',
        (grant.source_id,grant.account_ref,grant.grant_id,grant.version))


def raw_revision(writer,stream,grant,record):
    writer.execute('INSERT INTO discovery.revisions VALUES('+','.join(['%s']*15)+')',
        (record.revision_id,stream,record.source_id,record.source_revision,record.logical_key,record.sequence,
         record.data.kind,record.listing_id,record.available_at,grant.grant_id,grant.version,
         record.instrument_revision_id,record.supersedes_id,record.content_hash,Jsonb(record.model_dump(mode='json'))))


@pytest.mark.parametrize('path',['grant_scope','stream_scope','unknown_scope','missing_grant_scope','unknown_grant_scope','membership','page','evidence_batch'])
def test_sql_data_scope_rejected(scoped_writer,path):
    from stock_discovery_analysis.revision_fixtures import fixture_records
    conn,_,writer,_=scoped_writer;ingest(conn)
    g=fixture_grant(version='limited',scopes=['calendar'],allowed_uses=['store'])
    if path in ('stream_scope','unknown_scope'):g=fixture_grant(version='limited')
    if path in ('missing_grant_scope','unknown_grant_scope'):
        payload=g.model_dump(mode='json');payload.pop('scopes')
        if path=='unknown_grant_scope':payload['scopes']=['unknown']
        conn.execute('INSERT INTO discovery.grants VALUES(%s,%s,%s)',(g.grant_id,g.version,Jsonb(payload)))
        conn.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)',(g.source_id,g.account_ref,g.grant_id,g.version))
    else:register_test_grant(conn,g)
    scope='calendar' if path in ('stream_scope','evidence_batch') else 'unknown' if path=='unknown_scope' else 'prices'
    sid='SYN-scope-check'
    writer.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,%s,%s,%s)',
        (sid,g.source_id,g.account_ref,scope))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with writer.transaction():
            if path in ('grant_scope','stream_scope','unknown_scope','missing_grant_scope','unknown_grant_scope'):
                raw_revision(writer,sid,g,next(r for r in fixture_records() if r.data.kind=='candle'))
            elif path=='membership':insert_membership(writer,sid)
            else:
                writer.execute('INSERT INTO discovery.ingestion_grants VALUES(%s,\'\',%s,%s)',(sid,g.grant_id,g.version))
                writer.execute("INSERT INTO discovery.pages VALUES(%s,'','SYN-hash',NULL,true,0,0)",(sid,))
                if path=='evidence_batch':
                    writer.execute("INSERT INTO discovery.evidence_batches VALUES(%s,'','SYN-hash',clock_timestamp(),'{}')",(sid,))
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)
    assert conn.execute('SELECT count(*) FROM discovery.pages WHERE stream_id=%s',(sid,)).fetchone()==(0,)
    assert conn.execute('SELECT count(*) FROM discovery.ingestion_grants WHERE stream_id=%s',(sid,)).fetchone()==(0,)


@pytest.mark.parametrize('path',['destination','second_grant'])
def test_expiry_after_later_dependency_lock(scoped_writer,path):
    from stock_discovery_analysis.revision_fixtures import fixture_records
    conn,url,writer,role=scoped_writer
    now=conn.execute('SELECT clock_timestamp()').fetchone()[0]
    short=fixture_grant(version='short',expires_at=(now+timedelta(seconds=5)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    ingest(conn,short if path=='destination' else fixture_grant())
    if path=='second_grant':register_test_grant(conn,short)
    if path=='destination':sid=membership_destination(conn,writer)
    else:
        sid='SYN-expiring-price'
        writer.execute("INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,'SYN-source','SYN-account','prices')",(sid,))
    ready=Event();pid=[]
    def write():
        with psycopg.connect(url,autocommit=True) as other:
            other.execute(sql.SQL('SET SESSION AUTHORIZATION {}').format(sql.Identifier(role)))
            other.execute("SET statement_timeout='15s'")
            pid.append(other.info.backend_pid);ready.set()
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with other.transaction():
                    if path=='destination':insert_membership(other,sid)
                    else:
                        raw_revision(other,sid,short,next(r for r in fixture_records() if r.data.kind=='candle'))
    with psycopg.connect(url,autocommit=True) as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute('BEGIN')
        try:
            if path=='destination':
                holder.execute("SELECT scope_id FROM discovery.grant_fences WHERE kind='account' AND account_ref='SYN-destination' FOR UPDATE")
            else:
                holder.execute("SELECT scope_id FROM discovery.grant_fences WHERE kind='grant' AND grant_version='fixture-1' FOR UPDATE")
            future=pool.submit(write);assert ready.wait(5)
            wait_for_blocker(conn,pid[0],holder.info.backend_pid)
            assert conn.execute('SELECT clock_timestamp()<%s::timestamptz',(short.expires_at,)).fetchone()==(True,)
            conn.execute('SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM %s::timestamptz-clock_timestamp())))',(short.expires_at,))
        finally:holder.execute('ROLLBACK')
        future.result(timeout=10)
    assert conn.execute('SELECT count(*) FROM discovery.stream_revisions WHERE stream_id=%s',(sid,)).fetchone()==(0,)
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)
    assert conn.execute('SELECT count(*) FROM discovery.pages WHERE stream_id=%s',(sid,)).fetchone()==(0,)
    assert conn.execute('SELECT count(*) FROM discovery.ingestion_grants WHERE stream_id=%s',(sid,)).fetchone()==(0,)
    assert conn.execute("SELECT count(*) FROM discovery.grant_fences WHERE state<>'OPEN' OR generation<>0").fetchone()==(0,)


def test_repeatable_read_revocation_serialization_rolls_back(scoped_writer):
    from stock_discovery_analysis.revision_fixtures import fixture_records
    conn,_,writer,_=scoped_writer;ingest(conn)
    with pytest.raises(psycopg.errors.SerializationFailure):
        with writer.transaction():
            writer.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            writer.execute('SELECT txid_current_snapshot()')
            writer.execute("INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES('SYN-rr','SYN-source','SYN-account','prices')")
            fence(conn)
            raw_revision(writer,'SYN-rr',fixture_grant(),next(r for r in fixture_records() if r.data.kind=='candle'))
    assert conn.execute("SELECT count(*) FROM discovery.streams WHERE stream_id='SYN-rr'").fetchone()==(0,)
    assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==(1,)
    assert writer.execute('SELECT 1').fetchone()==(1,)


def test_opposite_order_restrictions_deadlock_rolls_back_and_replays(case):
    conn,url=case
    grants=[fixture_grant(version='scope-a'),fixture_grant(version='scope-b')]
    for grant in grants:register_test_grant(conn,grant)
    barrier=Barrier(2);requests=[[uuid4(),uuid4()],[uuid4(),uuid4()]]
    def activate(operator,grant,key):
        return operator.execute("SELECT discovery.restrict_grant_scope(%s,'grant',%s,%s,%s,%s,'revoked',NULL)",
            (key,grant.source_id,grant.account_ref,grant.grant_id,grant.version)).fetchone()[0]
    def run(index):
        with psycopg.connect(url,autocommit=True) as operator:
            operator.execute("SET statement_timeout='10s'")
            operator.execute("SET deadlock_timeout='100ms'")
            try:
                with operator.transaction():
                    activate(operator,grants[index],requests[index][0]);barrier.wait(timeout=5)
                    activate(operator,grants[1-index],requests[index][1])
                return index,'committed'
            except psycopg.errors.DeadlockDetected:
                assert operator.execute('SELECT 1').fetchone()==(1,)
                return index,'rolled_back'
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,i) for i in range(2)]
        results=[f.result(timeout=15) for f in futures]
    assert sorted(status for _,status in results)==['committed','rolled_back']
    winner=next(i for i,status in results if status=='committed');loser=1-winner
    assert {row[0] for row in conn.execute('SELECT request_id FROM discovery.restriction_requests')}==set(requests[winner])
    assert conn.execute("SELECT state,generation FROM discovery.grant_fences WHERE kind='grant'").fetchall()==[('FENCED',1)]*2
    # Explicit retry uses the original audit identities, never partial prior state.
    for _ in range(2):
        for i,grant in enumerate([grants[loser],grants[winner]]):
            assert activate(conn,grant,requests[loser][i])==1
    assert conn.execute('SELECT count(*) FROM discovery.restriction_requests').fetchone()==(4,)


@pytest.mark.parametrize('kind',['instrument','membership','candle','action','session','document','news'])
def test_sql_exact_scope_allows_valid_revision(scoped_writer,kind):
    from stock_discovery_analysis.revision_fixtures import fixture_records
    conn,_,writer,_=scoped_writer
    if kind!='instrument':ingest(conn)
    record=next(r for r in fixture_records() if r.data.kind==('document' if kind=='news' else kind))
    if kind=='news':record=record.model_copy(update={'data':record.data.model_copy(update={'document_type':'news'})})
    g=fixture_grant(version='exact-scope',scopes=[record.scope],allowed_uses=['store'])
    register_test_grant(conn,g);sid='SYN-exact-scope'
    writer.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,%s,%s,%s)',
        (sid,g.source_id,g.account_ref,record.scope))
    with writer.transaction():
        raw_revision(writer,sid,g,record)
        writer.execute('INSERT INTO discovery.stream_revisions VALUES(%s,%s)',(sid,record.revision_id))
    assert conn.execute('SELECT grant_version FROM discovery.revisions WHERE revision_id=%s',(record.revision_id,)).fetchone()==('exact-scope',)


@pytest.mark.parametrize('financial_scope',[False,True])
def test_sql_financial_fact_requires_additional_scope(scoped_writer,financial_scope):
    from stock_discovery_analysis.evidence_fixtures import document_fixture
    from stock_discovery_analysis.evidence import extract
    conn,_,writer,_=scoped_writer;ingest(conn)
    doc=document_fixture();parsed=extract(doc,trusted_primary=True)
    g=fixture_grant(version='filing-grant',scopes=['filings']+(['financial_facts'] if financial_scope else []),
        allowed_uses=['store','extract','derive'])
    register_test_grant(conn,g);sid='SYN-filing-only'
    writer.execute("INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES(%s,%s,%s,'filings')",(sid,g.source_id,g.account_ref))
    with writer.transaction():
        raw_revision(writer,sid,g,doc.revision)
        writer.execute('INSERT INTO discovery.evidence_blobs VALUES(%s,%s)',(doc.revision.data.content_hash,doc.body))
        writer.execute('INSERT INTO discovery.evidence_documents VALUES(%s,%s,%s,%s,%s,%s)',
            (doc.revision.revision_id,doc.issuer_id,doc.revision.data.content_hash,parsed['text_fingerprint'],parsed['parser_version'],Jsonb(doc.model_dump(mode='json',exclude={'body'}))))
    fact=parsed['facts'][0]
    def insert_fact():
        writer.execute('INSERT INTO discovery.financial_facts VALUES(%s,%s,%s)',(fact['fact_id'],doc.revision.revision_id,Jsonb(fact)))
    if financial_scope:insert_fact()
    else:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):insert_fact()
    assert conn.execute('SELECT count(*) FROM discovery.financial_facts').fetchone()==(int(financial_scope),)
