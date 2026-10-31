"""Explicit two-level pipe-table spans captured from a financial disclosure.

Only the pinned observed layout is supported. This does not reconstruct HTML,
assert original-file integrity, infer currency or authorize production ingestion.
"""
import re
from stock_discovery_contracts.v2 import check,digest
from .filings import financial_number


def cell_reference(text,profile,row_label,period_label):
    check(digest(text)==profile['text_hash'],'table_snapshot_changed')
    check(profile['layout']=='pipe-two-groups-two-years-1','unsupported_table_layout')
    for marker in profile['context_markers']:
        check(marker in text,'table_context_missing')
    rows=[[c.strip() for c in line.split('|')] for line in text.splitlines() if '|' in line]
    check(len(rows)>=3 and rows[:2]==profile['headers'],'table_headers_changed')
    top,years=rows[:2]
    check(len(top)==3 and len(years)==5 and not years[0] and all(re.fullmatch(r'20\d{2}',x) for x in years[1:]),'table_header_shape')
    columns=[top[1 if i<2 else 2]+' '+year for i,year in enumerate(years[1:])]
    check(len(set(columns))==4,'ambiguous_table_periods')
    matching=[r for r in rows[2:] if r[0]==row_label]
    check(len(matching)==1,'missing_or_conflicting_table_row')
    row=matching[0];check(len(row)==5,'table_row_shape')
    check(columns.count(period_label)==1,'table_period_missing')
    index=columns.index(period_label)+1
    number=financial_number(row[index]);check(number is not None,'table_value_missing')
    return dict(row_label=row_label,period=period_label,value=number,unit=profile['unit'],scope=profile['scope'],
        evidence_id=profile['evidence_id'],source_hash=profile['text_hash'],
        locator='row:'+row_label+'/column:'+period_label,quote=' | '.join(row))


def verify_cell(raw,reference):
    """No model text/number becomes a fact unless every source field matches."""
    from decimal import Decimal
    check(isinstance(raw,dict) and set(raw)=={'status','value','unit','scope','period','evidence_id','quote'},'table_response_fields')
    check(raw['status']=='extracted','table_model_abstained')
    check(isinstance(raw['value'],str),'table_number_type')
    # Same financial-number parser as deterministic filing acquisition, including
    # thousands separators/parentheses; no float coercion or scale guessing.
    value=financial_number(raw['value'])
    check(value is not None and Decimal(value)==Decimal(reference['value']),'table_numeric_mismatch')
    for field in ('unit','scope','period','evidence_id','quote'):
        check(raw[field]==reference[field],'table_'+field+'_mismatch')
    return dict(reference,validation='exact_table_cell_and_span',actionable=False,publication_authorized=False)
