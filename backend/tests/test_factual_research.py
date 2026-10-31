"""Adversarial synthetic cases; real acceptance is executed separately."""
import json
from decimal import Decimal
import pytest
from test_rag_validation import bundle
from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis.factual_research import candidates,validate_response,model_context,limitations


def history():
    b=bundle();facts=[]
    for year,rev,earn,ocf in ((2024,'100','10','15'),(2025,'120','15','12')):
        for metric,value in (('revenue',rev),('earnings',earn),('operating_cash_flow',ocf)):
            f=b.facts[0];fid=digest([year,metric])
            facts.append(f.model_copy(update=dict(fact_id=fid,metric=metric,value=value,unit='INR',formula=None,
                period_start_at=f'{year}-01-01T00:00:00Z',period_end_at=f'{year}-12-31T23:59:59Z',
                citation=f.citation.model_copy(update={'evidence_id':fid}))))
    return b.model_copy(update={'facts':tuple(facts),'missing':('category:news',)})


def payload(c):
    return dict(candidate_id=c['candidate_id'],text=c['text'],citation_ids=list(dict.fromkeys(x['evidence_id'] for x in c['citations'])))


def validate(b,claims,interpretations=[]):
    return validate_response(json.dumps(dict(factual_claims=claims,interpretations=interpretations)),b,candidates(b))


def test_comparisons_are_decimal_calculations_with_exact_lineage():
    b=history();cs=candidates(b)
    growth=next(c for c in cs if c['metric']=='revenue_yoy')
    assert Decimal(growth['value'])==20 and len(growth['input_fact_ids'])==2
    assert growth['formula']=='(current/prior-1)*100-v1'
    assert all(c['scope']=='consolidated' for c in cs)
    ratio=next(c for c in cs if c['metric']=='operating_cash_flow_margin' and c['periods'][0]['end'].startswith('2025'))
    assert Decimal(ratio['value'])==Decimal('.1')


@pytest.mark.parametrize('field,value',[('scope','standalone'),('unit','USD'),('period_kind','quarter'),('period_start_at','2025-02-01T00:00:00Z'),('period_end_at','2026-12-31T23:59:59Z')])
def test_growth_requires_matching_scope_unit_and_adjacent_full_years(field,value):
    b=history();fs=list(b.facts);fs[3]=fs[3].model_copy(update={field:value});b=b.model_copy(update={'facts':tuple(fs)})
    assert not any(c['metric']=='revenue_yoy' for c in candidates(b))


def test_missing_evidence_does_not_suppress_supported_independent_facts():
    b=history();c=candidates(b)[0];r=validate(b,[payload(c)])
    assert len(r['accepted_claims'])==1 and r['action']=='INSUFFICIENT_EVIDENCE'
    assert 'category:news' in r['limitations'] and r['qualified'] is False


@pytest.mark.parametrize('change',[{'text':'Revenue growth = 999 percent'}, {'candidate_id':'0'*64}, {'citation_ids':['f'*64]}])
def test_invalid_claim_rejected_without_erasing_valid_claim(change):
    b=history();c=candidates(b)[0];good=payload(c);r=validate(b,[good,{**good,**change}])
    assert len(r['accepted_claims'])==1 and len(r['rejected_claims'])==1


def test_wrong_year_metric_scope_or_value_cannot_borrow_a_valid_citation():
    b=history();cs=candidates(b);base=payload(cs[0])
    wrong=[{**base,'text':base['text'].replace('2024','2023')},{**base,'text':base['text'].replace(cs[0]['metric'],'invented_metric')},
           {**base,'text':base['text'].replace('consolidated','standalone')}]
    r=validate(b,wrong)
    assert not r['accepted_claims'] and len(r['rejected_claims'])==3


@pytest.mark.parametrize('text',['The stock is undervalued.','Buy now.','Revenue grew 999 percent.','A safe investment.','A healthy cash position.','Financial quality is excellent.','Cash flow reconciles.'])
def test_unsupported_valuation_forecast_or_numbers_rejected(text):
    b=history();c=candidates(b)[0]
    r=validate(b,[],[dict(text=text,candidate_ids=[c['candidate_id']])])
    assert not r['pending_interpretations'] and len(r['rejected_claims'])==1


def test_positive_prose_is_not_accepted_without_independent_semantic_review():
    b=history();c=candidates(b)[0]
    r=validate(b,[],[dict(text='Revenue increased.',candidate_ids=[c['candidate_id']])])
    assert len(r['pending_interpretations'])==1 and not r.get('interpretive_findings')
    assert r['validation']['semantic']=='not_evaluated'


def test_missing_values_and_conflicting_period_exclude_affected_calculations():
    b=history();fs=list(b.facts);fs[3]=fs[3].model_copy(update={'value':None,'missing_reason':'unknown'})
    b=b.model_copy(update={'facts':tuple(fs)})
    assert not any(c['metric']=='revenue_yoy' for c in candidates(b))
    b=history();f=b.facts[0];b=b.model_copy(update={'facts':b.facts+(f.model_copy(update={'value':'101','fact_id':'f'*64}),)})
    assert not any(f.fact_id in c['input_fact_ids'] for c in candidates(b))


def test_catalogue_tampering_fails_and_model_context_retains_missing():
    b=history();cs=candidates(b);cs[0]['value']='999'
    with pytest.raises(ValueError,match='catalogue parity'):validate_response(json.dumps(dict(factual_claims=[],interpretations=[])),b,cs)
    assert 'category:news' in model_context(b,candidates(b))['limitations']


def test_cash_reconciliation_excerpt_is_preserved_as_limitation():
    from stock_discovery_analysis.rag_contracts import Hit
    b=history();text='Cash balance movement differs from reported total cash flow; reconciliation items are unavailable.'
    hit=Hit(chunk_id='a'*64,text=text,primary=False,citations=(b.facts[0].citation,),lexical_score='1',semantic_score=None,lexical_rank=1,semantic_rank=None,fused_score='1')
    b=b.model_copy(update={'hits':(hit,)})
    assert text in limitations(b)


def test_independent_judge_rejection_preserves_numerical_facts():
    from stock_discovery_analysis.factual_research import review_interpretations
    from stock_discovery_analysis.rag_research import MockResearchProvider
    b=history();c=candidates(b)[0]
    report=validate(b,[payload(c)],[dict(text='Revenue increased.',candidate_ids=[c['candidate_id']])])
    class Judge(MockResearchProvider):
        def judge(self,request,**kw):
            d=json.loads(request)['bundle']
            return json.dumps(dict(rubric=d['rubric'],claims=[dict(claim_index=0,support='unsupported',evidence_ids=[],reason='missing_premises')],contradictions='addressed',negative_evidence='unknown',completeness='incomplete',causal_support='unknown',abstention='appropriate'))
    review_interpretations(report,judge=Judge(),deadline=999999999,max_output_units=4000,remaining_units=50000)
    assert len(report['accepted_claims'])==1 and not report['interpretive_findings']
    assert not report['pending_interpretations'] and 'missing_premises' in report['rejected_claims'][0]['reason']
    assert not report['judge']['qualified']


def test_model_selected_direction_is_independently_proved_not_assumed():
    b=history();cs=candidates(b)
    pair=[next(c for c in cs if c['metric']==metric)['candidate_id'] for metric in ('earnings_yoy','operating_cash_flow_yoy')]
    for direction,accepted in [('opposite_direction',True),('same_direction',False)]:
        raw=json.dumps(dict(factual_claims=[],interpretations=[],relations=[dict(candidate_ids=pair,direction=direction)]))
        result=validate_response(raw,b,cs)
        assert bool(result['interpretive_findings'])==accepted
        if accepted:
            claim=result['interpretive_findings'][0]
            assert claim['text']=='Net profit increased while operating cash flow declined across the same comparable annual periods.'
            assert len(claim['citations'])==4 and claim['model_selected']
        else:assert result['rejected_claims'][0]['reason']=='unsupported growth direction'


def test_direction_rejects_duplicate_or_non_growth_candidates():
    b=history();cs=candidates(b);ids=[cs[0]['candidate_id'],cs[1]['candidate_id']]
    for pair in (ids,[ids[0],ids[0]],['f'*64,ids[1]]):
        result=validate_response(json.dumps(dict(factual_claims=[],interpretations=[],relations=[dict(candidate_ids=pair,direction='same_direction')])),b,cs)
        assert not result['interpretive_findings'] and result['rejected_claims']


@pytest.mark.parametrize('text',['Cash flow may indicate management issues.','Revenue will rise.','Growth suggests operating efficiency.'])
def test_speculative_explanations_and_forecasts_remain_rejected(text):
    b=history();c=candidates(b)[0]
    report=validate(b,[payload(c)],[dict(text=text,candidate_ids=[c['candidate_id']])])
    assert len(report['accepted_claims'])==1 and not report['pending_interpretations']
    assert report['rejected_claims']


def excerpt_bundle():
    from stock_discovery_analysis.rag_contracts import Hit
    b=history();c=b.facts[0].citation
    hit=Hit(chunk_id='b'*64,text='Synthetic source reports an unresolved regulatory inquiry; outcome is unknown.',
        primary=False,citations=(c,),lexical_score='1',semantic_score=None,lexical_rank=1,semantic_rank=None,fused_score='1')
    return b.model_copy(update={'documents':(c.revision_id,),'hits':(hit,)})


def test_selected_source_excerpt_is_exact_and_never_promoted_to_financial_or_event_truth():
    from stock_discovery_analysis.factual_research import excerpt_candidates
    b=excerpt_bundle();c=excerpt_candidates(b)[0]
    raw=json.dumps(dict(factual_claims=[],interpretations=[],source_excerpts=[payload(c),payload(c)]))
    r=validate_response(raw,b,candidates(b))
    assert len(r['accepted_source_excerpts'])==1 and not r['accepted_claims']
    assert not r['accepted_source_excerpts'][0]['financially_verified']
    assert not r['accepted_source_excerpts'][0]['event_truth_verified']
    assert not r['qualified'] and r['action']=='INSUFFICIENT_EVIDENCE'
    assert 'category:news' in r['limitations']
    assert model_context(b,candidates(b))['excerpt_candidates'][0]['text']==c['text']


@pytest.mark.parametrize('change',[{'text':'The company is safe.'},{'candidate_id':'f'*64},{'citation_ids':['f'*64]}])
def test_fabricated_excerpt_or_borrowed_citation_rejected_without_erasing_financial_facts(change):
    from stock_discovery_analysis.factual_research import excerpt_candidates
    b=excerpt_bundle();quote=payload(excerpt_candidates(b)[0]);fact=payload(candidates(b)[0])
    raw=json.dumps(dict(factual_claims=[fact],interpretations=[],source_excerpts=[{**quote,**change}]))
    r=validate_response(raw,b,candidates(b))
    assert len(r['accepted_claims'])==1 and not r['accepted_source_excerpts'] and len(r['rejected_claims'])==1


def test_excerpts_require_retrieved_document_membership_and_are_order_independent():
    from stock_discovery_analysis.factual_research import excerpt_candidates
    b=excerpt_bundle()
    with pytest.raises(ValueError,match='document membership'):excerpt_candidates(b.model_copy(update={'documents':()}))
    c=b.hits[0];other=c.model_copy(update={'text':'Different synthetic excerpt','chunk_id':'c'*64})
    assert excerpt_candidates(b.model_copy(update={'hits':(c,other,c)}))==excerpt_candidates(b.model_copy(update={'hits':(other,c)}))
    assert not excerpt_candidates(b.model_copy(update={'hits':(c.model_copy(update={'text':'x'*2001}),)}))


def test_excerpts_without_financial_facts_remain_attributed_and_missing_news_stays_missing():
    from stock_discovery_analysis.factual_research import excerpt_candidates
    b=excerpt_bundle().model_copy(update={'facts':()});q=excerpt_candidates(b)[0]
    r=validate_response(json.dumps(dict(factual_claims=[],interpretations=[],source_excerpts=[payload(q)])),b,[])
    assert len(r['accepted_source_excerpts'])==1 and r['validation']['numerical']=='no_accepted_claims'
    assert r['action']=='INSUFFICIENT_EVIDENCE' and 'category:news' in r['limitations']


def test_excerpt_output_count_bound_fails_closed():
    from stock_discovery_analysis.factual_research import excerpt_candidates
    b=excerpt_bundle();q=payload(excerpt_candidates(b)[0])
    with pytest.raises(ValueError,match='claim count limit'):
        validate_response(json.dumps(dict(factual_claims=[],interpretations=[],source_excerpts=[q]*4)),b,candidates(b))
