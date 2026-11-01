"""Read registered D3-11 evidence; never register, reserve or evaluate a trial."""
import json
from decimal import Decimal
import psycopg
from stock_discovery_contracts.v2 import at,check,digest
from stock_discovery_contracts.rights import authorize
from . import governance as g
from .governance_contracts import Experiment,Trial,ARMS,split_samples
from .paper_contracts import instant
from .paper_reporting import cohort_metrics
from .grant_fences import identity,database_request
from .evidence_storage import stored_stream
from .historical_research import original_grant
from .revisions import Revision

VERSION='registered-fold-report-v1'
METRICS=('status','research_unavailable','no_picks','not_selected','universe','decisions','resolved_trades','missing_outcomes','missing_evidence','research_failed',
    'provisional','ambiguous','unavailable','no_entry','rejected','win_rate','expectancy_after_costs',
    'profit_factor','profit_factor_unavailable_reason','portfolio_return','maximum_drawdown',
    'portfolio_reason','fees','slippage','research_cost','latency_ms','benchmark_return',
    'benchmark_reason','cash_benchmark_return','exposure','turnover','forecast_quality')


def samples_for(e,t,audit):
    if t.split=='forward':
        check(e.forward is not None,'forward_window_not_registered')
        samples=t.forward_samples
        check(all(at(e.forward.start)<=at(s.cutoff)<at(s.label_end)<=at(e.forward.end) and
            (at(s.label_end)-at(s.cutoff)).total_seconds()<=e.embargo_seconds for s in samples),
            'forward_sample_outside_registered_bounds')
    else:
        accepted=set(audit['accepted'][t.split]);samples=tuple(s for s in e.samples if s.sample_id in accepted)
    return samples


def source_check(conn,e,t,result,samples):
    """Locks live through the caller transaction; final pass refreshes validity."""
    contexts=[(sample.cutoff,sample.revision_ids) for sample in samples]
    for ref in result['lineage'].values():
        for rid in ref['recommendation_ids']:
            raw=conn.execute('SELECT artifact FROM discovery.recommendations WHERE recommendation_id=%s',(rid,)).fetchone()
            check(raw is not None,'fold_artifact_missing')
            a=raw[0];revisions=set((a.get('research_bundle') or {}).get('documents',[]))
            revisions.update(d['revision']['revision_id'] for d in (a.get('research') or {}).get('source_documents',[]))
            contexts.append((a['recommendation']['information_cutoff_at'],sorted(revisions)))
    if e.mode=='synthetic':
        from .publication_fixtures import access_for
        access=access_for(conn,g.now)
        sources=set()
        for ref in result['lineage'].values():
            for rid in ref['recommendation_ids']:
                row=conn.execute('SELECT artifact FROM discovery.recommendations WHERE recommendation_id=%s',(rid,)).fetchone()
                check(row is not None,'fold_artifact_missing')
                permissions=row[0]['permissions']
                check(permissions and all(v.get('source_id') for v in permissions.values()),'fold_source_identity_missing')
                sources.update(v['source_id'] for v in permissions.values())
        for source in sorted(sources):
            state=conn.execute('SELECT revoked FROM discovery.publication_source_controls WHERE source_id=%s FOR SHARE',(source,)).fetchone()
            if state is None or state[0]:raise PermissionError('fold_source_restricted')
    else:
        from .real_publication import configured_access
        access=configured_access()
    g.authorize_result(conn,result)
    deps={}
    for sample in samples:
        g.check_revisions(conn,sample,e.mode)
    for cutoff,revision_ids in contexts:
        pending=list(revision_ids);seen=set()
        while pending:
            rid=pending.pop()
            if rid in seen:continue
            seen.add(rid)
            check(len(deps)<10000,'fold_dependency_limit')
            raw=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(rid,)).fetchone()
            check(raw is not None,'fold_revision_missing')
            r=Revision.model_validate(raw[0]);original=original_grant(conn,rid);stream=stored_stream(conn,rid)
            check(original.source_id==stream.source_id==r.source_id and original.account_ref==stream.account_ref,'fold_revision_owner_mismatch')
            # Parent identity evidence is subject to the same original cutoff.
            from .revisions import eligible
            check(eligible(r,cutoff,e.mode) and at(r.published_at)<=at(cutoff),'fold_future_revision')
            deps[rid]=(original,stream,r)
            if r.instrument_revision_id:pending.append(r.instrument_revision_id)
    for key in sorted({identity(original) for original,_,_ in deps.values()}):
        conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)',key)
    for original,stream,r in deps.values():
        current=access.load_grant(stream)
        if current is None or identity(current)!=identity(original):raise PermissionError('fold_grant_unavailable')
        uses=('store','derive','historical_replay') if e.mode=='historical_reconstructed' else ('store','derive')
        request=database_request(conn,access.request_for(stream),uses)
        acquired=request.model_copy(update={'uses':('acquire',),'requested_at':r.fetched_at})
        if not all((authorize(original,acquired).allowed,authorize(original,request).allowed,authorize(current,request).allowed)):
            raise PermissionError('fold_grant_denied')


def ledger_check(conn,arm,ref,cutoff):
    if arm.portfolio_id is None:
        check(ref is None,'fold_unregistered_ledger');return [],None
    check(ref is not None and (ref['portfolio_id'],ref['sequence'])==(arm.portfolio_id,arm.ledger_sequence),'fold_ledger_identity')
    rows=conn.execute('SELECT sequence,event_at,kind,state,event_hash FROM paper.ledger WHERE portfolio_id=%s AND sequence<=%s ORDER BY sequence',
        (arm.portfolio_id,arm.ledger_sequence)).fetchall()
    check(rows and rows[-1][0]==arm.ledger_sequence and rows[-1][4]==ref['event_hash'],'fold_ledger_hash')
    policy=conn.execute('SELECT config FROM paper.portfolios WHERE portfolio_id=%s',(arm.portfolio_id,)).fetchone()
    check(policy is not None and digest(policy[0])==ref['policy_hash'],'fold_ledger_policy_hash')
    marks=[]
    for _,event_at,kind,state,_ in rows:
        check(event_at<=instant(cutoff) and instant(state['available_at'])<=instant(cutoff) and instant(state['asof'])<=instant(cutoff),'fold_future_outcome')
        check(set(state['orders'])<=set(arm.recommendation_ids),'fold_foreign_orders')
        g.authorize(conn,state)
        if kind in ('capital','observation'):marks.append(event_at.isoformat())
    return list(rows[-1][3]['orders'].values()),dict(start=marks[0],end=marks[-1]) if marks else None


def aggregate_folds(folds,private):
    """Add disjoint eligible trade observations; never compound separate ledgers."""
    groups={}
    for f in sorted(folds,key=lambda item:item['fold_id']):
        if f['status']!='completed':continue
        for arm in ARMS:
            key=digest([f['phase'],f['mode'],f['horizon'],f['comparison'],f['universe_hash'],
                f['versions'][arm],f['evaluator_hash'],private[f['fold_id']][arm]['policy_hash']])
            groups.setdefault((arm,key),[]).append(f)
    output=[]
    for (arm,key),items in sorted(groups.items()):
        samples=set();decisions=set();intervals=[];orders=[];reason=None
        for f in items:
            metrics=f['arms'][arm];data=private[f['fold_id']][arm]
            if not data['eligible']:reason='incomplete_fold_evidence'
            keys=set(tuple(s) for s in f['sample_keys']);ids=set(data['decision_ids'])
            interval=(at(f['sample_window']['start']),at(f['sample_window']['end'])) if f['sample_window'] else None
            if keys&samples or ids&decisions or interval and any(max(a,interval[0])<=min(b,interval[1]) for a,b in intervals):
                reason='overlapping_or_repeated_fold_evidence'
            samples.update(keys);decisions.update(ids);orders.extend(data['orders'])
            if interval:intervals.append(interval)
        metrics=cohort_metrics(orders) if reason is None else None
        output.append(dict(group_id=key,arm=arm,phase=items[0]['phase'],fold_ids=[f['fold_id'] for f in items],
            status='available' if reason is None else 'unavailable',reason=reason,
            samples=len(samples) if reason is None else None,decisions=len(decisions) if reason is None else None,
            metrics=metrics,portfolio_return=None,maximum_drawdown=None,benchmark_return=None,
            return_reason='no_continuous_registered_capital_ledger',benchmark_reason='no_comparable_registered_benchmark',
            interpretation='Disjoint observed trade statistics only; fold returns are not added or compounded.'))
    return output


def registered_folds(conn,experiment_ids):
    ids=sorted(experiment_ids)
    check(1<=len(ids)<=10 and len(set(ids))==len(ids),'invalid_fold_experiment_selection')
    try:
        with conn.transaction():
            conn.execute("SET LOCAL lock_timeout='5s'")
            experiments={};coverage=[]
            for eid in ids:
                row=conn.execute('SELECT manifest_hash,manifest,split_audit,registered_at FROM discovery.experiments WHERE experiment_id=%s',(eid,)).fetchone()
                if not row:raise KeyError('experiment_not_found')
                check(digest(row[1])==row[0],'fold_manifest_hash')
                e=Experiment.model_validate_json(json.dumps(row[1]));audit=split_samples(e)
                check(e.experiment_id==eid and audit==row[2],'fold_split_audit_mismatch')
                experiments[eid]=(e,audit,row[0],row[3])
            rows=conn.execute('''SELECT t.trial_id,t.experiment_id,t.request_hash,t.request,t.registered_at,r.result_hash,r.payload,r.evaluated_at
                FROM discovery.experiment_trials t LEFT JOIN discovery.experiment_results r USING(trial_id)
                WHERE t.experiment_id=ANY(%s) ORDER BY t.experiment_id,t.registered_at,t.trial_id LIMIT 101''',(ids,)).fetchall()
            check(len(rows)<=100,'fold_report_limit_exceeded')
            folds=[];pending=[];private={}
            for tid,eid,request_hash,request,registered,result_hash,result,evaluated in rows:
                e,audit,manifest_hash,created=experiments[eid]
                t=Trial.model_validate_json(json.dumps(request));check(digest(request)==request_hash and t.trial_id==tid and t.experiment_id==eid,'fold_request_identity')
                check(created<=registered and (evaluated is None or registered<=evaluated),'fold_registration_order')
                samples=samples_for(e,t,audit);window=getattr(e,t.split)
                if t.split=='forward':check(all(instant(s.cutoff)>=created for s in samples),'fold_forward_predates_registration')
                if t.split=='test':
                    check(conn.execute("SELECT 1 FROM discovery.experiment_events WHERE experiment_id=%s AND trial_id=%s AND kind='holdout_reserved'",(eid,tid)).fetchone() is not None,'fold_holdout_reservation_missing')
                    selected=conn.execute('''SELECT t.experiment_id,t.request->>'split',r.payload->>'status' FROM discovery.experiment_trials t
                        JOIN discovery.experiment_results r USING(trial_id) WHERE t.trial_id=%s''',(t.selected_validation_trial,)).fetchone()
                    check(selected==(eid,'validation','completed'),'fold_validation_selection_unavailable')
                fold_id=digest([eid,manifest_hash,tid,request_hash])
                f=dict(fold_id=fold_id,trial_id=tid,experiment_id=eid,manifest_hash=manifest_hash,request_hash=request_hash,result_hash=result_hash,
                    phase=t.split,mode=e.mode,horizon=e.horizon,comparison=e.comparison,universe_hash=e.universe_ref.content_hash,
                    benchmark_ref=e.benchmark_ref.model_dump(mode='json') if e.benchmark_ref else None,
                    registered_at=registered.isoformat(),evaluated_at=evaluated.isoformat() if evaluated else None,outcome_cutoff=t.outcome_cutoff,
                    registered_window=window.model_dump(mode='json'),sample_window=dict(start=min(s.cutoff for s in samples),end=max(s.label_end for s in samples)) if samples else None,
                    registered_samples=len(samples),sample_keys=sorted([[s.listing_id,s.cutoff,s.input_hash] for s in samples]),
                    excluded_samples=audit['excluded'],embargo_seconds=e.embargo_seconds,
                    versions={a.arm:a.model_dump(mode='json') for a in e.arms},status='registered_not_evaluated',arms={})
                if result is not None:
                    check(digest(result)==result_hash and result.get('trial_id')==tid and result.get('experiment_id')==eid,'fold_result_identity')
                    receipt=conn.execute("SELECT 1 FROM discovery.experiment_events WHERE experiment_id=%s AND trial_id=%s AND kind=%s AND payload->>'result_hash'=%s",
                        (eid,tid,'trial_'+result['status'],result_hash)).fetchone()
                    check(receipt is not None,'fold_sealed_receipt_missing')
                    f['status']=result['status']
                    if result['status']=='completed':
                        check(all(at(s.cutoff)<=at(t.outcome_cutoff) for s in samples),'fold_outcome_before_decision')
                        check(result['split']==t.split and result['comparison']==e.comparison and result['split_audit']==audit and set(result['lineage'])==set(result['arms'])==set(ARMS),'fold_result_scope')
                        source_check(conn,e,t,result,samples);pending.append((e,t,result,samples))
                        f.update(evaluator_hash=result['evaluator_hash'],evidence_class=result['evidence_class']);private[fold_id]={}
                        for arm in t.arms:
                            lineage=result['lineage'][arm.arm]
                            check(lineage['recommendation_ids']==list(arm.recommendation_ids),'fold_decision_lineage')
                            registered_samples={(s.listing_id,s.cutoff):s for s in samples}
                            config=next(a for a in e.arms if a.arm==arm.arm)
                            for rid,hashed in zip(arm.recommendation_ids,lineage['artifact_hashes'],strict=True):
                                a=g.read_artifact(conn,rid);check(digest(a)==hashed,'fold_artifact_hash');r=a['recommendation']
                                sample=registered_samples.get((r['instrument']['instrument_id'],r['information_cutoff_at']))
                                check(sample is not None and r['run_id']==arm.publication_run_id and r['cohort']['arm']==arm.arm
                                    and r['mode']==e.mode and r['horizon']['profile']==e.horizon,'fold_decision_scope')
                                check(digest(a['input_manifest'])==sample.input_hash and at(r['horizon']['holding_end_at'])<=at(sample.label_end),'fold_frozen_input_or_label')
                                for key,value in g.artifact_versions(a).items():
                                    if value is not None:check(value==getattr(config,key),'fold_frozen_version_mismatch')
                                check(all(at(f['period_end_at'])<=at(sample.cutoff) for f in (a.get('research_bundle') or {}).get('facts',[])),
                                    'fold_future_financial_fact')
                                if t.split=='forward':check(instant(r['generated_at'])>=created,'fold_forward_decision_predates_registration')
                            orders,observation_window=ledger_check(conn,arm,lineage['ledger'],t.outcome_cutoff)
                            metrics=result['arms'][arm.arm]
                            f['arms'][arm.arm]={k:metrics.get(k) for k in METRICS}
                            f['arms'][arm.arm]['observation_window']=observation_window
                            private[fold_id][arm.arm]=dict(orders=orders,decision_ids=list(arm.recommendation_ids),
                                policy_hash=lineage['ledger']['policy_hash'] if lineage['ledger'] else None,
                                eligible=bool(samples) and metrics['status']=='observed' and metrics['missing_outcomes']==0 and not any(metrics.get(k,0) for k in ('ambiguous','unavailable','provisional')))
                    else:check(result['status']=='failed','fold_result_status');f['error_code']=g.safe_error(ValueError(result.get('error_code','fold_evaluation_failed')))
                folds.append(f)
            # Revalidate after every potentially blocking dependency lock, with
            # fresh DB time; earlier grants may expire while later locks wait.
            for e,t,result,samples in pending:source_check(conn,e,t,result,samples)
            for eid,(e,audit,manifest_hash,_) in experiments.items():
                coverage.append(dict(experiment_id=eid,manifest_hash=manifest_hash,phases=[dict(phase=phase,
                    registered_trials=sum(f['experiment_id']==eid and f['phase']==phase for f in folds),
                    status='registered' if any(f['experiment_id']==eid and f['phase']==phase for f in folds) else 'not_opened_or_not_registered') for phase in audit['accepted']]))
            report=dict(version=VERSION,status='available' if folds else 'unavailable',reason=None if folds else 'no_registered_trials',folds=folds,
                aggregates=aggregate_folds(folds,private),coverage=coverage,holdout_access_performed=False,evaluation_performed=False,
                paired_comparison=dict(status='unavailable',eligible_pairs=0,ai_performance=None,reason='independent_historical_AI_quality_unqualified'),
                limitations=['Registered sealed observations only; no new evaluation or protected holdout access.',
                    'Development, validation, protected test and forward phases are separate; test independence is not certified by this view.',
                    'Synthetic/historical-exploratory evidence is not investment performance acceptance.',
                    'Separate capital histories and missing benchmarks cannot produce a pooled return or AI-performance claim.',
                    'M1/M2, policy, publication, admission and trading gates remain blocked.'])
            report['report_id']=digest(report)
            return report
    except psycopg.Error:raise PermissionError('fold_evidence_access_unavailable') from None
