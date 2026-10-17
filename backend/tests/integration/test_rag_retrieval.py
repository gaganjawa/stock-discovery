"""D3-07 golden retrieval cases against real PostgreSQL FTS, local mock vectors."""
import json
import os
from dataclasses import replace
from decimal import Decimal
import psycopg
import pytest
from stock_discovery_analysis.evidence import Document, content_hash
from stock_discovery_analysis.evidence_fixtures import document_fixture,evidence_access,evidence_grant,evidence_stream,adapter_fixture,seed_identity
from stock_discovery_analysis.evidence_storage import ingest_next_evidence
from stock_discovery_analysis.rag_contracts import Query,RetrievalPolicy
from stock_discovery_analysis.rag_retrieval import retrieve,MockEmbeddings
from stock_discovery_analysis.revision_fixtures import NOW

URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated PostgreSQL')


def access():
    g=evidence_grant()
    g=g.model_copy(update={'allowed_uses':(*g.allowed_uses,'embed')})
    return evidence_access(load_grant=lambda s:g)


def query(**changes):
    data=dict(issuer_id='SYN-issuer',listing_id='SYN-listing',horizon='swing',mode='synthetic',cutoff_at=NOW,
              text='earnings',categories=('annual_report',),required_metrics=('revenue','earnings'),
              period_start_at='2025-01-01T00:00:00Z',period_end_at='2025-12-31T00:00:00Z',period_kind='annual')
    data.update(changes)
    return Query(**data)


@pytest.fixture
def db():
    assert psycopg.conninfo.conninfo_to_dict(URL)['dbname']=='stk013_test'
    with psycopg.connect(URL,autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            seed_identity(conn)
            yield conn


def ingest(db,doc=None):
    doc=doc or document_fixture()
    stream=evidence_stream(doc.revision.scope).model_copy(update={'stream_id':'SYN-rag-'+doc.revision.revision_id})
    return ingest_next_evidence(db,stream,adapter_fixture(doc),access=evidence_access())


def fetch(db,**kwargs):
    return retrieve(db,kwargs.pop('query',query()),kwargs.pop('policy',RetrievalPolicy()),
                    access=kwargs.pop('access',access()),embeddings=kwargs.pop('embeddings',MockEmbeddings()),**kwargs)


def changed_document(rid,*,text=None,revenue=None,category='annual_report',available=None,sequence=1,supersedes=None,docid=None):
    raw=document_fixture(rid=rid,category=category,sequence=sequence,supersedes_id=supersedes).model_dump(mode='json')
    body=json.loads(raw['body'])
    if text is not None:
        body['text']=text;body['events']=[]
    if revenue is not None:body['facts'][0]['value']=revenue
    raw['body']=json.dumps(body)
    raw['revision']['data']['content_hash']=content_hash(raw['body'])
    if available:
        raw['revision']['available_at']=available
        raw['revision']['fetched_at']=available
    if docid:raw['revision']['data']['document_id']=docid
    return Document.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize('text,lexical,semantic',[('earnings',True,True),('profit',False,True),('unknownquasar',False,False)])
def test_golden_lexical_semantic_and_no_match(db,text,lexical,semantic):
    assert ingest(db)['accepted']==1
    b=fetch(db,query=query(text=text))
    assert b.retrieval_mode=='hybrid'
    assert bool(b.hits and b.hits[0].lexical_rank)==lexical
    assert bool(b.hits and b.hits[0].semantic_rank)==semantic
    if b.hits:
        assert b.hits[0].citations[0].locator=='$.text:chars[0:48]'
    else:assert 'relevant_text' in b.missing
    assert {f.metric:f.value for f in b.facts}=={'revenue':'10000000','earnings':'1000000'}
    assert fetch(db,query=query(text=text)).content_hash==b.content_hash


def test_issuer_type_cutoff_period_and_scope_prefilters(db):
    ingest(db)
    for q in (query(issuer_id='other'),query(listing_id='other'),query(categories=('news',)),
              query(cutoff_at='2026-10-14T10:00:00Z'),query(mode='historical_reconstructed')):
        b=fetch(db,query=q)
        assert not b.documents and not b.hits and not b.facts and b.missing
    for q in (query(scope='standalone'),query(period_kind='quarter')):
        assert not fetch(db,query=q).facts


@pytest.mark.parametrize('use',['derive','store'])
def test_rights_denial_prevents_bundle_persistence(db,use):
    ingest(db);g=evidence_grant();g=g.model_copy(update={'allowed_uses':tuple(x for x in g.allowed_uses if x!=use)})
    with pytest.raises(PermissionError):fetch(db,access=evidence_access(load_grant=lambda s:g))
    assert db.execute('SELECT count(*) FROM discovery.rag_bundles').fetchone()[0]==0


def test_embed_denial_labelled_fallback_before_model(db):
    ingest(db)
    class Never(MockEmbeddings):
        def embed(self,*args,**kwargs):raise AssertionError('must not embed')
    b=fetch(db,access=evidence_access(),embeddings=Never())
    assert b.retrieval_mode=='lexical_only' and b.embedding is None
    assert 'semantic:embedding_permission_denied' in b.omitted
    assert b.hits[0].semantic_score is None


def test_revocation_during_embedding_blocks_results(db):
    ingest(db);state={'revoked':False};g=access().load_grant(None)
    a=evidence_access(load_grant=lambda s:g.model_copy(update={'status':'revoked','revoked_at':NOW}) if state['revoked'] else g)
    class Revoking(MockEmbeddings):
        def embed(self,*args,**kwargs):
            result=super().embed(*args,**kwargs);state['revoked']=True;return result
    with pytest.raises(PermissionError):fetch(db,access=a,embeddings=Revoking())
    assert db.execute('SELECT count(*) FROM discovery.rag_bundles').fetchone()[0]==0


def test_revisions_do_not_leak_future_and_staleness_is_explicit(db):
    ingest(db)
    revised=changed_document('SYN-revised',revenue='200',available='2026-10-15T11:30:00Z',sequence=2,supersedes='SYN-E-report')
    assert ingest(db,revised)['accepted']==1
    old=fetch(db,query=query(cutoff_at='2026-10-15T11:00:00Z'))
    new=fetch(db)
    assert old.documents==('SYN-E-report',) and new.documents==('SYN-revised',)
    assert next(f.value for f in new.facts if f.metric=='revenue')=='20000000'
    stale=fetch(db,query=query(cutoff_at='2026-10-20T12:00:00Z'),policy=RetrievalPolicy(max_age_days=1),access=replace(access(),clock=lambda:'2026-10-20T12:00:00Z'))
    assert 'category:annual_report' in stale.missing and any(x.startswith('stale:') for x in stale.omitted)


def test_dedup_keeps_attribution_and_conflicting_facts(db):
    ingest(db)
    assert ingest(db,changed_document('SYN-copy',revenue='200',docid='SYN-other-report'))['accepted']==1
    b=fetch(db)
    assert len(b.hits)==1 and len(b.hits[0].citations)==2
    assert len(b.contradictions)==1 and len(b.facts)==4
    assert b.source_count==1


def test_chunk_caps_ties_and_primary_preference(db):
    ingest(db)
    assert ingest(db,changed_document('SYN-news',category='news'))['accepted']==1
    b=fetch(db,query=query(categories=('annual_report','news')))
    assert len(b.hits)==1 and b.hits[0].primary and len(b.hits[0].citations)==2
    assert ingest(db,changed_document('SYN-counter',text='Earnings debt risks',docid='SYN-counter'))['accepted']==1
    capped=fetch(db,query=query(text='earnings debt'),policy=RetrievalPolicy(max_chunks=1))
    assert len(capped.hits)==1 and any(x.startswith('chunk_cap:') for x in capped.omitted)


def test_bounded_input_documents_deadline_and_paid_provider(db):
    ingest(db)
    with pytest.raises(ValueError,match='byte cap'):fetch(db,policy=RetrievalPolicy(max_bytes=10))
    with pytest.raises(ValueError,match='deadline'):fetch(db,deadline=0)
    class Paid(MockEmbeddings):cost_per_unit=Decimal('0.1')
    with pytest.raises(ValueError,match='disabled'):fetch(db,embeddings=Paid())
    ingest(db,changed_document('SYN-second',docid='SYN-second'))
    with pytest.raises(ValueError,match='scan cap'):fetch(db,policy=RetrievalPolicy(max_documents=1))


def test_postgres_fts_index_and_manifest_immutable(db):
    ingest(db);fetch(db)
    assert db.execute("SELECT indexdef FROM pg_indexes WHERE indexname='evidence_chunks_fts'").fetchone()
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute("UPDATE discovery.rag_bundles SET payload='{}'")
