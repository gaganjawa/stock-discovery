"""Real PostgreSQL: serialized reservations, atomic execution, immutable outcomes."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.research import db as api_db
from stock_discovery_analysis import paper_store as store
from stock_discovery_analysis.paper_contracts import PortfolioConfig,Observation,FICTIONAL,VERSION
from stock_discovery_analysis.paper_reporting import report,cohort_metrics
from stock_discovery_analysis.publication_store import RunRequest,enqueue,run_next,read_artifact
from stock_discovery_analysis.publication_fixtures import SOURCE
from test_rag_research import isolated_url


@pytest.fixture(scope='module')
def database(isolated_url):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        for h in ('swing','short_term','long_term'):
            enqueue(conn,RunRequest(horizon=h),h,'test')
            assert run_next(conn,'test')['status']=='completed'
        yield conn,isolated_url


def cfg(**changes):
    body=dict(name='Fictional test',mode='fictional_simulation',contract_version=FICTIONAL,
        starting_capital='100000',simulation_start_at='2025-06-25T10:01:01Z')
    return PortfolioConfig(**{**body,**changes})


def new(database,**changes):return store.create(database[0],cfg(**changes),uuid4().hex)


def rec(database,horizon='swing',cohort='quant',action='BUY'):
    return database[0].execute('SELECT recommendation_id FROM discovery.recommendations WHERE horizon=%s AND cohort=%s AND payload->>\'action\'=%s ORDER BY (listing_id=\'SYN-D309-READY\') DESC,sort_key LIMIT 1',(horizon,cohort,action)).fetchone()[0]


def admit(database,pid=None,horizon='swing',cohort='quant'):
    pid=pid or new(database);rid=rec(database,horizon,cohort)
    result=store.admit(database[0],pid,rid,uuid4().hex)
    assert result['status']=='admitted',result
    return pid,rid


def observe(database,pid,**changes):
    conn=database[0];policy,last=store.config_state(conn,pid);orders=list(last[1]['orders'].values());bars={}
    for o in orders:
        s=store.next_session(conn,o);terms=o['terms'];price=D(terms['entry_price']) if terms else D(o['mark'])
        bars[o['listing_id']]=dict(dict(listing_id=o['listing_id'],session_open_at=s['opens_at'],session_close_at=s['closes_at'],available_at=s['closes_at'],
            open=str(price),high=str(price*D('1.01')),low=str(price*D('.99')),close=str(price)),**changes)
    at=list(bars.values())[0]['session_close_at']
    body=Observation(contract_version=FICTIONAL,session_close_at=at,observed_at=at,bars=list(bars.values()))
    oid=store.enqueue(conn,pid,body,uuid4().hex);store.process(conn,oid)
    return oid


@pytest.mark.parametrize('horizon',['swing','short_term','long_term'])
def test_horizons_original_shadow_contract_unchanged(database,horizon):
    conn,_=database;rid=rec(database,horizon);before=read_artifact(conn,rid)
    pid,rid=admit(database,horizon=horizon);observe(database,pid)
    data=report(conn,pid);o=data['decisions'][0]
    assert D(data['reserved'])==o['quantity']*D(data['config']['fixed_fee']) and D(data['cash'])<100000 and o['quantity']>0
    assert o['horizon']==horizon and o['forecast']['status']=='provisional'
    assert read_artifact(conn,rid)==before
    assert before['recommendation']['paper_admission']['status']=='blocked'
    assert data['benchmark']['market_return'] is None


def test_forward_portfolio_rejects_mock_and_fictional_observations(database):
    conn,_=database;pid=new(database,mode='forward_paper',contract_version=VERSION,simulation_start_at=None)
    result=store.admit(conn,pid,rec(database),uuid4().hex)
    assert result['status']=='rejected' and result['reason']=='mock_shadow_non_actionable'
    assert D(report(conn,pid)['reserved'])==0
    body=Observation(contract_version=FICTIONAL,session_close_at='2026-10-20T10:00:00Z',observed_at='2026-10-20T10:00:00Z',bars=[])
    with pytest.raises(ValueError,match='forbidden'):store.enqueue(conn,pid,body,'forward')


@pytest.mark.parametrize('action',['WATCH','AVOID','INSUFFICIENT_EVIDENCE'])
def test_all_decisions_retained_without_forced_entry(database,action):
    conn,_=database;pid=new(database);r=store.admit(conn,pid,rec(database,action=action),uuid4().hex)
    assert r['status']=='rejected';data=report(conn,pid)
    assert data['execution_quality']['decisions']==1 and data['execution_quality']['resolved_trades']==0
    assert data['execution_quality']['win_rate'] is None


@pytest.mark.parametrize('changes,reason',[
    ({'starting_capital':'1'},'capital_or_portfolio_risk_limit'),
    ({'per_trade_risk':'.000001'},'capital_or_portfolio_risk_limit'),
    ({'simulation_start_at':'2025-07-01T10:01:01Z'},'recommendation_expired'),
    ({'simulation_start_at':'2025-06-24T10:01:01Z'},'decision_not_available_at_cutoff')])
def test_admission_controls(database,changes,reason):
    pid=new(database,**changes);r=store.admit(database[0],pid,rec(database),uuid4().hex)
    assert r['status']=='rejected' and r['reason']==reason


def test_deterministic_risk_veto_even_when_ai_buy(database,monkeypatch):
    conn,_=database;pid=new(database);original=store.read_artifact
    def blocked(conn,rid):
        from copy import deepcopy
        a=deepcopy(original(conn,rid));a['recommendation']['risk_context']['eligibility']='blocked';a['recommendation']['cohort']['arm']='quant_agent';return a
    monkeypatch.setattr(store,'read_artifact',blocked)
    result=store.admit(conn,pid,rec(database),uuid4().hex)
    assert result['reason']=='deterministic_risk_veto'


def test_duplicate_admissions_and_command_conflict(database):
    conn,_=database;pid=new(database);rid=rec(database);key=uuid4().hex
    a=store.admit(conn,pid,rid,key);assert store.admit(conn,pid,rid,key)==a
    assert store.admit(conn,pid,rid,'other')['reason']=='duplicate_admission'
    with pytest.raises(ValueError,match='idempotency_conflict'):store.admit(conn,pid,rec(database,'long_term'),key)
    assert len(report(conn,pid)['ledger'])==2


def test_concurrent_reservations_shared_cash_and_issuer(database):
    conn,url=database;pid=new(database);ids=[rec(database,h) for h in ('swing','short_term','long_term')]
    def reserve(rid):
        with psycopg.connect(url,autocommit=True) as other:return store.admit(other,pid,rid,rid)
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(reserve,ids))
    _,last=store.config_state(conn,pid);s=last[1]
    assert D(s['reserved'])<=D(s['cash'])
    assert sum(D(o['cap'])*o['remaining'] for o in s['orders'].values())<=D('20000')
    assert any(r['status']=='admitted' for r in results)
    assert len(s['orders'])==3


def test_immutable_every_ledger_and_input_table(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid)
    for table in ('portfolios','ledger','observations','processed'):
        for sql in (f'DELETE FROM paper.{table}',f'UPDATE paper.{table} SET portfolio_id=portfolio_id'):
            with pytest.raises(psycopg.Error):conn.execute(sql)


def test_atomic_processing_retry_and_concurrent_workers(database):
    conn,url=database;pid,rid=admit(database);oid=store.demo_observation(conn,pid,'demo')
    def process(_):
        with psycopg.connect(url,autocommit=True) as c:return store.process(c,oid)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(process,range(2)))
    assert results[0]==results[1]
    assert conn.execute('SELECT count(*) FROM paper.processed WHERE observation_id=%s',(oid,)).fetchone()[0]==1
    assert len(report(conn,pid)['ledger'])==3


def test_rollback_during_execution_preserves_cash_and_receipt(database,monkeypatch):
    conn,_=database;pid,rid=admit(database);oid=store.demo_observation(conn,pid,'rollback');before=store.config_state(conn,pid)[1]
    original=store.append
    def fail(*args):original(*args);raise RuntimeError('injected storage fault')
    with monkeypatch.context() as m:
        m.setattr(store,'append',fail)
        with pytest.raises(RuntimeError):store.process(conn,oid)
    assert store.config_state(conn,pid)[1]==before
    assert not conn.execute('SELECT 1 FROM paper.processed WHERE observation_id=%s',(oid,)).fetchone()
    store.process(conn,oid)


def test_gap_stop_fees_and_ledger_cash_reconcile(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid)
    observe(database,pid,open='90',high='95',low='89',close='92')
    data=report(conn,pid);o=data['decisions'][0]
    assert o['status']=='closed' and o['reason']=='stop_gap' and D(o['realized_pnl'])<0
    assert D(data['cash'])==100000+D(o['realized_pnl'])
    assert data['execution_quality']['win_rate']=='0' and D(data['execution_quality']['profit_factor'])==0
    assert D(data['maximum_drawdown'])>0 and D(o['fees'])>0 and D(o['slippage'])>0
    assert data['by_horizon']['swing']['resolved_trades']==1


def test_ambiguity_never_invents_exit_and_pauses(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid,high='125',low='100')
    data=report(conn,pid);o=data['decisions'][0]
    assert o['status']=='ambiguous' and not any(f['side']=='sell' for f in o['fills'])
    assert data['equity'] is None and data['maximum_drawdown'] is None and data['paused']
    result=store.admit(conn,pid,rec(database,'short_term'),uuid4().hex);assert result['reason']=='portfolio_paused'


def test_missing_session_and_historical_rewrite(database):
    conn,_=database;pid,rid=admit(database)
    body=Observation(contract_version=FICTIONAL,session_close_at='2025-06-27T10:00:00Z',observed_at='2025-06-27T10:00:00Z',bars=[])
    oid=store.enqueue(conn,pid,body,'missing');store.process(conn,oid)
    data=report(conn,pid);assert data['decisions'][0]['reason']=='missing_trading_session'
    assert data['decisions'][0]['forecast']['status']=='unavailable'
    with pytest.raises(ValueError,match='historical_rewrite'):store.enqueue(conn,pid,body,'new')


def test_stale_observation_and_partial_fills(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid,entry_capacity=2)
    data=report(conn,pid);assert data['decisions'][0]['quantity']==2 and D(data['reserved'])>0
    p2,rid=admit(database)
    oid=store.demo_observation(conn,p2,'stale');raw=conn.execute('SELECT payload FROM paper.observations WHERE observation_id=%s',(oid,)).fetchone()[0]
    # Separate portfolio: no editing a sealed observation.
    p3,rid=admit(database);raw['observed_at']='2025-07-10T10:00:00Z'
    oid=store.enqueue(conn,p3,Observation(**raw),'delayed');store.process(conn,oid)
    assert report(conn,p3)['decisions'][0]['reason']=='stale_price'
    store.process(conn,conn.execute('SELECT observation_id FROM paper.observations WHERE portfolio_id=%s',(p2,)).fetchone()[0])


def test_revocation_between_reservation_and_fill_and_read(database):
    conn,_=database;pid,rid=admit(database);oid=store.demo_observation(conn,pid,'revoke')
    conn.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
    try:
        with pytest.raises(PermissionError):report(conn,pid)
        store.process(conn,oid)
        s=store.config_state(conn,pid)[1][1]
        assert s['orders'][rid]['reason']=='source_permission_revoked' and D(s['reserved'])==0 and s['cash']=='100000'
        with pytest.raises(PermissionError):store.admit(conn,new(database),rid,'revoked')
    finally:conn.execute('UPDATE discovery.publication_source_controls SET revoked=false WHERE source_id=%s',(SOURCE,))


def test_auth_api_outcome_and_current_permissions(database,monkeypatch):
    conn,_=database;monkeypatch.setenv('AUTH_TOKEN','paper-owner-key-at-least-thirty-two-characters')
    app.dependency_overrides[api_db]=lambda:conn
    headers={'Authorization':'Bearer paper-owner-key-at-least-thirty-two-characters','Idempotency-Key':uuid4().hex}
    try:
        with TestClient(app) as c:
            assert c.get('/v1/paper-portfolio').status_code==401
            assert c.post('/v1/paper-portfolio',json=cfg().model_dump(mode='json')).status_code==401
            response=c.post('/v1/paper-portfolio',json=cfg().model_dump(mode='json'),headers=headers)
            assert response.status_code==201;pid=response.json()['portfolio_id'];rid=rec(database)
            assert c.post('/v1/paper-portfolio/'+pid+'/admissions',json={'recommendation_id':rid},headers=headers).json()['status']=='admitted'
            assert c.get('/v1/paper-portfolio/'+pid+'/outcomes/'+rid,headers=headers).json()['outcome']['original_decision']=='BUY'
            assert c.post('/v1/paper-portfolio/'+pid+'/admissions/batch',json={'recommendation_ids':[rid]},headers=headers).json()['results'][0]['reason']=='duplicate_admission'
            assert c.post('/v1/paper-portfolio/'+pid+'/fictional-session',json={},headers=headers).status_code==202
            store.run_next(conn)
            assert c.get('/v1/paper-portfolio/'+pid,headers=headers).status_code==200
            conn.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
            assert c.get('/v1/paper-portfolio/'+pid,headers=headers).status_code==403
    finally:
        conn.execute('UPDATE discovery.publication_source_controls SET revoked=false WHERE source_id=%s',(SOURCE,))
        app.dependency_overrides.clear()


def test_late_observation_never_backdates_new_admission(database):
    conn,_=database;pid,rid=admit(database)
    # Completed session arrived after entry expiry but within allowed mark age.
    s=store.next_session(conn,store.config_state(conn,pid)[1][1]['orders'][rid])
    body=Observation(contract_version=FICTIONAL,session_close_at=s['closes_at'],observed_at='2025-06-28T10:00:00Z',bars=[dict(
        listing_id='SYN-D309-READY',session_open_at=s['opens_at'],session_close_at=s['closes_at'],available_at='2025-06-28T10:00:00Z',
        open='115.31',high='116',low='114',close='115.31')])
    oid=store.enqueue(conn,pid,body,'late')
    with pytest.raises(ValueError,match='pending_observations'):store.admit(conn,pid,rec(database,'short_term'),'before')
    store.process(conn,oid)
    result=store.admit(conn,pid,rec(database,'short_term'),'after')
    assert result['reason']=='recommendation_expired'


def test_frozen_ledger_hash_chain_and_provisional_history(database):
    from stock_discovery_contracts.v2 import digest
    conn,_=database;pid,rid=admit(database);observe(database,pid)
    prior='genesis'
    for seq,key,at,kind,payload,state,previous,current in conn.execute('SELECT sequence,event_key,event_at,kind,payload,state,previous_hash,event_hash FROM paper.ledger WHERE portfolio_id=%s ORDER BY sequence',(pid,)):
        assert previous==prior
        assert current==digest(dict(portfolio_id=pid,sequence=seq,event_key=key,kind=kind,at=at.isoformat(),payload=payload,state=state,previous_hash=previous))
        prior=current
    old=conn.execute('SELECT state FROM paper.ledger WHERE portfolio_id=%s AND sequence=3',(pid,)).fetchone()[0]
    observe(database,pid,open='90',high='95',low='89',close='92')
    assert conn.execute('SELECT state FROM paper.ledger WHERE portfolio_id=%s AND sequence=3',(pid,)).fetchone()[0]==old


def test_forecast_maturity_is_separate_from_trade_exit(database):
    conn,_=database;pid,rid=admit(database)
    for _ in range(3):observe(database,pid)
    data=report(conn,pid);o=data['decisions'][0]
    assert o['reason']=='time_exit' and o['status']=='closed'
    assert o['forecast']['status']=='matured' and o['forecast']['return'] is not None
    assert data['execution_quality']['forecast_quality']['matured']==1
    assert D(o['realized_pnl'])<0  # flat execution price still pays fees/slippage


def test_expiry_releases_capital_without_rewriting_buy(database):
    conn,_=database;pid,rid=admit(database)
    for _ in range(2):observe(database,pid,open='100',high='101',low='99',close='100')
    data=report(conn,pid);o=data['decisions'][0]
    assert o['status']=='no_entry' and o['original_decision']=='BUY'
    assert D(data['cash'])==100000 and D(data['reserved'])==0
    assert data['execution_quality']['resolved_trades']==0


def test_observation_corporate_actions_block_instead_of_guessing(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid,corporate_action=True)
    data=report(conn,pid)
    assert data['decisions'][0]['reason']=='unsupported_corporate_action' and data['paused']


def test_batch_rank_and_idempotency_independent_of_submission_order(database):
    conn,_=database;ids=[rec(database,h) for h in ('swing','short_term','long_term')]
    p1=new(database);p2=new(database)
    result=store.admit_batch(conn,p1,ids,'rank')
    assert store.admit_batch(conn,p1,list(reversed(ids)),'rank')==result
    store.admit_batch(conn,p2,list(reversed(ids)),'rank')
    first=store.config_state(conn,p1)[1][1]['orders'];second=store.config_state(conn,p2)[1][1]['orders']
    assert {k:o['admitted_quantity'] for k,o in first.items()}=={k:o['admitted_quantity'] for k,o in second.items()}
    with pytest.raises(ValueError,match='idempotency_conflict'):store.admit_batch(conn,p1,ids[:1],'rank')


def test_opening_risk_recheck_cancels_pending_but_keeps_known_exits(database):
    conn,_=database;pid,rid=admit(database);observe(database,pid,entry_capacity=2)
    before=report(conn,pid);assert before['decisions'][0]['remaining']>0
    # A loss at the open rechecks pending risk using current equity. Extremely
    # small daily limit exercises the gate without using future candle extrema.
    pid2=new(database,daily_loss_limit='.00001');pid2,rid=admit(database,pid2)
    observe(database,pid2,entry_capacity=2)
    observe(database,pid2,open='90',high='125',low='89',close='120')
    data=report(conn,pid2);o=data['decisions'][0]
    assert o['bought']==2 and o['sold']==2 and o['reason']=='stop_gap'
    assert o['remaining']==0 and data['paused']


def test_idempotent_admission_cannot_bypass_permission_revocation(database):
    conn,_=database;pid=new(database);rid=rec(database)
    store.admit(conn,pid,rid,'cached')
    conn.execute('UPDATE discovery.publication_source_controls SET revoked=true WHERE source_id=%s',(SOURCE,))
    try:
        with pytest.raises(PermissionError):store.admit(conn,pid,rid,'cached')
    finally:conn.execute('UPDATE discovery.publication_source_controls SET revoked=false WHERE source_id=%s',(SOURCE,))
