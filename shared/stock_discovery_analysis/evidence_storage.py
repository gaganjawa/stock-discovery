"""Rights-gated evidence acquisition, extraction, retrieval and event dispatch."""
import json
from dataclasses import dataclass, field, replace

from psycopg.types.json import Jsonb
from stock_discovery_contracts.rights import UseRequest
from stock_discovery_contracts.v2 import check, digest, at
from .evidence import Document, EvidencePage, extract
from .revision_storage import Stream, Page, ingest_page, permission, wire
from .revisions import Revision, eligible
from .schedule_events import MaterialEvent, nominate


@dataclass(frozen=True)
class Access:
    load_grant: object
    request_for: object
    audit: object
    clock: object
    primary_source_ids: frozenset[str] = frozenset()

    fence_conn: object = field(default=None,repr=False,compare=False)
    fence_permits: dict = field(default_factory=dict,repr=False,compare=False)

    def require(self,stream,uses):
        request=self.request_for(stream)
        request=UseRequest.model_validate({**request.model_dump(),'requested_at':self.clock()})
        grant=self.load_grant(stream)
        permission(grant,request,stream,uses,self.audit)
        if self.fence_conn is not None:
            from .grant_fences import capture, enforce
            key=(stream.source_id,stream.account_ref)
            if key not in self.fence_permits:
                self.fence_permits[key]=capture(self.fence_conn,grant,request,uses)
            else:
                with self.fence_conn.transaction():
                    enforce(self.fence_conn,self.fence_permits[key],grant,request,uses)
        return grant,request


def stored_stream(conn,revision_id):
    row=conn.execute('''SELECT s.stream_id,s.source_id,s.account_ref,s.scope FROM discovery.streams s
        JOIN discovery.revisions r USING(stream_id) WHERE r.revision_id=%s''',(revision_id,)).fetchone()
    check(row is not None,'source revision unavailable')
    return Stream(stream_id=row[0],source_id=row[1],account_ref=row[2],scope=row[3])


def verify_identity(conn,document,access):
    rid=document.revision.instrument_revision_id
    stream=stored_stream(conn,rid)
    access.require(stream,('derive',))
    row=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(rid,)).fetchone()
    identity=Revision.model_validate(row[0])
    check(identity.data.kind=='instrument' and identity.listing_id==document.revision.listing_id,'instrument identity conflict')
    check(identity.data.issuer_id==document.issuer_id,'issuer identity conflict')
    check(at(identity.available_at)<=at(document.revision.available_at),'future instrument identity')
    check(identity.availability_basis==document.revision.availability_basis,'identity provenance mismatch')


def ingest_evidence_page(conn,stream,page,*,access,permit=None):
    """Whole page, D3-03 checkpoint and extracted content commit atomically."""
    page=EvidencePage.model_validate_json(page.model_dump_json())
    grant,request=access.require(stream,('store',))
    from .grant_fences import capture, enforce, sanitized_fence_errors
    permit=permit or capture(conn,grant,request)
    check(len(page.records)<=request.units,'page quota')
    full_hash=digest(page.model_dump(mode='json'))
    with sanitized_fence_errors(), conn.transaction():
        enforce(conn,permit,access.load_grant(stream),request)
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('D3-stream:'+stream.stream_id,))
        previous=conn.execute('SELECT content_hash,result FROM discovery.evidence_batches WHERE stream_id=%s AND cursor_key=%s',(stream.stream_id,page.cursor or '')).fetchone()
        if previous:
            conn.execute('SELECT discovery.check_ingestion_page(%s,%s)',(stream.stream_id,page.cursor or ''))
            check(previous[0]==full_hash,'changed evidence page on retry')
            # Cached extracted results also require current extraction/derivation rights.
            access.require(stream,('extract','derive'))
            return {**previous[1],'reused':True}
        accepted=[]
        rejections=[]
        metadata=[]
        for raw in page.records:
            try:
                document=Document.model_validate_json(json.dumps(raw))
                check(document.revision.source_id==stream.source_id and document.revision.scope==stream.scope,'source scope mismatch')
                check((document.revision.availability_basis=='fictional_fixture')==request.synthetic,'document mode mismatch')
                check(at(document.revision.fetched_at)<=at(request.requested_at),'future fetch')
                check(grant.attribution in document.attribution,'required source attribution')
                verify_identity(conn,document,access)
                access.require(stream,('extract',))
                if document.media_type=='application/vnd.stock-evidence+json':
                    access.require(stream.model_copy(update={'scope':'financial_facts'}),('extract','store'))
                parsed=extract(document,trusted_primary=stream.source_id in access.primary_source_ids)
                if parsed['facts']:
                    access.require(stream.model_copy(update={'scope':'financial_facts'}),('extract','store'))
                check(sum(len(parsed[k]) for k in ('chunks','facts','events'))<=request.units,'extraction quota')
                old=conn.execute('SELECT payload FROM discovery.evidence_documents WHERE revision_id=%s',(document.revision.revision_id,)).fetchone()
                check(old is None or old[0]==document.model_dump(mode='json',exclude={'body'}),'document identity conflict')
            except (ValueError,KeyError) as exc:
                # No raw unpermitted content is retained in quarantine.
                reason=str(exc) if type(exc) is ValueError and str(exc) in {'issuer identity conflict','instrument identity conflict','source revision unavailable','document identity conflict','balance sheet reconciliation','margin reconciliation','required source attribution','future fetch','source scope mismatch','document mode mismatch','extraction quota','duplicate/conflicting financial fact','future financial period','event quote not in source text'} else 'invalid_evidence'
                rejections.append(dict(position=len(metadata),content_hash=digest(raw),reason=reason))
                metadata.append({'invalid_evidence_hash':digest(raw),'reason':reason})
                continue
            metadata.append(wire(document.revision))
            accepted.append((document,parsed))
        # D3-03 validates mode, timestamps, identity chains and record collisions.
        _,request=access.require(stream,('store',))
        result=ingest_page(conn,stream,Page(cursor=page.cursor,next_cursor=page.next_cursor,complete=page.complete,records=tuple(metadata)),
            load_grant=lambda:access.load_grant(stream),request=request,audit=access.audit,permit=permit)
        documents=[]
        for document,parsed in accepted:
            rid=document.revision.revision_id
            row=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(rid,)).fetchone()
            if row is None or row[0]!=wire(document.revision):
                continue
            # Recheck current permissions after parsing, before committing source or derived content.
            access.require(stream,('store','extract','derive'))
            if parsed['facts']:
                access.require(stream.model_copy(update={'scope':'financial_facts'}),('store',))
            conn.execute('INSERT INTO discovery.evidence_blobs VALUES (%s,%s) ON CONFLICT DO NOTHING', (document.revision.data.content_hash,document.body))
            check(conn.execute('SELECT body FROM discovery.evidence_blobs WHERE content_hash=%s',(document.revision.data.content_hash,)).fetchone()[0]==document.body,'content hash conflict')
            conn.execute('INSERT INTO discovery.evidence_documents VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (rid,document.issuer_id,document.revision.data.content_hash,parsed['text_fingerprint'],parsed['parser_version'],Jsonb(document.model_dump(mode='json',exclude={'body'}))))
            for chunk in parsed['chunks']:
                conn.execute('INSERT INTO discovery.evidence_chunks VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(chunk['chunk_id'],rid,Jsonb(chunk)))
            for fact in parsed['facts']:
                conn.execute('INSERT INTO discovery.financial_facts VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(fact['fact_id'],rid,Jsonb(fact)))
            for event in parsed['events']:
                conn.execute('INSERT INTO discovery.evidence_claims VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (event['claim_id'],rid,event['event_key'],event['status'],Jsonb(event)))
            documents.append(rid)
        result={**result,'document_revision_ids':sorted(documents),'complete':page.complete,'rejections':rejections,
                'status':'partial' if result['quarantined'] else 'complete'}
        enforce(conn,permit,access.load_grant(stream),request,('store','extract','derive'))
        conn.execute('INSERT INTO discovery.evidence_batches VALUES (%s,%s,%s,%s,%s)',
                     (stream.stream_id,page.cursor or '',full_hash,access.clock(),Jsonb(result)))
        return result


def ingest_next_evidence(conn,stream,adapter,*,access):
    grant,request=access.require(stream,('acquire',))
    from .grant_fences import capture
    permit=capture(conn,grant,request,('acquire','store'))
    state=conn.execute('SELECT cursor,complete FROM discovery.streams WHERE stream_id=%s',(stream.stream_id,)).fetchone()
    if state and state[1]:
        with conn.transaction():
            for row in conn.execute('SELECT cursor_key FROM discovery.pages WHERE stream_id=%s ORDER BY cursor_key',(stream.stream_id,)):
                conn.execute('SELECT discovery.check_ingestion_page(%s,%s)',(stream.stream_id,row[0]))
        return dict(complete=True,status='already_complete',document_revision_ids=[])
    cursor=state[0] if state else None
    page=adapter.fetch(cursor,min(request.units,10))
    check(page.cursor==cursor,'adapter cursor mismatch')
    return ingest_evidence_page(conn,stream,page,access=access,permit=permit)


def read_evidence(conn,revision_id,*,access,cutoff,mode,purpose='derive'):
    check(purpose in ('derive','embed','external_ai','export','paper_evaluation'),'unsupported downstream use')
    check(at(cutoff)<=at(access.clock()),'future observation cutoff')
    stream=stored_stream(conn,revision_id)
    uses=(purpose,'historical_replay') if mode=='historical_reconstructed' else (purpose,)
    _,request=access.require(stream,uses)
    check(request.synthetic==(mode=='synthetic'),'evidence mode mismatch')
    metadata=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(revision_id,)).fetchone()
    revision=Revision.model_validate(metadata[0])
    check(eligible(revision,cutoff,mode),'evidence unavailable at cutoff')
    row=conn.execute('SELECT d.payload,b.body FROM discovery.evidence_documents d JOIN discovery.evidence_blobs b USING(content_hash) WHERE revision_id=%s',(revision_id,)).fetchone()
    check(row is not None,'document body unavailable')
    document=Document.model_validate_json(json.dumps({**row[0],'body':row[1]}))
    # Source text is untrusted data. No instruction contained in it is executed.
    chunks=[r[0] for r in conn.execute('SELECT payload FROM discovery.evidence_chunks WHERE revision_id=%s ORDER BY payload->>\'locator\'',(revision_id,))]
    has_facts=conn.execute('SELECT 1 FROM discovery.financial_facts WHERE revision_id=%s LIMIT 1',(revision_id,)).fetchone()
    if has_facts:
        access.require(stream.model_copy(update={'scope':'financial_facts'}),uses)
    facts=[r[0] for r in conn.execute('SELECT payload FROM discovery.financial_facts WHERE revision_id=%s ORDER BY fact_id',(revision_id,))]
    claims=[r[0] for r in conn.execute('SELECT payload FROM discovery.evidence_claims WHERE revision_id=%s ORDER BY claim_id',(revision_id,))]
    access.require(stream,uses)
    required={'revenue','earnings','operating_cash_flow','capital_expenditure','debt','cash','equity','diluted_shares'}
    periods={(f['period_start_at'],f['period_end_at'],f['period_kind'],f['scope']) for f in facts if f['period_kind']!='instant'}
    financial_coverage=[]
    for start,end,kind,scope in sorted(periods):
        present={f['metric'] for f in facts if f['scope']==scope and f['period_end_at']==end and f['value'] is not None
                 and ((f['period_start_at']==start and f['period_kind']==kind) or f['period_kind']=='instant')}
        financial_coverage.append(dict(period_start_at=start,period_end_at=end,period_kind=kind,scope=scope,missing_metrics=sorted(required-present)))
    incomplete=document.category in ('annual_report','quarterly_report') and (not financial_coverage or any(p['missing_metrics'] for p in financial_coverage))
    return dict(document=wire(document),chunks=chunks,facts=facts,events=claims,
        financial_coverage=financial_coverage,extraction_status='partial' if incomplete else 'complete')


def evidence_asof(conn,listing_id,*,access,cutoff,mode,max_age_days,required_categories):
    check(type(max_age_days) is int and max_age_days>0,'explicit freshness setting required')
    check(set(required_categories)<={'announcement','annual_report','quarterly_report','news'},'coverage categories')
    rows=conn.execute('''SELECT r.revision_id,r.logical_key,r.source_id,r.available_at,r.sequence
        FROM discovery.revisions r JOIN discovery.evidence_documents d USING(revision_id)
        WHERE r.listing_id=%s AND r.available_at<=%s ORDER BY r.available_at,r.sequence,r.revision_id''',(listing_id,cutoff)).fetchall()
    # Rights are checked for every selected source. Denial is not silently hidden by another source.
    latest={}
    for rid,key,source,_,_ in rows:
        latest[(source,key)]=rid
    documents=[]
    for rid in sorted(latest.values()):
        documents.append(read_evidence(conn,rid,access=access,cutoff=cutoff,mode=mode))
    fresh={d['document']['category'] for d in documents
           if (at(cutoff)-at(d['document']['revision']['available_at'])).total_seconds()<=max_age_days*86400}
    missing=sorted(set(required_categories)-fresh)
    incomplete=[d['document']['revision']['revision_id'] for d in documents if d['extraction_status']=='partial']
    return dict(documents=documents,missing_or_stale=missing,incomplete_financial_revisions=incomplete,status='partial' if missing or incomplete else 'complete')


def dispatch_events(conn,config,revision_ids,*,access,cutoff,read_authorized_snapshot):
    jobs=[]
    with conn.transaction():
        for rid in sorted(set(revision_ids)):
            bundle=read_evidence(conn,rid,access=access,cutoff=cutoff,mode=config.mode)
            revision=bundle['document']['revision']
            for event in bundle['events']:
                if event['status']!='confirmed':
                    continue
                key=event['event_key']
                conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('evidence-event:'+key,))
                if conn.execute('SELECT 1 FROM discovery.evidence_dispatch WHERE event_key=%s',(key,)).fetchone():
                    continue
                # The snapshot loader rechecks rights and must contain this exact document revision.
                nominated=nominate(conn,config,(MaterialEvent(listing_id=revision['listing_id'],source_revision_id=rid,
                    event_type=event['event_type'],observed_at=cutoff),),access.clock(),read_authorized_snapshot=read_authorized_snapshot)
                if nominated:
                    conn.execute('INSERT INTO discovery.evidence_dispatch VALUES (%s,%s)',(key,nominated[0]))
                    jobs.extend(nominated)
    return tuple(jobs)


def evidence_handler(stream,adapter,access,*,config=None,read_authorized_snapshot=None):
    """Install as event_poll: bounded pages, durable continuations, a new scan per occurrence.

    Snapshot callback signature is (connection, current_stream, trusted_now).
    Handlers and adapters are trusted installed code, never document instructions.
    """
    def handle(conn,job,clock):
        from .schedule_store import enqueue
        from .scheduling import Occurrence
        active=replace(access,clock=clock)
        stream_id=job['payload']['extra'].get('evidence_stream_id',stream.stream_id+':'+job['payload']['occurrence_id'])
        current_stream=stream.model_copy(update={'stream_id':stream_id})
        result=ingest_next_evidence(conn,current_stream,adapter,access=active)
        if config is not None and result['document_revision_ids']:
            check(read_authorized_snapshot is not None,'authorized event snapshot required')
            result['reassessment_jobs']=dispatch_events(conn,config,result['document_revision_ids'],access=active,
                cutoff=clock(),read_authorized_snapshot=lambda:read_authorized_snapshot(conn,current_stream,clock()))
        if not result['complete'] and result['status']!='partial':
            row=conn.execute('SELECT payload FROM discovery.occurrences WHERE occurrence_id=%s',(job['payload']['occurrence_id'],)).fetchone()
            item=Occurrence.model_validate(row[0])
            enqueue(conn,item,'event_poll',clock(),parent_id=job['job_id'],
                catch_up=job['payload']['catch_up'],extra={'evidence_stream_id':stream_id})
        return result,None
    return handle
