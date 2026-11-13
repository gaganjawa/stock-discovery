from copy import deepcopy
import pytest
from stock_discovery_analysis.candidate_swing import review,page


def result():
    return dict(status='completed',market_data={'latest_close':'110'},technical=dict(
        status='AVAILABLE_DESCRIPTIVE_ONLY',freshness={'status':'current'},
        metrics={'ema10':'105','ema30':'100','breakout20':'109'}))


def test_price_checks_are_partial_strategy_only():
    r=review(result())
    assert r['price_checks_met']==2 and r['checks']['relative_volume'] is None
    assert not r['actionable'] and r['rank'] is None
    assert r['strategy_status']=='incomplete_volume_basis_unverified'


@pytest.mark.parametrize('mode',['missing','stale','delayed','nan','null','zero'])
def test_unqualified_inputs_never_rank(mode):
    r=result()
    if mode=='missing':r={'status':'blocked','reasons':['nse_identity_missing_or_ambiguous']}
    if mode=='stale':r['technical']['status']='UNAVAILABLE'
    if mode=='delayed':r['technical']['freshness']['status']='delayed_one_session'
    if mode in ('nan','null','zero'):r['technical']['metrics']['ema10']={'nan':'NaN','null':None,'zero':'0'}[mode]
    assert review(r)['price_checks_met'] is None


def test_ties_current_clock_and_no_cached_rank(monkeypatch):
    from stock_discovery_analysis import candidate_swing
    calls=[]
    def analyze(conn,config,symbol,session,clock):
        calls.append(clock())
        r=result()
        if symbol=='Z':r['status']='blocked'
        return r
    monkeypatch.setattr(candidate_swing,'analyze',analyze)
    rows=[dict(symbol=s,candidate_id=s,session_date='2026-11-13',research={'rank':1}) for s in ('Z','B','A')]
    p=page(None,None,{'rows':deepcopy(rows)},clock=lambda:'2026-11-13T12:00:00Z')
    assert [r['symbol'] for r in p['rows']]==['A','B','Z']
    assert [r['swing_review']['rank'] for r in p['rows']]==[1,1,None]
    assert len(set(calls))==1 and len(calls)==3
    assert p['ranking_scope']=='displayed_page_only'
