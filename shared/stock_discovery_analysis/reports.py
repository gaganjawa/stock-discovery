"""Descriptive uncertainty and grouped reports, never signal probabilities."""
from decimal import Decimal as D, ROUND_FLOOR, localcontext
from .evaluation import summarize, portfolio, risk_ratios


def wilson(successes:int,count:int):
    if not 0<=successes<=count: raise ValueError('invalid counts')
    if not count: return {'lower':None,'upper':None,'reason':'no_eligible_observations'}
    z=D('1.96');n=D(count);p=D(successes)/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*((p*(1-p)/n+z*z/(4*n*n)).sqrt())/denominator
    return {'lower':max(D(0),center-half),'upper':min(D(1),center+half),
            'method':'95% Wilson descriptive interval; independence assumption may fail for overlapping trades'}


def validation_report(rows,analyses):
    lookup={a['recommendation']['recommendation_id']:a for a in analyses}
    groups={}
    for row in rows:
        a=lookup[row['id']]; r=a['recommendation']; f=a['indicators']
        regime='unknown'
        if f.get('ema10') is not None and f.get('ema30') is not None:
            regime='ema_uptrend' if D(f['ema10'])>D(f['ema30']) else 'ema_not_uptrend'
        for dimension,label in [('horizon',r['horizon']['profile']),('sector','unclassified_synthetic'),('regime',regime),('strategy',r['strategy']['version'])]:
            groups.setdefault(dimension+':'+label,[]).append(row)
    result={}
    for group,items in groups.items():
        metrics=summarize(items);m=metrics['direction']
        result[group]={'sample_count':len(items),'metrics':metrics,'direction_interval':wilson(int(m['numerator']),m['denominator'])}
    return {'groups':result,'status':'software_validation_only',
            'limitations':['Fictional sector and price history; no market inference','EP-1 real-experiment coverage and policy approval absent','No tuning or promotion based on synthetic outcomes']}


def session_risk(curve,dataset):
    """Expand known idle cash only; never invent a missing position mark."""
    from .replay import dt
    unavailable=lambda reason:dict(intervals=0,sharpe=None,sortino=None,reason=reason,annualized=False)
    if len(curve)<2:return unavailable('insufficient_equity_observations')
    result=portfolio(curve)
    if result['reason']:return unavailable(result['reason'])
    start,end=dt(curve[0]['at']),dt(curve[-1]['at'])
    sessions=[s for s in dataset.calendar.sessions if start<s.closes_at<=end]
    points={dt(p['at']):p for p in curve};marks=[];prior=curve[0];missing=[]
    for s in sessions:
        if s.closes_at in points:prior=points[s.closes_at]
        elif prior['positions']:
            missing.append(s.closes_at.isoformat());continue
        marks.append(dict(at=s.closes_at.isoformat(),cash=prior['cash'],positions=prior['positions'],external_flow=D(0)))
    if missing:return {**unavailable('missing_session_position_marks'),'missing_observations':len(missing)}
    if any(D(p['external_flow']) for p in curve):return unavailable('session_flow_timing_unqualified')
    series=portfolio(marks)
    if series['reason']:return unavailable(series['reason'])
    equity=series['equity']
    if any(v<=0 for v in equity[:-1]):return unavailable('nonpositive_session_capital')
    returns=[b/a-1 for a,b in zip(equity,equity[1:])]
    return {**risk_ratios(returns,risk_free='0'),'reason':None,'missing_observations':0,
        'closing_marks':len(marks),'initial_partial_session_excluded':True,
        'interpretation':'Descriptive fictional close-to-close ratios; no annualization, IID or promotion claim.'}


def synthetic_benchmark(dataset,instrument,start,end,capital,*,knowledge_at=None):
    """Costed fictional buy/hold reference; no arbitrary observed series accepted."""
    from .replay import dt,Costs
    from .calendar import action_crosses_window
    unavailable=lambda reason:dict(status='unavailable',reason=reason,net_return=None,excess_return=None)
    if instrument is None:return unavailable('benchmark_not_selected')
    if instrument not in {i.instrument_id for i in dataset.instruments}:raise ValueError('Unknown synthetic benchmark')
    if dataset.rights_ref!='synthetic-only':return unavailable('benchmark_source_unqualified')
    a,b=dt(start),dt(end)
    sessions=[s for s in dataset.calendar.sessions if a<s.opens_at and s.closes_at<=b]
    if not sessions or sessions[-1].closes_at!=b:return unavailable('benchmark_window_unaligned')
    if dataset.quality(instrument,a,1):return unavailable('benchmark_initial_evidence_unqualified')
    from .universe import universe_asof
    if any(instrument not in universe_asof(dataset.memberships,s.closes_at) for s in sessions):
        return unavailable('benchmark_universe_change_unqualified')
    if knowledge_at is None:return unavailable('benchmark_knowledge_cutoff_missing')
    knowledge=dt(knowledge_at)
    if knowledge<b:return unavailable('benchmark_outcome_immature')
    if action_crosses_window(dataset.actions,instrument,a,b,knowledge):return unavailable('benchmark_actions_unsupported')
    bars={c.starts_at:c for c in dataset.asof(instrument,knowledge)}
    missing=[s for s in sessions if s.opens_at not in bars or bars[s.opens_at].ends_at!=s.closes_at or bars[s.opens_at].volume<=0]
    if missing:return {**unavailable('benchmark_missing_observations'),'missing_observations':len(missing)}
    costs=Costs()
    if not all(costs.effective_from<=t<costs.effective_to for t in (sessions[0].opens_at,sessions[-1].closes_at)):
        return unavailable('benchmark_cost_schedule_unavailable')
    first,last=(bars[s.opens_at] for s in (sessions[0],sessions[-1]))
    entry=first.open+costs.adverse_slippage;exit_price=last.close-costs.adverse_slippage
    if exit_price<=0:return unavailable('benchmark_invalid_exit')
    quantity=int(((capital-costs.brokerage_per_side)/(entry+costs.fees_per_share_side)).to_integral_value(rounding=ROUND_FLOOR))
    if quantity<=0:return unavailable('benchmark_insufficient_cash')
    # Entry sizing uses entry information only. Never resize using future liquidity.
    if any(quantity>D(c.volume)*D('.01') for c in (first,last)):
        return unavailable('benchmark_liquidity_unavailable')
    fee=costs.fee(quantity);cash=capital-quantity*entry-fee
    curve=[dict(at=start,cash=capital,positions=[],external_flow=D(0))]
    for s in sessions:
        bar=bars[s.opens_at];final=s==sessions[-1]
        curve.append(dict(at=s.closes_at.isoformat(),cash=cash+quantity*exit_price-fee if final else cash,
            positions=[] if final else [dict(quantity=quantity,mark=bar.close)],external_flow=D(0)))
    p=portfolio(curve)
    return dict(status='available',reason=None,instrument_id=instrument,version='SYN-buy-hold-net-v1',
        dataset_version=dataset.version,calendar_version=dataset.calendar.version,source_mode='synthetic',
        source_versions=sorted({bars[s.opens_at].provenance.source_version for s in sessions}),
        source_refs=sorted({bars[s.opens_at].provenance.source_ref for s in sessions}),
        price_basis='raw-v1',currency='INR',cost_version=costs.version,fees=2*fee,
        slippage=2*costs.adverse_slippage*quantity,quantity=quantity,observation_count=len(sessions),missing_observations=0,
        start_at=start,end_at=end,knowledge_cutoff_at=knowledge_at,entry_at=first.starts_at.isoformat(),exit_at=last.ends_at.isoformat(),
        net_return=p['time_weighted_return'],maximum_drawdown=p['maximum_drawdown'],curve=curve,
        limitation='Exploratory fictional costed reference, not an approved or exposure-matched real benchmark.')


def performance_report(dataset,records,rows,p,split_audit,benchmark_instrument=None):
    with localcontext() as ctx:
        ctx.prec=34
        return _performance_report(dataset,records,rows,p,split_audit,benchmark_instrument)


def _performance_report(dataset,records,rows,p,split_audit,benchmark_instrument):
    """Additive read-only presentation of existing outcomes; never tunes a strategy."""
    from stock_discovery_contracts.v2 import digest
    from .portfolio import replay_portfolio
    from .strategy import CONFIG_VERSION
    from .dataset import canonical
    import json
    records=sorted(records,key=lambda pair:pair[0]['recommendation']['recommendation_id'])
    rows=sorted(rows,key=lambda row:row['id'])
    reason=p.get('reason')
    if benchmark_instrument and benchmark_instrument not in {i.instrument_id for i in dataset.instruments}:
        raise ValueError('Unknown synthetic benchmark')
    technical=all(a['recommendation']['strategy']['config_version']==CONFIG_VERSION for a,_ in records)
    if not technical:reason='combined_or_unknown_policy_unqualified'
    curve=p.get('curve',[]) if not reason else []
    base=dict(version='synthetic-performance-report-v1',status='available' if curve else 'unavailable',reason=reason or (None if curve else 'no_equity_curve'),
        source_mode='synthetic',strategy=records[0][0]['recommendation']['strategy'] if records else None,
        dataset_version=dataset.version,benchmark_options=[i.instrument_id for i in dataset.instruments],
        decision_ids=sorted(a['recommendation']['recommendation_id'] for a,_ in records),
        outcome_hashes={a['recommendation']['recommendation_id']:digest(json.loads(canonical(o))) if o else None for a,o in sorted(records,key=lambda pair:pair[0]['recommendation']['recommendation_id'])},
        start_at=curve[0]['at'] if curve else None,end_at=curve[-1]['at'] if curve else None,
        decisions=len(records),resolved_trades=sum(r['trade_status']=='closed' for r in rows),
        missing_outcomes=sum(o is None for _,o in records),trade_status_counts=summarize(rows)['trade_status_counts'],
        win_rate=summarize(rows)['net_win'],expectancy_inr=summarize(rows)['net_expectancy_inr'],
        net_return=p.get('time_weighted_return') if technical else None,
        maximum_drawdown=p.get('maximum_drawdown') if technical else None,
        exposure_mark_fraction=p.get('exposure_mark_fraction') if technical else None,
        exposure_definition=p.get('exposure_definition'),curve=curve,
        walk_forward=dict(status='unavailable',reason='registered_walk_forward_folds_and_untouched_evaluation_required',
            governance_path='/v1/experiments',acceptance='unratified_EP1; no promotion'),
        paired_comparison=dict(status='unavailable',eligible_pairs=0,ai_performance=None,
            reason='independently_qualified_historical_AI_pairs_unavailable'),
        limitations=['Fictional development software observations, not real strategy performance.',
            'Selected benchmark is exploratory; no holdout selection, optimization or approval.',
            'Per-session descriptive risk ratios exclude the initial partial session; cash rate/target zero is synthetic.',
            'Partition results are a fixed split audit, not registered walk-forward or independent trials.',
            'M1/M2, policy, publication, admission and trading gates remain blocked.'])
    pnl=[D(r['net']) for r in rows if r['action']=='BUY' and r['entry'] is True and r['trade_status']=='closed' and r['net'] is not None]
    gains=sum((max(D(0),v) for v in pnl),D(0));losses=-sum((min(D(0),v) for v in pnl),D(0))
    base.update(profit_factor=gains/losses if losses else None,
        net_pnl_observations=len(pnl),profit_factor_reason=None if losses else 'no_realized_losses' if pnl else 'no_resolved_trades')
    base['risk']=session_risk(curve,dataset) if curve else dict(sharpe=None,sortino=None,reason=base['reason'],intervals=0)
    knowledge=max((o['evaluated_at'] for _,o in records if o),default=None)
    base['benchmark']=synthetic_benchmark(dataset,benchmark_instrument,curve[0]['at'],curve[-1]['at'],D(100000),knowledge_at=knowledge) if curve else dict(status='unavailable',reason=base['reason'],net_return=None)
    bench=base['benchmark'];bench['excess_return']=base['net_return']-bench['net_return'] if base['net_return'] is not None and bench.get('net_return') is not None else None
    partitions=[]
    for name,window in split_audit.get('windows',{}).items():
        ids=set(window['recommendation_ids']);subset=[(a,o) for a,o in records if a['recommendation']['recommendation_id'] in ids]
        metrics=summarize([r for r in rows if r['id'] in ids]);part=replay_portfolio(subset)
        if not technical:
            for key in ('net_win','net_expectancy_inr'):
                metrics[key]={**metrics[key],'value':None,'reason':'combined_policy_unqualified'}
        partitions.append(dict(name=name,start_at=window['start_at'],end_at=window['end_at'],decisions=len(subset),
            net_return=part['time_weighted_return'] if technical else None,maximum_drawdown=part['maximum_drawdown'] if technical else None,
            reason=part['reason'] if technical else 'combined_policy_unqualified',win_rate=metrics['net_win'],expectancy_inr=metrics['net_expectancy_inr']))
    base['partitions']=partitions;base['split_audit_id']=split_audit.get('audit_id')
    if not technical:
        for metric in ('win_rate','expectancy_inr'):
            base[metric]={**base[metric],'value':None,'reason':'combined_policy_unqualified'}
        base.update(profit_factor=None,profit_factor_reason='combined_policy_unqualified')
    base['report_id']='SYN-PERF-'+digest(json.loads(canonical(base)))
    return base
