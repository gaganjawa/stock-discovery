"""STK-002 metric definitions reused verbatim; runtime helpers below."""
from collections import Counter
from decimal import Decimal as D, localcontext
from datetime import datetime

def require(value,message):
    if not value: raise ValueError(message)

def money(value):
    v=D(value)
    require(v.is_finite(),'nonfinite money')
    return v

def stamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(t.tzinfo is not None,'timezone required')
    return t

def index(rows,key):
    result={r[key]:r for r in rows}
    require(len(result)==len(rows),'duplicate identities')
    return result

def metric(total, count):
    return {'numerator': total, 'denominator': count,
            'value': total / D(count) if count else None,
            'reason': None if count else 'no_eligible_observations'}


def rate(labels):
    known = [v for v in labels if v is not None]
    require(all(type(v) is bool for v in known), 'labels must be boolean or null')
    return metric(D(sum(known)), len(known))


def direction(reference, endpoint, prediction):
    require(prediction in ('up', 'down', 'flat'), 'unknown direction')
    if endpoint is None:
        return None
    reference, endpoint = money(reference), money(endpoint)
    require(reference > 0 and endpoint > 0, 'positive forecast prices')
    actual = 'up' if endpoint > reference else 'down' if endpoint < reference else 'flat'
    return actual == prediction


def target_touch(observations, target, orientation, start, end, complete, matured):
    """Prove a touch, never barrier ordering. Completeness is an explicit input."""
    if not matured:
        return None
    require(orientation in ('up', 'down'), 'target orientation')
    start, end, level = stamp(start), stamp(end), money(target)
    require(start < end and level > 0, 'target definition')
    straddles = False
    for o in observations:
        if o['kind'] == 'point':
            if not start < stamp(o['at']) <= end:
                continue
            price = money(o['price'])
        else:
            a, b = stamp(o['start_at']), stamp(o['end_at'])
            if b <= start or a > end:
                continue
            if a <= start or b > end:
                straddles = True
                continue
            price = money(o['high' if orientation == 'up' else 'low'])
        if (orientation == 'up' and price >= level) or (orientation == 'down' and price <= level):
            return True
    return False if complete and not straddles and observations else None


def round_trip(entry, exit_price, quantity, entry_fees, exit_fees):
    e, x, ce, cx = map(money, (entry, exit_price, entry_fees, exit_fees))
    require(e > 0 and x >= 0 and type(quantity) is int and quantity > 0 and ce >= 0 and cx >= 0,
            'invalid cash inputs')
    gross = D(quantity) * (x - e)
    invested = D(quantity) * e + ce
    net = gross - ce - cx
    return {'gross': gross, 'net': net, 'invested': invested, 'return': net / invested}


def summarize(rows):
    """Rows are individually classified evaluation inputs; no fill simulation."""
    index(rows, 'id')
    buyers = [r for r in rows if r['action'] == 'BUY']
    direction_labels = [r['direction'] if r['forecast_status'] == 'matured' else None for r in rows]
    target_labels = [r['target'] if r['target_status'] == 'matured' else None for r in rows]
    closed = [r for r in buyers if r['entry'] is True and r['trade_status'] == 'closed']
    valid_pnl = [r for r in closed if r['net'] is not None]
    nets = [money(r['net']) for r in valid_pnl]
    return {
        'action_counts': {a: sum(r['action'] == a for r in rows) for a in ('BUY', 'SELL', 'WAIT', 'HOLD', 'INSUFFICIENT_EVIDENCE')},
        'trade_status_counts': {s: sum(r['trade_status'] == s for r in rows) for s in ('closed', 'no_entry', 'ambiguous', 'not_applicable', 'open', 'pending', 'invalid_data', 'cancelled', 'missing')},
        'forecast_status_counts': dict(Counter(r['forecast_status'] for r in rows)),
        'target_status_counts': dict(Counter(r['target_status'] for r in rows)),
        'direction': rate(direction_labels), 'target_attainment': rate(target_labels),
        'entry_trigger': rate([r['entry'] for r in buyers]),
        'target_before_stop': rate([r['target_first'] for r in closed]),
        'net_win': rate([n > 0 for n in nets]),
        'net_expectancy_inr': metric(sum(nets, D(0)), len(nets)),
        'zero_net_count': sum(n == 0 for n in nets),
        'coverage': {
            'direction': metric(D(sum(r['forecast_due'] and r['forecast_status'] == 'matured' and r['direction'] is not None for r in rows)), sum(r['forecast_due'] for r in rows)),
            'target': metric(D(sum(r['target_due'] and r['target_status'] == 'matured' and r['target'] is not None for r in rows)), sum(r['target_due'] for r in rows)),
            'entry': metric(D(sum(r['entry_due'] and r['entry'] is not None for r in buyers)), sum(r['entry_due'] for r in buyers)),
            'due_trade_resolution': metric(D(sum(r['trade_due'] and r['entry'] is True and r['trade_status'] == 'closed' and r['net'] is not None for r in buyers)), sum(r['trade_due'] and r['entry'] is True for r in buyers))},
        'entry_expired_count': sum(r['reason'] == 'entry_expired' for r in rows),
        'time_exit_count': sum(r['reason'] == 'maximum_holding_expired' for r in closed),
        'eligible_pnl_ids': [r['id'] for r in valid_pnl],
    }


def portfolio(curve):
    """Post-flow marks supplied by a separate synthetic ledger, not scenarios."""
    def undefined(reason):
        return {'time_weighted_return': None, 'maximum_drawdown': None, 'reason': reason}
    if len(curve) < 2:
        return undefined('insufficient_intervals')
    equity, flow, dates = [], [], []
    for point in curve:
        dates.append(stamp(point['at']))
        if any(p['mark'] is None for p in point['positions']):
            return undefined('missing_position_mark')
        equity.append(money(point['cash']) + sum((money(p['quantity']) * money(p['mark']) for p in point['positions']), D(0)))
        flow.append(money(point['external_flow']))
    require(all(a < b for a, b in zip(dates, dates[1:])), 'equity chronology')
    if flow[0] != 0:
        return undefined('initial_equity_must_be_after_initial_funding')
    if any(e <= 0 for e in equity[:-1]) or equity[-1] < 0:
        return undefined('nonpositive_capital_or_negative_equity')
    wealth, peak, maximum = [D(1)], D(1), D(0)
    for i in range(1, len(equity)):
        before_flow = equity[i] - flow[i]
        if before_flow < 0 or (before_flow == 0 and flow[i] != 0) or (equity[i] == 0 and flow[i] != 0):
            return undefined('invalid_flow_or_capital_segment')
        value = wealth[-1] * before_flow / equity[i-1]
        wealth.append(value); peak = max(peak, value)
        maximum = max(maximum, 1 - value / peak)
    return dict(time_weighted_return=wealth[-1]-1, maximum_drawdown=maximum,
                wealth_index=wealth, equity=equity, cash_profit=equity[-1]-equity[0]-sum(flow), reason=None)


def risk_ratios(returns, *, risk_free=None):
    """Descriptive per-session ratios, not annualized or independent-sample claims.

    The caller must establish a complete equal-session return series. No inferred
    risk-free rate: the explicit synthetic cash comparator is zero when supplied.
    Sortino uses all-session target semideviation; Sharpe uses sample deviation.
    """
    values=[money(v) for v in returns]
    result=dict(intervals=len(values),sharpe=None,sortino=None,annualized=False,
        method='per-session-sample-sharpe-all-session-target-sortino-v1',
        risk_free_per_session=risk_free,sharpe_reason=None,sortino_reason=None)
    reason='risk_free_unavailable' if risk_free is None else 'insufficient_return_intervals' if len(values)<2 else None
    if reason:return {**result,'sharpe_reason':reason,'sortino_reason':reason}
    with localcontext() as ctx:
        ctx.prec=34
        excess=[v-money(risk_free) for v in values];n=D(len(excess));mean=sum(excess,D(0))/n
        variance=sum(((v-mean)**2 for v in excess),D(0))/(n-1)
        downside=sum((min(D(0),v)**2 for v in excess),D(0))/n
        result.update(sharpe=mean/variance.sqrt() if variance else None,
            sortino=mean/downside.sqrt() if downside else None,
            sharpe_reason=None if variance else 'zero_return_variance',
            sortino_reason=None if downside else 'no_downside_deviation')
    return result


