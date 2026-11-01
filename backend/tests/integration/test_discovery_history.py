"""Actual relationships over disposable, explicitly fictional D3-09/10/11 rows."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
from copy import deepcopy

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db
from stock_discovery_analysis import discovery_history as history,paper_store,governance as g
from stock_discovery_analysis.paper_contracts import PortfolioConfig,FICTIONAL
from stock_discovery_analysis.publication_fixtures import SOURCE
from test_governance_store import database,isolated_url,fixture_experiment,trial


def selected(database,*,cohort='quant',horizon='swing',case='READY'):
    c,runs,_=database
    return c.execute('''SELECT recommendation_id FROM discovery.recommendations
        WHERE run_id=%s AND cohort=%s AND listing_id=%s''',(runs[horizon],cohort,'SYN-D309-'+case)).fetchone()[0]


def counts(c):
    tables=('discovery.recommendations','paper.ledger','paper.observations','paper.processed','discovery.experiment_trials',
        'discovery.experiment_results','discovery.experiment_events','discovery.rag_reservations','discovery.agent_results','research.decisions','research.trade_outcomes')
    return tuple(c.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in tables)


def record(database,rid):
    c,_,_=database
    pid=paper_store.create(c,PortfolioConfig(name='Navigation fixture',mode='fictional_simulation',contract_version=FICTIONAL,
        starting_capital='100000',simulation_start_at='2025-06-25T10:01:01Z'),uuid4().hex)
    paper_store.admit(c,pid,rid,uuid4().hex)
    oid=paper_store.demo_observation(c,pid,uuid4().hex);paper_store.process(c,oid)
    return pid


def test_missing_outcomes_evaluations_and_legacy_relationship_are_explicit_and_no_mutation(database):
    c,_,_=database;rid=selected(database,case='MISSING');before=counts(c)
    result=history.related_history(c,rid)
    assert result['records'] and result['records'][0]['recommendation_id']==rid
    assert not result['outcomes'] and result['outcome_status']=='unavailable_no_recorded_outcome'
    assert not result['evaluations'] and result['evaluation_status']=='unavailable_no_registered_trial'
    assert result['legacy_replay']==dict(status='unavailable',reason='no_explicit_dataset_relationship')
    assert result==history.related_history(c,rid) and counts(c)==before
    assert result['listing_id']=='SYN-D309-MISSING' and '2025' in result['cutoff_at']


def test_publication_history_only_matches_real_listing_horizon_arm_and_mode(database):
    from stock_discovery_analysis.publication_store import enqueue,run_next,RunRequest
    c,_,_=database;rid=selected(database)
    run=enqueue(c,RunRequest(horizon='swing'),uuid4().hex,'test');assert run_next(c,'test')['status']=='completed'
    r=history.related_history(c,rid,limit=1);assert r['next_cursor'] and len(r['records'])==1
    older=history.related_history(c,rid,limit=1,before=r['next_cursor'])
    assert not {x['recommendation_id'] for x in r['records']} & {x['recommendation_id'] for x in older['records']}
    assert len(older['records'])==1 and not older['next_cursor']
    for row in [*r['records'],*older['records']]:
        a=history.read_artifact(c,row['recommendation_id'])['recommendation']
        assert (a['instrument']['instrument_id'],a['horizon']['profile'],a['cohort']['arm'],a['mode'])==('SYN-D309-READY','swing','quant','synthetic')
    with pytest.raises(ValueError,match='history_cursor_scope'):history.related_history(c,rid,before=selected(database,cohort='quant_rag'))
    with pytest.raises(KeyError):history.related_history(c,'SYN-ALPHA')


def test_pinned_outcome_reveal_is_read_only_and_later_ledger_does_not_rewrite_it(database,monkeypatch):
    c,_,_=database;rid=selected(database);pid=record(database,rid)
    info=history.related_history(c,rid);ref=next(o for o in info['outcomes'] if o['portfolio_id']==pid)
    assert 'realized_pnl' not in str(info) and 'fills' not in str(info)
    before=counts(c);original=history.read_artifact(c,rid)
    with monkeypatch.context() as m:
        m.setattr(g,'evaluate',lambda *a,**k:pytest.fail('Reads must not evaluate'))
        m.setattr(paper_store,'admit',lambda *a,**k:pytest.fail('Reads must not admit'))
        result=history.recorded_outcome(c,pid,rid,ref['sequence'],ref['event_hash'])
        assert counts(c)==before
    assert result['outcome']['recommendation_id']==rid and result['history']
    assert all(h['sequence']<=ref['sequence'] for h in result['history'])
    for _ in range(2):
        oid=paper_store.demo_observation(c,pid,uuid4().hex);paper_store.process(c,oid)
    assert result==history.recorded_outcome(c,pid,rid,ref['sequence'],ref['event_hash'])
    assert original==history.read_artifact(c,rid)
    with pytest.raises(ValueError,match='history_ledger_hash'):history.recorded_outcome(c,pid,rid,ref['sequence'],'0'*64)
    with pytest.raises(KeyError):history.recorded_outcome(c,pid,rid,999999,ref['event_hash'])
    other=selected(database,case='WAITING')
    with pytest.raises(KeyError):history.recorded_outcome(c,pid,other,ref['sequence'],ref['event_hash'])


def test_registered_trial_links_only_exact_decision_and_do_not_open_results(database,monkeypatch):
    c,_,_=database;e,arms,run=fixture_experiment(database);g.register(c,e);t=trial(e,arms,run);g.begin_trial(c,t)
    rid=selected(database);before=counts(c)
    monkeypatch.setattr(g,'evaluate',lambda *a,**k:pytest.fail('No implicit evaluation'))
    r=history.related_history(c,rid)
    link=next(x for x in r['evaluations'] if x['trial_id']==t.trial_id)
    assert (link['experiment_id'],link['phase'],link['status'])==(e.experiment_id,'validation','registered_results_not_opened')
    assert counts(c)==before and c.execute('SELECT 1 FROM discovery.experiment_results WHERE trial_id=%s',(t.trial_id,)).fetchone() is None


@pytest.mark.parametrize('kind',['control','provider','grant'])
def test_cached_history_and_pinned_outcome_reauthorize_and_deny_restricted_sources(database,kind):
    from stock_discovery_analysis.grant_fences import restrict
    c,_,_=database;rid=selected(database,cohort='quant_rag');pid=record(database,rid)
    ref=next(x for x in history.related_history(c,rid)['outcomes'] if x['portfolio_id']==pid)
    with c.transaction(force_rollback=True):
        if kind=='control':c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
        else:
            grant=next(iter(history.read_artifact(c,rid)['permissions'].values()))
            args=dict(kind='grant' if kind=='grant' else 'provider',source_id=SOURCE)
            if kind=='grant':args.update(account_ref=grant['account_ref'],grant_id=grant['grant_id'],grant_version=grant['version'])
            restrict(c,request_id=uuid4(),reason='revoked',**args)
        with pytest.raises(PermissionError):history.related_history(c,rid)
        with pytest.raises(PermissionError):history.recorded_outcome(c,pid,rid,ref['sequence'],ref['event_hash'])


def test_restriction_waits_until_complete_history_read_transaction(database,monkeypatch):
    c,_,url=database;rid=selected(database);locked=Event();release=Event();original=history.validate_order
    pid=record(database,rid)
    def pause(*a):
        original(*a);locked.set();assert release.wait(5)
    monkeypatch.setattr(history,'validate_order',pause)
    def read():
        with psycopg.connect(url,autocommit=True) as other:return history.related_history(other,rid)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(read)
        try:
            assert locked.wait(5)
            with pytest.raises(psycopg.errors.LockNotAvailable):
                with c.transaction():
                    c.execute("SET LOCAL lock_timeout='150ms'")
                    c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
        finally:release.set()
        assert any(o['portfolio_id']==pid for o in future.result(timeout=10)['outcomes'])


def test_final_rights_recheck_and_database_error_roll_back_without_receipts(database,monkeypatch):
    c,_,_=database;rid=selected(database,case='RISK');before=counts(c);original=history.read_artifact;calls=[]
    def expires(*args):
        calls.append(1)
        if len(calls)>2:raise PermissionError('synthetic_expired')
        return original(*args)
    with monkeypatch.context() as m:
        m.setattr(history,'read_artifact',expires)
        with pytest.raises(PermissionError):history.related_history(c,rid,limit=1)
    assert counts(c)==before
    def broken(*args):c.execute('SELECT * FROM public.synthetic_absent_relation')
    with monkeypatch.context() as m:
        m.setattr(history,'read_artifact',broken)
        with pytest.raises(PermissionError,match='^history_access_unavailable$'):history.related_history(c,rid)
    assert c.execute('SELECT 1').fetchone()==(1,) and counts(c)==before


def test_api_auth_pinned_identity_no_store_and_sanitized_denial(database,monkeypatch):
    c,_,_=database;rid=selected(database);pid=record(database,rid)
    monkeypatch.setenv('AUTH_TOKEN','navigation-owner-access-key-at-least32')
    app.dependency_overrides[db]=lambda:c
    try:
        client=TestClient(app);path='/v1/recommendations/'+rid+'/history'
        assert client.get(path).status_code==401
        client.headers['Authorization']='Bearer navigation-owner-access-key-at-least32'
        response=client.get(path);assert response.status_code==200,response.text
        assert response.headers['cache-control']=='no-store'
        ref=next(x for x in response.json()['outcomes'] if x['portfolio_id']==pid);url=ref['url']
        response=client.get(url);assert response.status_code==200,response.text
        assert response.headers['cache-control']=='no-store'
        assert response.json()['sequence']==ref['sequence']
        assert client.get('/v1/paper-portfolio/'+pid+'/outcomes/'+rid+'?sequence=1').status_code==400
        assert client.get(path+'?limit=51').status_code==422
        assert client.get('/v1/recommendations/unknown/history').status_code==404
        with c.transaction(force_rollback=True):
            c.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
            for endpoint in (path,url):
                denied=client.get(endpoint);assert denied.status_code==403
                assert SOURCE not in denied.text and 'outcome' not in denied.json()
    finally:app.dependency_overrides.pop(db,None)


@pytest.mark.parametrize('problem',['expired','missing_permissions','unknown_grant','wrong_account'])
def test_unverifiable_original_permission_snapshot_fails_closed(database,monkeypatch,problem):
    c,_,_=database;rid=selected(database);original=history.read_artifact;before=counts(c)
    def altered(conn,key):
        a=deepcopy(original(conn,key))
        if problem=='missing_permissions':a['permissions']={}
        else:
            for grant in a['permissions'].values():
                if problem=='expired':grant['expires_at']='2021-01-01T00:00:00Z'
                if problem=='unknown_grant':grant['grant_id']='SYN-unregistered-grant'
                if problem=='wrong_account':grant['account_ref']='SYN-other-account'
        return a
    monkeypatch.setattr(history,'read_artifact',altered)
    with pytest.raises((PermissionError,ValueError)):history.related_history(c,rid)
    assert counts(c)==before


def test_mixed_portfolio_dependencies_and_unrelated_changes_are_not_silently_reused(database,monkeypatch):
    c,_,_=database;rid=selected(database);other=selected(database,case='WAITING');pid=record(database,rid)
    paper_store.admit(c,pid,other,uuid4().hex)
    oid=paper_store.demo_observation(c,pid,uuid4().hex);paper_store.process(c,oid)
    ref=next(o for o in history.related_history(c,rid)['outcomes'] if o['portfolio_id']==pid)
    revealed=history.recorded_outcome(c,pid,rid,ref['sequence'],ref['event_hash'])
    assert all(all(change['recommendation_id']==rid for change in h['payload'].get('changes',[])) for h in revealed['history'])
    original=history.read_artifact;before=counts(c)
    def deny(conn,key):
        if key==other:raise PermissionError('synthetic_mixed_dependency_restricted')
        return original(conn,key)
    monkeypatch.setattr(history,'read_artifact',deny)
    with pytest.raises(PermissionError):history.related_history(c,rid)
    with pytest.raises(PermissionError):history.recorded_outcome(c,pid,rid,ref['sequence'],ref['event_hash'])
    assert counts(c)==before
