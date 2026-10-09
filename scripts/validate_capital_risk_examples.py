#!/usr/bin/env python3
"""STK-003 linear synthetic examples only; not a production sizing engine."""
import copy
from decimal import Decimal as D, ROUND_FLOOR
from validate_contract_examples import ROOT, money, parse, require


def capacity(budget, per_share, fixed=D(0)):
    require(per_share > 0 and fixed >= 0, 'invalid cost model')
    return max(0, int(((budget-fixed)/per_share).to_integral_value(rounding=ROUND_FLOOR)))


def sizing(example):
    s = {k: money(v) for k, v in example.items()}
    require(all(v >= 0 for v in s.values()), 'negative risk input')
    require(0 < s['protective_exit'] < s['entry'], 'invalid protective exit')
    require(0 < s['per_trade_fraction'] <= s['combined_fraction'] <= 1, 'risk fractions')
    require(0 < s['instrument_fraction'] <= s['sector_fraction'] <= s['gross_fraction'] <= 1, 'exposure fractions')
    base = min(s['approved_ceiling'], s['period_base'], s['active_equity'])
    risk = min(base*s['per_trade_fraction'], base*s['combined_fraction']-s['existing_and_pending_risk'])
    variable = s['entry']-s['protective_exit']+s['entry_variable_fee']+s['exit_variable_fee']
    fixed = s['entry_fixed_fee']+s['exit_fixed_fee']
    bounds = dict(risk_quantity=capacity(risk, variable, fixed), cash_quantity=capacity(s['spendable_cash'],s['entry']+s['entry_variable_fee'],s['entry_fixed_fee']))
    for name in ('instrument','sector','gross'):
        bounds[name+'_quantity'] = capacity(base*s[name+'_fraction']-s[name+'_exposure'],s['entry'])
    q = min(bounds.values())
    return {**bounds,'quantity':q,'entry_cash':q*(s['entry']+s['entry_variable_fee'])+(s['entry_fixed_fee'] if q else 0),'planned_loss':q*variable+(fixed if q else 0)}


def loss_state(opening, equity, flows, base, fraction, already_paused=False):
    opening,equity,flows,base,fraction=map(money,(opening,equity,flows,base,fraction))
    require(base > 0 and 0 < fraction <= 1, 'invalid loss limit')
    pnl = equity-opening-flows
    loss = max(D(0),-pnl)
    breached = loss >= base*fraction
    return pnl,loss,breached,already_paused or breached


def holding_sale(quantity, held, reserved):
    require(all(type(v) is int and v >= 0 for v in (quantity,held,reserved)), 'invalid holding quantities')
    require(0 < quantity <= held-reserved, 'sale exceeds available holding; short disabled')
    return 'CLOSE_LONG' if quantity == held-reserved else 'REDUCE_LONG'


def main():
    f = parse((ROOT/'capital-risk.synthetic.json').read_text())
    require(f['synthetic'] and not f['live_enabled'] and f['approval_state']=='synthetic_only','fixture cannot activate live risk')
    expected=f['expected']; s=f['sizing']
    require(sum(money(c['posted']) for c in f['contributions'])==money(expected['posted_contributions']),'skipped contribution must not be imputed')
    result=sizing(s)
    for k,v in result.items():
        require(v==(expected[k] if isinstance(expected[k],int) else money(expected[k])),'hand-worked '+k)
    no_cash=copy.deepcopy(s);no_cash['spendable_cash']='0'
    require(sizing(no_cash)['quantity']==0 and sizing(no_cash)['planned_loss']==0 and sizing(no_cash)['entry_cash']==0,'no trade, no fees')
    exhausted=copy.deepcopy(s);exhausted['existing_and_pending_risk']='600'
    require(sizing(exhausted)['quantity']==0,'exhausted combined risk')
    invalid=copy.deepcopy(s);invalid['protective_exit']='100'
    try:sizing(invalid)
    except ValueError:pass
    else:raise ValueError('invalid stop accepted')
    lowered=copy.deepcopy(s);lowered['active_equity']='50000'
    require(sizing(lowered)['quantity']==0,'losses reduce effective capacity')
    deposited=copy.deepcopy(s);deposited['active_equity']='150000'
    require(sizing(deposited)==result,'deposit cannot increase approved risk base')
    m=f['monthly_loss'];paused=False
    for o in m['observations']:
        pnl,loss,breached,paused=loss_state(m['opening_equity'],o['equity'],o['net_flows'],m['frozen_base'],m['limit_fraction'],paused)
        require((pnl,loss,breached,paused)==(D('-1200'),D('1200'),True,True),'deposit/withdrawal loss accounting')
    require(loss_state('100000','99000','0','100000','.01')[2] is True,'loss equality breaches')
    require(loss_state('100000','99500','0','100000','.01',True)[3] is True,'pause latches after recovery')
    require(holding_sale(1,1,0)=='CLOSE_LONG' and holding_sale(2,3,1)=='CLOSE_LONG' and holding_sale(1,3,1)=='REDUCE_LONG','holding sale semantics')
    for args in ((2,1,0),(2,2,1),(1,0,0)):
        try:holding_sale(*args)
        except ValueError:pass
        else:raise ValueError('oversale accepted')
    print('PASS: STK-003 contribution, sizing, exposure, fees, loss-flow, pause and holding-sale examples.')


if __name__=='__main__':main()
