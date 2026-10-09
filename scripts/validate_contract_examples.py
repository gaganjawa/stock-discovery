#!/usr/bin/env python3
"""Validate STK-001's synthetic fixtures, not a replay engine or production schema."""
import copy
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'docs/contracts/examples'
REC_FIELDS = set('recommendation_id schema_version synthetic mode run_id instrument strategy horizon information_cutoff_at generated_at decision_available_at earliest_executable_entry_at action position_effect holding execution forecast evidence missing_evidence rationale versions risk_context revises_id revision_reason'.split())
COMMON = set('outcome_id recommendation_id schema_version synthetic evaluated_at evaluator_version observation_dataset supersedes_outcome_id'.split())
FORECAST_FIELDS = COMMON | set('status reference_price observed_price observed_at realized_direction direction_matches price_return_pct'.split())
TRADE_FIELDS = COMMON | set('status reason assumptions_version fills gross_pnl estimated_costs net_pnl net_proceeds sensitivity_net_pnl'.split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-JSON numeric constant: ' + value)


def parse(text):
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def stamp(value):
    require(isinstance(value, str) and value.endswith('Z'), 'UTC timestamp required')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def money(value):
    require(isinstance(value, str), 'decimal string required')
    number = Decimal(value)
    require(number.is_finite(), 'finite decimal required')
    return number


def index(rows, key):
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), 'duplicate ' + key)
    return result


def validate(recs, observations, forecasts, trades):
    by_id = index(recs, 'recommendation_id')
    paths = index(observations['scenarios'], 'recommendation_id')
    require(observations['synthetic'] is True, 'observations must be synthetic')
    require(set(paths) == set(by_id), 'scenario coverage')
    require(len({r['outcome_id'] for r in forecasts + trades}) == len(forecasts + trades), 'outcome IDs')
    for rows, fields in ((forecasts, FORECAST_FIELDS), (trades, TRADE_FIELDS)):
        require(set(index(rows, 'recommendation_id')) == set(by_id), 'outcome coverage')
        for row in rows:
            require(set(row) == fields, 'outcome fields')
            require(row['synthetic'] is True and row['schema_version'] == '1.0.0', 'outcome version')
            require(row['observation_dataset'] == observations['dataset_id'], 'dataset reference')
            require(row['supersedes_outcome_id'] is None, 'initial fixture outcomes only')
            require(stamp(row['evaluated_at']) >= stamp(by_id[row['recommendation_id']]['generated_at']), 'evaluation precedes generation')
    for r in recs:
        rid = r['recommendation_id']
        require(set(r) == REC_FIELDS, 'recommendation fields')
        require(rid.startswith('SYN-') and r['synthetic'] is True and r['mode'] == 'synthetic', 'synthetic identity')
        require(r['schema_version'] == '1.0.0', 'schema version')
        require(r['instrument']['exchange'] == 'SYNTHETIC_NSE' and r['instrument']['isin'] is None, 'fictional instrument')
        cutoff = stamp(r['information_cutoff_at'])
        require(cutoff < stamp(r['decision_available_at']) <= stamp(r['generated_at']), 'decision timeline')
        evidence = index(r['evidence'], 'evidence_id')
        require(set(r['rationale']['evidence_ids']) <= set(evidence), 'missing citation')
        for e in evidence.values():
            require(e['availability_basis'] == 'fictional_fixture', 'fixture provenance')
            require(stamp(e['published_at']) <= stamp(e['available_at']) <= cutoff, 'future evidence')
            require(stamp(e['available_at']) <= stamp(e['fetched_at']) <= stamp(r['generated_at']), 'fetch timing')
        require(r['versions']['model'] is None and r['versions']['prompt'] is None, 'no model used')
        if r['revises_id'] is not None:
            old = by_id[r['revises_id']]
            require(old['instrument'] == r['instrument'] and r['revision_reason'], 'revision identity')
            require(stamp(old['generated_at']) < stamp(r['generated_at']), 'revision chronology/cycle')
        else:
            require(r['revision_reason'] is None, 'initial revision reason')
        x = r['execution']
        if r['action'] in ('WAIT', 'INSUFFICIENT_EVIDENCE'):
            require(x is None and r['forecast'] is None and r['holding'] is None and r['position_effect'] == 'NONE' and r['earliest_executable_entry_at'] is None, 'abstention semantics')
            blocking = any(e['blocking'] for e in r['missing_evidence'])
            require(blocking == (r['action'] == 'INSUFFICIENT_EVIDENCE'), 'missing evidence semantics')
        else:
            require(r['action'] in ('BUY', 'SELL'), 'supported fixture action')
            require(stamp(r['decision_available_at']) < stamp(r['earliest_executable_entry_at']) < stamp(x['entry_expires_at']), 'entry window')
            require(type(x['quantity']) is int and x['quantity'] > 0, 'quantity')
            require(not any(e['blocking'] for e in r['missing_evidence']), 'blocked action')
            if r['action'] == 'BUY':
                require(r['position_effect'] == 'OPEN_LONG' and r['holding'] is None, 'buy semantics')
                require(x['entry']['type'] == 'buy_stop' and len(x['targets']) == 1, 'buy condition')
                require(0 < money(x['stop']['price']) < money(x['entry']['trigger_price']) < money(x['targets'][0]['price']), 'price barriers')
                require(x['targets'][0]['exit_fraction'] == '1' and x['max_holding_sessions'] > 0, 'exit policy')
            else:
                require(r['position_effect'] in ('CLOSE_LONG', 'REDUCE_LONG') and r['holding'], 'sell requires holding')
                qty = r['holding']['available_quantity']
                require(x['quantity'] <= qty and (x['quantity'] == qty) == (r['position_effect'] == 'CLOSE_LONG'), 'no short selling')
                require(x['entry']['type'] == 'market_at_next_open' and x['stop'] is None and x['targets'] == [] and x['max_holding_sessions'] == 0, 'holding sale policy')
        if r['forecast']:
            require(stamp(r['forecast']['reference_at']) <= cutoff, 'forecast reference cutoff')
            require(r['forecast']['end_at'] == r['horizon']['forecast_end_at'], 'forecast horizon')
        prior = cutoff
        for o in paths[rid]['observations']:
            at = stamp(o.get('at', o.get('end_at')))
            require(at > prior, 'observation chronology')
            prior = at
            if o['kind'] == 'bar':
                require(stamp(o['start_at']) < at, 'bar interval')
                require(0 < money(o['low']) <= min(money(o['open']), money(o['close'])) <= max(money(o['open']), money(o['close'])) <= money(o['high']), 'OHLC range')
            else:
                require(money(o['price']) > 0, 'positive price')
    for f in forecasts:
        r = by_id[f['recommendation_id']]
        if not r['forecast']:
            require(f['status'] == 'not_applicable' and all(f[k] is None for k in FORECAST_FIELDS - COMMON - {'status'}), 'abstention forecast')
            continue
        last = paths[r['recommendation_id']]['observations'][-1]
        p, ref = money(last['price']), money(r['forecast']['reference_price'])
        direction = 'up' if p > ref else 'down' if p < ref else 'flat'
        require(f['status'] == 'matured' and f['observed_at'] == last['at'] == r['forecast']['end_at'], 'forecast endpoint')
        require(f['reference_price'] == r['forecast']['reference_price'] and money(f['observed_price']) == p, 'forecast prices')
        require(f['realized_direction'] == direction and f['direction_matches'] == (direction == r['forecast']['direction']), 'forecast direction')
        require(money(f['price_return_pct']) == ((p/ref-1)*100).quantize(Decimal('.0001')), 'forecast arithmetic')
        require(stamp(f['evaluated_at']) >= stamp(f['observed_at']), 'forecast evaluation timing')
    for t in trades:
        r = by_id[t['recommendation_id']]
        x, fills = r['execution'], t['fills']
        require(t['assumptions_version'] == 'SYN-fill-v1', 'fill version')
        require(money(t['estimated_costs']) == Decimal('.10') * len(fills), 'cost arithmetic')
        previous = None
        for fill in fills:
            at = stamp(fill['at'])
            require(stamp(r['earliest_executable_entry_at']) <= at <= stamp(t['evaluated_at']), 'fill timing')
            require(previous is None or previous < at, 'fill chronology')
            previous = at
            require(fill['quantity'] == x['quantity'], 'fill quantity')
            if fill['role'] in ('entry', 'holding_exit'):
                require(at < stamp(x['entry_expires_at']), 'expired entry fill')
            obs = paths[r['recommendation_id']]['observations']
            require(any((o['kind'] == 'point' and o['at'] == fill['at'] and o['price'] == fill['price']) or (o['kind'] == 'bar' and o['end_at'] == fill['at'] and o['close'] == fill['price']) for o in obs), 'fill lacks observation')
        if t['status'] == 'closed' and r['action'] == 'BUY':
            require(len(fills) == 2 and [f['side'] for f in fills] == ['BUY', 'SELL'], 'round trip')
            gross = (money(fills[1]['price']) - money(fills[0]['price'])) * x['quantity']
            require(money(t['gross_pnl']) == gross and money(t['net_pnl']) == gross - money(t['estimated_costs']), 'trade arithmetic')
        elif r['action'] == 'SELL':
            require(t['status'] == 'closed' and len(fills) == 1 and fills[0]['side'] == 'SELL', 'holding exit')
            require(t['gross_pnl'] is None and t['net_pnl'] is None, 'unknown holding basis')
            require(money(t['net_proceeds']) == money(fills[0]['price']) * x['quantity'] - money(t['estimated_costs']), 'proceeds arithmetic')
        elif t['status'] == 'ambiguous':
            require(len(fills) == 1 and t['net_pnl'] is None and t['gross_pnl'] is None, 'ambiguous scalar P&L')
            for label, price in [('stop_first', x['stop']['price']), ('target_first', x['targets'][0]['price'])]:
                expected = (money(price) - money(fills[0]['price'])) * x['quantity'] - Decimal('.20')
                require(money(t['sensitivity_net_pnl'][label]) == expected, 'ambiguity bounds')
        else:
            require(t['status'] in ('not_applicable', 'no_entry') and not fills and t['net_pnl'] is None and t['gross_pnl'] is None, 'no-trade semantics')
        if t['status'] == 'no_entry':
            require(t['reason'] == 'entry_expired' and stamp(t['evaluated_at']) >= stamp(x['entry_expires_at']), 'entry expiry')
            bars = [o for o in paths[r['recommendation_id']]['observations'] if o['kind'] == 'bar']
            require(len(bars) == 2 and all(money(o['high']) < money(x['entry']['trigger_price']) for o in bars), 'never-triggered evidence')
        if t['reason'] == 'maximum_holding_expired':
            dates = observations['calendar_sessions']
            require(dates.index(fills[1]['at'][:10]) - dates.index(fills[0]['at'][:10]) + 1 == x['max_holding_sessions'], 'holding session expiry')


def main():
    data = [parse((ROOT / name).read_text()) for name in ('recommendations.synthetic.json', 'observations.synthetic.json', 'forecast-outcomes.synthetic.json', 'trade-outcomes.synthetic.json')]
    validate(*data)
    for mutation in ('future_evidence', 'short_sale', 'bad_pnl'):
        bad = copy.deepcopy(data)
        if mutation == 'future_evidence':
            bad[0][0]['evidence'][0]['available_at'] = '2025-08-07T10:00:00Z'
        elif mutation == 'short_sale':
            next(r for r in bad[0] if r['action'] == 'SELL')['holding']['available_quantity'] = 0
        else:
            bad[3][0]['net_pnl'] = '4.20'
        try:
            validate(*bad)
        except ValueError:
            pass
        else:
            raise ValueError('negative check not rejected: ' + mutation)
    try:
        parse('{"id": 1, "id": 2}')
    except ValueError:
        pass
    else:
        raise ValueError('duplicate key not rejected')
    print('PASS: 4 JSON files; 9 recommendations, 9 forecast outcomes, 9 trade outcomes; 4 negative checks.')


if __name__ == '__main__':
    main()
