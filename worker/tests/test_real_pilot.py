"""Fabricated inputs test selection/ranking safeguards; not real acceptance."""
from copy import deepcopy
import pytest
from worker.real_pilot import select_watchlist,screening,rank_rows,safe_error


def master(n=15):
 return [dict(segment='NSE_EQ',exchange='NSE',instrument_type='EQ',trading_symbol=f'T{i:02}',isin=f'INE{i:09}',instrument_key=f'NSE_EQ|INE{i:09}',name=f'Test {i}',lot_size=1,tick_size=5) for i in range(n)]


def test_watchlist_is_reproducible_bounded_and_not_liquidity_claim():
 rows=master();a=select_watchlist(rows,10,('T14',));b=select_watchlist(list(reversed(rows)),10,('T14',))
 assert a['members']==b['members'] and a['members'][0]['symbol']=='T14'
 assert a['label']=='LIMITED RESEARCH WATCHLIST' and all(m['liquidity']=='unqualified' for m in a['members'])
 assert len(a['bounded_out'])==5 and 'no liquidity claim' in a['selection']


def test_ambiguous_symbols_and_isins_are_excluded_not_selected():
 rows=master();rows.append(deepcopy(rows[0]));rows[1]['isin']=rows[2]['isin'];rows[1]['instrument_key']=rows[2]['instrument_key']
 got=select_watchlist(rows,10)
 assert {'T00','T01','T02'}.isdisjoint(m['symbol'] for m in got['members'])
 assert len(got['exclusions'])==4


@pytest.mark.parametrize('limit',[0,9,21,100])
def test_universe_size_is_bounded(limit):
 with pytest.raises(ValueError):select_watchlist(master(30),limit)


def test_missing_anchor_does_not_silently_substitute():
 with pytest.raises(ValueError,match='continuity_member_not_resolved'):select_watchlist(master(),10,('NOPE',))


def detail():
 return dict(price_features={'metrics':dict(ema10='110',ema30='100',atr14='3',breakout20='115')},market_readiness=dict(latest_session_present=True,warmup_complete=True,missing_sessions=[],unverified_bar_sessions=[],duplicate_bars=False),quantitative={h:dict(action='INSUFFICIENT_EVIDENCE',reasons=['policy_not_configured']) for h in ('swing','short_term','long_term')})


def finding(metric,value,end='2026-03-31T18:29:59Z'):
 return dict(kind='calculation',metric=metric,value=value,periods=[{'end':'2025-03-31T18:29:59Z'},{'end':end}])


def test_stale_prices_do_not_rank_as_weak_performance_but_historical_financials_remain():
 d=detail();d['market_readiness']['latest_session_present']=False
 r=screening(d,[finding('revenue_yoy','12'),finding('earnings_yoy','8')])
 assert not r['swing']['ranking_eligible'] and r['swing']['score'] is None
 assert r['short_term']['score']=='8' and not r['long_term']['ranking_eligible']
 assert r['short_term']['assessment']['action']=='INSUFFICIENT_EVIDENCE'


def test_mismatched_periods_and_nonexistent_metrics_never_get_score():
 r=screening(detail(),[finding('revenue_yoy','12'),finding('earnings_yoy','8','2025-03-31T18:29:59Z')])
 assert r['short_term']['missing']==['growth_periods_mismatch'] and r['short_term']['score'] is None
 assert r['long_term']['score'] is None


def test_rank_only_supported_values_with_stable_identity_ties():
 rows=[dict(isin=i,screening=screening(detail(),[finding('revenue_yoy',n),finding('earnings_yoy',n)])) for i,n in [('B','-4'),('A','-4'),('C','10')]]
 rows.append(dict(isin='D',screening=screening(detail(),[])))
 rank_rows(rows)
 assert [r['screening']['short_term']['rank'] for r in rows]==[3,2,1,None]
 assert all(r['screening']['short_term']['assessment']['action']=='INSUFFICIENT_EVIDENCE' for r in rows)


def test_errors_never_echo_secret_or_provider_payload():
 assert safe_error(RuntimeError('Bearer private-secret-value'))=='provider_or_validation_failure'
 assert safe_error(PermissionError('/private/file'))=='source_permission_or_credentials_denied'


def test_exact_missing_provider_field_is_safe_and_actionable():
 assert safe_error(KeyError('value'))=='missing_provider_field:value'
 assert safe_error(KeyError('Bearer secret'))=='missing_provider_field'
