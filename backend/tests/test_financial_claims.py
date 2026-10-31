"""Development fixtures only; not a human-verified research-quality holdout."""
import json
import pytest
from test_rag_validation import bundle
from stock_discovery_analysis.rag_contracts import Hit
from stock_discovery_analysis.factual_research import candidates,validate_response,model_context
from stock_discovery_analysis.financial_claims import verify_claim


def case():
    b=bundle();f=next(f for f in b.facts if f.metric=='revenue')
    quote=f'{f.metric} = {f.value} {f.unit}; {f.period_start_at}/{f.period_end_at}; {f.period_kind}; {f.scope}'
    c=f.citation.model_copy(update={'evidence_id':'b'*64,'excerpt':quote})
    hit=Hit(chunk_id='b'*64,text=quote,primary=True,citations=(c,),lexical_score='1',semantic_score=None,lexical_rank=1,semantic_rank=None,fused_score='1')
    b=b.model_copy(update={'hits':(hit,)})
    proposal=dict(issuer_id=b.query.issuer_id,listing_id=b.query.listing_id,revision_id=c.revision_id,evidence_id=c.evidence_id,quote=quote,
        fact=dict(metric=f.metric,value=f.value,missing_reason=None,unit=f.unit,period_start_at=f.period_start_at,
                  period_end_at=f.period_end_at,period_kind=f.period_kind,scope=f.scope,locator=f.source_locator))
    return b,proposal


def test_model_proposal_is_checked_against_source_and_independent_stored_fact():
    b,p=case();r=verify_claim(p,b)
    assert r['reference_fact_id'] and r['validation']=='deterministic_filing_fact_and_passage_parity'
    context=model_context(b,candidates(b));assert context['source_passages'][0]['text']==p['quote']
    assert all('value' not in x for x in context['reference_locators'])
    raw=json.dumps(dict(factual_claims=[],interpretations=[],extracted_claims=[p,p]))
    report=validate_response(raw,b,candidates(b))
    assert len(report['accepted_claims'])==1 and not report['qualified'] and report['publication']=='blocked'


@pytest.mark.parametrize('field,value', [('value','999'),('unit','USD'),('unit','INR_crore'),('scope','standalone'),
    ('period_start_at','2024-01-01T00:00:00Z'),('period_end_at','2027-12-31T00:00:00Z'),('locator','wrong table cell'),('metric','earnings')])
def test_incorrect_financial_fields_are_rejected(field,value):
    b,p=case();p['fact'][field]=value
    with pytest.raises(ValueError):verify_claim(p,b)


@pytest.mark.parametrize('field,value',[('issuer_id','other'),('listing_id','other'),('revision_id','missing'),
    ('evidence_id','f'*64),('quote','Revenue may be strong.')])
def test_wrong_entity_revision_citation_or_unsupported_passage_is_rejected(field,value):
    b,p=case();p[field]=value
    with pytest.raises(ValueError):verify_claim(p,b)


def test_conflicting_reference_fact_is_not_verified_and_rejection_preserves_uncertainty():
    b,p=case();f=next(f for f in b.facts if f.metric=='revenue')
    b=b.model_copy(update={'facts':b.facts+(f.model_copy(update={'fact_id':'f'*64,'value':'999'}),)})
    report=validate_response(json.dumps(dict(factual_claims=[],interpretations=[],extracted_claims=[p])),b,candidates(b))
    assert not report['accepted_claims'] and report['rejected_claims']
