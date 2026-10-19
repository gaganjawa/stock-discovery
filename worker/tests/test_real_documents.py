"""Fabricated provider responses; not evidence of source access or parser qualification."""
from dataclasses import replace
import httpx
import pytest
from stock_discovery_analysis.revision_storage import Stream
from stock_discovery_analysis.evidence import extract,Document
from stock_discovery_analysis.evidence_storage import Access
from stock_discovery_contracts.rights import Grant,UseRequest
from worker.providers.documents import OfficialDocument,FilingSpec,pdf_report
from test_real_filings import HTML,KW

NOW='2026-10-19T12:00:00Z'

def fixture():
    grant=Grant(schema_version='1.0.0',grant_id='test-only',version='1',source_id='test-official',account_ref='test',status='active',
        synthetic=False,approval_evidence_ref='TEST ONLY NOT PERMISSION',valid_from_at='2026-01-01T00:00:00Z',expires_at='2027-01-01T00:00:00Z',
        revoked_at=None,allowed_uses=('acquire','extract','store','derive','embed'),scopes=('universe','filings','financial_facts'),regions=('IN',),external_processors=(),retention_days=365,
        deletion_deadline_days=0,attribution='Test attribution',max_units_per_operation=100,audit_tombstones_permitted=True)
    def request(s):return UseRequest(source_id=s.source_id,account_ref=s.account_ref,scope=s.scope,uses=('acquire',),region='IN',
        destination_region=None,processor_ref=None,requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
    access=Access(lambda s:grant,request,lambda d:None,lambda:NOW,frozenset(('test-official',)))
    stream=Stream(stream_id='test-official-filing',source_id='test-official',account_ref='test',scope='filings')
    spec=FilingSpec(source_id='test-official',account_ref='test',url='https://www.sec.gov/Archives/edgar/data/1067491/test.htm',issuer_id='test-issuer',
        listing_id='NSE:test',instrument_revision_id='test-identity',document_id='test-filing',title='Fabricated test annual report',attribution='Test attribution',
        published_at='2026-06-15T15:03:56Z',category='annual_report',format='html_table',extraction=KW)
    return spec,access,stream


def test_html_document_preserves_source_hash_clock_and_normalization():
    spec,access,stream=fixture()
    calls=[]
    def response(r):calls.append(r);return httpx.Response(200,text=HTML)
    adapter=OfficialDocument(spec,access=access,stream=stream,transport=httpx.MockTransport(response))
    doc=Document.model_validate_json(__import__('json').dumps(adapter.fetch(None,1).records[0]))
    assert doc.revision.available_at==NOW and doc.revision.published_at==spec.published_at
    assert doc.revision.availability_basis=='observed' and 'sha256:' in doc.revision.data.locator
    parsed=extract(doc,trusted_primary=True)
    assert parsed['facts'][0]['value']=='1234560000000'
    repeat=OfficialDocument(spec,access=access,stream=stream,previous=doc.revision,transport=httpx.MockTransport(response))
    assert repeat.fetch(None,1).records[0]['revision']['revision_id']==doc.revision.revision_id
    changed=OfficialDocument(spec,access=access,stream=stream,previous=doc.revision,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML.replace('1,23,456','1,23,457'))))
    revision=changed.fetch(None,1).records[0]['revision']
    assert revision['sequence']==2 and revision['supersedes_id']==doc.revision.revision_id


def test_missing_rights_prevents_network_and_revocation_blocks_extraction():
    spec,access,stream=fixture();calls=[]
    def response(r):calls.append(r);return httpx.Response(200,text=HTML)
    absent=replace(access,load_grant=lambda s:None)
    adapter=OfficialDocument(spec,access=absent,stream=stream,transport=httpx.MockTransport(response))
    with pytest.raises(PermissionError):adapter.fetch(None,1)
    assert not calls
    revoked=replace(access,load_grant=lambda s:None if calls else access.load_grant(s))
    adapter=OfficialDocument(spec,access=revoked,stream=stream,transport=httpx.MockTransport(response))
    with pytest.raises(PermissionError):adapter.fetch(None,1)
    assert len(calls)==1


@pytest.mark.parametrize('url',['http://www.sec.gov/x','https://www.sec.gov.evil/x','https://127.0.0.1/x','https://www.sec.gov/Archives/edgar/data/x?url=http://localhost'])
def test_no_arbitrary_fetch(url):
    spec,access,stream=fixture()
    adapter=OfficialDocument(spec.model_copy(update={'url':url}),access=access,stream=stream,
        transport=httpx.MockTransport(lambda r:pytest.fail('network must not be reached')))
    with pytest.raises(ValueError):adapter.fetch(None,1)


@pytest.mark.parametrize('status',[301,403,429])
def test_denials_do_not_retry_or_redirect(status):
    spec,access,stream=fixture();calls=[]
    def response(r):calls.append(r);return httpx.Response(status,headers={'Location':'https://www.infosys.com/x'})
    adapter=OfficialDocument(spec,access=access,stream=stream,transport=httpx.MockTransport(response))
    with pytest.raises(ValueError,match='official_source_http'):adapter.fetch(None,1)
    assert len(calls)==1


def test_pdf_parser_missing_fails_explicitly():
    with pytest.raises(RuntimeError,match='pdf_parser_not_installed'):
        pdf_report(b'%PDF-test',{'pages':[1],'rules':[]},executable='/not-installed/pdftotext')


def test_announcement_quotes_must_exist_in_fetched_text():
    from stock_discovery_analysis.evidence import EventRow
    spec,access,stream=fixture()
    event=EventRow(event_type='earnings',statement='Annual earnings announced.',status='confirmed',locator='html:body')
    spec=spec.model_copy(update={'format':'html_text','category':'announcement','events':(event,)})
    adapter=OfficialDocument(spec,access=access,stream=stream,transport=httpx.MockTransport(lambda r:httpx.Response(200,text='<p>Annual earnings announced.</p>')))
    doc=Document.model_validate_json(__import__('json').dumps(adapter.fetch(None,1).records[0]))
    assert extract(doc,trusted_primary=True)['events'][0]['status']=='confirmed'
    assert extract(doc,trusted_primary=False)['events'][0]['status']=='unverified'
    adapter=OfficialDocument(spec,access=access,stream=stream,transport=httpx.MockTransport(lambda r:httpx.Response(200,text='<p>No announcement.</p>')))
    with pytest.raises(ValueError,match='event_quote_missing'):adapter.fetch(None,1)


def test_pdf_exact_page_context_and_number(monkeypatch):
    from pathlib import Path
    import worker.providers.documents as module
    def fake(command,**kw):Path(command[-1]).write_text('Consolidated INR crore FY2026\nRevenue   1,234\n')
    monkeypatch.setattr(module.subprocess,'run',fake)
    rule={'page':3,'markers':['Consolidated','INR crore','FY2026'],'pattern':r'^Revenue\s+([0-9,]+)$',
        'fact':dict(metric='revenue',unit='INR_crore',scope='consolidated',period_start_at='2025-04-01T00:00:00Z',period_end_at='2026-03-31T00:00:00Z',period_kind='annual')}
    report=pdf_report(b'%PDF-test',{'pages':[3],'rules':[rule]})
    assert report.facts[0].value=='1234' and report.facts[0].locator.startswith('pdf:page[3]')
    rule['markers']=['USD']
    with pytest.raises(ValueError,match='pdf_context_missing'):pdf_report(b'%PDF-test',{'pages':[3],'rules':[rule]})
