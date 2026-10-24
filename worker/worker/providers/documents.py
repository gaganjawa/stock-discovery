"""Configured official-document acquisition into existing D3-06 evidence.

No source permission is inferred from an HTTP success. Source profiles are local,
versioned configuration, not model output. Redirects and arbitrary hosts are denied.
"""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urlsplit
import httpx
from stock_discovery_contracts.v2 import Strict, Text, Timestamp, check, digest, at
from stock_discovery_analysis.evidence import Document, EvidencePage, StructuredReport, FinancialRow, EventRow, content_hash
from stock_discovery_analysis.revisions import Revision, DocumentData
from .filings import extract_html, financial_number

PARSER_VERSION='official-document-1.0.0'
ALLOWED_HOSTS=frozenset(('www.sec.gov','www.infosys.com'))

class FilingSpec(Strict):
    source_id: Text
    account_ref: Text
    url: Text
    issuer_id: Text
    listing_id: Text
    instrument_revision_id: Text
    document_id: Text
    title: Text
    attribution: Text
    published_at: Timestamp
    category: Literal['annual_report','quarterly_report','announcement']
    format: Literal['html_table','html_text','pdf_table']
    extraction: dict
    events: tuple[EventRow,...] = ()
    expected_sha256: Text | None = None


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,text):
        if not self.hidden and text.strip():self.parts.append(text.strip())

def html_text(raw):
    check(len(raw)<=2_000_000,'html_size_limit')
    parser=VisibleText();parser.feed(raw.decode('utf-8'));parser.close()
    text='\n'.join(parser.parts)
    check(0<len(text)<=100000,'html_text_limit')
    return StructuredReport(schema_version='1.0.0',text=text,facts=(),events=())


def pdf_report(raw, profile, *, executable='pdftotext'):
    check(raw.startswith(b'%PDF-') and len(raw)<=20_000_000,'invalid_pdf')
    pages=profile['pages']
    check(isinstance(pages,list) and 0<len(pages)<=10 and len(set(pages))==len(pages),'pdf_page_limit')
    check(all(type(p) is int and 1<=p<=1000 for p in pages),'pdf_page_range')
    facts=[];texts=[]
    with tempfile.TemporaryDirectory(prefix='stk-filing-') as directory:
        source=Path(directory)/'source.pdf';source.write_bytes(raw)
        for page in pages:
            target=Path(directory)/'page.txt'
            try:
                subprocess.run([executable,'-f',str(page),'-l',str(page),'-layout','-enc','UTF-8',str(source),str(target)],
                    check=True,timeout=15,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except FileNotFoundError:raise RuntimeError('pdf_parser_not_installed') from None
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired):raise ValueError('pdf_extraction_failed') from None
            check(target.exists() and target.stat().st_size<=100000,'pdf_text_limit')
            text=target.read_text();check(bool(text.strip()),'pdf_image_only_or_empty')
            texts.append(f'PDF page {page}\n'+text)
            for rule in profile['rules']:
                if rule['page']!=page:continue
                # Period, unit and scope markers must be on the same page.
                check(all(marker and marker in text for marker in rule['markers']),'pdf_context_missing')
                matches=re.findall(rule['pattern'],text,re.MULTILINE)
                check(len(matches)==1 and isinstance(matches[0],str),'pdf_row_ambiguous')
                value=financial_number(matches[0])
                row={k:v for k,v in rule['fact'].items()}
                facts.append(FinancialRow(**row,value=value,missing_reason='not_reported' if value is None else None,
                    locator=f'pdf:page[{page}]:pattern[{digest(rule)}]'))
    check(len(facts)==len(profile['rules']) and facts,'pdf_rules_not_applied')
    return StructuredReport(schema_version='1.0.0',text='\n'.join(texts),facts=tuple(facts),events=())


class OfficialDocument:
    def __init__(self, spec, *, access, stream, previous=None, transport=None, pdf_executable='pdftotext'):
        self.spec=FilingSpec.model_validate(spec);self.access=access;self.stream=stream;self.previous=previous
        check(self.spec.source_id!='upstox','structured_api_grant_cannot_authorize_issuer_documents')
        self.pdf_executable=pdf_executable
        self.client=httpx.Client(transport=transport,trust_env=False,follow_redirects=False,timeout=30)
    def close(self):self.client.close()
    def fetch(self,cursor,limit):
        check(cursor is None and limit>=1,'single_document_page')
        s=self.spec
        check((self.stream.source_id,self.stream.account_ref,self.stream.scope)==(s.source_id,s.account_ref,'filings'),'filing_stream_mismatch')
        url=urlsplit(s.url)
        check(url.scheme=='https' and url.hostname in ALLOWED_HOSTS and not url.username and not url.password
              and url.port in (None,443) and not url.fragment,'official_source_url_required')
        check(not url.query and (url.hostname!='www.sec.gov' or url.path.startswith('/Archives/edgar/data/')),'official_document_path_required')
        self.access.require(self.stream,('acquire',))
        try:
            with self.client.stream('GET',s.url,headers={'User-Agent':'StockDiscovery private research github.com/gaganjawa/stock-discovery'}) as response:
                check(response.status_code==200,'official_source_http_'+str(response.status_code))
                raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk);check(len(raw)<=20_000_000,'document_byte_limit')
        except httpx.HTTPError:raise RuntimeError('official_source_unavailable') from None
        fetched=self.access.clock()
        check(at(s.published_at)<=at(fetched),'future_filing_publication')
        self.access.require(self.stream,('acquire','extract','derive','store'))
        raw_hash=hashlib.sha256(raw).hexdigest()
        check(s.expected_sha256 is None or raw_hash==s.expected_sha256,'source_hash_changed')
        if s.format=='html_table':report=extract_html(raw.decode('utf-8'),**s.extraction)
        elif s.format=='html_text':report=html_text(raw)
        else:report=pdf_report(bytes(raw),s.extraction,executable=self.pdf_executable)
        for event in s.events:check(event.statement in report.text,'event_quote_missing')
        report=report.model_copy(update={'events':s.events})
        body=report.model_dump_json()
        source_version=digest([PARSER_VERSION,raw_hash,s.model_dump(mode='json')])
        prior=self.previous
        if prior:
            check(prior.source_id==s.source_id and prior.data.document_id==s.document_id and prior.listing_id==s.listing_id,'prior_document_mismatch')
        if prior and prior.source_revision==source_version:
            revision=prior
        else:
            sequence=prior.sequence+1 if prior else 1
            revision=Revision(schema_version='1.0.0',revision_id='DOC-'+digest([source_version,fetched,sequence]),
                source_id=s.source_id,source_revision=source_version,sequence=sequence,listing_id=s.listing_id,
                instrument_revision_id=s.instrument_revision_id,published_at=s.published_at,available_at=fetched,fetched_at=fetched,
                availability_basis='observed',archive_evidence_ref=None,archive_revision_id=None,
                supersedes_id=prior.revision_id if prior else None,
                data=DocumentData(kind='document',document_id=s.document_id,document_type='filing',url=s.url,
                    content_hash=content_hash(body),locator='sha256:'+raw_hash+';parser:'+PARSER_VERSION,metadata_only=True))
        doc=Document(revision=revision,issuer_id=s.issuer_id,title=s.title,attribution=s.attribution,
            category=s.category,authority='issuer_primary',media_type='application/vnd.stock-evidence+json',body=body)
        return EvidencePage(cursor=None,next_cursor=None,complete=True,records=(doc.model_dump(mode='json'),))
