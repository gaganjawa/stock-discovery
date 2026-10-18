"""Single-worker queue, fenced atomic publication and permission-aware reads."""
from datetime import datetime, timezone
import uuid
from typing import Literal
import json
from psycopg.types.json import Jsonb
from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Profile, digest, check
from .publication import build_artifact, research_candidate, COHORTS
from .publication_fixtures import inputs, ingest_candidate, access_for, CASES, VERSION, SOURCE
from .revision_storage import Stream
from .rag_research import recheck
from .rag_contracts import Bundle


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class RunRequest(Strict):
    horizon: Profile
    mode: Literal['synthetic'] = 'synthetic'
    scope: Literal['SYN-D309-1'] = VERSION


def require_sources(access):
    grants={}
    for scope in ('universe','calendar','prices','corporate_actions','filings','news','financial_facts'):
        stream=Stream(stream_id='SYN-D309-'+scope,source_id=SOURCE,account_ref='SYN-account',scope=scope)
        grant,_=access.require(stream,('derive',))
        grants[scope]=grant.model_dump(mode='json')
    return grants


def enqueue(conn, request, key, code_version):
    check(1<=len(key)<=128,'invalid idempotency key')
    request=RunRequest.model_validate_json(request.model_dump_json())
    body={**request.model_dump(),'code_version':code_version,'fixture_version':VERSION}
    hashed=digest(body); rid='RUN-'+uuid.uuid4().hex
    with conn.transaction():
        conn.execute('''INSERT INTO discovery.publication_runs(run_id,request_key,request_hash,request)
            VALUES (%s,%s,%s,%s) ON CONFLICT (request_key) DO NOTHING''',(rid,key,hashed,Jsonb(body)))
        row=conn.execute('SELECT run_id,request_hash FROM discovery.publication_runs WHERE request_key=%s',(key,)).fetchone()
        check(row[1]==hashed,'idempotency_conflict')
    return row[0]


def run_next(conn,code_version,clock=now):
    # Session lock survives transactions but releases on process death. Never
    # retry ambiguous model calls after a crash; start a separately budgeted run.
    if not conn.execute('SELECT pg_try_advisory_lock(309059)').fetchone()[0]: return None
    rid=None
    try:
        with conn.transaction():
            conn.execute("UPDATE discovery.publication_runs SET status='failed',stage='interrupted',error_code='worker_interrupted',updated_at=now() WHERE status='running'")
            row=conn.execute("SELECT run_id,request FROM discovery.publication_runs WHERE status='queued' ORDER BY created_at,run_id FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
            if not row: return None
            rid,request=row;token=uuid.uuid4().hex
            conn.execute("UPDATE discovery.publication_runs SET status='running',stage='ingestion',token=%s,updated_at=now() WHERE run_id=%s",(token,rid))
        check(request['code_version']==code_version,'execution_version_mismatch')
        conn.execute('INSERT INTO discovery.publication_source_controls VALUES (%s,false) ON CONFLICT DO NOTHING',(SOURCE,))
        access=access_for(conn,clock);permissions=require_sources(access)
        artifacts=[]
        for case in CASES:
            data,strategy=inputs(request['horizon'],case)
            issuer=ingest_candidate(conn,data,case,access)
            event_ids=[r[0] for r in conn.execute('''SELECT c.claim_id FROM discovery.evidence_claims c JOIN discovery.revisions r USING(revision_id)
                WHERE r.listing_id=%s AND r.available_at<=%s AND c.status='confirmed' ORDER BY c.claim_id''',(data['instrument_id'],data['cutoff']))]
            for cohort in COHORTS:
                conn.execute("UPDATE discovery.publication_runs SET stage=%s,updated_at=now() WHERE run_id=%s AND token=%s",('research:'+case+':'+cohort,rid,token))
                try:
                    research,bundle=research_candidate(conn,rid,data,issuer,cohort,access)
                except PermissionError:
                    raise
                except (ValueError,TimeoutError,RuntimeError,OSError) as exc:
                    research={'status':'abstained','error_code':'research_budget_exhausted' if 'budget exhausted' in str(exc) else 'required_research_failed'};bundle=None
                artifacts.append(build_artifact(run_id=rid,data=data,strategy=strategy,issuer=issuer,cohort=cohort,
                    research=research,bundle=bundle,generated_at=clock(),code_version=code_version,permissions=permissions,event_ids=event_ids))
        # Final source check immediately before one atomic publish. A stale worker
        # cannot leave half a batch visible. Existing complete batches stay intact.
        require_sources(access)
        for artifact in artifacts:
            if artifact['research_bundle']:
                recheck(conn,Bundle.model_validate_json(json.dumps(artifact['research_bundle'])),access)
        coverage={}
        for cohort in COHORTS:
            rows=[a['recommendation'] for a in artifacts if a['recommendation']['cohort']['arm']==cohort]
            complete=sum(r['research_status']=='succeeded' for r in rows) if cohort!='quant' else 0
            coverage[cohort]=dict(universe_total=len(CASES),ineligible=0,eligible=len(CASES),screened=len(CASES),unscreened=0,
                candidate=len(CASES),noncandidate=0,research_complete=complete,research_pending=0,
                research_failed=len(CASES)-complete if cohort!='quant' else 0,research_not_selected=len(CASES) if cohort=='quant' else 0,
                data_complete=sum(r['action']!='INSUFFICIENT_EVIDENCE' for r in rows))
        batch=dict(run_id=rid,horizon=request['horizon'],mode='synthetic',scope=VERSION,coverage=coverage,
            information_cutoff_at=artifacts[0]['recommendation']['information_cutoff_at'],published_at=clock(),
            status='partial' if any(a['recommendation']['action']=='INSUFFICIENT_EVIDENCE' for a in artifacts) else 'complete',
            labels=['MOCK','SHADOW','NON-ACTIONABLE'],next_run_at=None,
            source_issues=['Fictional universe only; missing and conflicting evidence are deliberate acceptance cases'],
            source_permissions=permissions)
        with conn.transaction():
            current=conn.execute("SELECT status,token FROM discovery.publication_runs WHERE run_id=%s FOR UPDATE",(rid,)).fetchone()
            check(current==('running',token),'stale_publication_fence')
            conn.execute('SELECT source_id FROM discovery.publication_source_controls WHERE source_id=%s FOR SHARE',(SOURCE,))
            require_sources(access)
            conn.execute('INSERT INTO discovery.publication_batches(run_id,horizon,mode,payload) VALUES (%s,%s,%s,%s)',(rid,request['horizon'],'synthetic',Jsonb(batch)))
            for a in artifacts:
                r=a['recommendation']
                conn.execute('INSERT INTO discovery.recommendations VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (r['recommendation_id'],rid,r['instrument']['instrument_id'],request['horizon'],r['cohort']['arm'],Jsonb(r),Jsonb(a),str(a['ranking']['action_tier'])+'|'+str(1-int(a['ranking']['quant_score']))+'|'+r['instrument']['instrument_id']))
            conn.execute('INSERT INTO discovery.publication_outbox VALUES (%s,%s)',(rid,Jsonb({'event':'published_shadow','run_id':rid})))
            conn.execute("UPDATE discovery.publication_runs SET status='completed',stage='published',updated_at=now() WHERE run_id=%s AND token=%s",(rid,token))
        return {'run_id':rid,'status':'completed'}
    except Exception as exc:
        if rid:
            conn.execute("UPDATE discovery.publication_runs SET status='failed',stage='failed',error_code=%s,updated_at=now() WHERE run_id=%s AND token=%s",
                ('source_unavailable' if isinstance(exc,PermissionError) else 'execution_version_mismatch' if str(exc)=='execution_version_mismatch' else type(exc).__name__,rid,token))
        return {'run_id':rid,'status':'failed'}
    finally:
        conn.execute('SELECT pg_advisory_unlock(309059)')


def read_artifact(conn,rid,access=None):
    row=conn.execute('SELECT artifact FROM discovery.recommendations WHERE recommendation_id=%s',(rid,)).fetchone()
    if not row: raise KeyError(rid)
    a=row[0];access=access or access_for(conn,now)
    require_sources(access)
    if a['research_bundle']:recheck(conn,Bundle.model_validate_json(json.dumps(a['research_bundle'])),access)
    return a


def run_status(conn,rid):
    row=conn.execute('SELECT run_id,status,stage,error_code,created_at,updated_at,request FROM discovery.publication_runs WHERE run_id=%s',(rid,)).fetchone()
    if not row: raise KeyError(rid)
    return dict(zip(('run_id','status','stage','error_code','created_at','updated_at','request'),row))
