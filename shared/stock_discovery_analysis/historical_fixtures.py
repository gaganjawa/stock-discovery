"""Explicit, opt-in fictional filings for Replay development. No market claims."""
import json
from .revision_fixtures import fixture_grant,fixture_request
from .revision_storage import Stream,Page,ingest_page
from .revisions import Revision
from .evidence import Document,EvidencePage,content_hash
from .evidence_storage import Access,ingest_evidence_page
from .publication_store import now

SOURCE='SYN-replay-financial'
ACCOUNT='SYN-replay-account'


def seed(conn,instrument):
    if not instrument.startswith('SYN-'):raise ValueError('synthetic_replay_required')
    grant=fixture_grant(grant_id='SYN-replay-grant',source_id=SOURCE,account_ref=ACCOUNT,
        valid_from_at='2020-01-01T00:00:00Z',expires_at='2030-01-01T00:00:00Z',
        allowed_uses=('acquire','store','extract','derive','historical_replay'),
        scopes=('universe','filings','financial_facts'),attribution='FICTIONAL REPLAY DEVELOPMENT ONLY')
    access=Access(load_grant=lambda s:grant,request_for=lambda s:fixture_request(s.scope,source_id=SOURCE,
        account_ref=ACCOUNT,requested_at=now()),audit=lambda d:None,clock=now,primary_source_ids=frozenset({SOURCE}))
    def revision(rid,data,when,sequence=1,supersedes=None):
        return Revision(schema_version='1.0.0',revision_id=rid,source_id=SOURCE,source_revision='upstream-'+rid,
            sequence=sequence,listing_id=instrument,instrument_revision_id=None if data['kind']=='instrument' else instrument+'-financial-identity',
            published_at=when,available_at=when,fetched_at=when,availability_basis='fictional_fixture',
            archive_evidence_ref=None,archive_revision_id=None,supersedes_id=supersedes,data=data)
    rid=instrument+'-financial-identity'
    identity=revision(rid,dict(kind='instrument',issuer_id=instrument,symbol=instrument,isin=None,series='EQ',
        status='active',lot_size=1,tick_size='0.01',effective_at='2020-01-01T00:00:00Z'),'2020-01-01T00:00:00Z')
    stream=Stream(stream_id=rid,source_id=SOURCE,account_ref=ACCOUNT,scope='universe')
    ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(identity.model_dump(mode='json'),)),
        load_grant=lambda:grant,request=access.request_for(stream),audit=lambda d:None)
    for year,values,known,sequence in ((2023,('100','10','15'),'2025-05-05T00:00:00Z',1),
        (2024,('120','15','12'),'2025-05-06T00:00:00Z',1),
        (2024,('125','14','12'),'2025-07-01T00:00:00Z',2),
        (2025,('140','18','16'),'2026-01-10T00:00:00Z',1)):
        docid=f'{instrument}-fictional-annual-{year}';rid=f'{docid}-v{sequence}'
        facts=[dict(metric=m,value=v,missing_reason=None,unit='INR',period_start_at=f'{year}-01-01T00:00:00Z',
            period_end_at=f'{year}-12-31T23:59:59Z',period_kind='annual',scope='consolidated',locator='fictional-row:'+m)
            for m,v in zip(('revenue','earnings','operating_cash_flow'),values)]
        text='FICTIONAL REPLAY DEVELOPMENT ONLY. Invented revenue, earnings and operating cash flow.'
        body=json.dumps(dict(schema_version='1.0.0',text=text,facts=facts,events=[]))
        rev=revision(rid,dict(kind='document',document_id=docid,document_type='filing',url='https://example.invalid/'+rid,
            content_hash=content_hash(body),locator='fictional annual table',metadata_only=True),known,sequence,
            f'{docid}-v1' if sequence==2 else None)
        doc=Document(revision=rev,issuer_id=instrument,title='FICTIONAL annual statement',attribution=grant.attribution,
            category='annual_report',authority='issuer_primary',media_type='application/vnd.stock-evidence+json',body=body)
        stream=Stream(stream_id=rid,source_id=SOURCE,account_ref=ACCOUNT,scope='filings')
        result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,
            records=(doc.model_dump(mode='json'),)),access=access)
        if result['quarantined']:raise ValueError('synthetic_financial_fixture_rejected')
