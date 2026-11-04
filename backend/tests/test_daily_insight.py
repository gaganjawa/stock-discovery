"""STK-083 deterministic interpretation of invented evidence, not performance."""
from copy import deepcopy
from decimal import localcontext
import pytest
from stock_discovery_analysis.daily_insight import interpret,compose
from test_descriptive_freshness import delayed,NOW


def detail(lag=1):
 r,ready=delayed(lag=lag)
 return dict(listing_id='NSE:INE009A01021',symbol='TEST',adjusted_research=r.model_dump(mode='json'),
  price_series=[dict(close='105',time='2026-10-18')] if r.metrics else [],financial_facts=[],documents=[],
  publication_blockers=['financial_publication_timestamps_unknown','real_policies_required'],
  market_readiness={'input_revision_ids':[o.revision_id for o in r.observations]})


def test_interpretation_reproducible_without_ratios_or_signals():
 d=detail();r=compose(d,{'financial':None,'gaps':['financial_research_requires_refresh']},evaluated_at=NOW)
 with localcontext() as ctx:
  ctx.prec=5
  assert r==compose(d,{'financial':None,'gaps':['financial_research_requires_refresh']},evaluated_at=NOW)
 assert r['state']=='delayed_descriptive' and r['market']['freshness']['trailing_missing_sessions']==1
 assert r['ai']['status']=='AI_RESEARCH_UNAVAILABLE' and r['ai']['new_model_calls']==0
 assert r['fundamentals']['facts']==[] and r['hypothetical_levels']['entry'] is None
 for k in ['actionable','publication_authorized','paper_admission_authorized','trading_authorized']:assert r[k] is False
 assert len(r['technical']['interpretation']['neutral'])>=3


def test_two_session_delay_clears_interpretations():
 r=compose(detail(2),{},evaluated_at=NOW)
 assert r['state']=='unavailable_data' and not r['technical']['metrics']
 assert not r['conclusion']['bullish_observations'] and r['market']['latest_candle'] is None


def test_reported_period_age_and_unknown_values_preserved():
 d=detail();d['financial_facts']=[dict(fact_id='test',period_end_at='2026-09-30T00:00:00Z',metric='eps',value=None,unit='INR',source_locator='test page 4')]
 r=compose(d,{},evaluated_at=NOW)
 f=r['fundamentals']['facts'][0]
 assert f['value'] is None and f['age_days']==19 and f['source_locator']=='test page 4'
 assert f['age_basis']=='reporting_period_end_not_publication'


def test_price_above_and_below_actual_indicators():
 m=dict(sma20='100',ema10='104',ema30='103',atr14='2',breakout20='110',support20='95')
 r=interpret('105',m)
 assert len(r['bullish'])==4 and not r['bearish']
 assert '1.90%' in r['neutral'][0]['text']
 r=interpret('99',m);assert len(r['bearish'])==3


@pytest.mark.parametrize('price',['0','NaN','Infinity'])
def test_invalid_price_rejected(price):
 with pytest.raises((ValueError,ArithmeticError)):interpret(price,{})
