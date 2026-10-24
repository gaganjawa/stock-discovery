"""D3-09 real shadow publication through its existing v2 assembly and tables.

No source grants or strategy approvals are created here. Frozen data is loaded
from rights-aware storage; requests cannot supply a recommendation or its clock.
"""
import json
import os
from datetime import timedelta
from pathlib import Path
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import Policy, Evidence, check, digest, at
from .publication import build_artifact
from .publication_store import now
from .real_views import ViewConfig,company
from .real_access import source_access
from .evidence_storage import stored_stream,read_evidence
from .rag_contracts import Bundle
from .rag_research import recheck


def configured_access():
    path=os.getenv('REAL_RESEARCH_VIEW_CONFIG')
    if not path:raise PermissionError('real_sources_not_configured')
    try:config=ViewConfig.model_validate_json(Path(path).read_text())
    except (OSError,ValueError):raise PermissionError('real_sources_not_configured') from None
    return source_access(config.sources)


def authorize_artifact(conn,artifact,access,*,publishing=False):
    r=artifact['recommendation']
    check(r['mode']=='live_paper' and not r['synthetic'] and r['cohort']['shadow'],'real_shadow_required')
    ids=artifact.get('source_revision_ids',[])
    check(bool(ids),'source_revision_manifest_required')
    for rid in ids:
        stream=stored_stream(conn,rid)
        control=conn.execute('SELECT revoked FROM discovery.publication_source_controls WHERE source_id=%s',(stream.source_id,)).fetchone()
        if control and control[0]:raise PermissionError('source_revoked')
        access.require(stream,('derive','store') if publishing else ('derive',))
        if stream.scope=='filings':access.require(stream.model_copy(update={'scope':'financial_facts'}),('derive','store') if publishing else ('derive',))
    if artifact['research_bundle']:recheck(conn,Bundle.model_validate_json(json.dumps(artifact['research_bundle'])),access)


def load_inputs(conn,config,listing,horizon,clock):
    check(horizon in ('swing','short_term','long_term'),'invalid_horizon')
    # A genuine prior-second cutoff avoids simulated publication availability.
    cutoff=(at(clock())-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    detail,inputs,records=company(conn,config,listing,clock=clock,cutoff_at=cutoff,publication_inputs=True)
    candidates=[r for r in detail['analysis_history'] if r['horizon']==horizon]
    research=None;bundle=None
    if candidates:
        chosen=candidates[0];cutoff=chosen['cutoff_at']
        detail,inputs,records=company(conn,config,listing,clock=clock,cutoff_at=cutoff,publication_inputs=True)
        research=chosen['result']
        check(not research.get('research_only'),'factual_research_not_recommendation')
        row=conn.execute('SELECT payload FROM discovery.rag_bundles WHERE bundle_hash=%s',(research.get('bundle_hash') or research.get('final_bundle_hash') or research.get('baseline_hash'),)).fetchone()
        check(row is not None,'research_bundle_unavailable')
        bundle=Bundle.model_validate_json(json.dumps(row[0]))
        check(bundle.query.listing_id==listing and bundle.query.horizon==horizon and bundle.query.mode=='live_paper','research_identity_mismatch')
        access=source_access(config.sources,clock)
        research={**research,'source_documents':[{k:v for k,v in read_evidence(conn,rid,access=access,cutoff=cutoff,mode='live_paper')['document'].items() if k!='body'} for rid in bundle.documents]}
    check(config.policy_file is not None,'real_policies_required')
    policies=[Policy.model_validate_json(json.dumps(p)) for p in json.loads(Path(config.policy_file).read_text())]
    policies=[p for p in policies if p.profile==horizon]
    strategy=next((p for p in policies if p.kind=='strategy'),None)
    check(strategy is not None,'real_strategy_required')
    identity=next(r for r in records if r.data.kind=='instrument')
    price_evidence=[]
    for r in records:
        if r.data.kind!='candle':continue
        price_evidence.append(Evidence(evidence_id=r.revision_id,revision_id=r.revision_id,instrument_id=listing,
            kind='closed_candles',source_ref=r.source_id,source_version=r.source_revision,locator='revision:'+r.revision_id,
            published_at=r.published_at,available_at=r.available_at,fetched_at=r.fetched_at,period_end_at=r.data.ends_at,
            availability_basis='observed',archive_verification_ref=None,summary='Observed daily OHLCV').model_dump())
    real=dict(instrument=dict(instrument_id=listing,issuer_id=identity.data.issuer_id,symbol=identity.data.symbol,
        exchange='NSE',series=identity.data.series,isin=identity.data.isin,currency='INR',exchange_timezone='Asia/Kolkata',lot_size=identity.data.lot_size),
        policies=policies,price_evidence=price_evidence,events=detail['events'],dataset_version=digest([r.revision_id for r in records]))
    return dict(data=inputs[horizon],strategy=strategy,issuer=identity.data.issuer_id,cohort=chosen['cohort'] if research else 'quant',
        research=research,bundle=bundle,real=real,event_ids=tuple(e['claim_id'] for e in detail['events'] if e['status']=='confirmed'),source_revision_ids=[r.revision_id for r in records])


def publish(conn,config,listing,horizon,key,code_version,*,clock=now,loader=load_inputs):
    config=ViewConfig.model_validate(config)
    check(listing in config.listing_ids and 1<=len(key)<=128,'publication_request_invalid')
    check(conn.autocommit,'dedicated_autocommit_connection_required')
    request=dict(mode='live_paper',listing_id=listing,horizon=horizon,code_version=code_version,
        configuration_hash=digest(config.model_dump(mode='json')))
    hashed=digest(request);run_id='REAL-RUN-'+digest([key,hashed]);access=source_access(config.sources,clock)
    lock='real-publication:'+key
    check(conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0],'publication_busy')
    try:
        with conn.transaction():
            conn.execute('INSERT INTO discovery.publication_runs(run_id,request_key,request_hash,request) VALUES (%s,%s,%s,%s) ON CONFLICT(request_key) DO NOTHING',
                (run_id,key,hashed,Jsonb(request)))
            prior=conn.execute('SELECT run_id,request_hash,status FROM discovery.publication_runs WHERE request_key=%s FOR UPDATE',(key,)).fetchone()
            check(prior[1]==hashed,'idempotency_conflict');run_id=prior[0]
            if prior[2]=='completed':
                artifact=conn.execute('SELECT artifact FROM discovery.recommendations WHERE run_id=%s',(run_id,)).fetchone()[0]
                authorize_artifact(conn,artifact,access)
                return artifact
            check(prior[2]=='queued','ambiguous_or_failed_publication_use_new_key')
            conn.execute("UPDATE discovery.publication_runs SET status='running',stage='real_inputs',token=%s WHERE run_id=%s",(run_id,run_id))
        loaded=loader(conn,config,listing,horizon,clock)
        source_ids=loaded.pop('source_revision_ids')
        permissions={}
        for rid in source_ids:
            stream=stored_stream(conn,rid);grant,_=access.require(stream,('derive','store'))
            permissions[grant.grant_id]=grant.model_dump(mode='json')
        generated=clock()
        artifact=build_artifact(run_id=run_id,generated_at=generated,code_version=code_version,permissions=permissions,**loaded)
        artifact['source_revision_ids']=source_ids
        r=artifact['recommendation']
        check(r['instrument']['instrument_id']==listing and r['horizon']['profile']==horizon,'publication_scope_mismatch')
        with conn.transaction():
            state=conn.execute('SELECT status,token FROM discovery.publication_runs WHERE run_id=%s FOR UPDATE',(run_id,)).fetchone()
            check(state==('running',run_id),'stale_publication_fence')
            authorize_artifact(conn,artifact,access,publishing=True)
            batch=dict(run_id=run_id,horizon=horizon,mode='live_paper',published_at=generated,status='partial',
                labels=['REAL RESEARCH','SHADOW','NON-ACTIONABLE'],source_permissions=permissions)
            conn.execute('INSERT INTO discovery.publication_batches(run_id,horizon,mode,published_at,payload) VALUES (%s,%s,%s,%s,%s)',
                (run_id,horizon,'live_paper',generated,Jsonb(batch)))
            conn.execute('INSERT INTO discovery.recommendations VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (r['recommendation_id'],run_id,listing,horizon,r['cohort']['arm'],Jsonb(r),Jsonb(artifact),r['recommendation_id']))
            from .shadow_tracking import register
            register(conn,artifact)
            conn.execute('INSERT INTO discovery.publication_outbox VALUES (%s,%s)',(run_id,Jsonb({'event':'published_shadow','mode':'live_paper','run_id':run_id})))
            conn.execute("UPDATE discovery.publication_runs SET status='completed',stage='published',updated_at=now() WHERE run_id=%s",(run_id,))
        return artifact
    except Exception:
        conn.execute("UPDATE discovery.publication_runs SET status='failed',stage='real_blocked',error_code='real_publication_blocked',updated_at=now() WHERE run_id=%s AND status='running'",(run_id,))
        raise
    finally:conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))
