"""Deterministic long-only fictional execution. Daily candles never establish ordering."""
from copy import deepcopy
from decimal import Decimal as D
from .paper_contracts import instant


def fee(notional, policy):
    return D(policy['fixed_fee']) + notional * D(policy['fee_bps']) / 10000


def entry_cap(terms, policy):
    price = D(terms['entry_price'])
    return price if terms['entry_type'] == 'limit' else price * (1 + D(policy['entry_gap_cap']))


def reservation(order, policy):
    qty = order['remaining']
    amount = D(order['cap']) * qty
    # Worst case one entry fee and one exit fee per share. Exit fees remain
    # reserved while held, including unresolved positions and zero-price gaps.
    return (amount * (1 + D(policy['fee_bps']) / 10000)
            + D(policy['fixed_fee']) * (2*qty + order['quantity']))


def planned_risk(order, policy):
    qty = order['remaining'] + order['quantity']
    return qty * (max(D(0), D(order['cap']) - D(order['terms']['stop_price']) * (1-D(policy['slippage_bps'])/10000))
                  + 2*D(policy['fixed_fee']) + 2*D(order['cap'])*D(policy['fee_bps'])/10000)


def size_order(state, candidate, policy):
    """Largest whole lot, jointly constrained by risk, fees and pending exposure."""
    active = [o for o in state['orders'].values() if o['remaining'] or o['quantity']]
    equity = D(state['cash']) + sum(D(o['mark'])*o['quantity'] for o in active)
    base = min(D(policy['starting_capital']), D(state['period_base']), equity)
    cash = D(state['cash']) - D(state['reserved']) - base*D(policy['cash_reserve_fraction'])
    def exposure(predicate):
        return sum(max(D(o['cap']),D(o['mark']))*(o['remaining']+o['quantity']) for o in active if predicate(o))
    existing_risk = sum(planned_risk(o, policy) for o in active)
    lot = candidate['lot_size']
    def fits(q):
        trial = {**candidate,'remaining':q,'quantity':0}
        notional = D(candidate['cap'])*q
        return (reservation(trial,policy) <= cash and planned_risk(trial,policy) <= base*D(policy['per_trade_risk'])
            and planned_risk(trial,policy)+existing_risk <= base*D(policy['combined_risk'])
            and all(exposure(predicate)+notional <= base*D(policy[key]) for key,predicate in (
                ('issuer_limit',lambda o:o['issuer_id']==candidate['issuer_id']),
                ('sector_limit',lambda o:o['sector']==candidate['sector']),
                ('horizon_limit',lambda o:o['horizon']==candidate['horizon']),('gross_limit',lambda o:True))))
    lo,hi=0,max(0,int(cash/D(candidate['cap'])/lot))
    while lo<hi:
        mid=(lo+hi+1)//2
        if fits(mid*lot):lo=mid
        else:hi=mid-1
    return lo*lot


def step(original, bar, at, policy):
    """Return a new order and signed cash delta. Ambiguous positions stay unresolved."""
    o=deepcopy(original);cash=D(0);terms=o['terms'];start=len(o['fills'])
    if o['status'] in ('ambiguous','unavailable','closed','no_entry','rejected'):return o,cash
    if bar is None or bar.get('corporate_action'):
        o.update(status='unavailable',reason='missing_session' if bar is None else 'unsupported_corporate_action',remaining=0)
        return o,cash
    if (instant(at)-instant(bar['available_at'])).total_seconds()>policy['mark_max_age_seconds']:
        o.update(status='unavailable',reason='stale_price',remaining=0)
        return o,cash
    op,hi,lo,close=(D(bar[k]) for k in ('open','high','low','close'))
    slip=D(policy['slippage_bps'])/10000
    entered=False;entry_at_open=False
    def fill(side,qty,raw,price,reason):
        nonlocal cash
        amount=price*qty;cost=fee(amount,policy)
        delta=-(amount+cost) if side=='buy' else amount-cost
        cash+=delta
        o['fees']=str(D(o['fees'])+cost)
        o['slippage']=str(D(o['slippage'])+abs(price-raw)*qty)
        o['fills'].append(dict(side=side,quantity=qty,raw_price=str(raw),price=str(price),fee=str(cost),
            slippage=str(abs(price-raw)*qty),session_close_at=at,reason=reason))
        if side=='buy':
            o['quantity']+=qty;o['remaining']-=qty
            o['basis']=str(D(o['basis'])+amount+cost);o['entry_cost']=str(D(o['entry_cost'])+amount+cost)
            o['entry_notional']=str(D(o['entry_notional'])+amount)
            o['bought']+=qty
            o['entry_at']=o['entry_at'] or at
        else:
            basis=D(o['basis'])*qty/o['quantity']
            o['realized_pnl']=str(D(o['realized_pnl'])+amount-cost-basis)
            o['basis']=str(D(o['basis'])-basis);o['quantity']-=qty
            o['exit_notional']=str(D(o['exit_notional'])+amount);o['sold']+=qty
            o['exit_at']=at
    # Existing positions: stops/targets are evaluated before adding exposure.
    prior_qty=o['quantity']
    stop=D(terms['stop_price']);target=D(terms['target_price']) if terms['target_price'] else None
    entry=D(terms['entry_price'])
    def exit_signal():
        if op<=stop:return 'stop_gap',op,max(D('0.00000001'),op*(1-slip))
        if target is not None and op>=target:return 'target_gap',op,max(target,op*(1-slip))
        hitstop=lo<=stop;hittarget=target is not None and hi>=target
        if hitstop and hittarget:return 'ambiguous',None,None
        if hitstop:return 'stop',stop,stop*(1-slip)
        if hittarget:return 'target',target,target
        if instant(at)>=instant(terms['time_exit_at']):return 'time_exit',close,close*(1-slip)
        return None,None,None
    signal,raw,price=('pending_exit',op,op*(1-slip)) if o.get('exit_pending') and prior_qty else exit_signal() if prior_qty else (None,None,None)
    if not prior_qty and o['remaining'] and instant(bar['session_open_at'])>=instant(terms['earliest_entry_at']):
        if instant(bar['session_open_at'])>=instant(terms['entry_expires_at']):o['remaining']=0
        elif instant(at)>instant(terms['entry_expires_at']):
            # Cannot prove a daily-candle entry preceded an intraday expiry.
            o.update(status='unavailable',reason='intraday_expiry_unobservable',remaining=0)
            return o,cash
    if o['remaining'] and instant(at)<=instant(terms['entry_expires_at']) and instant(bar['session_open_at'])>=instant(terms['earliest_entry_at']) and signal is None:
        raw_entry=None
        if terms['entry_type']=='buy_stop' and hi>=entry:
            raw_entry=max(op,entry);entry_at_open=op>=entry
        elif terms['entry_type']=='limit' and lo<=entry:
            raw_entry=min(op,entry);entry_at_open=op<=entry
        if raw_entry is not None:
            px=raw_entry*(1+slip)
            if terms['entry_type']=='limit':px=min(entry,px)
            if px<=D(o['cap']):
                capacity=bar.get('entry_capacity')
                q=min(o['remaining'],o['remaining'] if capacity is None else capacity)
                q=q//o['lot_size']*o['lot_size']
                if q:
                    fill('buy',q,raw_entry,px,'entry');entered=True
                    signal,raw,price=exit_signal()
                    if not entry_at_open and signal is not None:
                        signal='ambiguous'  # low/high could have occurred before entry
    if signal=='ambiguous' and o['quantity']:
        o.update(status='ambiguous',reason='daily_bar_sequence_unknown',remaining=0,
            bounds={'stop_price':str(stop*(1-slip)),'target_price':str(target) if target else None})
    elif signal and o['quantity']:
        o['remaining']=0
        capacity=bar.get('exit_capacity')
        q=min(o['quantity'],o['quantity'] if capacity is None else capacity)
        q=q//o['lot_size']*o['lot_size']
        if q:fill('sell',q,raw,price,signal)
        if o['quantity']:
            # A triggered exit persists; next session is an at-open liquidation.
            o['exit_pending']=o['exit_pending'] or signal
            o.update(status='open',reason='partial_exit')
        else:o.update(status='closed',reason=o['exit_pending'] or signal,exit_pending=None)
    elif o['quantity']:o['status']='open'
    if instant(at)>=instant(terms['entry_expires_at']):o['remaining']=0
    if not o['quantity'] and not o['remaining'] and o['status'] not in ('closed','ambiguous','unavailable'):
        o.update(status='no_entry',reason='order_expired')
    o['mark']=str(close);o['mark_at']=at
    if o['quantity'] or prior_qty or entered:o['holding_sessions']+=1
    # Extrema only for fully observed held sessions, excluding exit/ambiguous bars.
    sold=any(f['side']=='sell' for f in o['fills'][start:])
    if o['quantity'] and (not entered or entry_at_open) and not sold and o['status']=='open':
        avg=D(o['entry_notional'])/o['bought']
        o['mae']=str(min(D(o['mae']),lo/avg-1));o['mfe']=str(max(D(o['mfe']),hi/avg-1))
        o['excursion_sessions']+=1
    return o,cash
