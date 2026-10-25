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


@pytest.mark.parametrize('error',['income-statement:upstox_timeout','balance-sheet:upstox_http_503','cash-flow:upstox_unavailable','financial:upstox_rate_limited','source_rate_limited'])
def test_financial_transients_remain_retryable_after_prices_succeed(error):
 from worker.real_pilot import retryable_rows
 assert retryable_rows([dict(status='observed',errors=[error])])
 assert not retryable_rows([dict(status='observed',errors=['income-statement:source_permission_or_credentials_denied'])])


@pytest.mark.parametrize('change',['embedding_model','embedding_digest','model_digest','retrieval','context','prompt','validator','factual_version'])
def test_research_fingerprint_invalidates_configuration_changes(change,monkeypatch):
 from types import SimpleNamespace
 from worker import real_pilot as pilot
 from worker.real_evidence import EvidenceConfig
 from stock_discovery_analysis.real_access import SourceConfig
 from stock_discovery_analysis.rag_contracts import Budget
 from stock_discovery_contracts.v2 import Ref
 row=dict(isin='INE009A01021',listing_id='NSE:INE009A01021',financial_findings=[dict(candidate_id='fixture-fact')])
 query=pilot.query_for(None,row,'long_term','2026-10-19T12:00:00Z')
 config=SimpleNamespace(evidence=EvidenceConfig(sources=SourceConfig(grant_file='/test-only',retention_days=1),filings=(),queries=(query,),budget=Budget(account='test'),factual_report=True))
 models={name:SimpleNamespace(ref=Ref(id=name,version='1',content_hash='a'*64)) for name in (config.evidence.model,config.evidence.embedding_model)}
 before=pilot.research_fingerprint(config,row,'long_term',models)
 monkeypatch.setattr(pilot,'now',lambda:'2026-10-20T12:00:00Z')
 assert pilot.research_fingerprint(config,deepcopy(row),'long_term',models)==before
 if change=='embedding_model':config.evidence=config.evidence.model_copy(update={'embedding_model':'different-embedding'})
 elif change in ('embedding_digest','model_digest'):
  name=config.evidence.embedding_model if change=='embedding_digest' else config.evidence.model
  models[name]=SimpleNamespace(ref=models[name].ref.model_copy(update={'version':'2','content_hash':'b'*64}))
 elif change=='retrieval':config.evidence=config.evidence.model_copy(update={'retrieval':config.evidence.retrieval.model_copy(update={'max_chunks':3})})
 elif change=='context':config.evidence=config.evidence.model_copy(update={'context':8192})
 elif change=='prompt':monkeypatch.setattr(pilot.factual_research,'PROMPT_HASH','b'*64)
 elif change=='validator':monkeypatch.setattr(pilot.rag_research,'VALIDATOR_VERSION','next')
 else:monkeypatch.setattr(pilot.factual_research,'VERSION','next')
 assert pilot.research_fingerprint(config,row,'long_term',models)!=before


@pytest.mark.parametrize('same_name',[False,True])
def test_pinned_model_factory_selects_explicit_constructor_contracts(same_name):
 from types import SimpleNamespace
 from worker.real_pilot import pinned_model_factory
 config=SimpleNamespace(model='research',embedding_model='research' if same_name else 'embedding',context=16384,max_model_bytes=6000000000)
 models={role:SimpleNamespace(ref=SimpleNamespace(id=name)) for role,name in [('research',config.model),('embedding',config.embedding_model)]}
 factory=pinned_model_factory(config,models)
 parameters=dict(context=16384,max_input_bytes=32768,max_model_bytes=6000000000)
 # Selection is independent of call order, and identical names keep distinct instances.
 assert factory(config.embedding_model) is models['embedding']
 assert factory(config.model,**parameters) is models['research']
 assert factory(config.model,**parameters) is models['research']
 for name,kwargs in [('unexpected',{}),('unexpected',parameters),(config.model,{'context':16384}),
                     (config.model,{**parameters,'max_input_bytes':1}),
                     (config.model,{**parameters,'max_model_bytes':7000000000}),
                     (config.embedding_model,{'base_url':'http://unexpected'}),
                     (config.embedding_model,{'context':8192})]:
  with pytest.raises(ValueError,match='unexpected_model_request'):factory(name,**kwargs)
 if not same_name:
  with pytest.raises(ValueError,match='unexpected_model_request'):factory(config.model)
  with pytest.raises(ValueError,match='unexpected_model_request'):factory(config.embedding_model,**parameters)
 models['research'].ref.id='unrequested-model'
 with pytest.raises(ValueError,match='pinned_model_identity_mismatch'):factory(config.model,**parameters)
