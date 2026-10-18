"""Explicit denominators: forecast quality is never a simulated-trade win rate."""
from decimal import Decimal as D
from stock_discovery_contracts.v2 import digest
from .paper_engine import fee, reservation, planned_risk
from .paper_store import config_state, authorize, mark_equity
from .paper_contracts import HORIZONS, instant

LIMITATIONS=[
    'Fictional software simulation only; not approved forward-paper performance.',
    'No benchmark feed: market benchmark return and excess return are unavailable; cash benchmark is zero.',
    'Daily OHLC cannot prove intraday sequence, liquidity, queue priority or exact stop fills.',
    'MAE/MFE cover only completely observed held sessions, excluding exit and ambiguous sessions.',
    'Long-horizon forecasts remain provisional until their own endpoints; no annualization or promotion claim.',
    'Trade averages are per resolved trade, not portfolio returns. Overlapping issuers/cohorts are not independent samples.',
    'Corporate actions require a qualified adapter; flagged actions suspend affected outcomes instead of guessing adjustments.',
    'Sharpe ratio and uncertainty intervals are unavailable: no independent qualified sample or registered experiment.',
]


def cohort_metrics(orders):
    closed=[o for o in orders if o['status']=='closed'];pnl=[D(o['realized_pnl']) for o in closed]
    gains=sum(max(D(0),p) for p in pnl);losses=-sum(min(D(0),p) for p in pnl)
    return dict(decisions=len(orders),admitted=sum(o['admission']=='admitted' for o in orders),resolved_trades=len(closed),
        rejected=sum(o['status']=='rejected' for o in orders),no_entry=sum(o['status']=='no_entry' for o in orders),
        ambiguous=sum(o['status']=='ambiguous' for o in orders),unavailable=sum(o['status']=='unavailable' for o in orders),
        provisional=sum(o['status'] in ('pending','open') for o in orders),
        win_rate=str(D(sum(p>0 for p in pnl))/len(pnl)) if pnl else None,
        average_return=str(sum(D(o['realized_pnl'])/D(o['entry_cost']) for o in closed)/len(closed)) if closed else None,
        profit_factor=str(gains/losses) if losses else None,
        profit_factor_unavailable_reason=None if losses else 'no_realized_losses',
        expectancy_after_costs=str(sum(pnl)/len(pnl)) if pnl else None,
        expectancy_unit='INR_per_resolved_trade',
        forecast_quality=dict(denominator=len(orders),matured=sum(o['forecast']['status']=='matured' for o in orders),
            provisional=sum(o['forecast']['status']=='provisional' for o in orders),
            unavailable=sum(o['forecast']['status']=='unavailable' for o in orders),
            direction_hit_rate=None,reason='four_action_decisions_do_not_define_a_common_direction_forecast'))


def report(conn,pid):
    policy,last=config_state(conn,pid);state=last[1];authorize(conn,state)
    orders=list(state['orders'].values())
    bad=any(o['quantity'] and (o['status'] in ('ambiguous','unavailable') or
        (instant(state['asof'])-instant(o['mark_at'])).total_seconds()>policy['mark_max_age_seconds']) for o in orders)
    positions=[]
    for o in orders:
        if o['quantity']:
            value=D(o['mark'])*o['quantity']
            valid=o['status']=='open' and (instant(state['asof'])-instant(o['mark_at'])).total_seconds()<=policy['mark_max_age_seconds']
            positions.append(dict(recommendation_id=o['recommendation_id'],listing_id=o['listing_id'],horizon=o['horizon'],cohort=o['cohort'],
                quantity=o['quantity'],mark=o['mark'],mark_at=o['mark_at'],value=str(value) if valid else None,
                unrealized_pnl=str(value-D(o['basis'])) if valid else None,
                estimated_liquidation_pnl=str(value*(1-D(policy['slippage_bps'])/10000)-fee(value*(1-D(policy['slippage_bps'])/10000),policy)-D(o['basis'])) if valid else None,
                status=o['status']))
    curve=[];peak=D(0);drawdown=D(0);history_bad=False
    rows=conn.execute('SELECT sequence,event_at,kind,payload,state,event_hash,previous_hash FROM paper.ledger WHERE portfolio_id=%s AND sequence<=%s ORDER BY sequence',(pid,last[0])).fetchall()
    for seq,at,kind,payload,s,eh,ph in rows:
        if kind not in ('capital','observation'):continue
        invalid=any(o['quantity'] and o['status'] in ('ambiguous','unavailable') for o in s['orders'].values())
        history_bad |= invalid
        equity=mark_equity(s);peak=max(peak,equity);drawdown=max(drawdown,1-equity/peak)
        curve.append(dict(at=at.isoformat(),equity=None if invalid else str(equity),external_flow=payload.get('external_flow','0')))
    value=sum(D(p['value']) for p in positions if p['value'] is not None);equity=mark_equity(state)
    fills=[f for o in orders for f in o['fills']];turnover=sum(D(f['price'])*f['quantity'] for f in fills)
    clean_curve=[D(c['equity']) for c in curve if c['equity'] is not None]
    avg=sum(clean_curve)/len(clean_curve)
    def breakdown(field):
        keys=HORIZONS if field=='horizon' else ('quant','quant_rag','quant_agent')
        return {key:{**cohort_metrics([o for o in orders if o[field]==key]),
            'exposure':None if bad else str(sum(D(o['mark'])*o['quantity'] for o in orders if o[field]==key)),
            'reserved':str(sum(reservation(o,policy) for o in orders if o[field]==key))} for key in keys}
    summaries=[{**{k:v for k,v in o.items() if k not in ('calendar','permissions')},
        'outcome_id':'FOUT-'+digest([pid,last[0],o['recommendation_id']]),
        'observation_cutoff_at':state['asof'],'knowledge_cutoff_at':state['available_at'],
        'average_entry_price':str(D(o['entry_notional'])/o['bought']) if o['bought'] else None,
        'average_exit_price':str(D(o['exit_notional'])/o['sold']) if o['sold'] else None,
        'holding_calendar_days':(instant(o['exit_at'] or state['asof'])-instant(o['entry_at'])).total_seconds()/86400 if o['entry_at'] else None,
        'mae':o['mae'] if o['excursion_sessions'] else None,'mfe':o['mfe'] if o['excursion_sessions'] else None,
        'excursion_coverage':'full_held_sessions_only_excludes_intraday_entries_and_exit_sessions'} for o in orders]
    return dict(portfolio_id=pid,config=policy,labels=['MOCK','SHADOW','FICTIONAL SIMULATION','NON-ACTIONABLE'] if policy['mode']=='fictional_simulation' else ['PAPER','ACTIVATION BLOCKED'],
        asof=state['asof'],available_at=state['available_at'],sequence=last[0],cash=state['cash'],reserved=state['reserved'],available_cash=str(D(state['cash'])-D(state['reserved'])),
        policy_cash_reserve=str(min(D(policy['starting_capital']),equity)*D(policy['cash_reserve_fraction'])),
        equity=None if bad else str(equity),exposure=None if bad else str(value/equity),
        issuer_concentration=None if bad else {issuer:str(sum(D(o['mark'])*o['quantity'] for o in orders if o['issuer_id']==issuer)/equity) for issuer in {o['issuer_id'] for o in orders}},
        pending_notional=str(sum(D(o['cap'])*o['remaining'] for o in orders)),
        combined_planned_loss=str(sum(planned_risk(o,policy) for o in orders if o['quantity'] or o['remaining'])),
        sector_concentration=None if bad else {sector:str(sum(D(o['mark'])*o['quantity'] for o in orders if o['sector']==sector)/equity) for sector in {o['sector'] for o in orders}},
        paused=state['paused'],pause_reasons=state['pause_reasons'],positions=positions,decisions=summaries,
        execution_quality=cohort_metrics(orders),by_horizon=breakdown('horizon'),by_cohort=breakdown('cohort'),
        portfolio_return=None if bad else str(equity/D(policy['starting_capital'])-1),
        maximum_drawdown=None if history_bad else str(drawdown),turnover=None if history_bad else str(turnover/avg),
        turnover_notional=str(turnover),turnover_definition='buy_plus_sell_notional / mean_recorded_session_equity',
        fees=str(sum(D(o['fees']) for o in orders)),slippage=str(sum(D(o['slippage']) for o in orders)),
        curve=curve,benchmark=dict(cash_return='0',market_return=None,reason='no_permitted_comparable_benchmark'),
        limitations=LIMITATIONS,valuation_unavailable_reason='unresolved_or_stale_holdings' if bad else None,
        ledger=[dict(sequence=seq,at=at.isoformat(),kind=kind,payload=payload,event_hash=eh,previous_hash=ph) for seq,at,kind,payload,s,eh,ph in rows],
        pending_observations=conn.execute('''SELECT count(*) FROM paper.observations o LEFT JOIN paper.processed p USING(observation_id)
            WHERE o.portfolio_id=%s AND p.observation_id IS NULL''',(pid,)).fetchone()[0])
