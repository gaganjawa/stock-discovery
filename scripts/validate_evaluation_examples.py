#!/usr/bin/env python3
"""STK-002: deterministic contract arithmetic, not a replay engine."""
from collections import Counter
from decimal import Decimal as D, ROUND_HALF_EVEN
from pathlib import Path
import copy
import json

from validate_contract_examples import ROOT, index, money, parse, require, stamp, validate


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


def original_rows(data):
    recs, obs, forecasts, trades = data
    validate(*data)  # Reuse STK-001's established validation unchanged.
    fo, tr = index(forecasts, 'recommendation_id'), index(trades, 'recommendation_id')
    paths = index(obs['scenarios'], 'recommendation_id')
    rows = []
    for r in recs:
        rid = r['recommendation_id']; f, t = fo[rid], tr[rid]
        is_buy = r['action'] == 'BUY'
        opening = next((v for v in t['fills'] if v['role'] == 'entry'), None)
        # Original fixtures explicitly establish valid entries and complete paths.
        entry = True if is_buy and opening else False if is_buy and t['status'] == 'no_entry' else None
        forecast = r['forecast']
        correct = direction(forecast['reference_price'], f['observed_price'], forecast['direction']) if forecast else None
        targets = r['execution']['targets'] if r['execution'] else []
        target = target_touch(paths[rid]['observations'], targets[0]['price'], 'up', r['information_cutoff_at'], forecast['end_at'], True, True) if targets else None
        first = t['reason'] == 'target' if is_buy and t['status'] == 'closed' and t['reason'] in ('target', 'stop', 'gap_stop', 'maximum_holding_expired') else None
        rows.append(dict(id=rid, action=r['action'], forecast_status=f['status'], direction=correct,
                         target_status='matured' if targets else 'not_applicable', target=target,
                         entry=entry, trade_status=t['status'], reason=t['reason'], target_first=first, net=t['net_pnl'],
                         forecast_due=bool(forecast), target_due=bool(targets), entry_due=is_buy, trade_due=entry is True))
        if is_buy and t['status'] == 'closed':
            result = round_trip(t['fills'][0]['price'], t['fills'][1]['price'], opening['quantity'], '.10', '.10')
            require(result['net'] == money(t['net_pnl']), 'original net P&L changed')
    return rows


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


def main():
    data = [parse((ROOT / n).read_text()) for n in ('recommendations.synthetic.json', 'observations.synthetic.json', 'forecast-outcomes.synthetic.json', 'trade-outcomes.synthetic.json')]
    extra = parse((ROOT / 'evaluation-edge-cases.synthetic.json').read_text())
    require(extra['synthetic'] is True, 'synthetic-only evaluation fixtures')
    require(all(stamp(r['forecast']['end_at']) < stamp(extra['evaluation_as_of']) for r in data[0] if r['forecast']), 'elapsed forecast snapshot')
    require(stamp(extra['additional_fictional_session_for_deadline_only']+'T10:00:00Z') < stamp(extra['evaluation_as_of']), 'elapsed maximum trade deadline')
    rows = original_rows(data); result = summarize(rows)
    # Independently hand-worked values, not generated with the tested functions.
    expected = {'direction': (6, 7), 'target_attainment': (4, 6), 'entry_trigger': (5, 6),
                'target_before_stop': (1, 4), 'net_win': (2, 4), 'net_expectancy_inr': ('-4.80', 4)}
    for key, (total, count) in expected.items():
        require(result[key]['numerator'] == D(total) and result[key]['denominator'] == count, key)
    require(result['net_expectancy_inr']['value'] == D('-1.20'), 'expectancy')
    expected_rows = [
        (True, True, True, False, '-4.20'), (True, True, True, True, '7.80'),
        (True, True, False, None, None), (True, False, True, False, '0.80'),
        (True, True, True, None, None), (False, False, True, False, '-9.20'),
        (True, None, None, None, None), (None, None, None, None, None), (None, None, None, None, None)]
    require([tuple(r[k] for k in ('direction','target','entry','target_first','net')) for r in rows] == expected_rows, 'nine-scenario eligibility')
    require(result['action_counts'] == dict(BUY=6, SELL=1, WAIT=1, HOLD=0, INSUFFICIENT_EVIDENCE=1), 'action coverage')
    require(result['trade_status_counts'] == dict(closed=5, no_entry=1, ambiguous=1, not_applicable=2, open=0, pending=0, invalid_data=0, cancelled=0, missing=0), 'trade coverage')
    # Explicit due flags describe this fully elapsed fixture snapshot, not a calendar engine.
    require([(result['coverage'][k]['numerator'], result['coverage'][k]['denominator']) for k in ('direction','target','entry','due_trade_resolution')] == [(7,7),(6,6),(6,6),(4,5)], 'coverage denominators')
    require(result['coverage']['due_trade_resolution']['value'] == D('.8'), 'resolution coverage')
    for case in extra['round_trips']:
        actual = round_trip(case['entry'],case['exit'],case['quantity'],case['entry_fees'],case['exit_fees'])
        for key in ('gross','net','invested'):
            require(actual[key] == money(case['expected_'+key]), case['id']+' '+key)
    boundary = [dict(extra['unresolved_cases'][0], id=c['id'], trade_status='closed', reason='maximum_holding_expired', target_first=False, net=c['expected_net']) for c in extra['round_trips']]
    require(summarize(boundary)['net_win']['value'] == 0 and summarize(boundary)['net_win']['denominator'] == 2, 'net loss and breakeven are not wins')
    unresolved = summarize(extra['unresolved_cases'])
    require(unresolved['coverage']['direction']['numerator'] == 2 and unresolved['coverage']['direction']['denominator'] == 5, 'overdue pending stays in coverage')
    require(unresolved['coverage']['due_trade_resolution']['value'] == 0, 'overdue unresolved trade coverage')
    require(unresolved['entry_trigger']['numerator'] == 2 and unresolved['entry_trigger']['denominator'] == 3, 'unresolved entry classification')
    for key in ('net_win','net_expectancy_inr','target_before_stop'):
        require(unresolved[key]['value'] is None and unresolved[key]['reason'] == 'no_eligible_observations', 'unresolved is not a loss')
    for key in expected:
        require(summarize([])[key]['value'] is None and summarize([])[key]['denominator'] == 0, 'empty denominator')
    require(all(m['value'] is None and m['reason'] == 'no_eligible_observations' for m in summarize([])['coverage'].values()), 'empty coverage')
    require(direction('100','100','flat') is True and direction('100','100','up') is False and direction('100',None,'up') is None, 'unchanged/missing endpoint')
    start, end = '2025-01-01T10:00:00Z', '2025-01-02T10:00:00Z'
    points = [{'kind':'point','at':end,'price':'110'}]
    require(target_touch(points,'110','up',start,end,True,True) is True, 'endpoint target equality')
    require(target_touch(points,'111','up',start,end,False,True) is None, 'incomplete miss')
    require(target_touch(points,'110','up',start,end,False,True) is True, 'known touch despite gaps')
    require(target_touch(points,'110','up',start,end,True,False) is None, 'no early success bias')
    require(target_touch([{'kind':'point','at':start,'price':'110'}],'110','up',start,end,True,True) is False, 'exclude cutoff touch')
    require(target_touch(points,'110','down',start,end,True,True) is True, 'down target equality')
    crossing = [{'kind':'bar','start_at':start,'end_at':end,'high':'120','low':'90'}]
    require(target_touch(crossing,'110','up',start,end,True,True) is None, 'straddling bar')
    curve = portfolio(extra['equity_curve']); want = extra['equity_expected']
    for key in ('time_weighted_return','maximum_drawdown','cash_profit'):
        require(curve[key] == money(want[key]), 'curve '+key)
    require(curve['wealth_index'] == list(map(money,want['wealth_index'])), 'wealth index')
    require(curve['equity'] == [money(p['expected_equity']) for p in extra['equity_curve']], 'open position marks')
    missing = copy.deepcopy(extra['equity_curve']); missing[2]['positions'][0]['mark'] = None
    require(portfolio(missing)['reason'] == 'missing_position_mark', 'missing curve observation')
    require(portfolio(extra['equity_curve'][:1])['reason'] == 'insufficient_intervals', 'one point cannot measure a path')
    require(portfolio([])['reason'] == 'insufficient_intervals', 'empty curve')
    zero = copy.deepcopy(extra['equity_curve'][:2]); zero[1].update(cash='0',positions=[],external_flow='0')
    require(portfolio(zero)['maximum_drawdown'] == 1, 'total loss is 100% drawdown')
    result['eligibility'] = rows
    result['portfolio_example'] = curve
    def serialize(value):
        if isinstance(value, D):
            return str(value.quantize(D('.0001'), rounding=ROUND_HALF_EVEN))
        raise TypeError(type(value).__name__)
    print(json.dumps(result, indent=2, default=serialize))
    print('PASS: original nine scenarios, costs, zero denominators, unresolved outcomes, target boundaries, cash flows and drawdown.')


if __name__ == '__main__':
    main()
