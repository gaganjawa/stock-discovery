"""Registered fold reads over disposable synthetic D3-09/10/11 evidence."""
import json
from copy import deepcopy
from uuid import uuid4
from threading import Event
from concurrent.futures import ThreadPoolExecutor
import psycopg
from psycopg.types.json import Jsonb
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db
from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis import governance as g,paper_store
from stock_discovery_analysis.fold_reporting import registered_folds
from stock_discovery_analysis.governance_contracts import Trial
from stock_discovery_analysis.paper_contracts import PortfolioConfig,FICTIONAL
from stock_discovery_analysis.publication_fixtures import SOURCE
from test_governance_store import database,isolated_url,fixture_experiment,empty,trial


def counts(c):
    return c.execute('SELECT (SELECT count(*) FROM discovery.experiment_trials),'
        '(SELECT count(*) FROM discovery.experiment_results),(SELECT count(*) FROM discovery.experiment_events),'
        '(SELECT count(*) FROM discovery.rag_reservations),(SELECT count(*) FROM paper.ledger)').fetchone()


def completed(database,horizon='swing',*,ledger=False):
    c,_,_=database;e,arms,run=fixture_experiment(database,horizon);g.register(c,e);t=trial(e,arms,run)
    if ledger:
        wire=t.model_dump(mode='json')
        for arm in wire['arms']:
            pid=paper_store.create(c,PortfolioConfig(name='Fold fixture',mode='fictional_simulation',contract_version=FICTIONAL,
                starting_capital='100000',simulation_start_at='2025-06-25T10:01:01Z'),uuid4().hex)
            for rid in arm['recommendation_ids']:paper_store.admit(c,pid,rid,rid)
            oid=paper_store.demo_observation(c,pid,uuid4().hex);paper_store.process(c,oid)
            _,last=paper_store.config_state(c,pid);arm.update(portfolio_id=pid,ledger_sequence=last[0])
        t=Trial.model_validate_json(json.dumps(wire))
    g.begin_trial(c,t);r=g.evaluate(c,t.trial_id);assert r['status']=='completed',r
    return e,t,r


def test_empty_and_pending_do_not_open_or_evaluate_holdout(database,monkeypatch):
    c,_,_=database;e=empty(c);before=counts(c)
    report=registered_folds(c,[e.experiment_id]);assert report['status']=='unavailable' and report['folds']==[]
    assert all(p['status']=='not_opened_or_not_registered' for p in report['coverage'][0]['phases'])
    assert counts(c)==before
    t=trial(e);g.begin_trial(c,t);before=counts(c)
    with monkeypatch.context() as m:
        m.setattr(g,'evaluate',lambda *args,**kwargs:pytest.fail('GET must never evaluate'))
        m.setattr(g,'begin_trial',lambda *args,**kwargs:pytest.fail('GET must never reserve'))
        pending=registered_folds(c,[e.experiment_id])
        assert pending['folds'][0]['status']=='registered_not_evaluated' and pending['folds'][0]['arms']=={}
        assert not pending['holdout_access_performed'] and counts(c)==before
    g.evaluate(c,t.trial_id)
    sealed=registered_folds(c,[e.experiment_id])
    assert sealed['folds'][0]['fold_id']==pending['folds'][0]['fold_id']
    assert sealed['report_id']!=pending['report_id']


def test_sealed_arms_missing_observations_and_repeated_reads_preserve_history(database):
    c,_,_=database;e,t,result=completed(database);before=counts(c)
    r=registered_folds(c,[e.experiment_id]);f=r['folds'][0]
    assert f['trial_id']==t.trial_id and f['result_hash']==digest(result) and f['phase']=='validation'
    assert f['registered_samples']==5 and f['embargo_seconds']==e.embargo_seconds
    for arm,m in f['arms'].items():
        assert m['decisions']==m['missing_outcomes']==5 and m['resolved_trades']==0
        assert m['portfolio_return'] is None and m['benchmark_return'] is None
        assert m['benchmark_reason'] and f['versions'][arm]['strategy_hash']
    assert all(a['metrics'] is None and a['reason']=='incomplete_fold_evidence' for a in r['aggregates'])
    assert r['paired_comparison']['eligible_pairs']==0 and r['paired_comparison']['ai_performance'] is None
    assert r==registered_folds(c,[e.experiment_id]) and counts(c)==before


def test_holdout_crash_stays_reserved_and_is_not_finished_by_reporting(database,monkeypatch):
    c,_,_=database;e=empty(c);v=trial(e);g.begin_trial(c,v);g.evaluate(c,v.trial_id)
    t=trial(e,split='test',selected_validation_trial=v.trial_id);g.begin_trial(c,t)
    before=counts(c)
    monkeypatch.setattr(g,'evaluate',lambda *args,**kwargs:pytest.fail('No protected evaluation'))
    r=registered_folds(c,[e.experiment_id])
    holdout=next(f for f in r['folds'] if f['phase']=='test')
    assert holdout['status']=='registered_not_evaluated' and counts(c)==before
    assert not r['evaluation_performed']


def test_overlapping_validation_trials_remain_visible_without_pooled_results(database):
    c,_,_=database;e,t,_=completed(database)
    second=Trial.model_validate_json(t.model_copy(update={'trial_id':'TR-'+uuid4().hex}).model_dump_json())
    g.begin_trial(c,second);g.evaluate(c,second.trial_id)
    r=registered_folds(c,[e.experiment_id])
    assert len(r['folds'])==2
    assert all(a['status']=='unavailable' and a['reason']=='overlapping_or_repeated_fold_evidence' for a in r['aggregates'])


def test_pinned_ledger_window_costs_and_long_term_maturity_not_latest_state(database):
    c,_,_=database;e,t,_=completed(database,'long_term',ledger=True)
    r=registered_folds(c,[e.experiment_id]);f=r['folds'][0]
    for arm in f['arms'].values():
        assert arm['portfolio_return'] is not None and arm['maximum_drawdown'] is not None
        assert arm['fees'] is not None and arm['observation_window']
        assert arm['forecast_quality']['provisional']>0 and arm['forecast_quality']['matured']==0
        assert arm['benchmark_return'] is None
    for arm in t.arms:
        oid=paper_store.demo_observation(c,arm.portfolio_id,uuid4().hex);paper_store.process(c,oid)
    assert registered_folds(c,[e.experiment_id])==r


def test_source_restriction_denies_cached_results_and_other_selection_stays_usable(database):
    c,_,_=database;e,_,_=completed(database);unrelated=empty(c)
    before=registered_folds(c,[e.experiment_id])
    assert before['folds']
    with c.transaction(force_rollback=True):
        c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
        with pytest.raises(PermissionError):registered_folds(c,[e.experiment_id])
        assert registered_folds(c,[unrelated.experiment_id])['status']=='unavailable'
    from stock_discovery_analysis.grant_fences import restrict
    with c.transaction(force_rollback=True):
        restrict(c,request_id=uuid4(),kind='provider',source_id=SOURCE,reason='revoked')
        with pytest.raises(PermissionError):registered_folds(c,[e.experiment_id])


def test_invalid_result_hash_fails_closed_without_repair_or_new_audit(database):
    c,_,_=database;e=empty(c);t=trial(e);g.begin_trial(c,t)
    result=dict(status='failed',trial_id=t.trial_id,experiment_id=e.experiment_id,error_code='synthetic_failure')
    c.execute('INSERT INTO discovery.experiment_results(trial_id,result_hash,payload) VALUES(%s,%s,%s)',(t.trial_id,'0'*64,Jsonb(result)))
    before=counts(c)
    with pytest.raises(ValueError,match='fold_result_identity'):registered_folds(c,[e.experiment_id])
    assert counts(c)==before


def test_outcome_cutoff_and_split_audit_are_independently_checked(database):
    c,_,_=database;e,t,result=completed(database)
    wire=t.model_dump(mode='json');wire.update(trial_id='TR-'+uuid4().hex,outcome_cutoff='2000-01-01T00:00:00Z')
    altered=Trial.model_validate_json(json.dumps(wire));g.begin_trial(c,altered)
    seal_fixture(c,altered,result)
    with pytest.raises(ValueError,match='fold_outcome_before_decision'):registered_folds(c,[e.experiment_id])


def test_api_auth_bounds_order_no_store_and_sanitized_denial(database,monkeypatch):
    c,_,_=database;e,_,_=completed(database);other=empty(c)
    monkeypatch.setenv('AUTH_TOKEN','fold-owner-key-with-at-least-32-characters')
    app.dependency_overrides[db]=lambda:c
    try:
        client=TestClient(app);path='/v1/experiments/fold-results';params=[('experiment_id',x) for x in (e.experiment_id,other.experiment_id)]
        assert client.get(path,params=params).status_code==401
        client.headers['Authorization']='Bearer fold-owner-key-with-at-least-32-characters'
        response=client.get(path,params=params);assert response.status_code==200,response.text
        assert response.headers['cache-control']=='no-store'
        assert response.json()==client.get(path,params=list(reversed(params))).json()
        assert client.get(path).status_code==422
        assert client.get(path,params=[('experiment_id',e.experiment_id)]*11).status_code==422
        assert client.get(path,params=[('experiment_id',e.experiment_id)]*2).status_code==409
        with c.transaction(force_rollback=True):
            c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
            denied=client.get(path,params=params)
            assert denied.status_code==403 and 'folds' not in denied.json() and SOURCE not in denied.text
    finally:app.dependency_overrides.pop(db,None)


def test_restriction_serializes_with_report_read(database,monkeypatch):
    c,_,url=database;e,_,_=completed(database);locked=Event();release=Event();original=g.authorize_result
    def paused(conn,result):
        value=original(conn,result);locked.set();assert release.wait(5);return value
    monkeypatch.setattr(g,'authorize_result',paused)
    def read():
        with psycopg.connect(url,autocommit=True) as conn:return registered_folds(conn,[e.experiment_id])
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(read)
        try:
            assert locked.wait(5)
            with pytest.raises(psycopg.errors.LockNotAvailable):
                with c.transaction():
                    c.execute("SET LOCAL lock_timeout='150ms'")
                    c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
        finally:release.set()
        assert future.result(timeout=10)['status']=='available'


def seal_fixture(c,t,result):
    forged={**deepcopy(result),'trial_id':t.trial_id,'experiment_id':t.experiment_id}
    c.execute('INSERT INTO discovery.experiment_results(trial_id,result_hash,payload) VALUES(%s,%s,%s)',(t.trial_id,digest(forged),Jsonb(forged)))
    g.event(c,t.experiment_id,'trial_'+forged['status'],dict(result_hash=digest(forged)),t.trial_id)


def test_future_ledger_cannot_be_laundered_through_a_valid_result_hash(database):
    c,_,_=database;e,t,result=completed(database,'long_term',ledger=True)
    changed=t.model_copy(update={'trial_id':'TR-'+uuid4().hex,'outcome_cutoff':e.samples[0].cutoff})
    g.begin_trial(c,changed);seal_fixture(c,changed,result)
    with pytest.raises(ValueError,match='fold_future_outcome'):registered_folds(c,[e.experiment_id])


def test_later_financial_revision_never_replaces_pinned_asof_evidence(database):
    from stock_discovery_analysis.revisions import Revision
    from stock_discovery_analysis.governance_contracts import split_samples
    from test_governance import parse
    c,_,_=database;e,t,result=completed(database)
    raw=c.execute("SELECT payload,stream_id,grant_id,grant_version FROM discovery.revisions WHERE kind='document' AND listing_id=%s ORDER BY available_at LIMIT 1",(e.samples[0].listing_id,)).fetchone()
    old,stream,grant,version=raw
    revised={**old,'revision_id':'SYN-fold-revised-'+uuid4().hex,'source_revision':uuid4().hex,'sequence':old['sequence']+1,
        'supersedes_id':old['revision_id'],'published_at':'2025-07-01T00:00:00Z','available_at':'2025-07-01T00:00:00Z','fetched_at':'2025-07-01T00:00:00Z'}
    r=Revision.model_validate_json(json.dumps(revised))
    c.execute('INSERT INTO discovery.revisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (r.revision_id,stream,r.source_id,r.source_revision,r.logical_key,r.sequence,'document',r.listing_id,r.available_at,grant,version,r.instrument_revision_id,r.supersedes_id,r.content_hash,Jsonb(revised)))
    wire=e.model_dump(mode='json');wire['experiment_id']='EXP-'+uuid4().hex;wire['samples'][0]['revision_ids']=[r.revision_id]
    altered=parse(wire);g.register(c,altered)
    changed=t.model_copy(update={'experiment_id':altered.experiment_id,'trial_id':'TR-'+uuid4().hex});g.begin_trial(c,changed)
    # Deliberately forged disposable record: hash validity alone is insufficient.
    seal_fixture(c,changed,{**result,'split_audit':split_samples(altered)})
    with pytest.raises(ValueError,match='post_cutoff_or_unverified_revision'):registered_folds(c,[altered.experiment_id])
    assert registered_folds(c,[e.experiment_id])['folds'][0]['result_hash']==digest(result)
    assert c.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(old['revision_id'],)).fetchone()[0]==old


def test_final_authorization_recheck_after_later_locks_is_required(database,monkeypatch):
    import stock_discovery_analysis.fold_reporting as module
    c,_,_=database;e,_,_=completed(database);original=module.source_check;calls=[];before=counts(c)
    def expires(*args):
        original(*args);calls.append(1)
        if len(calls)>1:raise PermissionError('synthetic_expiry_after_later_lock')
    with monkeypatch.context() as m:
        m.setattr(module,'source_check',expires)
        with pytest.raises(PermissionError):registered_folds(c,[e.experiment_id])
    assert len(calls)==2 and counts(c)==before
    assert registered_folds(c,[e.experiment_id])['status']=='available'


def test_database_failure_is_sanitized_rolls_back_and_connection_recovers(database,monkeypatch):
    c,_,_=database;e,_,_=completed(database);before=counts(c)
    def broken(conn,result):conn.execute('SELECT * FROM public.synthetic_missing_relation')
    with monkeypatch.context() as m:
        m.setattr(g,'authorize_result',broken)
        with pytest.raises(PermissionError,match='^fold_evidence_access_unavailable$'):registered_folds(c,[e.experiment_id])
    assert c.execute('SELECT 1').fetchone()==(1,) and counts(c)==before
    assert registered_folds(c,[e.experiment_id])['status']=='available'


def test_forward_is_distinct_and_missing_run_is_not_a_successful_no_pick(database):
    c,_,_=database;e=empty(c,forward={'start':'2050-01-01T00:00:00Z','end':'2051-01-01T00:00:00Z'})
    sample=dict(sample_id='SYN-forward',listing_id=e.universe[0],cutoff='2050-01-01T00:00:00Z',label_end='2050-01-02T00:00:00Z',
        groups=['SYN-forward'],input_hash=digest('synthetic forward contract'),revision_ids=[])
    t=trial(e,split='forward',forward_samples=[sample],outcome_cutoff='2051-01-01T00:00:00Z');g.begin_trial(c,t);g.evaluate(c,t.trial_id)
    report=registered_folds(c,[e.experiment_id]);f=report['folds'][0]
    assert f['phase']=='forward' and f['registered_samples']==1
    assert all(a['research_unavailable'] and not a['no_picks'] for a in f['arms'].values())
    assert all(a['status']=='unavailable' for a in report['aggregates'])


def test_failed_trials_remain_visible_without_metrics(database):
    c,_,_=database;e,arms,run=fixture_experiment(database);g.register(c,e)
    fewer=deepcopy(arms);fewer['quant']=fewer['quant'][:-1]
    t=trial(e,fewer,run);g.begin_trial(c,t);assert g.evaluate(c,t.trial_id)['status']=='failed'
    r=registered_folds(c,[e.experiment_id])
    assert r['folds'][0]['status']=='failed' and r['folds'][0]['error_code']=='omitted_or_foreign_decisions'
    assert r['folds'][0]['arms']=={} and not r['aggregates']


def test_report_bound_is_explicit_without_silently_omitting_trials(database):
    c,_,_=database;e=empty(c,tuning_budget=101)
    for _ in range(101):g.begin_trial(c,trial(e))
    before=counts(c)
    with pytest.raises(ValueError,match='fold_report_limit_exceeded'):registered_folds(c,[e.experiment_id])
    assert counts(c)==before


def test_changed_registered_strategy_cannot_reuse_old_sealed_artifact(database):
    from test_governance import parse
    c,_,_=database;e,t,result=completed(database)
    wire=e.model_dump(mode='json');wire['experiment_id']='EXP-'+uuid4().hex
    for arm in wire['arms']:arm['strategy_hash']=digest('different frozen strategy')
    changed=parse(wire);g.register(c,changed)
    other=t.model_copy(update={'trial_id':'TR-'+uuid4().hex,'experiment_id':changed.experiment_id});g.begin_trial(c,other)
    seal_fixture(c,other,result)
    with pytest.raises(ValueError,match='fold_frozen_version_mismatch'):registered_folds(c,[changed.experiment_id])


def test_result_without_immutable_evaluation_receipt_is_not_authoritative(database):
    c,_,_=database;e=empty(c);t=trial(e);g.begin_trial(c,t)
    result=dict(status='failed',trial_id=t.trial_id,experiment_id=e.experiment_id,error_code='synthetic_failure')
    c.execute('INSERT INTO discovery.experiment_results(trial_id,result_hash,payload) VALUES(%s,%s,%s)',(t.trial_id,digest(result),Jsonb(result)))
    before=counts(c)
    with pytest.raises(ValueError,match='fold_sealed_receipt_missing'):registered_folds(c,[e.experiment_id])
    assert counts(c)==before
