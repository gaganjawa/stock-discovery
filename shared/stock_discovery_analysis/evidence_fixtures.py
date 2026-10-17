"""Fictional automatic filing/news feed. No credentials or external requests."""
import json
from .evidence import Document, EvidencePage, MockEvidenceAdapter, content_hash
from .evidence_storage import Access
from .revision_fixtures import fixture_grant,fixture_request,fixture_stream,fixture_records,NOW
from .revision_storage import Stream,Page,ingest_page


def evidence_grant(**changes):
    return fixture_grant(grant_id='SYN-D306-grant',
        allowed_uses=['acquire','store','extract','derive','historical_replay'],
        scopes=['universe','calendar','prices','corporate_actions','filings','news','financial_facts'],**changes)


def evidence_access(clock=lambda:NOW,load_grant=None,audit=lambda d:None):
    return Access(load_grant=load_grant or (lambda s:evidence_grant()),
        request_for=lambda s:fixture_request(s.scope,source_id=s.source_id,account_ref=s.account_ref),audit=audit,clock=clock,primary_source_ids=frozenset({'SYN-source'}))


def evidence_stream(scope='filings'):
    return Stream(stream_id='SYN-D306-'+scope,source_id='SYN-source',account_ref='SYN-account',scope=scope)


def document_fixture(*,rid='SYN-E-report',category='annual_report',sequence=1,supersedes_id=None):
    announcement='The issuer confirms its annual earnings release.'
    facts=[]
    for metric,value in dict(revenue='100',earnings='10',operating_cash_flow='15',capital_expenditure='2',
                              debt='20',cash='5',equity='80',assets='100',liabilities='20',diluted_shares='100').items():
        instant=metric in ('debt','cash','equity','assets','liabilities')
        facts.append(dict(metric=metric,value=value,missing_reason=None,unit='shares' if metric=='diluted_shares' else 'INR_lakh',
            period_start_at='2025-12-31T00:00:00Z' if instant else '2025-10-01T00:00:00Z' if category=='quarterly_report' else '2025-01-01T00:00:00Z',period_end_at='2025-12-31T00:00:00Z',
            period_kind='instant' if instant else 'quarter' if category=='quarterly_report' else 'annual',scope='consolidated',locator='provider-table:'+metric))
    body=json.dumps(dict(schema_version='1.0.0',text=announcement,facts=[] if category=='news' else facts,
        events=[dict(event_type='earnings',statement=announcement,status='confirmed',locator='announcement paragraph 1')]))
    revision=fixture_records()[-1].model_dump()
    revision.update(revision_id=rid,source_revision=rid,sequence=sequence,supersedes_id=supersedes_id)
    revision['data'].update(document_id='SYN-evidence-'+category,document_type='news' if category=='news' else 'filing',content_hash=content_hash(body))
    return Document.model_validate(dict(revision=revision,issuer_id='SYN-issuer',title='Fictional annual evidence',
        attribution=evidence_grant().attribution,category=category,authority='secondary' if category=='news' else 'issuer_primary',
        media_type='application/vnd.stock-evidence+json',body=body))


def adapter_fixture(document=None):
    document=document or document_fixture()
    return MockEvidenceAdapter((EvidencePage(cursor=None,next_cursor=None,complete=True,records=(document.model_dump(mode='json'),)),))


def seed_identity(conn):
    # Mock automatic universe feed is deliberately independent of filing content.
    stream=fixture_stream('universe')
    records=tuple(r.model_dump(mode='json') for r in fixture_records() if r.scope=='universe')
    return ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=records),
        load_grant=evidence_grant,request=fixture_request('universe'),audit=lambda d:None)


def scheduled_handlers(config):
    """Explicit fictional worker mode: automatically poll filings and news feeds."""
    from .schedule_fixtures import handlers as base_handlers
    from .evidence_storage import evidence_handler
    from .revision_fixtures import fixture_adapter
    from .revision_storage import ingest_next,freeze_snapshot
    installed=base_handlers(config)  # Checks pinned synthetic mode and input identity.

    def snapshot(conn,stream,now):
        streams=tuple(fixture_stream(s) for s in ('universe','calendar','prices','corporate_actions'))+(stream,)
        return freeze_snapshot(conn,streams=streams,load_grant=lambda s:evidence_grant(),
            requests={s.stream_id:fixture_request(s.scope,requested_at=now) for s in streams},audit=lambda d:None,
            mode='synthetic',cutoff=now,created_at=now,universe_version='SYN-universe-1',calendar_version='SYN-calendar-1')

    feeds=tuple((evidence_stream(scope),adapter_fixture(document_fixture(rid=rid,category=category)))
                for scope,rid,category in (('filings','SYN-E-report','annual_report'),('news','SYN-E-news','news')))

    def poll(conn,job,clock):
        for scope in ('universe','calendar','prices','corporate_actions'):
            adapter=fixture_adapter(scope)
            for _ in adapter.pages:
                ingest_next(conn,fixture_stream(scope),adapter,clock=clock,load_grant=evidence_grant,
                    request=fixture_request(scope,requested_at=clock()),audit=lambda d:None)
        results=[]
        for stream,adapter in feeds:
            handler=evidence_handler(stream,adapter,evidence_access(clock=clock),config=config,read_authorized_snapshot=snapshot)
            result,_=handler(conn,job,clock)
            results.append(result)
        return dict(fixture_only=True,sources=results,status='partial' if any(r['status']=='partial' for r in results) else 'complete'),None

    installed['event_poll']=poll
    return installed
