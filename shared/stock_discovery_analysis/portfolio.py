"""Predeclared single-slot synthetic portfolio; never sums independent capital."""
from decimal import Decimal as D
from .evaluation import portfolio
from .replay import dt

POLICY='SYN-one-slot-100k-v1'


def replay_portfolio(records):
    """Reserve one slot at signal time; deterministic symbol ordering breaks ties.

    Admission depends on then-current settled cash/risk. Unknown paths invalidate
    the report instead of releasing capital based on a favorable assumption.
    """
    if not records: return {'reason':'no_recommendations','time_weighted_return':None,'maximum_drawdown':None}
    ordered=sorted(records,key=lambda pair:(pair[0]['recommendation']['information_cutoff_at'],pair[0]['recommendation']['instrument']['symbol'],pair[0]['recommendation']['recommendation_id']))
    groups={(a['recommendation']['versions']['dataset'],a['recommendation']['versions']['code'],a['recommendation']['strategy']['version']) for a,_ in ordered}
    if len(groups)!=1: return {'reason':'select_one_dataset_code_strategy_cohort','time_weighted_return':None,'maximum_drawdown':None}
    first=ordered[0][0]['recommendation']['information_cutoff_at']
    curve=[{'at':first,'cash':D(100000),'positions':[],'external_flow':D(0)}]
    cash=D(100000); reserved_until=None; exclusions=[]; admitted=[]; turnover=D(0); exposed=0; marks=0
    for a,out in ordered:
        r=a['recommendation']; rid=r['recommendation_id']; signal=dt(r['information_cutoff_at'])
        if r['action']!='BUY': exclusions.append({'id':rid,'reason':'abstention'}); continue
        if reserved_until and signal<reserved_until:
            exclusions.append({'id':rid,'reason':'single_slot_reserved_at_signal'}); continue
        sizing=a['sizing']
        if D(sizing['entry_cap'])*r['execution']['quantity']+D('1')+D('.10')*r['execution']['quantity']>cash or D(sizing['planned_loss'])>min(D(100000),cash)*D('.0025'):
            exclusions.append({'id':rid,'reason':'current_cash_or_risk_revalidation'}); continue
        if out is None or out['trade']['status'] in ('pending','open','ambiguous','invalid_data'):
            return {'policy':POLICY,'reason':'unresolved_admitted_trade','time_weighted_return':None,'maximum_drawdown':None,'exclusions':exclusions,'unresolved_id':rid}
        t=out['trade']; admitted.append(rid)
        if t['status'] in ('no_entry','cancelled'):
            reserved_until=dt(r['execution']['entry_expires_at']); continue
        shift=cash-D(100000)
        for point in out['equity_curve'][1:]:
            adjusted={**point,'cash':D(point['cash'])+shift}
            if dt(adjusted['at'])<=dt(curve[-1]['at']): raise ValueError('overlapping portfolio marks')
            curve.append(adjusted); marks+=1; exposed+=bool(point['positions'])
        cash+=D(t['net_pnl'])
        reserved_until=dt(t['fills'][-1]['interval_end'])
        turnover+=sum(D(f['price'])*f['quantity'] for f in t['fills'])
    last=max((a['recommendation']['horizon']['forecast_end_at'] or a['recommendation']['information_cutoff_at']) for a,_ in ordered)
    if dt(last)>dt(curve[-1]['at']): curve.append({'at':last,'cash':cash,'positions':[],'external_flow':D(0)})
    return {**portfolio(curve),'policy':POLICY,'curve':curve,'admitted_ids':admitted,'exclusions':exclusions,
            'turnover_notional_inr':turnover,'exposure_mark_fraction':D(exposed)/marks if marks else D(0),
            'exposure_definition':'fraction of recorded trade-session closing marks with a position; not calendar-weighted exposure',
            'benchmark':{'cash_return':D(0),'market_return':None,'reason':'no_permitted_comparable_benchmark'}}
