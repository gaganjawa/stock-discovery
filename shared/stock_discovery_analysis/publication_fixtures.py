"""Pinned D3-09 fictional universe. Automatic local ingestion, no real activation."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
from .quant_fixtures import fixture_inputs, fixture_policy
from .evidence_fixtures import document_fixture, adapter_fixture, evidence_grant
from .evidence_storage import Access, ingest_next_evidence
from .revision_storage import Stream, Page, ingest_page
from .revision_fixtures import fixture_records, fixture_request
from .evidence import Document, content_hash
from stock_discovery_contracts.v2 import at

VERSION = 'SYN-D309-1'
SOURCE = 'SYN-D309-source'
CASES = ('ready', 'waiting', 'risk', 'missing', 'conflict')


def access_for(conn, clock):
    def grant(stream):
        row = conn.execute('SELECT revoked FROM discovery.publication_source_controls WHERE source_id=%s', (SOURCE,)).fetchone()
        return evidence_grant(source_id=SOURCE, valid_from_at='2020-01-01T00:00:00Z',
            expires_at='2099-01-01T00:00:00Z', revoked_at=clock() if row and row[0] else None, status='revoked' if row and row[0] else 'active').model_copy(update={'grant_id':'SYN-D309-permission'})
    return Access(load_grant=grant, request_for=lambda s: fixture_request(s.scope, source_id=SOURCE),
                  audit=lambda d: None, clock=clock, primary_source_ids=frozenset({SOURCE}))


def inputs(profile, case):
    data = fixture_inputs(profile)
    listing = 'SYN-D309-' + case.upper()
    data['instrument_id'] = listing
    data['calendar']=replace(data['calendar'],provenance=replace(data['calendar'].provenance,source_ref=SOURCE))
    data['bars'] = tuple(replace(b, instrument_id=listing,provenance=replace(b.provenance,source_ref=SOURCE)) for b in data['bars'] if b.instrument_id=='SYN-ALPHA')
    data['coverage'] = tuple(c.model_copy(update={'evidence': c.evidence.model_copy(update={
        'instrument_id':listing, 'source_ref':SOURCE, 'evidence_id':listing+'-'+c.requirement,
        'revision_id':listing+'-'+c.requirement})}) for c in data['coverage'])
    data['statements'] = tuple(s.model_copy(update={'instrument_id':listing,'revision_id':listing+'-'+s.revision_id,
        'evidence':s.evidence.model_copy(update={'instrument_id':listing,'source_ref':SOURCE,
            'revision_id':listing+'-'+s.revision_id,'evidence_id':listing+'-'+s.revision_id})}) for s in data['statements'])
    if case=='conflict':
        original=data['statements'][-1]
        revision=original.revision_id+'-conflict'
        data['statements']+= (original.model_copy(update={'revision_id':revision,'revenue':'8888',
            'evidence':original.evidence.model_copy(update={'revision_id':revision,'evidence_id':revision})}),)
    if case=='risk': data['risk_prohibited']=True
    if case=='missing': data['coverage']=tuple(c for c in data['coverage'] if c.requirement!='filings')
    if case=='waiting':
        if profile=='swing':
            data['bars']=tuple(replace(b,volume=1) if b.ends_at.strftime('%Y-%m-%d')==data['cutoff'][:10] else b for b in data['bars'])
        else:
            data['bars']=tuple(replace(b,open=b.open*10,high=b.high*10,low=b.low*10,close=b.close*10) for b in data['bars'])
    return data, fixture_policy(profile)


def ingest_candidate(conn, data, case, access):
    """Feed exact same annual statements to D3-05 and D3-06; preserve units/clocks."""
    listing=data['instrument_id']; issuer=listing+'-issuer'; cutoff=data['cutoff']
    known=(at(cutoff)-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    stream=Stream(stream_id=listing+'-identity',source_id=SOURCE,account_ref='SYN-account',scope='universe')
    instrument=fixture_records()[0].model_dump(mode='json')
    instrument.update(revision_id=listing+'-identity',source_id=SOURCE,listing_id=listing,
        published_at=known,available_at=known,fetched_at=known)
    instrument['data'].update(issuer_id=issuer,symbol=listing,effective_at='2020-01-01T00:00:00Z')
    ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(instrument,)),
        load_grant=lambda:access.load_grant(stream),request=access.request_for(stream),audit=access.audit)
    docs=[]
    for category in ('annual_report','news'):
        if case=='missing' and category=='annual_report': continue
        statement=data['statements'][-1]
        body={'schema_version':'1.0.0','text':f'Fictional {listing} earnings disclosure. Local engineering fixture only.', 'facts':[], 'events':[]}
        if category=='annual_report':
            for metric in ('revenue','earnings'):
                body['facts'].append(dict(metric=metric,value=getattr(statement,metric),missing_reason=None,unit='INR',
                    period_start_at=statement.period_start_at,period_end_at=statement.period_end_at,
                    period_kind='annual',scope='consolidated',locator='fixture-table:'+metric))
        if case=='waiting' and category=='annual_report':
            body['events']=[dict(event_type='earnings',statement=body['text'],status='confirmed',locator='fixture announcement')]
        raw=document_fixture().model_dump(mode='json')
        raw.update(issuer_id=issuer,title=f'{listing} fictional {category}',category=category,
                   body=json.dumps(body),attribution=evidence_grant().attribution,
                   authority='secondary' if category=='news' else 'issuer_primary')
        rid=listing+'-'+category
        raw['revision'].update(revision_id=rid,source_revision=rid,source_id=SOURCE,listing_id=listing,
            instrument_revision_id=listing+'-identity',published_at=known,available_at=known,fetched_at=known)
        raw['revision']['data'].update(document_id=rid,document_type='news' if category=='news' else 'filing',
            content_hash=content_hash(raw['body']),url='https://example.invalid/'+rid)
        docs.append(raw)
        if case=='conflict' and category=='annual_report':
            other=json.loads(json.dumps(raw)); other['revision'].update(revision_id=rid+'-conflict',source_revision=rid+'-conflict')
            other['revision']['data']['document_id']=rid+'-conflict'
            changed=json.loads(other['body']); changed['facts'][0]['value']='9999'
            other['body']=json.dumps(changed); other['revision']['data']['content_hash']=content_hash(other['body']);docs.append(other)
    for raw in docs:
        doc=Document.model_validate_json(json.dumps(raw))
        stream=Stream(stream_id=doc.revision.revision_id,source_id=SOURCE,account_ref='SYN-account',scope=doc.revision.scope)
        result=ingest_next_evidence(conn,stream,adapter_fixture(doc),access=access)
        if result.get('quarantined'): raise ValueError('fixture ingestion quarantined')
    return issuer
