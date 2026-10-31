"""Synthetic component checks, not model-quality or real-market acceptance."""
import json
from copy import deepcopy
from datetime import timedelta
import pytest
from test_factual_research import history, payload
from stock_discovery_analysis import factual_research as factual
from stock_discovery_analysis.combined_research import compose, financial_projection, replay_context
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze
from stock_discovery_analysis.service import json_value


def stored():
    bundle=history(); catalogue=factual.candidates(bundle)
    pair=[next(c for c in catalogue if c['metric']==m)['candidate_id']
          for m in ('revenue_yoy','operating_cash_flow_yoy')]
    raw=json.dumps(dict(factual_claims=[payload(catalogue[0])],interpretations=[],
        relations=[dict(candidate_ids=pair,direction='opposite_direction')]))
    return bundle,dict(status='completed',research_only=True,
        factual_report=factual.validate_response(raw,bundle,catalogue))


def test_supported_trends_model_selection_and_uncertainty_remain_separate():
    bundle,result=stored(); f=financial_projection(result,bundle)
    assert any(t['metric']=='revenue_yoy' and t['value']=='20.0' for t in f['trends'])
    assert len(f['findings'])==1 and len(f['interpretations'])==1
    assert 'category:news' in f['uncertainties'] and not f['human_verified']
    result['factual_report']['rejected_claims']=[dict(claim='PRIVATE REJECTED TEXT')]
    assert 'PRIVATE' not in json.dumps(financial_projection(result,bundle))


@pytest.mark.parametrize('bad',['version','issuer_id','listing_id','cutoff_at','catalogue','citation','future','text','direction','relation_text'])
def test_changed_or_unverifiable_report_is_not_projected(bad):
    b,r=stored();r=deepcopy(r);p=r['factual_report']
    if bad in ('version','issuer_id','listing_id','cutoff_at'):p[bad]='invalid'
    if bad=='catalogue':p['candidates'][0]['value']='999'
    if bad=='citation':p['accepted_claims'][0]['citations'][0]['revision_id']='other'
    if bad=='text':p['accepted_claims'][0]['text']='Invented earnings = 999'
    if bad=='direction':p['interpretive_findings'][0]['direction']='same_direction'
    if bad=='relation_text':p['interpretive_findings'][0]['text']='Unsupported future return'
    if bad=='future':b=b.model_copy(update={'query':b.query.model_copy(update={'cutoff_at':'2023-01-01T00:00:00Z'})});p['cutoff_at']=b.query.cutoff_at
    with pytest.raises(ValueError):financial_projection(r,b)


@pytest.mark.parametrize('status,condition',[('BUY','conditions_met'),('WAIT','conditions_not_met'),('INSUFFICIENT_EVIDENCE','insufficient_evidence')])
def test_no_component_can_promote_combined_action(status,condition):
    technical=dict(status=status,indicators={'atr14':'1'},levels={'entry':'10'},hypothetical_sizing={'quantity':999})
    r=compose('TEST','2026-10-31T00:00:00Z',technical)
    assert r['technical']['condition']==condition and r['status']=='INSUFFICIENT_EVIDENCE'
    assert all(v=='BLOCKED' for v in r['acceptance_gates'].values())
    assert not any(r[k] for k in ('actionable','publication_authorized','paper_admission_authorized','trading_authorized'))
    assert 'quantity' not in json.dumps(r) and 'levels' not in r['technical']
    assert r==compose('TEST','2026-10-31T00:00:00Z',technical)


def test_replay_projection_uses_frozen_inputs_only_and_cannot_attach_later_research():
    d=demo_dataset();cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    a=json_value(analyze(d,'SYN-ALPHA',cutoff,code_version='test')); before=deepcopy(a)
    r=replay_context(a)
    assert a==before and r['mode']=='synthetic_replay' and r['financial'] is None
    assert r['replay']['future_outcomes']=='hidden_until_explicit_reveal'
    assert r==replay_context(dict(a,trade={'net_pnl':'999999'}))
    a['recommendation']['instrument']['instrument_id']='NSE:INFY'
    with pytest.raises(ValueError):replay_context(a)


def test_cached_extracted_financial_claim_reuses_unchanged_source_verifier():
    from test_financial_claims import case
    b,proposal=case()
    report=factual.validate_response(json.dumps(dict(factual_claims=[],interpretations=[],
        extracted_claims=[proposal])),b,factual.candidates(b))
    result=dict(status='completed',research_only=True,factual_report=report)
    assert len(financial_projection(result,b)['findings'])==1
    report['accepted_claims'][0]['extracted_fields']['fact']['value']='999'
    with pytest.raises(ValueError,match='verification_failed'):financial_projection(result,b)


def test_cached_source_excerpt_cannot_borrow_valid_citation_for_changed_text():
    from test_financial_claims import case
    b,_=case();excerpt=factual.excerpt_candidates(b)[0]
    report=factual.validate_response(json.dumps(dict(factual_claims=[],interpretations=[],
        source_excerpts=[dict(candidate_id=excerpt['candidate_id'],text=excerpt['text'],
            citation_ids=[c['evidence_id'] for c in excerpt['citations']])])),b,factual.candidates(b))
    result=dict(status='completed',research_only=True,factual_report=report)
    assert financial_projection(result,b)['source_excerpts']
    report['accepted_source_excerpts'][0]['text']='Unsupported announcement'
    with pytest.raises(ValueError,match='verification_failed'):financial_projection(result,b)
