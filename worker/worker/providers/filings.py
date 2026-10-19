"""Bounded HTML financial-table extraction for approved issuer disclosures.

A source-specific, versioned mapping must name the exact table header, unit and
scope markers. Ambiguous rows/columns fail, missing values remain missing. The
existing D3-06 normalizer owns arithmetic, provenance, events and persistence.
PDF/OCR is deliberately unavailable until a parser is installed and qualified.
"""
import re
from decimal import Decimal
from html.parser import HTMLParser
from stock_discovery_contracts.v2 import check
from stock_discovery_analysis.evidence import FinancialRow, StructuredReport


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]; self.table=None; self.row=None; self.cell=None
        self.hidden=0; self.text=[]; self.cells=0

    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'):self.hidden+=1
        if self.hidden:return
        if tag=='table':
            check(self.table is None,'nested_table_unsupported')
            self.table=[]
        elif tag=='tr' and self.table is not None:self.row=[]
        elif tag in ('td','th') and self.row is not None:
            check(self.cell is None,'malformed_cell')
            check(not any(k in ('rowspan','colspan') and v not in ('1',None) for k,v in attrs),'merged_cell_unsupported')
            self.cell=[]

    def handle_data(self, data):
        if self.hidden:return
        if data.strip():self.text.append(data.strip())
        if self.cell is not None:self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('script','style'):
            self.hidden=max(0,self.hidden-1)
            return
        if self.hidden:return
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
            self.cells+=1
            check(self.cells<=10000,'table_size_limit')
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row);self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table);self.table=None


def financial_number(raw):
    raw=raw.strip()
    if raw in ('','—','–','-','N/A'):return None
    negative=raw.startswith('(') and raw.endswith(')')
    if negative:raw=raw[1:-1].strip()
    check(re.fullmatch(r'-?(?:\d+|\d{1,3}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',raw) is not None,'ambiguous_financial_number')
    check(not negative or not raw.startswith('-'),'ambiguous_sign')
    value=Decimal(raw.replace(',',''))*(-1 if negative else 1)
    return format(value,'f')


def extract_html(html, *, table_header, column_header, unit_marker, scope_marker,
                 unit, scope, period_start_at, period_end_at, period_kind, rows):
    check(len(html.encode())<=2_000_000,'html_size_limit')
    check(bool(unit_marker.strip()) and bool(scope_marker.strip()),'explicit_context_markers_required')
    parser=Tables();parser.feed(html);parser.close()
    text='\n'.join(parser.text)
    check(unit_marker in text and scope_marker in text,'financial_context_missing')
    check(scope_marker.casefold()==scope and (('standalone' if scope=='consolidated' else 'consolidated') not in text.casefold()),'ambiguous_reporting_scope')
    check(unit_marker == {'INR':'INR','INR_thousand':'INR thousand','INR_lakh':'INR lakh','INR_crore':'INR crore'}.get(unit),'unsupported_unit_marker')
    matches=[(i,t) for i,t in enumerate(parser.tables) if t and t[0]==list(table_header)]
    check(len(matches)==1,'financial_table_missing_or_ambiguous')
    index,table=matches[0]
    check(table[0].count(column_header)==1,'ambiguous_period_column')
    column=table[0].index(column_header)
    facts=[]
    for metric,label in rows.items():
        matching=[(i,r) for i,r in enumerate(table[1:],1) if r and r[0]==label]
        check(len(matching)<=1,'ambiguous_financial_row')
        value=None;locator=f'html:table[{index}]:row-label[{label}]'
        if matching:
            row_index,row=matching[0]
            check(len(row)==len(table[0]),'ragged_financial_table')
            value=financial_number(row[column]);locator=f'html:table[{index}]/tr[{row_index}]/td[{column}]'
        facts.append(FinancialRow(metric=metric,value=value,missing_reason='not_reported' if value is None else None,
            unit=unit,scope=scope,period_start_at=period_start_at,period_end_at=period_end_at,
            period_kind=period_kind,locator=locator))
    check(len(text)<=100000,'extracted_text_limit')
    return StructuredReport(schema_version='1.0.0',text=text,facts=tuple(facts),events=())
