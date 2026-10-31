"""LLM proposals are checked against deterministic filing extraction and passages.

First slice requires explicit ISO period, scope, metric and unit markers. Unknown
source layouts abstain; these checks do not establish source truth or completeness.
"""
import re
from decimal import Decimal
from pydantic import Field
from typing import Annotated
from stock_discovery_contracts.v2 import Strict,Text,Hash,check,at
from .evidence import FinancialRow,normalize
from .rag_retrieval import conflicts


class ExtractedClaim(Strict):
    issuer_id: Text
    listing_id: Text
    revision_id: Text
    evidence_id: Hash
    quote: Annotated[str,Field(min_length=1,max_length=2000)]
    fact: FinancialRow


def verify_claim(raw,bundle):
    c=ExtractedClaim.model_validate(raw);q=bundle.query;r=c.fact
    check((c.issuer_id,c.listing_id)==(q.issuer_id,q.listing_id),'extraction entity mismatch')
    check(c.revision_id in bundle.documents,'extraction document membership')
    check(at(r.period_end_at)<=at(q.cutoff_at),'extraction future period')
    matches=[x for h in bundle.hits for x in h.citations if x.evidence_id==c.evidence_id
             and x.revision_id==c.revision_id and c.quote in (x.excerpt or '')]
    check(matches and len({x.model_dump_json() for x in matches})==1,'extraction passage support')
    citation=matches[0]
    check(r.value is not None,'extraction missing value')
    # First supported source-row grammar is deliberately explicit and whole-row.
    # Do not borrow a number/date from another row or infer a table's context.
    pattern=(re.escape(r.metric)+r' = (-?\d+(?:\.\d+)?) '+re.escape(r.unit)+r'; '
        +re.escape(r.period_start_at+'/'+r.period_end_at+'; '+r.period_kind+'; '+r.scope))
    match=re.fullmatch(pattern,c.quote)
    check(match is not None,'extraction explicit source row required')
    check(Decimal(match[1])==Decimal(r.value),'extraction quoted number mismatch')
    normalized=normalize(r)
    reference=[f for f in bundle.facts if f.citation.revision_id==c.revision_id and f.formula is None
        and f.metric==r.metric and f.period_start_at==r.period_start_at and f.period_end_at==r.period_end_at
        and f.period_kind==r.period_kind and f.scope==r.scope and f.source_locator==r.locator]
    check(len(reference)==1,'extraction reference missing or ambiguous')
    f=reference[0]
    check(f.value is not None and Decimal(f.value)==Decimal(normalized['value']) and f.unit==normalized['unit'],
          'extraction number or unit mismatch')
    bad={i for group in conflicts(bundle.facts) for i in group}
    check(f.fact_id not in bad,'extraction conflicting evidence')
    return dict(text=f'{r.metric} = {f.value} {f.unit}; {r.period_start_at}/{r.period_end_at}; {r.period_kind}; {r.scope}',
        citations=[citation.model_dump(mode='json'),f.citation.model_dump(mode='json')],
        reference_fact_id=f.fact_id,extracted_fields=c.model_dump(mode='json'),
        validation='deterministic_filing_fact_and_passage_parity')
