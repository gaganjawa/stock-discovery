"""D3-11 adapters over D3-10 outcomes and the existing flow-neutral evaluator."""
from decimal import Decimal as D
from .paper_contracts import instant as at
from .evaluation import portfolio
from .paper_store import authorize


def pinned_portfolio(conn,arm,cutoff):
    """A mixed portfolio cannot establish the return of one research arm."""
    unavailable=dict(portfolio_return=None,maximum_drawdown=None,turnover=None,exposure=None,concentration=None,
        portfolio_reason='no_pinned_portfolio',cash_benchmark_return=None,exposure_matched_return=None,
        exposure_matched_reason='no_comparable_benchmark_exposure_series')
    if not arm.portfolio_id:return unavailable
    policy=conn.execute('SELECT config FROM paper.portfolios WHERE portfolio_id=%s',(arm.portfolio_id,)).fetchone()[0]
    rows=conn.execute('SELECT event_at,kind,payload,state FROM paper.ledger WHERE portfolio_id=%s AND sequence<=%s ORDER BY sequence',(arm.portfolio_id,arm.ledger_sequence)).fetchall()
    curve=[];last=None
    for event_at,kind,payload,state in rows:
        authorize(conn,state)
        if at(state['available_at'])>at(cutoff):return {**unavailable,'portfolio_reason':'future_ledger_revision'}
        if set(state['orders'])-set(arm.recommendation_ids):return {**unavailable,'portfolio_reason':'portfolio_includes_other_decisions'}
        last=state
        if kind not in ('capital','observation'):continue
        positions=[]
        for o in state['orders'].values():
            if not o['quantity']:continue
            valid=o['status']=='open' and (at(state['asof'])-at(o['mark_at'])).total_seconds()<=policy['mark_max_age_seconds']
            positions.append(dict(quantity=o['quantity'],mark=o['mark'] if valid else None))
        curve.append(dict(at=event_at.isoformat(),cash=state['cash'],positions=positions,
            external_flow=payload.get('external_flow','0') if curve else '0'))
    result=portfolio(curve)
    if result['reason']:return {**unavailable,'portfolio_reason':result['reason']}
    orders=list(last['orders'].values());equity=result['equity'][-1]
    exposure=sum(D(o['quantity'])*D(o['mark']) for o in orders)
    turnover=sum(D(f['price'])*f['quantity'] for o in orders for f in o['fills'])
    mean=sum(result['equity'])/len(result['equity'])
    return {**unavailable,'portfolio_return':str(result['time_weighted_return']),'maximum_drawdown':str(result['maximum_drawdown']),
        'portfolio_reason':None,'return_basis':'full_capital_time_weighted_external_flows_removed',
        'cash_benchmark_return':'0','turnover':str(turnover/mean) if mean else None,
        'turnover_definition':'buy_plus_sell_notional / mean_recorded_session_equity',
        'exposure':str(exposure/equity) if equity else None,
        'concentration':{issuer:str(sum(D(o['quantity'])*D(o['mark']) for o in orders if o['issuer_id']==issuer)/equity) for issuer in {o['issuer_id'] for o in orders}} if equity else None,
        'fees':str(sum(D(o['fees']) for o in orders)),'slippage':str(sum(D(o['slippage']) for o in orders)),
        'curve_intervals':len(curve)-1}


def comparisons(reports):
    """Descriptive deltas retain both denominators; never imply causal alpha."""
    metrics=('win_rate','expectancy_after_costs','portfolio_return','research_cost','latency_ms')
    baseline=reports['quant'];result={}
    for arm in ('quant_rag','quant_agent'):
        other=reports[arm];deltas={}
        for key in metrics:
            left,right=baseline.get(key),other.get(key)
            deltas[key]=dict(baseline=left,challenger=right,delta=str(D(str(right))-D(str(left))) if left is not None and right is not None else None,
                reason='descriptive_only_dependent_samples' if left is not None and right is not None else 'missing_comparable_observations')
        result[arm]=dict(metrics=deltas,baseline_decisions=baseline['decisions'],challenger_decisions=other['decisions'],
            baseline_resolved=baseline['resolved_trades'],challenger_resolved=other['resolved_trades'],established_improvement=False)
    return result
