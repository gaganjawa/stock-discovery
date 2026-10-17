"""STK-046–051: bounded provider-neutral evidence and deterministic extraction.

No network, PDF execution, AI, or inferred financial values. Unsupported source
formats are explicit failures, never silently treated as extracted reports.
"""
import hashlib
import json
import re
from decimal import Decimal, Context, localcontext
from typing import Annotated, Literal, Protocol

from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, Number, Timestamp, check, digest, at
from .revisions import Revision

PARSER_VERSION = 'structured-evidence-1.0.0'
METRICS = Literal['revenue','earnings','operating_cash_flow','capital_expenditure',
                  'debt','cash','equity','assets','liabilities','diluted_shares',
                  'operating_margin','net_margin']
EVENTS = Literal['earnings','restatement','default','auditor_change','regulatory_action']


def content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class FinancialRow(Strict):
    metric: METRICS
    value: Number | None
    missing_reason: Text | None
    unit: Literal['INR','INR_thousand','INR_lakh','INR_crore','shares','percent','ratio']
    period_start_at: Timestamp
    period_end_at: Timestamp
    period_kind: Literal['annual','quarter','instant']
    scope: Literal['consolidated','standalone']
    locator: Text

    @model_validator(mode='after')
    def valid(self):
        check((self.value is None)==(self.missing_reason is not None),'explicit missing value')
        days=(at(self.period_end_at)-at(self.period_start_at)).days
        check((days==0) if self.period_kind=='instant' else (330<=days<=371 if self.period_kind=='annual' else 75<=days<=100),'financial period')
        if self.value is not None:
            check(len(Decimal(self.value).as_tuple().digits)<=28,'financial precision bound')
        balances={'assets','liabilities','equity','debt','cash'}
        check((self.metric in balances)==(self.period_kind=='instant'),'metric period mismatch')
        allowed={'diluted_shares':{'shares'},'operating_margin':{'percent','ratio'},'net_margin':{'percent','ratio'}}.get(self.metric,{'INR','INR_thousand','INR_lakh','INR_crore'})
        check(self.unit in allowed,'metric unit mismatch')
        return self


class EventRow(Strict):
    event_type: EVENTS
    statement: Annotated[str,Field(min_length=1,max_length=2000)]
    status: Literal['confirmed','unverified']
    locator: Text


class StructuredReport(Strict):
    schema_version: Literal['1.0.0']
    text: Annotated[str,Field(min_length=1,max_length=100000)]
    facts: Annotated[tuple[FinancialRow,...],Field(max_length=80)]
    events: Annotated[tuple[EventRow,...],Field(max_length=20)]


class Document(Strict):
    revision: Revision
    issuer_id: Text
    title: Text
    attribution: Text
    category: Literal['announcement','annual_report','quarterly_report','news']
    authority: Literal['issuer_primary','secondary']
    media_type: Literal['text/plain','application/vnd.stock-evidence+json']
    body: Annotated[str,Field(min_length=1,max_length=150000)]

    @model_validator(mode='after')
    def valid(self):
        check(self.revision.data.kind=='document','document revision required')
        check(self.revision.data.content_hash==content_hash(self.body),'document content hash')
        check((self.category=='news')==(self.revision.data.document_type=='news'),'document category/scope')
        check(self.category!='news' or self.authority=='secondary','news is not issuer confirmation')
        return self


class EvidencePage(Strict):
    cursor: Text | None
    next_cursor: Text | None
    complete: bool
    records: Annotated[tuple[dict,...],Field(max_length=10)]

    @model_validator(mode='after')
    def bounded(self):
        check(self.complete==(self.next_cursor is None),'page completion')
        check(self.complete or self.cursor!=self.next_cursor,'page cursor progress')
        check(len(json.dumps(self.records).encode())<=2000000,'page byte limit')
        return self


class EvidenceAdapter(Protocol):
    def fetch(self, cursor: str | None, limit: int) -> EvidencePage: ...


class MockEvidenceAdapter:
    def __init__(self,pages):
        self.pages={p.cursor:p for p in pages}
        check(len(self.pages)==len(pages),'duplicate cursor')
        self.calls=0
        for page in pages:
            for raw in page.records:
                check(raw.get('revision',{}).get('availability_basis')=='fictional_fixture','mock only')

    def fetch(self,cursor,limit):
        self.calls+=1
        page=self.pages[cursor]
        check(len(page.records)<=limit,'page quota')
        return page


def normalize(row):
    scale={'INR':Decimal(1),'INR_thousand':Decimal(1000),'INR_lakh':Decimal(100000),
           'INR_crore':Decimal(10000000),'shares':Decimal(1),'percent':Decimal('0.01'),'ratio':Decimal(1)}[row.unit]
    with localcontext(Context(prec=38)):
        value=None if row.value is None else format(Decimal(row.value)*scale,'f')
    unit='shares' if row.unit=='shares' else 'ratio' if row.unit in ('percent','ratio') else 'INR'
    return {**row.model_dump(), 'source_value':row.value,'source_unit':row.unit,'value':value,'unit':unit}


def extract(document, *, trusted_primary=False):
    """Pure bounded parsing. Caller must authorize extract before calling."""
    if document.media_type=='text/plain':
        text=document.body
        report=None
        facts=[]
        events=[]
    else:
        report=StructuredReport.model_validate_json(document.body)
        text=report.text
        facts=[normalize(row) for row in report.facts]
        events=[row.model_dump() for row in report.events]
    keys=set()
    for row in facts:
        check(at(row['period_end_at'])<=at(document.revision.published_at),'future financial period')
        key=tuple(row[k] for k in ('metric','period_start_at','period_end_at','period_kind','scope'))
        check(key not in keys,'duplicate/conflicting financial fact')
        keys.add(key)
    # Reconcile only identical periods/scopes; never splice quarterly and annual data.
    groups={}
    for row in facts:
        key=tuple(row[k] for k in ('period_start_at','period_end_at','period_kind','scope'))
        groups.setdefault(key,{})[row['metric']]=row
    for rows in groups.values():
        if all(k in rows and rows[k]['value'] is not None for k in ('assets','liabilities','equity')):
            with localcontext(Context(prec=38)):
                check(Decimal(rows['assets']['value'])==Decimal(rows['liabilities']['value'])+Decimal(rows['equity']['value']),'balance sheet reconciliation')
        if all(k in rows and rows[k]['value'] is not None for k in ('revenue','earnings','net_margin')):
            with localcontext(Context(prec=38)):
                revenue=Decimal(rows['revenue']['value'])
                check(revenue!=0,'undefined reported margin')
                check(Decimal(rows['net_margin']['value'])*revenue==Decimal(rows['earnings']['value']),'margin reconciliation')
    chunks=[]
    for start in range(0,len(text),2000):
        end=min(start+2000,len(text))
        chunk=dict(document_revision_id=document.revision.revision_id,parser_version=PARSER_VERSION,
            locator=('$.text' if report else 'body')+f':chars[{start}:{end}]',start=start,end=end,text=text[start:end])
        chunks.append(dict(chunk_id=digest(chunk),**chunk))
    for index,row in enumerate(facts):
        row['source_locator']=row.pop('locator')
        row['locator']=f'$.facts[{index}]'
        row['document_revision_id']=document.revision.revision_id
        row['parser_version']=PARSER_VERSION
        row['fact_id']=digest(row)
    # Derived margins are labelled calculations, never invented reported facts.
    for group in groups.values():
        if 'net_margin' in group or not {'earnings','revenue'} <= set(group):
            continue
        revenue,earnings=group['revenue'],group['earnings']
        # The normalized row dictionaries now carry stable source-fact IDs.
        missing=revenue['value'] is None or earnings['value'] is None or Decimal(revenue['value'])==0
        with localcontext(Context(prec=38)):
            value=None if missing else format(Decimal(earnings['value'])/Decimal(revenue['value']),'f')
        derived={k:revenue[k] for k in ('period_start_at','period_end_at','period_kind','scope','document_revision_id','parser_version')}
        derived.update(metric='net_margin',value=value,unit='ratio',missing_reason='undefined_or_missing_denominator' if missing else None,
            source_value=None,source_unit=None,source_locator=None,locator='derived:net_margin',
            formula='earnings/revenue',input_fact_ids=[earnings['fact_id'],revenue['fact_id']])
        derived['fact_id']=digest(derived)
        facts.append(derived)
    for index,row in enumerate(events):
        check(row['statement'] in text,'event quote not in source text')
        # A classifier/provider label alone never promotes secondary news to a confirmed fact.
        confirmed=row['status']=='confirmed' and document.authority=='issuer_primary' and trusted_primary
        row.update(status='confirmed' if confirmed else 'unverified',document_revision_id=document.revision.revision_id,
                   source_locator=row['locator'],locator=f'$.events[{index}]',parser_version=PARSER_VERSION)
        normalized=' '.join(re.findall(r'\w+',row['statement'].casefold()))
        row['event_key']=digest([document.issuer_id,row['event_type'],normalized])
        row['claim_id']=digest(row)
    return dict(parser_version=PARSER_VERSION,chunks=chunks,facts=facts,events=events,
                extraction_status='structured' if report else 'text_only',
                text_fingerprint=content_hash(' '.join(re.findall(r'\w+',text.casefold()))))


def statement_from_evidence(bundle,*,period_start_at,period_end_at,period_kind,scope):
    """Map normalized report facts to D3-05 without inferring absent metrics."""
    from stock_discovery_contracts.v2 import Evidence
    from .quant_policies import Statement
    doc=Document.model_validate_json(json.dumps(bundle['document']))
    check(doc.category in ('annual_report','quarterly_report'),'financial report required')
    check((doc.category=='annual_report')==(period_kind=='annual'),'report period category')
    revision=doc.revision
    values={}
    fields=('revenue','earnings','operating_cash_flow','capital_expenditure','debt','cash','equity','diluted_shares')
    for field in fields:
        is_balance=field in ('debt','cash','equity')
        matches=[f for f in bundle['facts'] if f['metric']==field and f['scope']==scope and
            f['period_end_at']==period_end_at and f['period_kind']==('instant' if is_balance else period_kind)
            and f['period_start_at']==(period_end_at if is_balance else period_start_at)]
        check(len(matches)<=1,'ambiguous statement fact')
        values[field]=matches[0]['value'] if matches else None
    evidence=Evidence(evidence_id=revision.revision_id,revision_id=revision.revision_id,instrument_id=revision.listing_id,
        kind='filing',source_ref=revision.source_id,source_version=revision.source_revision,locator=revision.data.url,
        published_at=revision.published_at,available_at=revision.available_at,fetched_at=revision.fetched_at,
        period_end_at=period_end_at,availability_basis=revision.availability_basis,
        archive_verification_ref=revision.archive_evidence_ref,summary=doc.title+'; '+doc.attribution)
    return Statement(revision_id=revision.revision_id,instrument_id=revision.listing_id,
        period_start_at=period_start_at,period_end_at=period_end_at,period_kind=period_kind,scope=scope,
        currency='INR',monetary_unit='INR',evidence=evidence,**values)
