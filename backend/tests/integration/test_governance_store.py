"""T14/T15: genuine PostgreSQL transactions over explicitly synthetic D3-09/10 evidence."""
import json
import os
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db as api_db
from stock_discovery_contracts.v2 import digest,at
from stock_discovery_analysis import governance as g,paper_store
from stock_discovery_analysis.governance_contracts import Experiment,Trial
from stock_discovery_analysis.publication_store import RunRequest,enqueue,run_next
from stock_discovery_analysis.publication_fixtures import SOURCE
from stock_discovery_analysis.paper_contracts import PortfolioConfig,FICTIONAL
from test_rag_research import isolated_url
from test_governance import manifest,parse

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable migrated PostgreSQL')


@pytest.fixture(scope='module')
def database(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        runs={}
        for horizon in ('swing','short_term','long_term'):
            rid=enqueue(conn,RunRequest(horizon=horizon),'governance-'+horizon,'test')
            assert run_next(conn,'test')['status']=='completed'
            runs[horizon]=rid
        yield conn,runs,isolated_url


def fixture_experiment(database,horizon='swing',**changes):
    conn,runs,_=database
    m=manifest('EXP-'+uuid4().hex);m['horizon']=horizon
    rows=conn.execute('SELECT artifact FROM discovery.recommendations WHERE run_id=%s ORDER BY recommendation_id',(runs[horizon],)).fetchall()
    artifacts=[r[0] for r in rows];byarm={arm:[a for a in artifacts if a['recommendation']['cohort']['arm']==arm] for arm in g.ARMS}
    m['universe']=sorted({a['recommendation']['instrument']['instrument_id'] for a in artifacts})
    m['universe_ref']['content_hash']=digest(m['universe'])
    m['validation']={'start':'2025-01-01T00:00:00Z','end':'2031-12-31T00:00:00Z'}
    m['test']={'start':'2040-01-01T00:00:00Z','end':'2047-01-01T00:00:00Z'}
    m['samples']=[]
    for a in byarm['quant']:
        r=a['recommendation'];listing=r['instrument']['instrument_id']
        m['samples'].append(dict(sample_id=listing,listing_id=listing,cutoff=r['information_cutoff_at'],label_end=r['horizon']['holding_end_at'],groups=[listing],input_hash=digest(a['input_manifest']),revision_ids=[]))
    m['embargo_seconds']=int(max((at(s['label_end'])-at(s['cutoff'])).total_seconds() for s in m['samples']))
    for config in m['arms']:
        candidates=byarm[config['arm']]
        a=next((a for a in candidates if a['research'] and a['research'].get('status')=='completed'),candidates[0])
        config.update({k:v for k,v in g.artifact_versions(a).items() if v is not None})
    m.update(changes)
    return parse(m),byarm,runs[horizon]


def trial(e,byarm=None,run=None,split='validation',**changes):
    arms=[dict(arm=a,publication_run_id=run,recommendation_ids=[x['recommendation']['recommendation_id'] for x in (byarm or {}).get(a,[])]) for a in g.ARMS]
    body=dict(trial_id='TRIAL-'+uuid4().hex,experiment_id=e.experiment_id,split=split,arms=arms,outcome_cutoff='2031-12-31T00:00:00Z')
    return Trial.model_validate_json(json.dumps({**body,**changes}))


def empty(conn,**changes):
    m=manifest('EXP-'+uuid4().hex);m['universe']=['EMPTY-'+uuid4().hex];m.update(changes)
    e=parse(m);g.register(conn,e);return e


@pytest.mark.parametrize('horizon',['swing','short_term','long_term'])
def test_all_arms_reproduce_with_failure_inclusive_denominators(database,horizon):
    conn,_,_=database;e,arms,run=fixture_experiment(database,horizon);g.register(conn,e)
    t=trial(e,arms,run);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='completed',r
    assert r['evidence_class']=='synthetic_software_only' and not r['profitability_claim']
    assert set(r['arms'])==set(g.ARMS) and set(r['selection_differences'].values())=={0}
    for arm,metrics in r['arms'].items():
        assert metrics['decisions']==5 and metrics['missing_outcomes']==5 and metrics['resolved_trades']==0
        assert metrics['benchmark_return'] is None and metrics['win_rate'] is None
        assert metrics['forecast_quality']['missing']==5
        assert metrics['actions']['INSUFFICIENT_EVIDENCE']>=1
    assert g.evaluate(conn,t.trial_id)==r
    assert conn.execute('SELECT count(*) FROM discovery.experiment_results WHERE trial_id=%s',(t.trial_id,)).fetchone()[0]==1


def test_holdout_reservation_survives_crash_and_repeated_access(database):
    conn,_,_=database;e=empty(conn);v=trial(e);g.begin_trial(conn,v);assert g.evaluate(conn,v.trial_id)['status']=='completed'
    t=trial(e,split='test',selected_validation_trial=v.trial_id);g.begin_trial(conn,t)
    def crash():raise RuntimeError('injected_crash')
    with pytest.raises(RuntimeError):g.evaluate(conn,t.trial_id,fault=crash)
    assert conn.execute('SELECT count(*) FROM discovery.experiment_results WHERE trial_id=%s',(t.trial_id,)).fetchone()[0]==0
    with pytest.raises(ValueError,match='already_exposed'):g.begin_trial(conn,trial(e,split='test',selected_validation_trial=v.trial_id))
    assert g.evaluate(conn,t.trial_id)['status']=='completed'
    assert g.begin_trial(conn,t)['status']=='already_registered'
    # Changing the experiment name, hypothesis or hashes cannot launder access.
    m=e.model_dump(mode='json');m['experiment_id']='EXP-'+uuid4().hex;m['hypothesis']='changed after test'
    renamed=parse(m);g.register(conn,renamed);v2=trial(renamed);g.begin_trial(conn,v2);g.evaluate(conn,v2.trial_id)
    with pytest.raises(ValueError,match='already_exposed'):g.begin_trial(conn,trial(renamed,split='test',selected_validation_trial=v2.trial_id))
    assert conn.execute("SELECT count(*) FROM discovery.experiment_events WHERE experiment_id=%s AND kind='trial_denied'",(renamed.experiment_id,)).fetchone()[0]==1


def test_concurrent_test_access_has_single_winner(database):
    conn,_,url=database;e=empty(conn);v=trial(e);g.begin_trial(conn,v);g.evaluate(conn,v.trial_id)
    ts=[trial(e,split='test',selected_validation_trial=v.trial_id) for _ in range(2)]
    def reserve(t):
        with psycopg.connect(url,autocommit=True) as other:
            try:return g.begin_trial(other,t)['status']
            except ValueError:return 'blocked'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,ts))
    assert sorted(results)==['blocked','registered']


@pytest.mark.parametrize('table',['experiments','experiment_trials','experiment_events','experiment_results'])
@pytest.mark.parametrize('operation',['UPDATE','DELETE','TRUNCATE'])
def test_registry_is_append_only(database,table,operation):
    conn,_,_=database
    statement=f'UPDATE discovery.{table} SET '+('manifest=manifest' if table=='experiments' else 'request=request' if table=='experiment_trials' else 'payload=payload') if operation=='UPDATE' else f'{operation} '+('FROM ' if operation=='DELETE' else '')+f'discovery.{table}'
    with pytest.raises(psycopg.Error):conn.execute(statement)


def test_trial_conflicts_and_rollback_only_change_future_runs(database):
    conn,_,_=database;e=empty(conn);target=empty(conn);t=trial(e);g.begin_trial(conn,t);before=g.evaluate(conn,t.trial_id)
    with pytest.raises(ValueError,match='immutable_trial'):g.begin_trial(conn,t.model_copy(update={'outcome_cutoff':'2032-01-01T00:00:00Z'}))
    result=g.control(conn,e.experiment_id,'rollback','software rollback',target.experiment_id)
    assert result['future_runs_only'] and not result['live_strategy_activated']
    with pytest.raises(ValueError,match='rollback_requires'):g.begin_trial(conn,trial(e))
    assert g.evaluate(conn,t.trial_id)==before
    assert g.begin_trial(conn,trial(target))['status']=='registered'
    gate=g.promotion(conn,e.experiment_id)
    assert not gate['eligible'] and 'unset_threshold:minimum_samples' in gate['reasons']


def test_omitted_abstentions_and_wrong_frozen_inputs_seal_failure(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database);g.register(conn,e)
    fewer=deepcopy(arms);fewer['quant']=fewer['quant'][:-1]
    t=trial(e,fewer,run);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='failed' and r['error_code']=='omitted_or_foreign_decisions'
    bad=e.model_dump(mode='json');bad['experiment_id']='EXP-'+uuid4().hex;bad['samples'][0]['input_hash']=digest('tampered')
    changed=parse(bad);g.register(conn,changed);t=trial(changed,arms,run);g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['error_code']=='frozen_input_mismatch'


def test_cached_metrics_recheck_revocation(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database);g.register(conn,e);t=trial(e,arms,run);g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['status']=='completed'
    with conn.transaction(force_rollback=True):
        conn.execute('INSERT INTO discovery.publication_source_controls VALUES (%s,true) ON CONFLICT (source_id) DO UPDATE SET revoked=true',(SOURCE,))
        with pytest.raises(PermissionError):g.evaluate(conn,t.trial_id)


def test_zero_picks_distinct_from_failed_or_missing_run(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database)
    wire=e.model_dump(mode='json');wire['universe']=['SYN-D309-WAITING'];wire['samples']=[s for s in wire['samples'] if s['listing_id'] in wire['universe']]
    e=parse(wire);arms={k:[a for a in rows if a['recommendation']['instrument']['instrument_id'] in wire['universe']] for k,rows in arms.items()}
    g.register(conn,e);t=trial(e,arms,run);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='completed' and all(a['no_picks'] and a['decisions']==1 for a in r['arms'].values()),r
    t=trial(e);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert all(a['research_unavailable'] and not a['no_picks'] for a in r['arms'].values())
    unrelated=empty(conn);t=trial(unrelated,run=run);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert all(a['research_unavailable'] and not a['no_picks'] for a in r['arms'].values())


def test_api_auth_conflicts_and_immutable_results(database,monkeypatch):
    conn,_,_=database;monkeypatch.setenv('AUTH_TOKEN','test-governance-owner-key-at-least-32-characters')
    def connection():yield conn
    app.dependency_overrides[api_db]=connection
    headers={'Authorization':'Bearer test-governance-owner-key-at-least-32-characters'}
    try:
        with TestClient(app) as client:
            assert client.get('/v1/experiments').status_code==401
            e=manifest('EXP-'+uuid4().hex);url='/v1/experiments';headers['Idempotency-Key']=e['experiment_id']
            assert client.post(url,json=e,headers=headers).status_code==200
            assert client.post(url,json={**e,'hypothesis':'changed'},headers=headers).status_code==409
            assert client.get(url+'/'+e['experiment_id'],headers=headers).json()['promotion']['eligible'] is False
            second=manifest('EXP-'+uuid4().hex);assert client.post(url,json=second,headers={**headers,'Idempotency-Key':second['experiment_id']}).status_code==200
            first=client.get(url+'?limit=1',headers=headers).json();assert first['next_cursor']==second['experiment_id']
            page=client.get(url,params={'limit':1,'cursor':first['next_cursor']},headers=headers).json()
            assert page['experiments'][0]['experiment_id']==e['experiment_id']
    finally:app.dependency_overrides.clear()


def test_end_to_end_selection_difference_not_paired_research_gain(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database,comparison='end_to_end');g.register(conn,e)
    t=trial(e,arms,run);wire=t.model_dump(mode='json');wire['arms'][1].update(publication_run_id=None,recommendation_ids=[])
    t=Trial.model_validate_json(json.dumps(wire));g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='completed' and r['selection_differences']['quant_rag']==5
    assert r['arms']['quant_rag']['research_unavailable'] and not r['comparisons']['quant_rag']['established_improvement']
    paired,_,_=fixture_experiment(database);g.register(conn,paired)
    wire.update(trial_id='TRIAL-'+uuid4().hex,experiment_id=paired.experiment_id)
    t=Trial.model_validate_json(json.dumps(wire));g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['error_code']=='paired_candidates_or_snapshots_differ'


def test_later_financial_revision_is_not_backdated(database):
    from psycopg.types.json import Jsonb
    from stock_discovery_analysis.revisions import Revision
    conn,_,_=database;e,arms,run=fixture_experiment(database)
    # Append an explicit restatement of a stored fictional filing. Never mutate its original.
    source=conn.execute("SELECT payload,stream_id,grant_id,grant_version FROM discovery.revisions WHERE kind='document' AND listing_id=%s ORDER BY available_at LIMIT 1",(e.samples[0].listing_id,)).fetchone()
    old,stream,grant,version=source
    revised={**old,'revision_id':'SYN-revised-'+uuid4().hex,'source_revision':uuid4().hex,'sequence':old['sequence']+1,'supersedes_id':old['revision_id'],
        'published_at':'2025-07-01T00:00:00Z','available_at':'2025-07-01T00:00:00Z','fetched_at':'2025-07-01T00:00:00Z'}
    revision=Revision.model_validate_json(json.dumps(revised))
    conn.execute('INSERT INTO discovery.revisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (revision.revision_id,stream,revision.source_id,revision.source_revision,revision.logical_key,revision.sequence,'document',revision.listing_id,revision.available_at,grant,version,revision.instrument_revision_id,revision.supersedes_id,revision.content_hash,Jsonb(revised)))
    wire=e.model_dump(mode='json');wire['samples'][0]['revision_ids']=[old['revision_id']]
    original=parse(wire);g.register(conn,original);t=trial(original,arms,run);g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['status']=='completed'
    wire['experiment_id']='EXP-'+uuid4().hex;wire['samples'][0]['revision_ids']=[revision.revision_id]
    changed=parse(wire);g.register(conn,changed);t=trial(changed,arms,run);g.begin_trial(conn,t)
    r=g.evaluate(conn,t.trial_id)
    assert r['status']=='failed' and r['error_code']=='post_cutoff_or_unverified_revision'
    assert conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(old['revision_id'],)).fetchone()[0]==old


def test_pinned_long_term_outcomes_remain_immature_and_history_frozen(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database,'long_term');g.register(conn,e);t=trial(e,arms,run);wire=t.model_dump(mode='json')
    for arm in wire['arms']:
        pid=paper_store.create(conn,PortfolioConfig(name='Governance fixture',mode='fictional_simulation',contract_version=FICTIONAL,starting_capital='100000',simulation_start_at='2025-06-25T10:01:01Z'),uuid4().hex)
        for rid in arm['recommendation_ids']:paper_store.admit(conn,pid,rid,rid)
        oid=paper_store.demo_observation(conn,pid,uuid4().hex);paper_store.process(conn,oid)
        _,last=paper_store.config_state(conn,pid);arm.update(portfolio_id=pid,ledger_sequence=last[0])
    t=Trial.model_validate_json(json.dumps(wire));g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='completed',r
    for arm in r['arms'].values():
        assert arm['forecast_quality']['matured']==0 and arm['forecast_quality']['provisional']>0
        assert arm['resolved_trades']==0 and arm['win_rate'] is None
        assert arm['portfolio_return'] is not None and arm['maximum_drawdown'] is not None
        assert arm['return_basis']=='full_capital_time_weighted_external_flows_removed'
    for arm in t.arms:
        oid=paper_store.demo_observation(conn,arm.portfolio_id,uuid4().hex);paper_store.process(conn,oid)
    assert g.evaluate(conn,t.trial_id)==r
    assert not g.promotion(conn,e.experiment_id)['eligible']


def test_all_supplied_thresholds_do_not_self_approve(database):
    conn,_,_=database;ref={'id':'client-assertion','version':'1','content_hash':digest('unverified')}
    e=empty(conn,thresholds=dict(minimum_samples=1,forward_days=1,coverage=0.1,max_drawdown=1.0,cost_stress=1.0,benchmark_criterion='greater than cash',research_quality_approval=ref,strategy_approval=ref))
    gate=g.control(conn,e.experiment_id,'request_promotion','test client-supplied claims')
    assert not gate['eligible'] and not gate['strategy_activated']
    assert 'independent_approvals_not_verified' in gate['reasons']


def test_holdout_cannot_be_relabelled_validation(database):
    conn,_,_=database;e=empty(conn);v=trial(e);g.begin_trial(conn,v);g.evaluate(conn,v.trial_id)
    g.begin_trial(conn,trial(e,split='test',selected_validation_trial=v.trial_id))
    wire=e.model_dump(mode='json');wire.update(experiment_id='EXP-'+uuid4().hex,validation=wire['test'],test={'start':'2006-01-01T00:00:00Z','end':'2007-01-01T00:00:00Z'})
    other=parse(wire);g.register(conn,other)
    with pytest.raises(ValueError,match='already_exposed'):g.begin_trial(conn,trial(other))


def test_failed_ai_counts_and_cost_unknown_remain_visible(database,monkeypatch):
    from stock_discovery_analysis import publication_store
    conn,runs,_=database;original=publication_store.research_candidate
    def failed(conn,rid,data,issuer,arm,access):
        if arm!='quant':raise TimeoutError('synthetic injected timeout')
        return original(conn,rid,data,issuer,arm,access)
    monkeypatch.setattr(publication_store,'research_candidate',failed)
    rid=enqueue(conn,RunRequest(horizon='swing'),uuid4().hex,'test');assert run_next(conn,'test')['status']=='completed'
    e,arms,run=fixture_experiment((conn,{**runs,'swing':rid},database[2]));g.register(conn,e);t=trial(e,arms,run);g.begin_trial(conn,t);r=g.evaluate(conn,t.trial_id)
    assert r['status']=='completed',r
    for arm in ('quant_rag','quant_agent'):
        assert r['arms'][arm]['research_failed']==5 and r['arms'][arm]['no_picks']
        assert r['arms'][arm]['research_cost'] is None and r['arms'][arm]['latency_ms'] is None
        assert r['arms'][arm]['decisions']==5 and r['arms'][arm]['missing_outcomes']==5


def test_forward_window_requires_real_preregistration(database):
    conn,_,_=database;m=manifest('EXP-'+uuid4().hex);m['forward']={'start':'2006-01-01T00:00:00Z','end':'2007-01-01T00:00:00Z'}
    with pytest.raises(ValueError,match='preregistered'):g.register(conn,parse(m))
    e=empty(conn,forward={'start':'2070-01-01T00:00:00Z','end':'2071-01-01T00:00:00Z'})
    t=trial(e,split='forward',outcome_cutoff='2070-01-01T00:00:00Z');g.begin_trial(conn,t)
    r=g.evaluate(conn,t.trial_id);assert r['status']=='completed' and r['evidence_class']=='synthetic_software_only'
    assert all(a['research_unavailable'] for a in r['arms'].values())


def test_missing_snapshot_cannot_hide_a_published_failure(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database);wire=e.model_dump(mode='json');wire['samples']=wire['samples'][1:]
    e=parse(wire);g.register(conn,e);t=trial(e,arms,run);g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['error_code']=='unregistered_decision_snapshot'


def test_registration_retry_after_forward_start_is_idempotent(database,monkeypatch):
    conn,_,_=database;e=empty(conn,forward={'start':'2070-01-01T00:00:00Z','end':'2071-01-01T00:00:00Z'})
    monkeypatch.setattr(g,'now',lambda:'2070-06-01T00:00:00Z')
    assert g.register(conn,e)['manifest_hash']==digest(e.model_dump(mode='json'))


def test_controls_are_idempotent_and_trial_budget_enforced(database):
    conn,_,_=database;e=empty(conn,tuning_budget=1);t=trial(e);g.begin_trial(conn,t)
    with pytest.raises(ValueError,match='budget_exhausted'):g.begin_trial(conn,trial(e))
    a=g.control(conn,e.experiment_id,'pause','data quality',key='pause-once')
    assert g.control(conn,e.experiment_id,'pause','data quality',key='pause-once')==a
    with pytest.raises(ValueError,match='idempotency_conflict'):g.control(conn,e.experiment_id,'pause','other',key='pause-once')
    assert conn.execute("SELECT count(*) FROM discovery.experiment_events WHERE experiment_id=%s AND kind='pause'",(e.experiment_id,)).fetchone()[0]==1


def test_future_fact_in_retrieved_content_fails_evaluation(database,monkeypatch):
    conn,_,_=database;e,arms,run=fixture_experiment(database);g.register(conn,e);t=trial(e,arms,run);g.begin_trial(conn,t)
    original=g.read_artifact
    def future(conn,rid):
        a=deepcopy(original(conn,rid));b=a.get('research_bundle')
        if b and b['facts']:b['facts'][0]['period_end_at']='2099-01-01T00:00:00Z'
        return a
    monkeypatch.setattr(g,'read_artifact',future)
    r=g.evaluate(conn,t.trial_id)
    assert r['status']=='failed' and r['error_code']=='post_cutoff_financial_observation'

def test_paired_outcomes_cannot_change_capital_cost_risk_assumptions(database):
    conn,_,_=database;e,arms,run=fixture_experiment(database);g.register(conn,e);t=trial(e,arms,run);wire=t.model_dump(mode='json')
    for i,arm in enumerate(wire['arms']):
        pid=paper_store.create(conn,PortfolioConfig(name='Different bookkeeping name '+str(i),mode='fictional_simulation',contract_version=FICTIONAL,starting_capital='100000',fixed_fee=str(i+1),simulation_start_at='2025-06-25T10:01:01Z'),uuid4().hex)
        arm.update(portfolio_id=pid,ledger_sequence=1)
    t=Trial.model_validate_json(json.dumps(wire));g.begin_trial(conn,t)
    assert g.evaluate(conn,t.trial_id)['error_code']=='paired_ledger_cost_risk_or_observation_window_mismatch'
