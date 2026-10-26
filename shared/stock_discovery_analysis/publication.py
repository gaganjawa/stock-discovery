"""D3-09 deterministic four-action policy and strict v2 publication assembly.

Synthetic and explicitly configured real shadow runs share this assembly.
No AI rank can promote a quant result or grant admission. Every artifact carries the complete pinned inputs.
"""
from dataclasses import asdict, is_dataclass
from datetime import timedelta, timezone
from decimal import Decimal
import json
import time
from stock_discovery_contracts.v2 import Recommendation, Policy, Parameter, Ref, digest, at, check, validate_bundle
from .dataset import canonical
from .quant_policies import assess, PolicyRegistry
from .rag_contracts import Query, RetrievalPolicy, Budget, Bundle
from .rag_research import run_research, MockResearchProvider, recheck, time_limit
from .agent_storage import run_investigation
from .agent_contracts import Rubric, JudgeReport
from .agent_research import MockAgent, MockJudge, validate_judge, JUDGE_PROMPT, JUDGE_PROMPT_HASH, Meter, encode
from .evidence_storage import read_evidence, stored_stream
from .publication_fixtures import VERSION, SOURCE

def manifest(value):
    if hasattr(value, 'model_dump'): return value.model_dump(mode='json')
    if is_dataclass(value): return manifest(asdict(value))
    if isinstance(value, dict): return {k:manifest(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)): return [manifest(v) for v in value]
    return json.loads(canonical(value))


POLICY_VERSION='publication-1.0.0'
COHORTS=('quant','quant_rag','quant_agent')


def decision(quant, research=None, *, required=False, missing=()):
    """Architecture 9.2 precedence. Capacity affects admission, never thesis."""
    absent=list(missing)+list(quant['reasons'] if quant['action']=='INSUFFICIENT_EVIDENCE' else [])
    if required:
        if not research or research.get('status')!='completed' or research.get('validator',{}).get('semantic')!='supported':
            absent.append('required_research_unavailable')
        elif research['assessment']['action']=='INSUFFICIENT_EVIDENCE':
            absent.append('research_evidence_insufficient')
        if research:
            if research.get('error_code'): absent.append(research['error_code'])
            a=research.get('assessment') or {}
            absent.extend(a.get('missing',()))
            if a.get('contradictions'): absent.append('conflicting_evidence')
    if absent: return 'INSUFFICIENT_EVIDENCE',sorted(set(absent))
    if quant['known_adverse'] or quant['action']=='AVOID':
        return 'AVOID',quant['known_adverse'] or ['quant_disqualifier']
    # AI proposals cannot invent a verified adverse fact or upgrade readiness.
    if required and research['assessment']['action']!='BUY':
        return 'WATCH',['research_not_ready']
    if quant['action']!='BUY': return 'WATCH',['quant_conditions_pending']
    return 'BUY',['quant_conditions_and_safety_gates_passed']


def research_candidate(conn, run_id, data, issuer, cohort, access):
    if cohort=='quant': return None,None
    current=data['statements'][-1]
    query=Query(issuer_id=issuer,listing_id=data['instrument_id'],horizon=data['profile'],mode=data['mode'],
        cutoff_at=data['cutoff'],text='earnings',categories=('annual_report','news'),required_metrics=('revenue','earnings'),
        period_start_at=current.period_start_at,period_end_at=current.period_end_at,period_kind='annual')
    policy=RetrievalPolicy()
    budget=Budget(account='SYN-D309-local',max_day_units=20000000,max_month_units=200000000)
    deadline=time.monotonic()+budget.max_seconds
    key=run_id+'-'+data['instrument_id']+'-'+cohort
    if cohort=='quant_agent':
        result=run_investigation(conn,run_id=key,query=query,retrieval_policy=policy,access=access,
            budget=budget,provider=MockAgent(),judge=MockJudge())
        bundle_hash=result.get('final_bundle_hash')
    else:
        result=run_research(conn,run_id=key,query=query,policy=policy,access=access,budget=budget,provider=MockResearchProvider())
        bundle_hash=result.get('bundle_hash')
    bundle=None
    if bundle_hash:
        row=conn.execute('SELECT payload FROM discovery.rag_bundles WHERE bundle_hash=%s',(bundle_hash,)).fetchone()
        bundle=Bundle.model_validate_json(encode(row[0]))
        recheck(conn,bundle,access)
    if cohort=='quant_rag' and result['status']=='completed' and bundle:
        # Same separate D3-08 judge, no tools added to the fixed-bundle arm.
        rubric=Rubric(); judge=MockJudge()
        meter=Meter(budget,deadline,time.monotonic)
        meter.charge(result['accounting']['input_units']+result['accounting']['output_units'])
        payload=dict(instruction=JUDGE_PROMPT,schema=JudgeReport.model_json_schema(),rubric=rubric.ref.model_dump(),
            source_bundle=bundle.model_dump(mode='json'),assessment=result['assessment'])
        report=JudgeReport.model_validate_json(meter.call('judge',judge.judge,payload))
        from .rag_contracts import Assessment
        passed=validate_judge(report,Assessment.model_validate_json(encode(result['assessment'])),rubric)
        result={**result,'validator':{**result['validator'],'semantic':'supported' if passed else 'not_supported','judge':'completed'},
            'judge':report.model_dump(mode='json'),'judge_model':judge.ref.model_dump(),'rubric':rubric.ref.model_dump(),
            'judge_prompt_hash':JUDGE_PROMPT_HASH,'total_units_including_judge':meter.units}
        recheck(conn,bundle,access)
    if bundle:
        result={**result,'source_documents':[
            {k:v for k,v in read_evidence(conn,rid,access=access,cutoff=query.cutoff_at,mode=query.mode)['document'].items() if k!='body'}
            for rid in bundle.documents]}
    return result,bundle


def policy(kind,profile,parameters):
    items=[Parameter(name=k,value=v,unit='fixture_setting',unavailable_reason=None) for k,v in sorted(parameters.items())]
    return Policy(schema_version='2.0.0',ref=Ref(id=f'SYN-D309-{kind}-{profile}',version=POLICY_VERSION,
        content_hash=digest([p.model_dump() for p in items])),kind=kind,profile=profile,status='fixture',
        effective_at='2020-01-01T00:00:00Z',parameters=items,approval_ref=None)


def build_artifact(*,run_id,data,strategy,issuer,cohort,research,bundle,generated_at,code_version,permissions,extra_missing=(),event_ids=(),real=None):
    live=data['mode']=='live_paper'
    check(data['mode']=='synthetic' or live and real is not None,'real publication context required')
    if live:
        check(at(data['cutoff'])<at(generated_at),'publication_must_follow_cutoff')
        check(data['calendar'] is not None and data['calendar'].provenance.availability_basis=='observed_live','observed_calendar_required')
        check(all(b.provenance.availability_basis=='observed_live' for b in data['bars']),'observed_prices_required')
        check(all(e['availability_basis']=='observed' for e in real['price_evidence']),'observed_evidence_required')
    # Freeze only cutoff-eligible observations. Future calendar sessions are
    # preannounced plans; future price bars/filings must never reach API artifacts.
    from .quant_policies import available
    point=at(data['cutoff']).replace(tzinfo=timezone.utc)
    data={**data,'bars':tuple(b for b in data['bars'] if b.ends_at<=point and b.provenance.eligible(point,live=live)),
        'statements':tuple(s for s in data['statements'] if available(s.evidence,data['cutoff'],data['mode'])),
        'coverage':tuple(c for c in data['coverage'] if available(c.evidence,data['cutoff'],data['mode']))}
    registry=PolicyRegistry();registry.register(strategy)
    quant=assess(registry,strategy.ref,**data)
    if live and quant['action']=='BUY' and not quant['entry_terms'].get('stop'):
        extra_missing=(*extra_missing,'real_execution_terms_unavailable')
    original_quant=quant
    action,reasons=decision(quant,research,required=cohort!='quant',missing=extra_missing)
    # Fixture inputs always include a valid calendar even when coverage is missing.
    if quant['horizon'] is None: raise ValueError('publication horizon unavailable')
    listing=data['instrument_id']; profile=data['profile']; cutoff=data['cutoff']
    available=generated_at if live else (at(cutoff)+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    closes=[s.closes_at.strftime('%Y-%m-%dT%H:%M:%SZ') for s in data['calendar'].sessions]
    cal_ref=dict(id='observed-calendar' if live else 'SYN-D309-calendar',version=data['calendar'].version,content_hash=digest(closes))
    horizon={**quant['horizon'],'anchor_at':available,'calendar_ref':cal_ref}
    if live:
        from .quant_policies import horizon_for
        values={p.name:Decimal(p.value) for p in strategy.parameters if p.value is not None}
        horizon={**horizon_for(profile,values,data['calendar'],available).model_dump(),'calendar_ref':cal_ref}
        quant={**quant,'conditions':{**quant['conditions'],'expires_at':horizon['entry_expires_at']}}
        future_opens=[s.opens_at for s in data['calendar'].sessions if s.opens_at>at(available).replace(tzinfo=timezone.utc)]
        check(bool(future_opens),'entry_calendar_unavailable')
        quant['entry_terms']={**quant['entry_terms'],'earliest_entry_at':future_opens[0].strftime('%Y-%m-%dT%H:%M:%SZ')}
    evidence={c.evidence.evidence_id:c.evidence.model_dump() for c in data['coverage'] if c.evidence.available_at<=cutoff}
    evidence.update({s.evidence.evidence_id:s.evidence.model_dump() for s in data['statements'] if s.evidence.available_at<=cutoff})
    if live:
        evidence.update({e['evidence_id']:e for e in real['price_evidence']})
    else:
        bar_id=listing+'-bars-'+quant['input_hash']
        evidence[bar_id]=dict(evidence_id=bar_id,revision_id=bar_id,instrument_id=listing,kind='closed_candles',source_ref=SOURCE,
            source_version=VERSION,locator='snapshot:closed-bars',published_at=cutoff,available_at=cutoff,fetched_at=cutoff,
            period_end_at=cutoff,availability_basis='fictional_fixture',archive_verification_ref=None,summary='Closed fictional candles at the cutoff')
    citations=[]
    if bundle:
        citations=[c.model_dump() for h in bundle.hits for c in h.citations]+[f.citation.model_dump() for f in bundle.facts]
        documents={d['revision']['revision_id']:d for d in (research or {}).get('source_documents',[])}
        for citation in citations:
            document=documents[citation['revision_id']];revision=document['revision']
            evidence[citation['evidence_id']]=dict(evidence_id=citation['evidence_id'],revision_id=citation['revision_id'],
                instrument_id=listing,kind='news' if document['category']=='news' else 'filing',source_ref=revision['source_id'],
                source_version=revision['source_revision'],locator=citation['locator'],published_at=revision['published_at'],
                available_at=revision['available_at'],fetched_at=revision['fetched_at'],period_end_at=None,
                availability_basis=revision['availability_basis'],archive_verification_ref=None,
                summary=citation['excerpt'] or 'Structured fact cited by the frozen research bundle')
    if live:
        policies=real['policies']
        check(next(p for p in policies if p.kind=='strategy')==strategy,'strategy_context_mismatch')
        check(len(policies)==8 and len({p.kind for p in policies})==8,'complete_real_policy_manifest_required')
        check(all(p.status!='fixture' and not p.ref.id.startswith('SYN-') for p in policies),'fixture_policy_in_real_publication')
    else:
        policies=[strategy]+[policy(k,profile,v) for k,v in dict(horizon={'duration':str(horizon['duration'])},
            research={'local_only':'1','shadow_only':'1'},risk={'fixture_stop_fraction':'0.2','admission_enabled':'0'},
            cost={'orders_enabled':'0'},retrieval={'max_chunks':'20'},schedule={'manual_and_worker':'1'},universe={'declared_total':'5'}).items()]
    refs={p.kind:p.ref.model_dump() for p in policies}
    success=bool(research and research.get('status')=='completed' and research.get('validator',{}).get('semantic')=='supported')
    research_id=digest(research) if success else None
    risk_id=digest({'quant':quant['assessment_id'],'instrument_risk':data['risk_prohibited'],'eligible':data['eligible'],'policy':refs['risk']})
    snapshot_id=digest({'inputs':manifest(data),'strategy':strategy.model_dump(),'bundle':bundle.content_hash if bundle else None,'permissions':permissions})
    rec_id='REC-'+digest([run_id,listing,cohort,snapshot_id])
    missing=list(reasons) if action=='INSUFFICIENT_EVIDENCE' else []
    contradictions=[digest(c) for c in bundle.contradictions] if bundle else []
    execution=None
    if action=='BUY':
        terms=quant['entry_terms']; entry=terms.get('trigger',terms.get('max_price'))
        stop=terms.get('stop',format(Decimal(entry)*Decimal('.8'),'f'))
        execution=dict(profile=profile,side='OPEN_LONG',entry_type='buy_stop' if profile=='swing' else 'limit',
            entry_price=entry,stop_price=stop,target_price=terms.get('target'),earliest_entry_at=terms['earliest_entry_at'],
            entry_expires_at=horizon['entry_expires_at'],time_exit_at=horizon['holding_end_at'],assumptions_ref=refs['cost'])
    rec=dict(schema_version='2.0.0',recommendation_id=rec_id,synthetic=not live,mode=data['mode'],run_id=run_id,
        instrument=dict(instrument_id=listing,issuer_id=issuer,symbol=listing,exchange='SYNTHETIC_NSE',series='EQ',isin=None,
                        currency='INR',exchange_timezone='Asia/Kolkata',lot_size=1),
        strategy=dict(id=strategy.ref.id,version=strategy.ref.version,config_version=strategy.ref.content_hash if live else POLICY_VERSION),horizon=horizon,
        information_cutoff_at=cutoff,generated_at=generated_at,decision_available_at=available,availability_simulated=not live,
        action=action,cohort=dict(arm=cohort,config_hash=digest([refs,cohort]),capability='researched' if success else 'technical_only',shadow=True),
        candidate_origin='both' if event_ids else 'quant',event_ids=list(event_ids),snapshot_id=snapshot_id,baseline_ref=quant['assessment_id'],
        research_status='succeeded' if success else 'not_requested' if cohort=='quant' else 'unavailable',
        research_ref=research_id,validation_ref=research_id+'-validation' if success else None,judge_ref=research_id+'-judge' if success else None,
        research_unavailable_reason=None if success else 'quantitative_only' if cohort=='quant' else 'required_research_unavailable',
        policy_refs=refs,evidence=list(evidence.values()),missing_evidence=[dict(requirement=m,reason=m,blocking=True) for m in missing],
        rationale=dict(summary='; '.join(reasons)+('. Real shadow research; admission blocked.' if live else '. Fictional shadow research; admission blocked.'),evidence_ids=list(evidence)),
        versions=dict(code=code_version,dataset=real['dataset_version'] if live else VERSION,model=research.get('model',{}).get('version') if success else None,
            prompt=research.get('agent_prompt_hash',research.get('prompt_hash')) if success else None),
        evidence_quality=dict(coverage=bundle.coverage if bundle else None,freshness='unknown',source_quality='primary',
            claim_support='1' if success else None,contradiction_ids=contradictions,
            uncertainty=['Unqualified real research; not approved for execution'] if live else ['Fictional engineering inputs; uncalibrated mock models; not investment validation'],missing_required=missing),
        conditions=quant['conditions'],valuation=quant['valuation'],execution=execution,
        risk_context=dict(eligibility='unknown' if data['risk_prohibited'] is None or data['eligible'] is None else 'blocked' if data['risk_prohibited'] or not data['eligible'] else 'eligible',
            binding_constraints=quant['known_adverse']+['shadow_only','capital_profile_unconfigured'],risk_ref=risk_id,capital_profile_ref=None),
        paper_admission=dict(status='blocked',reservation_ref=None,quantity=None,reason='REAL RESEARCH / SHADOW / NON-ACTIONABLE' if live else 'MOCK / SHADOW / NON-ACTIONABLE; no capital approval or broker execution'),
        action_reason_codes=reasons,revises_id=None,revision_reason=None)
    if live:rec['instrument']=real['instrument']
    Recommendation.model_validate(rec)
    reference_records=[]
    def reference(rid,kind,assessment=None,passed=None):
        reference_records.append(dict(id=rid,kind=kind,snapshot_id=snapshot_id,instrument_id=listing,assessment_id=assessment,passed=passed,quantity=None))
    reference(quant['assessment_id'],'baseline');reference(risk_id,'risk',passed=data['risk_prohibited'] is False and data['eligible'] is True)
    if success:
        for rid,kind in ((research_id,'research'),(rec['validation_ref'],'validation'),(rec['judge_ref'],'judge')):reference(rid,kind,research_id,True)
    for eid in event_ids:reference(eid,'event')
    for cid in contradictions:reference(cid,'contradiction')
    for cid in (quant['valuation'] or {}).get('calculation_ids',[]):reference(cid,'calculation')
    frozen=dict(schema_version='2.0.0',snapshot=dict(snapshot_id=snapshot_id,mode=data['mode'],information_cutoff_at=cutoff,
        calendar_ref=cal_ref,session_closes=closes,evidence=list(evidence.values()),references=reference_records,
        policies=[p.model_dump() for p in policies]),recommendations=[rec],outcomes=[],observation_manifests=[],evaluator_refs=[])
    validate_bundle(frozen)
    return dict(recommendation=rec,contract_bundle=frozen,quantitative=quant,**({'prepublication_quantitative':original_quant,'material_events':real.get('events',[])} if live else {}),research=research,
        research_bundle=bundle.model_dump(mode='json') if bundle else None,citations=citations,permissions=permissions,
        input_manifest=manifest(data),policy_manifest=strategy.model_dump(),publication_status='published_shadow',
        ranking=dict(action_tier={'BUY':0,'WATCH':1,'AVOID':2,'INSUFFICIENT_EVIDENCE':3}[action],
            quant_score='1' if quant['action']=='BUY' else '0',ai_component='0',listing_id=listing,policy=POLICY_VERSION))


def reproduce_quant(artifact):
    """Recompute from immutable stored inputs, never consult current source rows."""
    from datetime import datetime
    from .data import Provenance, Candle
    from .calendar import Calendar, Session
    from .quant_policies import Statement, CoverageCheck
    raw=artifact['input_manifest']
    def provenance(row):
        return Provenance(**{k:datetime.fromisoformat(v) if k.endswith('_at') else v for k,v in row.items()})
    calendar=raw['calendar']
    data={**raw,'calendar':Calendar(version=calendar['version'],provenance=provenance(calendar['provenance']),
        sessions=tuple(Session(datetime.fromisoformat(s['opens_at']),datetime.fromisoformat(s['closes_at'])) for s in calendar['sessions'])),
        'bars':tuple(Candle(**{k:provenance(v) if k=='provenance' else datetime.fromisoformat(v) if k in ('starts_at','ends_at') else Decimal(v) if k in ('open','high','low','close') else v for k,v in b.items()}) for b in raw['bars']),
        'statements':tuple(Statement.model_validate(s) for s in raw['statements']),
        'coverage':tuple(CoverageCheck.model_validate(c) for c in raw['coverage'])}
    strategy=Policy.model_validate(artifact['policy_manifest']);registry=PolicyRegistry();registry.register(strategy)
    result=assess(registry,strategy.ref,**data)
    stored=artifact['quantitative']
    if artifact['recommendation']['mode']=='live_paper':
        # Publication reanchors conditions to the actual publish clock; the
        # deterministic pre-publication assessment remains pinned separately.
        stored=artifact.get('prepublication_quantitative',stored)
    if result!=stored:raise ValueError('quantitative reproduction mismatch')
    return result
