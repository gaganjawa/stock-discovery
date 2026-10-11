"""STK-003 linear Decimal sizing; synthetic risk profile only."""
from decimal import Decimal as D, ROUND_FLOOR


def capacity(budget, per_share, fixed=D(0)):
    if per_share<=0 or fixed<0: raise ValueError('invalid cost model')
    return max(0,int(((budget-fixed)/per_share).to_integral_value(rounding=ROUND_FLOOR)))


def sizing(example: dict, *, paused: bool = False, marks_fresh: bool = True) -> dict:
    if paused or not marks_fresh: return {'quantity':0,'reason':'paused_or_stale','entry_cash':D(0),'planned_loss':D(0)}
    s={k:D(v) for k,v in example.items()}
    if any(not v.is_finite() or v<0 for v in s.values()): raise ValueError('invalid risk input')
    if not 0<s['protective_exit']<s['entry']: raise ValueError('invalid protective exit')
    if not 0<s['per_trade_fraction']<=s['combined_fraction']<=1: raise ValueError('risk fractions')
    if not 0<s['instrument_fraction']<=s['sector_fraction']<=s['gross_fraction']<=1: raise ValueError('exposure fractions')
    base=min(s['approved_ceiling'],s['period_base'],s['active_equity'])
    risk=min(base*s['per_trade_fraction'],base*s['combined_fraction']-s['existing_and_pending_risk'])
    variable=s['entry']-s['protective_exit']+s['entry_variable_fee']+s['exit_variable_fee']
    fixed=s['entry_fixed_fee']+s['exit_fixed_fee']
    bounds={'risk_quantity':capacity(risk,variable,fixed),
            'cash_quantity':capacity(s['spendable_cash'],s['entry']+s['entry_variable_fee'],s['entry_fixed_fee'])}
    for name in ('instrument','sector','gross'):
        bounds[name+'_quantity']=capacity(base*s[name+'_fraction']-s[name+'_exposure'],s['entry'])
    q=min(bounds.values())
    return {**bounds,'quantity':q,'entry_cash':q*(s['entry']+s['entry_variable_fee'])+(s['entry_fixed_fee'] if q else 0),
            'planned_loss':q*variable+(fixed if q else 0)}


def demo_profile(entry: D, stop: D) -> dict:
    return dict(approved_ceiling='100000',period_base='100000',active_equity='100000',
        per_trade_fraction='.0025',combined_fraction='.005',existing_and_pending_risk='0',spendable_cash='100000',
        entry=str(entry),protective_exit=str(stop),entry_variable_fee='.10',exit_variable_fee='.10',
        entry_fixed_fee='1',exit_fixed_fee='1',instrument_fraction='.10',sector_fraction='.25',gross_fraction='.80',
        instrument_exposure='0',sector_exposure='0',gross_exposure='0')
