"""Append-only portfolio accounting with one PostgreSQL lock per portfolio.

All mutations, cash movements and processed receipts commit together. No real
source adapter or approval grant is installed; forward admission fails closed.
"""
from copy import deepcopy
from decimal import Decimal as D
from uuid import uuid4
import os
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import digest
from .paper_contracts import PortfolioConfig, Observation, FICTIONAL, VERSION, instant, HORIZONS
from .paper_engine import entry_cap, reservation, size_order, step, planned_risk
from .publication_store import read_artifact, now
from .publication import manifest, reproduce_quant

ACTIVE=('pending','open')


def config_state(conn,pid,lock=False):
    row=conn.execute('SELECT config FROM paper.portfolios WHERE portfolio_id=%s'+(' FOR UPDATE' if lock else ''),(pid,)).fetchone()
    if row is None:raise KeyError('portfolio_not_found')
    last=conn.execute('SELECT sequence,state,event_hash FROM paper.ledger WHERE portfolio_id=%s ORDER BY sequence DESC LIMIT 1',(pid,)).fetchone()
    return row[0],last


def append(conn,pid,key,kind,at,payload,state,last):
    state=manifest(state);payload=manifest({**payload,'recorded_at':now(),'code_version':os.getenv('CODE_VERSION','local-unversioned')})
    at=instant(at).isoformat()
    seq=last[0]+1 if last else 1;prev=last[2] if last else 'genesis'
    hashed=digest(dict(portfolio_id=pid,sequence=seq,event_key=key,kind=kind,at=at,payload=payload,state=state,previous_hash=prev))
    conn.execute('INSERT INTO paper.ledger VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                 (pid,seq,key,at,kind,Jsonb(payload),Jsonb(state),prev,hashed))
    return dict(portfolio_id=pid,sequence=seq,kind=kind,**payload)


def create(conn,body:PortfolioConfig,key):
    policy=body.model_dump(mode='json')
    with conn.transaction():
        pid='PAPER-'+uuid4().hex
        row=conn.execute('INSERT INTO paper.portfolios VALUES (%s,%s,%s,now()) ON CONFLICT(request_key) DO NOTHING RETURNING portfolio_id',
                         (pid,key,Jsonb(policy))).fetchone()
        if row is None:
            old=conn.execute('SELECT portfolio_id,config FROM paper.portfolios WHERE request_key=%s',(key,)).fetchone()
            if old[1]!=policy:raise ValueError('idempotency_conflict')
            return old[0]
        at=body.simulation_start_at or now()
        state=dict(cash=str(body.starting_capital),reserved='0',orders={},asof=at,paused=False,pause_reasons=[],
                   available_at=at,period_base=str(body.starting_capital),month=instant(at).strftime('%Y-%m'),month_base=str(body.starting_capital))
        append(conn,pid,'capital','capital',at,dict(external_flow=str(body.starting_capital),engine_version=VERSION),state,None)
        return pid


def authorize(conn,state):
    # Recheck current grants even for stored portfolio reports, not just entry.
    for rid in state['orders']:read_artifact(conn,rid)


def admit(conn,pid,rid,key):
    with conn.transaction():
        policy,last=config_state(conn,pid,True);state=deepcopy(last[1])
        previous=conn.execute('SELECT payload FROM paper.ledger WHERE portfolio_id=%s AND event_key=%s',(pid,'admit:'+key)).fetchone()
        if previous:
            if previous[0]['recommendation_id']!=rid:raise ValueError('idempotency_conflict')
            read_artifact(conn,rid)
            return previous[0]
        if rid in state['orders']:return dict(recommendation_id=rid,status=state['orders'][rid]['admission'],reason='duplicate_admission')
        if conn.execute('''SELECT 1 FROM paper.observations o LEFT JOIN paper.processed p USING(observation_id) WHERE o.portfolio_id=%s AND p.observation_id IS NULL''',(pid,)).fetchone():raise ValueError('pending_observations_must_settle_first')
        if len(state['orders'])>=100:raise ValueError('portfolio_decision_capacity_100')
        # Serialize permission revocation against the complete reservation commit.
        conn.execute('SELECT source_id FROM discovery.publication_source_controls ORDER BY source_id FOR SHARE').fetchall()
        a=read_artifact(conn,rid);r=a['recommendation'];at=state['available_at'] if policy['mode']=='fictional_simulation' else now()
        reason=None
        if policy['mode']=='forward_paper':
            reason='mock_shadow_non_actionable' if r['synthetic'] or r['cohort']['shadow'] or r['availability_simulated'] else 'forward_approvals_unconfigured'
        elif r['mode']!='synthetic' or not r['synthetic'] or a['policy_manifest']['status']!='fixture':reason='fictional_contract_only'
        elif state['paused']:reason='portfolio_paused'
        elif r['action']!='BUY':reason='decision_'+r['action'].lower()
        elif r['risk_context']['eligibility']!='eligible':reason='deterministic_risk_veto'
        elif instant(r['decision_available_at'])>instant(at) or instant(r['information_cutoff_at'])>instant(at):reason='decision_not_available_at_cutoff'
        elif instant(r['execution']['entry_expires_at'])<=instant(at):reason='recommendation_expired'
        elif (instant(at)-instant(a['input_manifest']['bars'][-1]['ends_at'])).total_seconds()>policy['mark_max_age_seconds']:reason='stale_recommendation_prices'
        elif any(o['quantity'] and (instant(at)-instant(o['mark_at'])).total_seconds()>policy['mark_max_age_seconds'] for o in state['orders'].values()):reason='stale_portfolio_marks'
        if reason is None:
            reproduce_quant(a)  # The same pinned deterministic gates, never an AI score.
        sector=a['input_manifest'].get('sector')
        if reason is None and not sector:reason='unknown_sector'
        terms=r['execution']
        order=dict(recommendation_id=rid,original_decision=r['action'],horizon=r['horizon']['profile'],cohort=r['cohort']['arm'],
            listing_id=r['instrument']['instrument_id'],issuer_id=r['instrument']['issuer_id'],sector=sector,
            lot_size=r['instrument']['lot_size'],terms=terms,cap=str(min(entry_cap(terms,policy),D(a['quantitative']['entry_terms'].get('cap',str(entry_cap(terms,policy)))))) if terms else '0',
            quantity=0,remaining=0,admitted_quantity=0,status='rejected',admission='rejected',reason=reason,
            basis='0',entry_cost='0',entry_notional='0',exit_notional='0',bought=0,sold=0,
            fees='0',slippage='0',realized_pnl='0',fills=[],entry_at=None,exit_at=None,exit_pending=None,
            holding_sessions=0,mae='0',mfe='0',excursion_sessions=0,
            mark=a['input_manifest']['bars'][-1]['close'],mark_at=r['information_cutoff_at'],
            decision_hash=digest(r),snapshot_id=r['snapshot_id'],policy_refs=r['policy_refs'],versions=r['versions'],
            information_cutoff_at=r['information_cutoff_at'],admitted_at=at,
            calendar_ref=r['horizon']['calendar_ref'],last_session_at=at,
            forecast_end_at=r['horizon']['holding_end_at'],forecast_reference_price=a['input_manifest']['bars'][-1]['close'],
            forecast={'status':'provisional','return':None,'reason':'endpoint_not_mature'},
            permissions=a['permissions'],simulation_contract=policy['contract_version'])
        if reason is None:
            qty=size_order(state,order,policy)
            if not qty:reason='capital_or_portfolio_risk_limit'
            else:order.update(quantity=0,remaining=qty,admitted_quantity=qty,status='pending',admission='admitted',reason='fictional_reservation')
        if reason:order['reason']=reason
        state['orders'][rid]=order
        state['reserved']=str(sum(reservation(o,policy) for o in state['orders'].values()))
        payload=dict(recommendation_id=rid,status=order['admission'],reason=order['reason'],quantity=order['admitted_quantity'],
                     original_recommendation=r,contract=policy['contract_version'],risk_policy=policy)
        append(conn,pid,'admit:'+key,'admission',at,payload,state,last)
        return conn.execute('SELECT payload FROM paper.ledger WHERE portfolio_id=%s AND event_key=%s',(pid,'admit:'+key)).fetchone()[0]


def enqueue(conn,pid,body:Observation,key):
    with conn.transaction():
        policy,last=config_state(conn,pid,True)
        if policy['mode']!='fictional_simulation':raise ValueError('fictional_observations_forbidden_in_forward_paper')
        authorize(conn,last[1]);payload=body.model_dump(mode='json')
        existing=conn.execute('SELECT observation_id,payload FROM paper.observations WHERE portfolio_id=%s AND request_key=%s',(pid,key)).fetchone()
        if existing:
            if existing[1]!=payload:raise ValueError('idempotency_conflict')
            return existing[0]
        if instant(body.observed_at)<instant(last[1]['available_at']):raise ValueError('observation_availability_cannot_go_backwards')
        if instant(body.session_close_at)<=instant(last[1]['asof']):raise ValueError('historical_rewrite_forbidden')
        queued=conn.execute('SELECT payload FROM paper.observations WHERE portfolio_id=%s ORDER BY created_at DESC LIMIT 1',(pid,)).fetchone()
        if queued and (instant(body.session_close_at)<=instant(queued[0]['session_close_at']) or instant(body.observed_at)<instant(queued[0]['observed_at'])):raise ValueError('observations_must_be_chronological')
        if not last[1]['orders']:raise ValueError('no_tracked_decisions')
        if any(b.listing_id not in {o['listing_id'] for o in last[1]['orders'].values()} for b in body.bars):raise ValueError('untracked_listing')
        oid='OBS-'+uuid4().hex
        conn.execute('INSERT INTO paper.observations(observation_id,portfolio_id,request_key,payload) VALUES (%s,%s,%s,%s)',(oid,pid,key,Jsonb(payload)))
        return oid


def next_session(conn,order):
    # The calendar is already immutable in D3-09. Do not duplicate six years of
    # sessions into every cash-ledger snapshot.
    sessions=conn.execute("SELECT artifact->'input_manifest'->'calendar'->'sessions' FROM discovery.recommendations WHERE recommendation_id=%s",(order['recommendation_id'],)).fetchone()[0]
    return next((s for s in sessions if instant(s['closes_at'])>instant(order['last_session_at'])),None)


def mark_equity(state):
    return D(state['cash'])+sum(D(o['mark'])*o['quantity'] for o in state['orders'].values())


def process(conn,oid):
    with conn.transaction():
        row=conn.execute('SELECT portfolio_id,payload FROM paper.observations WHERE observation_id=%s',(oid,)).fetchone()
        if row is None:raise KeyError('observation_not_found')
        pid,batch=row;policy,last=config_state(conn,pid,True)
        done=conn.execute('SELECT sequence FROM paper.processed WHERE observation_id=%s',(oid,)).fetchone()
        if done:return dict(status='completed',portfolio_id=pid,sequence=done[0])
        first=conn.execute('''SELECT o.observation_id FROM paper.observations o LEFT JOIN paper.processed p USING(observation_id)
            WHERE o.portfolio_id=%s AND p.observation_id IS NULL ORDER BY o.created_at,o.observation_id LIMIT 1''',(pid,)).fetchone()
        if first[0]!=oid:raise ValueError('observation_out_of_order')
        conn.execute('SELECT source_id FROM discovery.publication_source_controls ORDER BY source_id FOR SHARE').fetchall()
        state=deepcopy(last[1]);at=batch['session_close_at'];before=mark_equity(state)
        bars={b['listing_id']:b for b in batch['bars']};changes=[]
        # Entry gates use only opening marks, never this session's high/low/close.
        # A prior latched pause also cancels already-reserved unfilled entries.
        opened=[{**o,'mark':bars[o['listing_id']]['open']} if o['listing_id'] in bars else o for o in state['orders'].values()]
        opening_equity=D(state['cash'])+sum(D(o['mark'])*o['quantity'] for o in opened)
        base=min(D(policy['starting_capital']),D(state['period_base']),opening_equity)
        pending=any(o['remaining'] for o in opened)
        def exposure(items):return sum(D(o['mark'])*o['quantity']+D(o['cap'])*o['remaining'] for o in items)
        risk_breach=(sum(planned_risk(o,policy) for o in opened if o['terms'])>base*D(policy['combined_risk'])
            or any(o['remaining'] and planned_risk(o,policy)>base*D(policy['per_trade_risk']) for o in opened)
            or exposure(opened)>base*D(policy['gross_limit'])
            or any(exposure([o for o in opened if o[field]==key])>base*D(policy[limit])
                for field,limit in (('issuer_id','issuer_limit'),('sector','sector_limit'),('horizon','horizon_limit'))
                for key in {o[field] for o in opened}))
        opening_loss=(opening_equity<before*(1-D(policy['daily_loss_limit'])) or
            opening_equity<D(state['month_base'])*(1-D(policy['monthly_loss_limit'])))
        block_entries=state['paused'] or (pending and (risk_breach or opening_loss))
        if block_entries:
            state['paused']=True
            state['pause_reasons']=sorted(set(state['pause_reasons']+['entry_risk_recheck']))

        for rid,order in state['orders'].items():
            bar=bars.get(order['listing_id']);expected=next_session(conn,order);why=None
            try:read_artifact(conn,rid)
            except PermissionError:why='source_permission_revoked'
            if not expected or instant(expected['closes_at'])!=instant(at):why=why or 'missing_trading_session'
            if bar and expected and instant(bar['session_open_at'])!=instant(expected['opens_at']):why=why or 'session_clock_mismatch'
            if bar and (instant(batch['observed_at'])-instant(bar['session_close_at'])).total_seconds()>policy['mark_max_age_seconds']:why=why or 'stale_price'
            if instant(at)<=instant(order['information_cutoff_at']):why=why or 'historical_cutoff_violation'
            if bar and bar.get('corporate_action'):why=why or 'unsupported_corporate_action'
            if order['status'] in ACTIVE:
                if block_entries and order['remaining']:
                    order={**order,'remaining':0}
                    if not order['quantity']:order.update(status='no_entry',reason='portfolio_paused_before_entry')
                if why:
                    updated={**order,'status':'unavailable','reason':why,'remaining':0};delta=D(0)
                else:updated,delta=step(order,bar,at,policy)
                state['orders'][rid]=updated;state['cash']=str(D(state['cash'])+delta)
                changes.append(dict(recommendation_id=rid,cash_delta=str(delta),status=updated['status'],reason=updated['reason'],
                                    fills=updated['fills'][len(order['fills']):]))
                if updated['status'] in ('ambiguous','unavailable'):
                    state['paused']=True;state['pause_reasons']=sorted(set(state['pause_reasons']+[updated['reason']]))
            updated=state['orders'][rid]
            if updated['forecast']['status']=='provisional':
                if why or not bar:updated['forecast']={'status':'unavailable','return':None,'reason':why or 'missing_session'}
                elif instant(at)>=instant(updated['forecast_end_at']):
                    updated['forecast']={'status':'matured','return':str(D(bar['close'])/D(updated['forecast_reference_price'])-1),
                        'reason':'endpoint_price_return_not_trade_pnl','observed_at':at}
            updated['last_session_at']=at
        state['reserved']=str(sum(reservation(o,policy) for o in state['orders'].values()))
        after=mark_equity(state);month=instant(at).strftime('%Y-%m')
        if state['month']!=month:state.update(month=month,month_base=str(before),period_base=str(min(D(policy['starting_capital']),before)))
        if after<before*(1-D(policy['daily_loss_limit'])) or after<D(state['month_base'])*(1-D(policy['monthly_loss_limit'])):
            state['paused']=True;state['pause_reasons']=sorted(set(state['pause_reasons']+['portfolio_loss_limit']))
        state['asof']=at;state['available_at']=batch['observed_at']
        event=append(conn,pid,'observe:'+oid,'observation',at,dict(observation_id=oid,observation_hash=digest(batch),changes=changes,
            engine_version=VERSION,external_flow='0'),state,last)
        conn.execute('INSERT INTO paper.processed VALUES (%s,%s,%s)',(oid,pid,event['sequence']))
        return dict(status='completed',portfolio_id=pid,sequence=event['sequence'])


def run_next(conn):
    # Multiple workers may select the same inbox item; portfolio lock + receipt
    # makes its processing exactly once without stranded leases.
    row=conn.execute('''SELECT o.observation_id FROM paper.observations o LEFT JOIN paper.processed p USING(observation_id)
        WHERE p.observation_id IS NULL ORDER BY o.created_at,o.observation_id LIMIT 1''').fetchone()
    return process(conn,row[0]) if row else None


def demo_observation(conn,pid,key):
    """Pinned fictional allocation scenario. Never reads market data or future prices."""
    with conn.transaction():
        policy,last=config_state(conn,pid,True);state=last[1]
        existing=conn.execute('SELECT observation_id FROM paper.observations WHERE portfolio_id=%s AND request_key=%s',(pid,key)).fetchone()
        if existing:return existing[0]
        if conn.execute('''SELECT 1 FROM paper.observations o LEFT JOIN paper.processed p USING(observation_id)
            WHERE o.portfolio_id=%s AND p.observation_id IS NULL''',(pid,)).fetchone():raise ValueError('observation_already_queued')
        sessions=[next_session(conn,o) for o in state['orders'].values()]
        if not sessions or any(s is None for s in sessions):raise ValueError('calendar_unavailable')
        at=min(s['closes_at'] for s in sessions);bars={}
        for o,s in zip(state['orders'].values(),sessions):
            # Values based only on frozen entry/reference price. Same listing uses
            # one price path across cohorts/horizons, not a tailored winning path.
            reference=D(o['forecast_reference_price'])
            bars[o['listing_id']]=dict(listing_id=o['listing_id'],session_open_at=s['opens_at'],session_close_at=at,
                available_at=at,open=str(reference),high=str(reference*D('1.015')),low=str(reference*D('.985')),close=str(reference))
        return enqueue(conn,pid,Observation(contract_version=FICTIONAL,session_close_at=at,observed_at=at,bars=list(bars.values())),key)


def admit_batch(conn,pid,ids,key):
    """One locked candidate set in frozen D3-09 rank order; never an AI score."""
    with conn.transaction():
        policy,last=config_state(conn,pid,True)
        identity=digest(sorted(ids))
        old=conn.execute('SELECT payload FROM paper.ledger WHERE portfolio_id=%s AND event_key=%s',(pid,'batch:'+key)).fetchone()
        if old:
            if old[0]['request_hash']!=identity:raise ValueError('idempotency_conflict')
            authorize(conn,last[1])
            return old[0]
        artifacts=[read_artifact(conn,rid) for rid in ids]
        ranked=sorted(artifacts,key=lambda a:(a['ranking']['action_tier'],-D(a['ranking']['quant_score']),
            a['ranking']['listing_id'],a['recommendation']['horizon']['profile'],a['recommendation']['recommendation_id']))
        results=[admit(conn,pid,a['recommendation']['recommendation_id'],'batch-'+digest([key,a['recommendation']['recommendation_id']])) for a in ranked]
        _,last=config_state(conn,pid)
        payload=dict(request_hash=identity,rank_policy='frozen_action_quant_listing_horizon_id_v1',
            results=[{k:r[k] for k in ('recommendation_id','status','reason')} for r in results])
        append(conn,pid,'batch:'+key,'admission_batch',last[1]['available_at'],payload,last[1],last)
        return conn.execute('SELECT payload FROM paper.ledger WHERE portfolio_id=%s AND event_key=%s',(pid,'batch:'+key)).fetchone()[0]
