"""Immutable governance of existing D3-09 artifacts and D3-10 ledger outcomes."""
import json
import re
from pathlib import Path
from collections import Counter
from decimal import Decimal
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import at, check, digest, validate_bundle
from .governance_contracts import Experiment, Trial, ARMS, split_samples
from .publication_store import read_artifact, now
from .publication import reproduce_quant
from .paper_reporting import cohort_metrics
from .paper_store import authorize
from .paper_contracts import instant
from .service import json_value
from .revisions import Revision, eligible
from .governance_metrics import pinned_portfolio, comparisons


def safe_error(exc):
    message=str(exc)
    return message if re.fullmatch(r'[a-z_]+(?::[a-z_]+)?',message) else 'evidence_validation_failed'


def evaluator_hash():
    return digest({name:Path(__file__).with_name(name+'.py').read_text() for name in ('governance','governance_metrics','governance_contracts','paper_reporting','evaluation')})


def event(conn,eid,kind,payload,tid=None):
    conn.execute('INSERT INTO discovery.experiment_events(experiment_id,trial_id,kind,payload) VALUES(%s,%s,%s,%s)',(eid,tid,kind,Jsonb(payload)))


def register(conn,body):
    body=Experiment.model_validate_json(body.model_dump_json());wire=body.model_dump(mode='json');audit=split_samples(body)
    with conn.transaction():
        prior=conn.execute('SELECT manifest_hash FROM discovery.experiments WHERE experiment_id=%s',(body.experiment_id,)).fetchone()
        if prior:check(prior[0]==digest(wire),'immutable_experiment_conflict')
        elif body.forward:check(at(body.forward.start)>at(now()),'forward_window_must_be_preregistered')
        conn.execute('INSERT INTO discovery.experiments(experiment_id,manifest_hash,manifest,split_audit) VALUES(%s,%s,%s,%s) ON CONFLICT(experiment_id) DO NOTHING',(body.experiment_id,digest(wire),Jsonb(wire),Jsonb(audit)))
        existing=conn.execute('SELECT manifest_hash FROM discovery.experiments WHERE experiment_id=%s',(body.experiment_id,)).fetchone()
        check(existing[0]==digest(wire),'immutable_experiment_conflict')
    return dict(experiment_id=body.experiment_id,manifest_hash=digest(wire),split_audit=audit,activation='blocked')


def load(conn,eid):
    row=conn.execute('SELECT manifest,split_audit FROM discovery.experiments WHERE experiment_id=%s',(eid,)).fetchone()
    if not row:raise KeyError('experiment_not_found')
    return Experiment.model_validate_json(json.dumps(row[0])),row[1]


def holdout_overlap(left,right):
    return bool(set(left.universe)&set(right.universe)) and max(at(left.test.start),at(right.test.start))<=min(at(left.test.end),at(right.test.end))


def begin_trial(conn,body):
    """Reserve holdout access before reading outcomes; crashes cannot release it."""
    body=Trial.model_validate_json(body.model_dump_json());wire=body.model_dump(mode='json');error=None
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('D3-11-holdouts',0))")
        experiment,audit=load(conn,body.experiment_id)
        previous=conn.execute('SELECT request_hash FROM discovery.experiment_trials WHERE trial_id=%s',(body.trial_id,)).fetchone()
        if previous:
            check(previous[0]==digest(wire),'immutable_trial_conflict');return dict(trial_id=body.trial_id,status='already_registered')
        control=conn.execute("SELECT kind,payload FROM discovery.experiment_events WHERE experiment_id=%s AND kind IN ('pause','rollback') ORDER BY sequence DESC LIMIT 1",(body.experiment_id,)).fetchone()
        if control:error='future_trials_paused' if control[0]=='pause' else 'rollback_requires_target_experiment'
        count=conn.execute("SELECT count(*) FROM discovery.experiment_trials WHERE experiment_id=%s AND request->>'split'='validation'",(body.experiment_id,)).fetchone()[0]
        if body.split=='validation' and count>=experiment.tuning_budget:error='tuning_budget_exhausted'
        if body.split=='forward':
            if experiment.forward is None:error='forward_window_not_registered'
            else:
                registered=conn.execute('SELECT registered_at FROM discovery.experiments WHERE experiment_id=%s',(experiment.experiment_id,)).fetchone()[0]
                for sample in body.forward_samples:
                    if not (sample.listing_id in experiment.universe and at(experiment.forward.start)<=at(sample.cutoff)<=at(experiment.forward.end) and instant(sample.cutoff)>=registered):error='forward_sample_outside_preregistered_window'
                    if (at(sample.label_end)-at(sample.cutoff)).total_seconds()>experiment.embargo_seconds:error='embargo_below_actual_maximum_label_span'
        window=getattr(experiment,body.split)
        prior_access=conn.execute('SELECT e.manifest,t.request FROM discovery.experiment_trials t JOIN discovery.experiments e USING(experiment_id)').fetchall()
        for raw,request in prior_access:
            other=Experiment.model_validate_json(json.dumps(raw));other_window=getattr(other,request['split'])
            if window and other_window and set(experiment.universe)&set(other.universe) and max(at(window.start),at(other_window.start))<=min(at(window.end),at(other_window.end)):
                if body.split=='test' or request['split']=='test':error='holdout_already_exposed_new_independent_window_required'
        if body.split=='test':
            selected=conn.execute('SELECT t.experiment_id,t.request,r.payload FROM discovery.experiment_trials t JOIN discovery.experiment_results r USING(trial_id) WHERE t.trial_id=%s',(body.selected_validation_trial,)).fetchone()
            if not selected or selected[0]!=body.experiment_id or selected[1]['split']!='validation' or selected[2]['status']!='completed':error='completed_validation_selection_required'
            consumed=conn.execute("SELECT e.manifest FROM discovery.experiment_events x JOIN discovery.experiments e USING(experiment_id) WHERE x.kind='holdout_reserved'").fetchall()
            if any(holdout_overlap(experiment,Experiment.model_validate_json(json.dumps(r[0]))) for r in consumed):error='holdout_already_exposed_new_independent_window_required'
        if error:
            event(conn,body.experiment_id,'trial_denied',dict(request_hash=digest(wire),reason=error))
        else:
            conn.execute('INSERT INTO discovery.experiment_trials(trial_id,experiment_id,request_hash,request) VALUES(%s,%s,%s,%s)',(body.trial_id,body.experiment_id,digest(wire),Jsonb(wire)))
            event(conn,body.experiment_id,'holdout_reserved' if body.split=='test' else 'trial_registered',dict(split=body.split),body.trial_id)
    if error:raise ValueError(error)  # Audit survives the rejection.
    return dict(trial_id=body.trial_id,status='registered')


def check_revisions(conn,sample,mode):
    for rid in sample.revision_ids:
        row=conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(rid,)).fetchone()
        check(row is not None,'revision_unavailable')
        r=Revision.model_validate_json(json.dumps(row[0]));check(eligible(r,sample.cutoff,mode),'post_cutoff_or_unverified_revision')
        check(at(r.published_at)<=at(sample.cutoff),'post_cutoff_publication')


def artifact_versions(a):
    r=a['recommendation'];research=a.get('research') or {};bundle=a.get('research_bundle') or {}
    return dict(strategy_hash=digest(a['policy_manifest']),policy_hash=digest(r['policy_refs']),
        cost_hash=digest(r['policy_refs']['cost']),risk_hash=digest(r['policy_refs']['risk']),
        model_hash=digest(research['model']) if research.get('model') else None,
        retrieval_hash=digest(dict(ranking=bundle['ranking'],embedding=bundle.get('embedding'))) if bundle.get('ranking') else None,
        prompt_hash=digest(research.get('agent_prompt_hash',research.get('prompt_hash'))) if research.get('agent_prompt_hash',research.get('prompt_hash')) else None)


def summarize_arm(artifacts,orders,universe_count,*,unavailable=False):
    """Use D3-10 trade arithmetic; preserve missing outcomes and non-picks separately."""
    recs=[a['recommendation'] for a in artifacts];actual={o['recommendation_id']:o for o in orders}
    report=cohort_metrics(orders)
    accounted=[(a.get('research') or {}).get('accounting') for a in artifacts if a['recommendation']['cohort']['arm']!='quant']
    complete_accounting=not unavailable and all(x and 'latency_ms' in x and 'actual_cost' in x for x in accounted)
    cost=sum((Decimal(x['actual_cost']) for x in accounted),Decimal(0)) if complete_accounting else None
    latency=sum(x['latency_ms'] for x in accounted) if complete_accounting else None
    report.update(universe=universe_count,decisions=len(recs),not_selected=universe_count-len({r['instrument']['instrument_id'] for r in recs}),
        actions=dict(Counter(r['action'] for r in recs)),research_failed=sum(r['cohort']['arm']!='quant' and r['research_status']!='succeeded' for r in recs),
        missing_evidence=sum(bool(r['missing_evidence']) for r in recs),missing_outcomes=sum(r['recommendation_id'] not in actual for r in recs),
        no_picks=not unavailable and not any(r['action']=='BUY' for r in recs),research_unavailable=unavailable,
        status='unavailable' if unavailable else 'observed',
        latency_ms=latency,research_cost=str(cost) if cost is not None else None,
        accounting_reason=None if complete_accounting else 'missing_research_accounting',
        researched_candidates=len(accounted),cost_per_researched_candidate=str(cost/len(accounted)) if cost is not None and accounted else None,
        cost_per_accepted_decision=str(cost/report['admitted']) if cost is not None and report['admitted'] else None,
        portfolio_return=None,portfolio_reason='requires_pinned_chronological_portfolio_report_not_sum_of_trades',
        benchmark_return=None,benchmark_reason='permitted_comparable_benchmark_observations_unavailable',
        uncertainty=None,uncertainty_reason='dependent_time_issuer_samples_no_preregistered_resampling_design',
        risk_adjusted_return=None,risk_adjusted_reason='insufficient_qualified_independent_samples')
    returns=[Decimal(o['forecast']['return']) for o in orders if o['forecast']['status']=='matured' and o['forecast'].get('return') is not None]
    report['forecast_quality']['observed_endpoint_return']={'mean':str(sum(returns)/len(returns)) if returns else None,'denominator':len(returns),'meaning':'observed_price_change_not_direction_accuracy_or_trade_return'}
    report['forecast_quality']['registered_decisions']=len(recs)
    report['forecast_quality']['missing']=report['missing_outcomes']
    report['execution_rate']=str(Decimal(sum(bool(o.get('bought')) for o in orders))/len(recs)) if recs else None
    report['coverage']=str(Decimal(len(recs)-report['missing_outcomes'])/len(recs)) if recs else None
    report['forecast_quality']['target_attainment']=None
    report['forecast_quality']['target_before_stop']=None
    report['forecast_quality']['target_reason']='not_established_by_existing_four_action_outcome_contract'
    report['cost_stress_result']=None
    report['cost_stress_reason']='no_independently_qualified_stress_observations'
    return report


def authorize_result(conn,result):
    for lineage in result.get('lineage',{}).values():
        for rid in lineage['recommendation_ids']:read_artifact(conn,rid)
        if lineage['ledger']:
            ref=lineage['ledger']
            state=conn.execute('SELECT state FROM paper.ledger WHERE portfolio_id=%s AND sequence=%s',(ref['portfolio_id'],ref['sequence'])).fetchone()[0]
            authorize(conn,state)
    return result


def evaluate(conn,tid,*,fault=None):
    row=conn.execute('SELECT request FROM discovery.experiment_trials WHERE trial_id=%s',(tid,)).fetchone()
    if not row:raise KeyError('trial_not_registered')
    trial=Trial.model_validate_json(json.dumps(row[0]));experiment,audit=load(conn,trial.experiment_id)
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('D3-11:'+tid,))
        prior=conn.execute('SELECT payload FROM discovery.experiment_results WHERE trial_id=%s',(tid,)).fetchone()
        if prior:return authorize_result(conn,prior[0])
        # Failed results are also sealed. Retry requires a new trial; test access stays consumed.
        try:
            check(trial.split in audit['accepted'],'forward_window_not_registered')
            accepted=set(audit['accepted'][trial.split]);samples={(s.listing_id,s.cutoff):s for s in (trial.forward_samples if trial.split=='forward' else experiment.samples) if trial.split=='forward' or s.sample_id in accepted}
            arm_reports={};pair_sets={};lineage={};ledger_assumptions=set()
            registered=conn.execute('SELECT registered_at FROM discovery.experiments WHERE experiment_id=%s',(experiment.experiment_id,)).fetchone()[0]
            check(all(at(s.cutoff)<=at(trial.outcome_cutoff) for s in samples.values()),'outcome_cutoff_before_decision')
            for arm in trial.arms:
                config=next(c for c in experiment.arms if c.arm==arm.arm)
                artifacts=[];missing_run=arm.publication_run_id is None
                if not missing_run:
                    pub=conn.execute('SELECT status FROM discovery.publication_runs WHERE run_id=%s',(arm.publication_run_id,)).fetchone()
                    check(pub is not None,'publication_run_missing');missing_run=pub[0]!='completed'
                    stored=conn.execute('SELECT recommendation_id,payload FROM discovery.recommendations WHERE run_id=%s AND cohort=%s',(arm.publication_run_id,arm.arm)).fetchall()
                    window=getattr(experiment,trial.split)
                    excluded={s.sample_id for s in experiment.samples}-{sid for ids in audit['accepted'].values() for sid in ids}
                    excluded_keys={(s.listing_id,s.cutoff) for s in experiment.samples if s.sample_id in excluded}
                    in_scope=[(rid,r) for rid,r in stored if r['instrument']['instrument_id'] in experiment.universe and at(window.start)<=at(r['information_cutoff_at'])<=at(window.end) and (r['instrument']['instrument_id'],r['information_cutoff_at']) not in excluded_keys]
                    check(all((r['instrument']['instrument_id'],r['information_cutoff_at']) in samples for _,r in in_scope),'unregistered_decision_snapshot')
                    # An unrelated completed run is not evidence of a zero-pick scan.
                    # Main's publisher records every candidate, including abstentions.
                    missing_run=missing_run or not in_scope
                    expected={rid for rid,r in in_scope}
                    check(expected==set(arm.recommendation_ids),'omitted_or_foreign_decisions')
                else:check(not arm.recommendation_ids,'missing_run_has_decisions')
                for rid in arm.recommendation_ids:
                    a=read_artifact(conn,rid);r=a['recommendation'];sample=samples[(r['instrument']['instrument_id'],r['information_cutoff_at'])]
                    check(r['mode']==experiment.mode and r['horizon']['profile']==experiment.horizon,'experiment_mode_or_horizon_mismatch')
                    check(digest(a['input_manifest'])==sample.input_hash,'frozen_input_mismatch')
                    check(at(r['horizon']['holding_end_at'])<=at(sample.label_end),'label_span_underdeclared')
                    if trial.split=='forward':
                        check(at(r['information_cutoff_at'])>=registered.replace(tzinfo=None) and at(r['generated_at'])>=registered.replace(tzinfo=None),'forward_decision_predates_registration')
                    check_revisions(conn,sample,experiment.mode);validate_bundle(a['contract_bundle']);reproduce_quant(a)
                    research=a.get('research') or {};bundle=a.get('research_bundle') or {}
                    for document in research.get('source_documents',[]):
                        revision=Revision.model_validate_json(json.dumps(document['revision']))
                        check(eligible(revision,sample.cutoff,experiment.mode) and at(revision.published_at)<=at(sample.cutoff),'post_cutoff_research_document')
                    for fact in bundle.get('facts',[]):check(at(fact['period_end_at'])<=at(sample.cutoff),'post_cutoff_financial_observation')
                    versions=artifact_versions(a)
                    for key,value in versions.items():
                        if value is not None:check(value==getattr(config,key),'artifact_version_mismatch:'+key)
                    artifacts.append(a)
                pair_sets[arm.arm]={(r['recommendation']['instrument']['instrument_id'],r['recommendation']['information_cutoff_at'],digest(r['input_manifest'])) for r in artifacts}
                orders=[];ledger_ref=None
                if arm.portfolio_id:
                    ledger=conn.execute('SELECT state,event_hash FROM paper.ledger WHERE portfolio_id=%s AND sequence=%s',(arm.portfolio_id,arm.ledger_sequence)).fetchone()
                    check(ledger is not None,'ledger_revision_unavailable');state,ledger_hash=ledger;authorize(conn,state)
                    check(instant(state['available_at'])<=instant(trial.outcome_cutoff),'future_outcome_revision')
                    check(set(state['orders'])<=set(arm.recommendation_ids),'portfolio_includes_other_decisions')
                    orders=list(state['orders'].values())
                    portfolio_policy=conn.execute('SELECT config FROM paper.portfolios WHERE portfolio_id=%s',(arm.portfolio_id,)).fetchone()[0]
                    observation_times=tuple(row[0].isoformat() for row in conn.execute(
                        "SELECT event_at FROM paper.ledger WHERE portfolio_id=%s AND sequence<=%s AND kind='observation' ORDER BY sequence",
                        (arm.portfolio_id,arm.ledger_sequence)).fetchall())
                    ledger_assumptions.add((digest({k:v for k,v in portfolio_policy.items() if k!='name'}),state['asof'],observation_times))
                    ledger_ref=dict(portfolio_id=arm.portfolio_id,sequence=arm.ledger_sequence,event_hash=ledger_hash,policy_hash=digest(portfolio_policy))
                    for o in orders:
                        check(o['horizon']==experiment.horizon and o['cohort']==arm.arm,'outcome_cohort_mismatch')
                arm_reports[arm.arm]=summarize_arm(artifacts,orders,len(experiment.universe),unavailable=missing_run)
                arm_reports[arm.arm].update(pinned_portfolio(conn,arm,trial.outcome_cutoff))
                lineage[arm.arm]=dict(recommendation_ids=list(arm.recommendation_ids),artifact_hashes=[digest(a) for a in artifacts],ledger=ledger_ref)
            if experiment.comparison=='paired':
                check(all(s==pair_sets['quant'] for s in pair_sets.values()),'paired_candidates_or_snapshots_differ')
                check(len(ledger_assumptions)<=1,'paired_ledger_cost_risk_or_observation_window_mismatch')
            result=dict(status='completed',trial_id=tid,experiment_id=experiment.experiment_id,split=trial.split,comparison=experiment.comparison,
                evaluator_hash=evaluator_hash(),arms=arm_reports,comparisons=comparisons(arm_reports),lineage=lineage,split_audit=audit,selection_differences={k:len(v^pair_sets['quant']) for k,v in pair_sets.items()},
                evidence_class='synthetic_software_only' if experiment.mode=='synthetic' else 'prospective_unqualified' if trial.split=='forward' else 'historical_exploratory',
                historical_llm_contamination=experiment.historical_llm_contamination,
                promotion='blocked',profitability_claim=False,limitations=['Existing arms/outcomes only; no new inference or trade execution.','Historical AI results exploratory even with PIT retrieval.','Missing benchmarks, immature outcomes and absent uncertainty are not zeros.'])
            result=json_value(result)
            if fault:fault()
        except (ValueError,KeyError,PermissionError) as exc:
            result=dict(status='failed',trial_id=tid,experiment_id=experiment.experiment_id,error_code='source_permission_denied' if isinstance(exc,PermissionError) else safe_error(exc),profitability_claim=False)
        conn.execute('INSERT INTO discovery.experiment_results(trial_id,result_hash,payload) VALUES(%s,%s,%s)',(tid,digest(result),Jsonb(json_value(result))))
        event(conn,experiment.experiment_id,'trial_'+result['status'],dict(result_hash=digest(result)),tid)
    return result


def promotion(conn,eid):
    experiment,_=load(conn,eid);thresholds=experiment.thresholds
    missing=[k for k,v in thresholds.model_dump().items() if v is None]
    rows=conn.execute("SELECT r.payload FROM discovery.experiment_results r JOIN discovery.experiment_trials t USING(trial_id) WHERE t.experiment_id=%s ORDER BY r.evaluated_at DESC",(eid,)).fetchall()
    results=[authorize_result(conn,r[0]) for r in rows if r[0]['status']=='completed']
    gates={}
    for arm in ('quant_rag','quant_agent'):
        test=next((r['arms'][arm] for r in results if r['split']=='test'),None)
        forward=next((r['arms'][arm] for r in results if r['split']=='forward' and r['evidence_class']=='prospective_unqualified'),None)
        def minimum(value,bound):return value is not None and bound is not None and Decimal(str(value))>=Decimal(str(bound))
        gates[arm]=dict(untouched_test_present=test is not None,
            resolved_sample=minimum(test['resolved_trades'] if test else None,thresholds.minimum_samples),
            matured_forecast_sample=minimum(test['forecast_quality']['matured'] if test else None,thresholds.minimum_samples),
            coverage=minimum(test.get('coverage') if test else None,thresholds.coverage),
            drawdown=bool(test and test.get('maximum_drawdown') is not None and thresholds.max_drawdown is not None and Decimal(test['maximum_drawdown'])<=Decimal(str(thresholds.max_drawdown))),
            prospective_sample=minimum(forward['resolved_trades'] if forward else None,thresholds.minimum_samples),
            forward_duration_verified=False,cost_stress_verified=False,benchmark_verified=False,uncertainty_supported=False)
    # Four independent approvals cannot be manufactured by supplying Ref objects.
    # D3-10 forward admission is unactivated on main; no route here activates it.
    reasons=['unset_threshold:'+k for k in missing]+['independent_approvals_not_verified','qualified_prospective_evidence_unavailable','benchmark_and_uncertainty_evidence_unavailable']
    reasons += [arm+':'+gate for arm,values in gates.items() for gate,passed in values.items() if not passed]
    return dict(eligible=False,reasons=reasons,gates=gates,ep1='unratified',strategy_activated=False,
        independent_approvals={name:'unverified' for name in ('software_correctness','research_quality','operational_release','investment_strategy')})


def control(conn,eid,action,reason,target=None,key=None):
    check(action in ('pause','rollback','request_promotion'),'invalid_governance_action');load(conn,eid)
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('D3-11-holdouts',))
        request=dict(action=action,reason=reason,target=target)
        if key:
            previous=conn.execute("SELECT payload FROM discovery.experiment_events WHERE experiment_id=%s AND payload->>'idempotency_key'=%s",(eid,key)).fetchone()
            if previous:
                check(previous[0]['request']==request,'idempotency_conflict');return previous[0]['result']
        if action=='rollback':
            check(target is not None and target!=eid,'rollback_target_required');other,_=load(conn,target);current,_=load(conn,eid)
            check(other.horizon==current.horizon,'rollback_horizon_mismatch')
        result=promotion(conn,eid) if action=='request_promotion' else dict(future_runs_only=True,target=target,reason=reason,live_strategy_activated=False)
        event(conn,eid,action,dict(idempotency_key=key,request=request,result=result))
    return result
