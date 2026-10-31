"""STK-037/043: full synthetic historical evidence freezing, no live acquisition.

Use existing revisions, extraction/retrieval, grant fences, immutable runs and
daily replay. No current cached research is silently attached to a past decision.
"""
import json
import psycopg
from dataclasses import asdict
from datetime import datetime,timezone

from stock_discovery_contracts.rights import Grant,UseRequest,authorize
from stock_discovery_contracts.v2 import check,digest,at
from .revisions import Revision
from .evidence import Document
from .evidence_storage import Access,read_evidence,stored_stream
from .rag_contracts import Query,RetrievalPolicy,Bundle
from .rag_retrieval import retrieve
from .factual_research import candidates,VERSION as VERIFIER_VERSION
from .combined_research import compose,financial_projection
from .grant_fences import identity,database_request
from .publication_store import now
from .service import freeze,persist_analysis,json_value
from .strategy import stamp

VERSION='synthetic-full-replay-1'


def original_grant(conn,rid):
    row=conn.execute('''SELECT g.payload FROM discovery.revisions r JOIN discovery.grants g
        ON (r.grant_id,r.grant_version)=(g.grant_id,g.version) WHERE r.revision_id=%s''',(rid,)).fetchone()
    check(row is not None,'historical_grant_missing')
    return Grant.model_validate_json(json.dumps(row[0]))


def request(stream,clock):
    return UseRequest(source_id=stream.source_id,account_ref=stream.account_ref,scope=stream.scope,
        uses=('store','derive','historical_replay'),region='IN',destination_region=None,processor_ref=None,
        requested_at=clock,synthetic=True,units=1,retention_days=30,attribution_present=True)


def access_for(conn):
    def grant(stream):
        row=conn.execute('''SELECT g.payload FROM discovery.grants g JOIN discovery.revisions r
            ON (r.grant_id,r.grant_version)=(g.grant_id,g.version) WHERE r.stream_id=%s LIMIT 1''',(stream.stream_id,)).fetchone()
        return Grant.model_validate_json(json.dumps(row[0])) if row else None
    return Access(load_grant=grant,request_for=lambda s:request(s,now()),audit=lambda d:None,
                  clock=now,primary_source_ids=frozenset({'SYN-replay-financial'}))


def authorize_snapshot(conn,snapshot):
    """Source ownership, hashes, historical clocks and durable current fences.

    Synthetic grants are deliberately confined to this synthetic replay boundary;
    observed/real grants and missing fence state are denied.
    """
    check(snapshot['version']==VERSION and snapshot['synthetic'] is True,'historical_snapshot_mode')
    check(snapshot['snapshot_id']==digest({k:v for k,v in snapshot.items() if k!='snapshot_id'}),'historical_snapshot_hash')
    check(len({p['revision_id'] for p in snapshot['source_revisions']})==len(snapshot['source_revisions']), 'duplicate_historical_revision')
    bundle=Bundle.model_validate_json(json.dumps(snapshot['bundle']))
    check(bundle.content_hash==snapshot['bundle_hash'] and bundle.query.mode=='synthetic'
          and bundle.query.listing_id==snapshot['instrument_id'] and bundle.query.cutoff_at==snapshot['cutoff_at'], 'historical_bundle_identity')
    check(snapshot['financial_facts']==[f.model_dump(mode='json') for f in bundle.facts]
          and all(at(f.period_end_at)<=at(snapshot['cutoff_at']) for f in bundle.facts), 'historical_financial_lineage')
    docs=[Document.model_validate_json(json.dumps(d['document'])) for d in snapshot['documents']]
    check(len({d.revision.revision_id for d in docs})==len(docs)
          and {d.revision.revision_id for d in docs}==set(bundle.documents), 'historical_document_lineage')
    expected={rid for d in docs for rid in (d.revision.revision_id,d.revision.instrument_revision_id)}
    check(expected=={p['revision_id'] for p in snapshot['source_revisions']}, 'historical_source_lineage')
    pins={p['revision_id']:p for p in snapshot['source_revisions']}
    check(all(d.revision.model_dump(mode='json')==pins[d.revision.revision_id]['revision'] for d in docs), 'historical_document_revision')
    rows=[]
    for pin in snapshot['source_revisions']:
        raw=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(pin['revision_id'],)).fetchone()
        check(raw is not None,'historical_revision_missing')
        r=Revision.model_validate(raw[0]);g=original_grant(conn,r.revision_id);s=stored_stream(conn,r.revision_id)
        check(r.model_dump(mode='json')==pin['revision'] and r.content_hash==pin['revision_hash'], 'historical_revision_changed')
        check(g.synthetic and r.availability_basis=='fictional_fixture' and r.listing_id==snapshot['instrument_id'], 'historical_source_mode')
        check(identity(g)==tuple(pin['grant_identity']) and digest(g.model_dump(mode='json'))==pin['grant_hash'], 'historical_grant_identity')
        check((s.source_id,s.account_ref)==(g.source_id,g.account_ref) and r.source_id==s.source_id, 'historical_source_owner')
        check(all(at(t)<=at(snapshot['cutoff_at']) for t in (r.published_at,r.available_at,r.fetched_at)), 'historical_future_revision')
        check(authorize(g,request(s,r.fetched_at).model_copy(update={'uses':('acquire',)})).allowed,'historical_acquisition_denied')
        scopes=[s.scope]
        if conn.execute('SELECT 1 FROM discovery.financial_facts WHERE revision_id=%s LIMIT 1',(r.revision_id,)).fetchone():scopes.append('financial_facts')
        rows.append((g,s,scopes))
    for key in sorted({identity(g) for g,_,_ in rows}):
        try:conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)',key)
        except psycopg.errors.InsufficientPrivilege:raise PermissionError('historical_source_access_denied') from None
    # Fresh DB time only AFTER the complete potentially-blocking lock set.
    for g,s,scopes in rows:
        for scope in scopes:
            req=database_request(conn,request(s.model_copy(update={'scope':scope}),now()),('store','derive','historical_replay'))
            if not authorize(g,req).allowed:raise PermissionError('historical_source_access_denied')


def build_snapshot(conn,dataset,instrument,cutoff,baseline,*,ai_run_id=None):
    cutoff=stamp(cutoff);access=access_for(conn)
    query=Query(issuer_id=instrument,listing_id=instrument,horizon='swing',mode='synthetic',cutoff_at=cutoff,
        text='revenue earnings cash flow financial risks',categories=('annual_report','announcement'))
    bundle=retrieve(conn,query,RetrievalPolicy(max_age_days=3000),access=access,persist=False)
    pins={};documents=[]
    for rid in bundle.documents:
        item=read_evidence(conn,rid,access=access,cutoff=cutoff,mode='synthetic');documents.append(item)
        for key in (rid,item['document']['revision']['instrument_revision_id']):
            raw=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(key,)).fetchone()[0]
            r=Revision.model_validate(raw);g=original_grant(conn,key)
            pins[key]=dict(revision_id=key,revision_hash=r.content_hash,revision=r.model_dump(mode='json'),
                grant_identity=list(identity(g)),grant_hash=digest(g.model_dump(mode='json')))
    ai=None;gaps=list(bundle.missing)
    if not bundle.documents:gaps.append('financial_evidence_not_frozen')
    if bundle.contradictions:gaps.append('conflicting_financial_evidence')
    if ai_run_id:
        row=conn.execute('''SELECT r.payload,b.payload,a.reserved_at FROM discovery.rag_results r
            JOIN discovery.rag_bundles b USING(bundle_hash) JOIN discovery.rag_reservations a USING(run_id)
            WHERE r.run_id=%s''',(ai_run_id,)).fetchone()
        if row:
            prior=Bundle.model_validate_json(json.dumps(row[1]))
            # Explicit exact bundle; never select today's latest cached report.
            completed=row[0].get('completed_at')
            if (prior==bundle and completed and row[2].astimezone(timezone.utc).replace(tzinfo=None)<=at(completed)<=at(cutoff)):
                ai=dict(financial_projection(row[0],bundle),run_id=ai_run_id)
        if ai is None:gaps.append('contemporaneous_ai_unavailable')
    else:gaps.append('ai_research_not_frozen')
    point=datetime.fromisoformat(cutoff.replace('Z','+00:00'))
    bars=dataset.asof(instrument,point)
    context=compose(instrument,cutoff,dict(status=baseline['recommendation']['action'],
        indicators=baseline['indicators'],reasons=[baseline['recommendation']['rationale']['summary']],
        strategy_version=baseline['recommendation']['strategy']['version']),ai,gaps=gaps,mode='synthetic_replay')
    snapshot=json_value(dict(version=VERSION,synthetic=True,instrument_id=instrument,cutoff_at=cutoff,
        source_revisions=[pins[k] for k in sorted(pins)],documents=documents,
        bundle=bundle.model_dump(mode='json'),bundle_hash=bundle.content_hash,
        financial_facts=[f.model_dump(mode='json') for f in bundle.facts],financial_calculations=candidates(bundle),
        contradictions=list(bundle.contradictions),missing_evidence=sorted(set(gaps)),
        technical_inputs=dict(bars=[dict(payload=asdict(b),content_hash=digest(json_value(asdict(b)))) for b in bars],
            calendar=[asdict(s) for s in dataset.calendar.through(point)],
            instrument=[asdict(i) for i in dataset.instruments if i.instrument_id==instrument],
            mappings=[asdict(m) for m in dataset.mappings if m.instrument_id==instrument and m.valid_from<=point and (m.valid_to is None or point<m.valid_to)],
            memberships=[asdict(m) for m in dataset.memberships if m.instrument_id==instrument and m.effective_at<=point and m.provenance.eligible(point)],
            actions=[asdict(a) for a in dataset.actions if a.instrument_id==instrument and a.effective_at<=point and a.provenance.eligible(point)],
            dataset_version=dataset.version,indicators=baseline['indicators']),
        ai=ai,versions=dict(snapshot=VERSION,verifier=VERIFIER_VERSION,strategy=baseline['recommendation']['strategy'],
            code=baseline['recommendation']['versions']['code'],model=ai['model'] if ai else None,prompt=ai['prompt_hash'] if ai else None),
        context=context,financial_qualified=False,
        limitations=['Invented synthetic disclosures and fictional knowledge clocks; no NSE qualification.',
            'Independent M2 quality, source qualification and historical acceptance remain blocked.',
            'Historical model knowledge contamination is unqualified; no AI performance inference.']))
    snapshot['snapshot_id']=digest(snapshot)
    return snapshot


def freeze_full(conn,dataset,instrument,cutoff,code_version,*,ai_run_id=None):
    with conn.transaction():
        baseline=freeze(conn,dataset,instrument,cutoff,code_version)
        snapshot=build_snapshot(conn,dataset,instrument,cutoff,baseline,ai_run_id=ai_run_id)
        authorize_snapshot(conn,snapshot)
        analysis=json_value(baseline);r=analysis['recommendation']
        r['run_id']='SYN-RUN-'+digest([r['run_id'],snapshot['snapshot_id']])[:32]
        r['recommendation_id']=r['run_id'].replace('RUN','REC')
        # Existing scorecard version grouping must not mix the abstaining
        # combined arm into the unchanged technical baseline cohort.
        r['strategy']['config_version']='SYN-COMBINED-ABSTAIN-1'
        r['generated_at']=now()  # Actual reconstruction time, distinct from simulated decision availability.
        r.update(action='INSUFFICIENT_EVIDENCE',position_effect='NONE',execution=None,forecast=None,earliest_executable_entry_at=None)
        r['rationale']['summary']='Combined research abstains: real-source, independent financial-quality and historical acceptance gates blocked.'
        r['missing_evidence'] += [dict(requirement=k,reason=k,blocking=True) for k in snapshot['missing_evidence']]
        analysis.update(sizing=None,historical_snapshot=snapshot,baseline_recommendation_id=baseline['recommendation']['recommendation_id'])
        return persist_analysis(conn,analysis,dataset.version)


def context(frozen):
    from copy import deepcopy
    result=deepcopy(frozen['historical_snapshot']['context'])
    result['replay']=dict(status='frozen_full_synthetic',future_outcomes='hidden_until_explicit_reveal',
        limitation='Frozen financial evidence is synthetic and unqualified. Combined performance remains unavailable.')
    result['report_id']=digest({k:v for k,v in result.items() if k!='report_id'})
    return result


def comparison(frozen,baseline_outcome):
    return dict(status='unavailable',paired_sample_size=0,ai_performance=None,
        reason='financial_quality_and_combined_policy_unqualified' if frozen.get('historical_snapshot') else 'financial_evidence_not_frozen',
        baseline=baseline_outcome,
        limitation='Technical baseline outcomes alone cannot measure AI or combined performance.')
