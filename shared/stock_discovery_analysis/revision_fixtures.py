"""Fictional paged-input fixtures for D3-03; no real instrument or provider."""
import json

from stock_discovery_contracts.rights import Grant, UseRequest
from .revisions import Revision
from .revision_storage import Page, Stream, SyntheticPageAdapter

NOW = '2026-10-15T12:00:00Z'
CUTOFF = '2026-10-15T11:00:00Z'


def fixture_grant(**changes):
    data = dict(
        schema_version='1.0.0', grant_id='SYN-D303-grant', version='fixture-1',
        source_id='SYN-source', account_ref='SYN-account', status='active',
        synthetic=True, approval_evidence_ref='fixture://permission',
        valid_from_at='2026-01-01T00:00:00Z', expires_at='2027-01-01T00:00:00Z',
        revoked_at=None, allowed_uses=['acquire','store','derive','historical_replay'],
        scopes=['universe','calendar','prices','corporate_actions','filings'],
        regions=['IN'], external_processors=[], retention_days=365,
        deletion_deadline_days=0, attribution='Fictional D3-03 fixture',
        max_units_per_operation=100, audit_tombstones_permitted=False,
    )
    data.update(changes)
    return Grant.model_validate_json(json.dumps(data))


def fixture_stream(scope):
    return Stream(stream_id='SYN-stream-'+scope,source_id='SYN-source',account_ref='SYN-account',scope=scope)


def fixture_request(scope, **changes):
    data = dict(source_id='SYN-source', account_ref='SYN-account',scope=scope,
                uses=['acquire'],region='IN',destination_region=None,processor_ref=None,
                requested_at=NOW,synthetic=True,units=100,retention_days=30,attribution_present=True)
    data.update(changes)
    return UseRequest.model_validate_json(json.dumps(data))


def fixture_records():
    def record(rid, data, **changes):
        payload = dict(schema_version='1.0.0', revision_id=rid, source_id='SYN-source',
                       source_revision=rid, sequence=1,listing_id='SYN-listing',
                       instrument_revision_id='SYN-instrument', published_at='2026-10-14T10:00:00Z',
                       available_at='2026-10-14T10:01:00Z',fetched_at='2026-10-15T10:30:00Z',
                       availability_basis='fictional_fixture',archive_evidence_ref=None,
                       archive_revision_id=None,supersedes_id=None,data=data)
        payload.update(changes)
        return Revision.model_validate(payload)
    return (
        record('SYN-instrument',dict(kind='instrument',issuer_id='SYN-issuer',symbol='FICTION',isin=None,
               series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at='2026-01-01T00:00:00Z'),instrument_revision_id=None),
        record('SYN-member',dict(kind='membership',universe_version='SYN-universe-1',valid_from_at='2026-01-01T00:00:00Z',valid_until_at=None,eligible=True,reason='fictional_member',selection_inputs_hash='a'*64)),
        record('SYN-session',dict(kind='session',calendar_version='SYN-calendar-1',opens_at='2026-10-14T03:45:00Z',closes_at='2026-10-14T10:00:00Z'),instrument_revision_id=None),
        record('SYN-candle',dict(kind='candle',interval='1d',starts_at='2026-10-14T03:45:00Z',ends_at='2026-10-14T10:00:00Z',open='100',high='110',low='90',close='105',volume=1000,adjustment_basis='raw')),
        record('SYN-action',dict(kind='action',action_id='SYN-split',action_type='split',effective_at='2026-10-15T03:45:00Z',share_ratio='2',cash_per_share=None,currency='INR')),
        record('SYN-doc',dict(kind='document',document_id='SYN-report',document_type='filing',url='https://example.invalid/fictional-report',content_hash='b'*64,locator='page 1',metadata_only=True)),
    )


def fixture_adapter(scope, page_size=1):
    records=[r.model_dump(mode='json') for r in fixture_records() if r.scope==scope]
    pages=[]
    for index in range(0,len(records),page_size):
        next_index=index+page_size
        pages.append(Page(cursor=str(index) if index else None,
                          next_cursor=str(next_index) if next_index<len(records) else None,
                          complete=next_index>=len(records),records=tuple(records[index:next_index])))
    return SyntheticPageAdapter(tuple(pages))
