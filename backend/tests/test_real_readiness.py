"""Fabricated timestamps check fail-closed coverage, not market acceptance."""
from types import SimpleNamespace as NS
from stock_discovery_analysis.real_views import market_readiness

def bar(day):
    return NS(revision_id='test-'+day,data=NS(ends_at=day+'T10:00:00Z',adjustment_basis='split_bonus_adjusted'))
def session(day):
    return NS(data=NS(closes_at=day+'T10:00:00Z'))

def test_missing_latest_session_is_not_hidden_by_warmup_or_age():
    r=market_readiness([bar('2026-10-20')],[session('2026-10-20'),session('2026-10-21')],'2026-10-21T11:00:00Z')
    assert not r['latest_session_present'] and r['missing_sessions']==['2026-10-21T10:00:00Z']
    assert not r['within_proposed_age'] and not r['warmup_complete'] and not r['execution_qualified']

def test_open_session_is_not_required_before_close():
    r=market_readiness([bar('2026-10-20')],[session('2026-10-20'),session('2026-10-21')],'2026-10-21T09:00:00Z')
    assert r['latest_session_present'] and not r['missing_sessions'] and r['within_proposed_age']
    assert r['volume_basis']=='unverified' and r['historical_pit']=='unqualified'

def test_duplicate_and_calendarless_bars_do_not_qualify():
    r=market_readiness([bar('2026-10-20')]*30,[],'2026-10-20T11:00:00Z')
    assert r['duplicate_bars'] and r['unverified_bar_sessions'] and not r['latest_session_present']
    assert not r['execution_qualified']


def test_shipped_swing_proposal_cannot_activate_or_supply_entry_terms():
    import json
    from pathlib import Path
    from stock_discovery_contracts.v2 import Policy
    from stock_discovery_analysis.quant_policies import PolicyRegistry,assess
    p=Policy.model_validate(json.loads((Path(__file__).resolve().parents[2]/'docs/policies/real-swing-proposed-2.0.0.json').read_text())[0])
    reg=PolicyRegistry();reg.register(p)
    r=assess(reg,p.ref,profile='swing',instrument_id='NSE:INE009A01021',cutoff='2026-10-22T12:00:00Z',mode='live_paper',calendar=None,bars=())
    assert p.status=='unconfigured' and p.approval_ref is None
    assert r['action']=='INSUFFICIENT_EVIDENCE' and 'policy_not_configured' in r['reasons']
    assert not r['entry_terms'] and r['paper_admission']['status']=='blocked'


import pytest
@pytest.mark.parametrize('cutoff,next_session',[
    ('2026-10-18T12:00:00Z','2026-10-19'),  # Sunday after Friday close
    ('2026-10-19T09:59:59Z','2026-10-19'),  # Monday before close
    ('2026-10-19T12:00:00Z','2026-10-20'),  # declared holiday: next dated session Tuesday
])
def test_session_freshness_does_not_confuse_elapsed_age_with_weekends_or_holidays(cutoff,next_session):
    r=market_readiness([bar('2026-10-16')],[session('2026-10-16'),session(next_session)],cutoff)
    assert r['session_freshness']=='matches_latest_verified_closed_session'
    assert not r['within_proposed_age']  # Legacy unapproved proposal is not silently rewritten.
    assert not r['execution_qualified'] and r['calendar_completeness']=='not_attested_by_session_list'


def test_session_close_requires_new_candle_and_provider_lag_is_explicit():
    sessions=[session('2026-10-16'),session('2026-10-19')]
    before=market_readiness([bar('2026-10-16')],sessions,'2026-10-19T09:59:59Z')
    after=market_readiness([bar('2026-10-16')],sessions,'2026-10-19T10:00:00Z')
    assert before['latest_session_present']
    assert after['session_freshness']=='missing_latest_verified_closed_session'
    assert after['missing_sessions']==['2026-10-19T10:00:00Z']
