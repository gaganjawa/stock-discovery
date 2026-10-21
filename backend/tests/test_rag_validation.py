"""Golden deterministic fixed-RAG validation and financial parity cases."""
import json
from decimal import Decimal, localcontext
import pytest
from stock_discovery_analysis.rag_contracts import Query, RetrievalPolicy, Budget, Bundle, Claim, Assessment
from stock_discovery_analysis.rag_retrieval import (MockEmbeddings, cosine, allocate_candidates, financial_facts,
    calculate_ratio, conflicts)
from stock_discovery_analysis.rag_research import (ResearchClaim, ResearchResponse, validate_assessment,
    validate_research_response, financial_text)
from stock_discovery_analysis.evidence import extract
from stock_discovery_analysis.evidence_fixtures import document_fixture
from stock_discovery_analysis.revision_fixtures import NOW


def query(**changes):
    data = dict(issuer_id='SYN-issuer',listing_id='SYN-listing',horizon='long_term',mode='synthetic',
                cutoff_at=NOW,text='earnings',categories=('annual_report',),required_metrics=('revenue','earnings'),
                period_start_at='2025-01-01T00:00:00Z',period_end_at='2025-12-31T00:00:00Z',period_kind='annual')
    data.update(changes)
    return Query(**data)


def bundle():
    doc = document_fixture()
    item = dict(document=doc.model_dump(mode='json'),**extract(doc,trusted_primary=True))
    facts = financial_facts([item],query())
    return Bundle(query=query(),ranking=RetrievalPolicy().ref,embedding=None,retrieval_mode='lexical_only',
                  documents=('SYN-E-report',),hits=(),facts=facts,missing=(),contradictions=(),omitted=(),
                  source_count=1,coverage='1',embedding_input_units=0)


def financial_assessment(b):
    f = b.facts[0]
    return Assessment(issuer_id=b.query.issuer_id,horizon=b.query.horizon,action='BUY',
        claims=(Claim(kind='financial',text=financial_text(f),citations=(f.citation,),fact=f),),missing=(),contradictions=())


@pytest.mark.parametrize('horizon',['swing','short_term','long_term'])
def test_all_horizons_shadow_only(horizon):
    b = bundle().model_copy(update={'query':query(horizon=horizon)})
    a,report = validate_assessment(financial_assessment(b).model_dump_json(),b)
    assert a.action=='WATCH' and a.actionable is False and a.paper_admission=='blocked'
    assert report['proposed_action']=='BUY' and report['semantic']=='not_evaluated'


@pytest.mark.parametrize('field,value', [('value','999'),('unit','USD'),('period_start_at','2024-01-01T00:00:00Z'),
    ('period_end_at','2024-12-31T00:00:00Z'),('scope','standalone'),('metric','invented')])
def test_numerical_unit_period_scope_and_metric_traps(field,value):
    b = bundle()
    a = financial_assessment(b).model_dump(mode='json')
    a['claims'][0]['fact'][field] = value
    with pytest.raises(ValueError):validate_assessment(json.dumps(a),b)


@pytest.mark.parametrize('field,value',[('locator','page invented'),('revision_id','other'),('source_url','https://evil.invalid'),('evidence_id','0'*64)])
def test_citation_membership_and_locator(field,value):
    b = bundle(); a = financial_assessment(b).model_dump(mode='json')
    a['claims'][0]['citations'][0][field] = value
    with pytest.raises(ValueError,match='citation'):validate_assessment(json.dumps(a),b)


def test_no_extra_tools_or_actionable_fields():
    b=bundle();a=financial_assessment(b).model_dump(mode='json')
    for field,value in [('tools',['buy']),('actionable',True),('paper_admission','approved')]:
        with pytest.raises(ValueError):validate_assessment(json.dumps({**a,field:value}),b)


def test_factual_prose_cannot_smuggle_unsupported_information():
    b=bundle();a=financial_assessment(b).model_dump(mode='json')
    a['claims'][0]['text']='Revenue will double. Buy now.'
    with pytest.raises(ValueError):validate_assessment(json.dumps(a),b)


def test_missing_and_contradictory_evidence_requires_abstention():
    b=bundle().model_copy(update={'missing':('category:news',),'contradictions':(('first','second'),)})
    a=financial_assessment(b)
    with pytest.raises(ValueError):validate_assessment(a.model_dump_json(),b)
    a=a.model_copy(update={'missing':b.missing,'contradictions':b.contradictions})
    with pytest.raises(ValueError,match='must abstain'):validate_assessment(a.model_dump_json(),b)
    a=a.model_copy(update={'action':'INSUFFICIENT_EVIDENCE'})
    assert validate_assessment(a.model_dump_json(),b)[0].action=='INSUFFICIENT_EVIDENCE'


def test_decimal_ratios_preserve_lineage_and_global_context_independence():
    facts={f.metric:f for f in bundle().facts}
    with localcontext() as ctx:
        ctx.prec=2
        result=calculate_ratio(facts['earnings'],facts['revenue'])
    assert result['value']=='0.1' and len(result['citations'])==2
    assert result==calculate_ratio(facts['earnings'],facts['revenue'])
    missing=facts['revenue'].model_copy(update={'value':None,'missing_reason':'unavailable'})
    assert calculate_ratio(facts['earnings'],missing)['value'] is None
    zero=facts['revenue'].model_copy(update={'value':'0'})
    assert calculate_ratio(facts['earnings'],zero)['missing_reason']=='zero_denominator'


@pytest.mark.parametrize('field,value',[('unit','USD'),('scope','standalone'),('period_kind','quarter'),('period_end_at','2024-12-31T00:00:00Z')])
def test_incompatible_calculation_inputs(field,value):
    a,b=bundle().facts
    with pytest.raises(ValueError):calculate_ratio(a,b.model_copy(update={field:value}))


def test_conflicting_facts_remain_visible_but_decimal_equivalence_is_not_conflict():
    f=bundle().facts[0]
    assert not conflicts((f,f.model_copy(update={'value':f.value+'.0'})))
    assert conflicts((f,f.model_copy(update={'fact_id':'f'*64,'value':'123'})))


def test_mock_semantic_synonym_and_finite_dimensions():
    model=MockEmbeddings()
    vectors=model.embed(('earnings','profit','debt'),deadline=1)
    assert cosine(vectors[0],vectors[1])==1 and cosine(vectors[0],vectors[2])==0
    for bad in ((Decimal('NaN'),),(),(Decimal('1'),)):
        with pytest.raises(ValueError):cosine(vectors[0],bad)


def test_versioned_policy_candidate_cap_and_event_reservation():
    p=RetrievalPolicy()
    changed=RetrievalPolicy(lexical_weight='2')
    assert p.ref.content_hash!=changed.ref.content_hash
    result=allocate_candidates(tuple(str(i) for i in range(20)),('event1','event2'),p)
    assert len(result['selected'])==10 and result['selected'][:2]==('event1','event2') and result['omitted']
    with pytest.raises(ValueError):RetrievalPolicy(max_chunks=21)
    with pytest.raises(ValueError):RetrievalPolicy(event_slots=11)
    with pytest.raises(ValueError):RetrievalPolicy(lexical_weight='-1')
    with pytest.raises(ValueError):Budget(account='test',max_run_cost='-1')
    with pytest.raises(ValueError):query(period_end_at='2027-01-01T00:00:00Z')


def test_numeric_inferences_cannot_bypass_financial_fact_parity():
    b=bundle();f=b.facts[0]
    a=Assessment(issuer_id=b.query.issuer_id,horizon=b.query.horizon,action='WATCH',
        claims=(Claim(kind='inference',text='Revenue grew 999 percent.',citations=(f.citation,),fact=None),),missing=(),contradictions=())
    with pytest.raises(ValueError,match='numeric_inference_requires_structured_fact'):
        validate_assessment(a.model_dump_json(),b)


def test_valid_citations_do_not_promote_model_abstention_to_watch():
    b=bundle()
    original=financial_assessment(b).model_copy(update={'action':'INSUFFICIENT_EVIDENCE'})
    result,report=validate_assessment(original.model_dump_json(),b)
    assert result.action=='INSUFFICIENT_EVIDENCE'
    assert report['deterministic']=='passed' and report['proposed_action']=='INSUFFICIENT_EVIDENCE'


def compact_assessment(b, **changes):
    f=b.facts[0]
    payload=dict(issuer_id=b.query.issuer_id,horizon=b.query.horizon,action='BUY',
        claims=(ResearchClaim(kind='financial',text=financial_text(f),
            citation_ids=(f.citation.evidence_id,),fact_id=f.fact_id),))
    payload.update(changes)
    return ResearchResponse(**payload)


def test_compact_citation_ids_materialize_exact_bundle_locator_and_fact():
    b=bundle()
    response=compact_assessment(b)
    result,report=validate_research_response(response.model_dump_json(),b)
    fact=b.facts[0]
    assert result.claims[0].fact==fact
    assert result.claims[0].citations==(fact.citation,)
    assert result.action=='WATCH'
    assert report['deterministic']=='passed'


def test_compact_response_rejects_unknown_citation_and_fact_ids():
    b=bundle();response=compact_assessment(b)
    claim=response.claims[0].model_copy(update={'citation_ids':('f'*64,)})
    with pytest.raises(ValueError,match='citation membership/locator'):
        validate_research_response(response.model_copy(update={'claims':(claim,)}).model_dump_json(),b)
    claim=response.claims[0].model_copy(update={'fact_id':'0'*64})
    with pytest.raises(ValueError,match='financial fact membership'):
        validate_research_response(response.model_copy(update={'claims':(claim,)}).model_dump_json(),b)


def test_compact_response_cannot_change_a_citation_locator():
    b=bundle();response=compact_assessment(b)
    raw=response.model_dump(mode='json')
    raw['claims'][0]['locator']='invented page'
    with pytest.raises(ValueError):
        validate_research_response(json.dumps(raw),b)


def test_bundle_owns_missing_and_conflicting_evidence_in_compact_response():
    b=bundle().model_copy(update={'missing':('category:news',),'contradictions':(('a','b'),)})
    response=compact_assessment(b,action='INSUFFICIENT_EVIDENCE',claims=())
    result,report=validate_research_response(response.model_dump_json(),b)
    assert result.missing==b.missing and result.contradictions==b.contradictions
    assert result.action=='INSUFFICIENT_EVIDENCE'
    assert report['deterministic']=='passed'
    with pytest.raises(ValueError):
        validate_research_response(response.model_copy(update={'action':'WATCH'}).model_dump_json(),b)
