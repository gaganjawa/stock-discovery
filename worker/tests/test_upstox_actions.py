"""Fabricated provider payloads only; not observed Upstox data."""
import pytest
from worker.providers.upstox_actions import parse_actions


def event(name, day, amount=None, ratio=None, kind=None):
    details = [{'name': 'Dividend type', 'value': kind}] if kind else []
    return {'name': name, 'expiry_date': day, 'amount': amount, 'ratio': ratio, 'event_details': details}


def test_dividend_cash_is_arithmetic_and_share_ratios_fail_closed():
    actions = parse_actions({'status': 'success', 'data': [
        event('Dividend', '14 Aug 2025', 5.5, kind='Final'), event('Dividend', '14 Aug 2025', '2', kind='Special'),
        event('Bonus', '02 Jul 2018', ratio='1:1'), event('Split', '10 Jan 2020', ratio='2:1'), event('Rights', '05 May 2021')]})
    by_id = {a.action_id: a for a in actions}
    final = by_id['upstox:dividend:2025-08-14:final']
    assert (final.action_type, final.cash_per_share, final.effective_at) == ('dividend', '5.5', '2025-08-13T18:30:00Z')
    assert by_id['upstox:dividend:2025-08-14:special'].cash_per_share == '2'
    for key in ('upstox:bonus:2018-07-02:1:1', 'upstox:split:2020-01-10:2:1', 'upstox:rights:2021-05-05:no-ratio'):
        assert by_id[key].action_type == 'unsupported' and by_id[key].share_ratio is None
    assert [a.effective_at for a in actions] == sorted(a.effective_at for a in actions)


def test_identical_duplicates_collapse_and_conflicts_fail_closed():
    same = event('Dividend', '14 Aug 2025', 5.5, kind='Final')
    assert len(parse_actions({'status': 'success', 'data': [same, dict(same)]})) == 1
    with pytest.raises(ValueError, match='ambiguous_corporate_action'):
        parse_actions({'status': 'success', 'data': [same, event('Dividend', '14 Aug 2025', 6, kind='Final')]})


@pytest.mark.parametrize('payload,code', [
    ({'status': 'error', 'data': []}, 'provider_status_failed'),
    ({'status': 'success', 'data': {}}, 'corporate_action_shape'),
    ({'status': 'success', 'data': [event('Dividend', '2025-08-14', 1)]}, 'corporate_action_date_unparseable'),
    ({'status': 'success', 'data': [event('Dividend', '14 Aug 2025', None)]}, 'invalid_dividend_amount'),
    ({'status': 'success', 'data': [event('Dividend', '14 Aug 2025', -1)]}, 'invalid_dividend_amount'),
    ({'status': 'success', 'data': [event('Dividend', '14 Aug 2025', 'NaN')]}, 'invalid_dividend_amount'),
])
def test_malformed_payloads_are_rejected(payload, code):
    with pytest.raises(ValueError, match=code):
        parse_actions(payload)
