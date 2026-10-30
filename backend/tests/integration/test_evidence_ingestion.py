import json
import os
from dataclasses import replace
import psycopg
import pytest
from stock_discovery_analysis.evidence import EvidencePage,Document,MockEvidenceAdapter,content_hash
from stock_discovery_analysis.evidence_fixtures import (document_fixture,evidence_access,evidence_grant,evidence_stream,adapter_fixture,seed_identity)
from stock_discovery_analysis.evidence_storage import (ingest_evidence_page,ingest_next_evidence,read_evidence,evidence_asof,evidence_handler,dispatch_events)
from stock_discovery_analysis.revision_fixtures import NOW,fixture_adapter,fixture_request,fixture_stream
from stock_discovery_analysis.revision_storage import ingest_next,freeze_snapshot
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.schedule_runner import tick

URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated PostgreSQL')


@pytest.fixture
def db():
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname']=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            seed_identity(conn)
            yield conn


def ingest(conn,doc=None,stream=None,access=None):
    return ingest_next_evidence(conn,stream or evidence_stream(),adapter_fixture(doc),access=access or evidence_access())


def read(conn,rid='SYN-E-report',**changes):
    args=dict(access=evidence_access(),cutoff=NOW,mode='synthetic')
    args.update(changes)
    return read_evidence(conn,rid,**args)


def test_automatic_page_atomicity_retry_and_content_dedup(db):
    doc=document_fixture(); adapter=adapter_fixture(doc); stream=evidence_stream()
    with pytest.raises(RuntimeError):
        with db.transaction():
            ingest_next_evidence(db,stream,adapter,access=evidence_access())
            raise RuntimeError('worker lost before commit')
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==0
    result=ingest(db)
    assert result['accepted']==1 and result['complete']
    same=ingest_evidence_page(db,stream,adapter.pages[None],access=evidence_access())
    assert same['reused']
    another_stream=stream.model_copy(update={'stream_id':'SYN-another-scan'})
    ingest(db,doc,another_stream)
    assert db.execute('SELECT count(*) FROM discovery.evidence_blobs').fetchone()[0]==1
    assert len(read(db)['facts'])==11
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute("UPDATE discovery.evidence_blobs SET body='tampered'")


@pytest.mark.parametrize('use',['acquire','store','extract','derive'])
def test_use_denial_halts_before_commit(db,use):
    grant=evidence_grant()
    denied=grant.model_copy(update={'allowed_uses':tuple(u for u in grant.allowed_uses if u!=use)})
    adapter=adapter_fixture()
    with pytest.raises(PermissionError):
        ingest_next_evidence(db,evidence_stream(),adapter,access=evidence_access(load_grant=lambda s:denied))
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==0
    if use=='acquire':assert adapter.calls==0


def test_revocation_after_acquisition_and_before_cached_use(db):
    state={'revoked':False}
    grant=evidence_grant()
    revoked=grant.model_copy(update={'status':'revoked','revoked_at':NOW})
    class Revoking:
        def fetch(self,cursor,limit):
            state['revoked']=True
            return adapter_fixture().fetch(cursor,limit)
    access=evidence_access(load_grant=lambda s:revoked if state['revoked'] else grant)
    with pytest.raises(PermissionError):ingest_next_evidence(db,evidence_stream(),Revoking(),access=access)
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==0
    ingest(db)
    with pytest.raises(PermissionError):read(db,access=access)
    with pytest.raises(PermissionError):read(db,purpose='external_ai')
    with pytest.raises(PermissionError):read(db,purpose='embed')


def test_future_cutoff_mode_and_financial_scope_denial(db):
    ingest(db)
    with pytest.raises(ValueError,match='unavailable'):read(db,cutoff='2026-10-14T09:00:00Z')
    with pytest.raises(ValueError,match='future'):read(db,cutoff='2027-01-01T00:00:00Z')
    with pytest.raises(PermissionError,match='^real_read_access_denied$'):read(db,mode='live_paper')
    grant=evidence_grant(); grant=grant.model_copy(update={'scopes':tuple(s for s in grant.scopes if s!='financial_facts')})
    with pytest.raises(PermissionError):read(db,access=evidence_access(load_grant=lambda s:grant))


@pytest.mark.parametrize('change',[
    lambda d:d.update(issuer_id='SYN-wrong-issuer'),
    lambda d:d['revision'].update(instrument_revision_id='missing'),
    lambda d:d['revision']['data'].update(content_hash='0'*64),
    lambda d:d.update(media_type='application/pdf'),
    lambda d:d.update(attribution='wrong source attribution'),
])
def test_invalid_conflicting_identity_is_hash_only_quarantine(db,change):
    raw=document_fixture().model_dump(mode='json');change(raw)
    page=EvidencePage(cursor=None,next_cursor=None,complete=True,records=(raw,))
    result=ingest_evidence_page(db,evidence_stream(),page,access=evidence_access())
    assert result['status']=='partial' and result['quarantined']==1
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==0
    assert db.execute('SELECT reason FROM discovery.quarantine').fetchone()[0]=='invalid_record'


def test_revised_filing_is_asof_and_stale_missing_is_explicit(db):
    first=document_fixture();ingest(db,first)
    raw=document_fixture(rid='SYN-E-correction',sequence=2,supersedes_id=first.revision.revision_id).model_dump(mode='json')
    body=json.loads(raw['body']);body['facts'][0]['value']='90'
    raw['body']=json.dumps(body);raw['revision']['data']['content_hash']=content_hash(raw['body'])
    raw['revision'].update(published_at='2026-10-15T11:00:00Z',available_at='2026-10-15T11:01:00Z',fetched_at=NOW)
    corrected=Document.model_validate_json(json.dumps(raw))
    ingest(db,corrected,evidence_stream().model_copy(update={'stream_id':'SYN-corrections'}))
    def coverage(cutoff,max_age=30,access=None):
        return evidence_asof(db,'SYN-listing',access=access or evidence_access(),cutoff=cutoff,mode='synthetic',max_age_days=max_age,required_categories=('annual_report','news'))
    before=coverage('2026-10-15T10:00:00Z');after=coverage(NOW)
    assert before['documents'][0]['document']['revision']['revision_id']==first.revision.revision_id
    assert after['documents'][0]['document']['revision']['revision_id']==corrected.revision.revision_id
    assert after['missing_or_stale']==['news']
    stale=coverage('2026-11-20T12:00:00Z',1,evidence_access(clock=lambda:'2026-11-20T12:00:00Z'))
    assert stale['missing_or_stale']==['annual_report','news']


def market_seed(conn):
    for scope in ('calendar','prices','corporate_actions'):
        adapter=fixture_adapter(scope)
        for _ in adapter.pages:
            ingest_next(conn,fixture_stream(scope),adapter,clock=lambda:NOW,load_grant=evidence_grant,
                        request=fixture_request(scope),audit=lambda d:None)


def event_snapshot(conn,stream,now):
    streams=tuple(fixture_stream(s) for s in ('universe','calendar','prices','corporate_actions'))+(stream,)
    return freeze_snapshot(conn,streams=streams,load_grant=lambda s:evidence_grant(),
        requests={s.stream_id:fixture_request(s.scope,requested_at=now) for s in streams},audit=lambda d:None,
        mode='synthetic',cutoff=now,created_at=now,universe_version='SYN-universe-1',calendar_version='SYN-calendar-1')


def test_unattended_scheduler_ingestion_reassessment_dedup(db):
    market_seed(db);config=fixture_config()
    handler=evidence_handler(evidence_stream(),adapter_fixture(),evidence_access(),config=config,read_authorized_snapshot=event_snapshot)
    result=tick(db,config,clock=lambda:NOW,handlers={'event_poll':handler})
    assert result['status']=='completed'
    assert db.execute('SELECT count(*) FROM discovery.evidence_dispatch').fetchone()[0]==1
    assert db.execute("SELECT count(*) FROM discovery.schedule_jobs WHERE stage='reassess'").fetchone()[0]==1
    streamrow=db.execute("SELECT stream_id FROM discovery.evidence_batches LIMIT 1").fetchone()[0]
    stream=evidence_stream().model_copy(update={'stream_id':streamrow})
    assert dispatch_events(db,config,('SYN-E-report',),access=evidence_access(),cutoff=NOW,read_authorized_snapshot=lambda:event_snapshot(db,stream,NOW))==()
    assert db.execute('SELECT count(*) FROM discovery.schedule_outbox').fetchone()[0]==1


def test_news_unverified_never_queues_reassessment(db):
    doc=document_fixture(category='news');ingest(db,doc,evidence_stream('news'))
    assert read(db)['events'][0]['status']=='unverified'
    def forbidden():raise AssertionError('unverified claim must not nominate')
    assert dispatch_events(db,fixture_config(),('SYN-E-report',),access=evidence_access(),cutoff=NOW,read_authorized_snapshot=forbidden)==()


def test_changed_retry_page_rejected_and_new_record_conflict_quarantined(db):
    ingest(db)
    raw=document_fixture().model_dump(mode='json');raw['title']='changed title'
    page=EvidencePage(cursor=None,next_cursor=None,complete=True,records=(raw,))
    with pytest.raises(ValueError,match='changed evidence page'):
        ingest_evidence_page(db,evidence_stream(),page,access=evidence_access())
    result=ingest_evidence_page(db,evidence_stream().model_copy(update={'stream_id':'SYN-conflict'}),page,access=evidence_access())
    assert result['quarantined']==1


def test_untrusted_primary_label_does_not_confirm_claim(db):
    access=replace(evidence_access(),primary_source_ids=frozenset())
    ingest(db,access=access)
    assert read(db)['events'][0]['status']=='unverified'


def test_paging_continues_on_restart_and_new_occurrence_rescans(db):
    one=document_fixture()
    two=one.model_copy(update={'revision':one.revision.model_copy(update={
        'revision_id':'SYN-second','source_revision':'SYN-second',
        'data':one.revision.data.model_copy(update={'document_id':'SYN-second-report'})})})
    adapter=MockEvidenceAdapter((EvidencePage(cursor=None,next_cursor='page2',complete=False,records=(one.model_dump(mode='json'),)),
        EvidencePage(cursor='page2',next_cursor=None,complete=True,records=(two.model_dump(mode='json'),))))
    config=fixture_config()
    handler=evidence_handler(evidence_stream(),adapter,evidence_access())
    first=tick(db,config,clock=lambda:NOW,handlers={'event_poll':handler})
    assert first['status']=='completed'
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==1
    # New handler instance simulates a process restart; cursor lives in PostgreSQL.
    second=tick(db,config,clock=lambda:NOW,handlers={'event_poll':evidence_handler(evidence_stream(),adapter,evidence_access())})
    assert second['status']=='completed' and adapter.calls==2
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==2
    assert db.execute('SELECT count(*) FROM discovery.evidence_blobs').fetchone()[0]==1
    later='2026-10-15T13:00:00Z'
    tick(db,config,clock=lambda:later,handlers={'event_poll':handler})
    assert adapter.calls==3


def test_worker_retry_and_partial_result_are_not_false_success(db):
    from stock_discovery_analysis.schedule_runner import JobFailure
    adapter=adapter_fixture()
    class Transient:
        def __init__(self):self.failed=False
        def fetch(self,cursor,limit):
            if not self.failed:
                self.failed=True
                raise JobFailure('transient',retry_after_seconds=60)
            return adapter.fetch(cursor,limit)
    config=fixture_config()
    handler=evidence_handler(evidence_stream(),Transient(),evidence_access())
    result=tick(db,config,clock=lambda:NOW,handlers={'event_poll':handler})
    assert result['status']=='retry_wait'
    result=tick(db,config,clock=lambda:'2026-10-15T12:01:00Z',handlers={'event_poll':handler})
    assert result['status']=='completed'
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==1
    raw=document_fixture().model_dump(mode='json');raw['issuer_id']='wrong'
    bad=MockEvidenceAdapter((EvidencePage(cursor=None,next_cursor=None,complete=True,records=(raw,)),))
    result=tick(db,config,clock=lambda:'2026-10-15T13:00:00Z',handlers={'event_poll':evidence_handler(evidence_stream(),bad,evidence_access())})
    assert result['status']=='partial'


def test_duplicate_news_fingerprint_preserves_both_sources(db):
    one=document_fixture(category='news')
    raw=one.model_dump(mode='json')
    body=json.loads(raw['body']);body['text']=body['text'].upper()+'  '
    body['events'][0]['statement']=body['text'].strip()
    raw['body']=json.dumps(body);raw['revision']['data']['content_hash']=content_hash(raw['body'])
    raw['revision'].update(revision_id='SYN-syndicated',source_revision='SYN-syndicated')
    raw['revision']['data']['document_id']='SYN-syndicated-report'
    two=Document.model_validate_json(json.dumps(raw))
    ingest(db,one,evidence_stream('news'))
    ingest(db,two,evidence_stream('news').model_copy(update={'stream_id':'SYN-news2'}))
    assert db.execute('SELECT count(DISTINCT text_fingerprint),count(*) FROM discovery.evidence_documents').fetchone()==(1,2)
    assert db.execute('SELECT count(DISTINCT event_key),count(*) FROM discovery.evidence_claims').fetchone()==(1,2)


def test_text_only_report_is_partial_financial_coverage(db):
    raw=document_fixture().model_dump(mode='json')
    raw.update(media_type='text/plain',body='Report table unavailable; do not infer figures.')
    raw['revision']['data']['content_hash']=content_hash(raw['body'])
    ingest(db,Document.model_validate_json(json.dumps(raw)))
    result=evidence_asof(db,'SYN-listing',access=evidence_access(),cutoff=NOW,mode='synthetic',max_age_days=30,required_categories=('annual_report',))
    assert result['status']=='partial' and result['incomplete_financial_revisions']==['SYN-E-report']


def test_shipped_automatic_worker_feed_needs_no_upload(db):
    from stock_discovery_analysis.evidence_fixtures import scheduled_handlers
    config=fixture_config()
    result=tick(db,config,clock=lambda:NOW,handlers=scheduled_handlers(config))
    assert result['status']=='completed'
    assert db.execute('SELECT count(*) FROM discovery.evidence_documents').fetchone()[0]==2
    assert dict(db.execute('SELECT status,count(*) FROM discovery.evidence_claims GROUP BY status').fetchall())=={'confirmed':1,'unverified':1}
    assert db.execute('SELECT count(*) FROM discovery.evidence_dispatch').fetchone()[0]==1


def test_revocation_during_extraction_rolls_back_everything(db,monkeypatch):
    import stock_discovery_analysis.evidence_storage as storage
    original=storage.extract
    state={'revoked':False}
    grant=evidence_grant()
    revoked=grant.model_copy(update={'status':'revoked','revoked_at':NOW})
    def extract_then_revoke(*args,**kwargs):
        result=original(*args,**kwargs);state['revoked']=True;return result
    monkeypatch.setattr(storage,'extract',extract_then_revoke)
    access=evidence_access(load_grant=lambda s:revoked if state['revoked'] else grant)
    with pytest.raises(PermissionError):ingest(db,access=access)
    assert db.execute('SELECT count(*) FROM discovery.evidence_blobs').fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM discovery.streams WHERE stream_id=%s',(evidence_stream().stream_id,)).fetchone()[0]==0


def test_financial_extract_permission_is_checked_before_parser(db,monkeypatch):
    import stock_discovery_analysis.evidence_storage as storage
    grant=evidence_grant().model_copy(update={'scopes':('universe','filings')})
    def forbidden(*args,**kwargs):raise AssertionError('parser must not run')
    monkeypatch.setattr(storage,'extract',forbidden)
    with pytest.raises(PermissionError):ingest(db,access=evidence_access(load_grant=lambda s:grant))
