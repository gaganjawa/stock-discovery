"""STK-079: Upstox corporate actions into D3-03 action revisions.

Only dividend cash is arithmetic. Split, bonus, rights and other ratios are kept
as provider labels and stored as 'unsupported': the provider ratio orientation is
undocumented, so adjustment across them fails closed until separately qualified.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from stock_discovery_contracts.v2 import check
from stock_discovery_analysis.revisions import ActionData

URL = 'https://api.upstox.com/v2/fundamentals/{isin}/corporate-actions'


def _detail(event, label):
    values = [d.get('value') for d in event.get('event_details') or () if isinstance(d, dict) and d.get('name') == label]
    return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0].strip() else None


def _day(value):
    try:return datetime.strptime(value.strip(), '%d %b %Y').date()
    except (AttributeError, ValueError):raise ValueError('corporate_action_date_unparseable') from None


def parse_actions(payload):
    check(isinstance(payload, dict) and payload.get('status') == 'success', 'provider_status_failed')
    events = payload.get('data')
    check(isinstance(events, list) and len(events) <= 500, 'corporate_action_shape')
    actions = {}
    for event in events:
        check(isinstance(event, dict) and isinstance(event.get('name'), str) and event['name'].strip(), 'corporate_action_shape')
        kind = event['name'].strip().lower()
        day = _day(event.get('expiry_date'))
        # Ex-date at 00:00 IST; never a publication or announcement time.
        effective = (day - timedelta(days=1)).isoformat() + 'T18:30:00Z'
        if kind == 'dividend':
            try:amount = Decimal(str(event.get('amount')))
            except InvalidOperation:raise ValueError('invalid_dividend_amount') from None
            check(type(event.get('amount')) in (int, float, str) and amount.is_finite() and amount >= 0, 'invalid_dividend_amount')
            label = (_detail(event, 'Dividend type') or 'unspecified').strip().lower()
            data = ActionData(kind='action', action_id=f'upstox:dividend:{day}:{label}', action_type='dividend',
                              effective_at=effective, share_ratio=None, cash_per_share=format(amount.normalize(), 'f'), currency='INR')
        else:
            ratio = event.get('ratio')
            label = ratio.strip() if isinstance(ratio, str) and ratio.strip() else 'no-ratio'
            data = ActionData(kind='action', action_id=f'upstox:{kind}:{day}:{label}', action_type='unsupported',
                              effective_at=effective, share_ratio=None, cash_per_share=None, currency='INR')
        if data.action_id in actions:
            check(actions[data.action_id] == data, 'ambiguous_corporate_action')
            continue
        actions[data.action_id] = data
    return tuple(sorted(actions.values(), key=lambda a: (a.effective_at, a.action_id)))


def fetch_actions(client, stream, isin):
    check(stream.scope == 'corporate_actions', 'corporate_actions_scope_required')
    return parse_actions(json.loads(client._get(URL.format(isin=isin), stream)))
