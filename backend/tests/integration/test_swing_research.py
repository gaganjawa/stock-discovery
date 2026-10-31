"""STK-079 synthetic PostgreSQL acceptance. NO real NSE/provider evidence."""
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from stock_discovery_contracts.rights import Grant
from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis.revisions import Revision
from stock_discovery_analysis.revision_storage import Stream, Page, ingest_page
from stock_discovery_analysis.evidence import Document, EvidencePage, content_hash
from stock_discovery_analysis.evidence_storage import ingest_evidence_page
from stock_discovery_analysis.real_access import SourceConfig, source_access
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.swing_research import research, SwingConfig, CoverageReview, SCOPES
from stock_discovery_analysis.risk import demo_profile
from stock_discovery_analysis.grant_fences import restrict

pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')


@pytest.fixture
def isolated_url():
    yield from _isolated_url.__wrapped__()


def stamp(t):return t.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def setup(conn,tmp_path,case='buy'):
    # Deliberately invented daily calendar and TEST identity; only observed-mode
    # contracts are exercised, never represented as actual NSE market observations.
    point=conn.execute('SELECT clock_timestamp()').fetchone()[0].replace(microsecond=0)-timedelta(seconds=2)
    cutoff=stamp(point); start=point-timedelta(days=29,hours=5)
    grant=Grant(schema_version='1.0.0',grant_id='TEST-G1',version='1',source_id='test-only',account_ref='test',
        status='active',synthetic=False,approval_evidence_ref='SYNTHETIC TEST ONLY',valid_from_at=stamp(start-timedelta(days=2)),
        expires_at=stamp(point+timedelta(days=60)),revoked_at=None,allowed_uses=('acquire','store','derive','extract'),
        scopes=tuple(SCOPES.values()),regions=('IN',),external_processors=(),retention_days=365,deletion_deadline_days=0,
        attribution='SYNTHETIC TEST ONLY',max_units_per_operation=100,audit_tombstones_permitted=False)
    if case=='no_acquire':grant=grant.model_copy(update={'allowed_uses':('store','derive','extract')})
    if case=='adverse_event':grant=grant.model_copy(update={'scopes':grant.scopes+('financial_facts',)})
    other=grant.model_copy(update={'grant_id':'TEST-G2','source_id':'test-other'})
    grants=[grant,other] if case in ('mixed','mixed_no_filing') else [grant]
    if case=='historical_parent':
        grants.append(grant.model_copy(update={'grant_id':'TEST-HISTORICAL','account_ref':'history'}))
    path=tmp_path/'grants.json';path.write_text(json.dumps([g.model_dump(mode='json') for g in grants]))
    sources=SourceConfig(grant_file=str(path),retention_days=365,primary_source_ids=('test-only',))
    access=source_access(sources,lambda:cutoff)
    def revision(rid,data,when=None,source='test-only'):
        when=when or cutoff
        return Revision(schema_version='1.0.0',revision_id=rid,source_id=source,source_revision='upstream-'+rid,
            sequence=1,listing_id='NSE' if data['kind']=='session' else 'NSE:TEST',
            instrument_revision_id=None if data['kind'] in ('session','instrument') else 'identity',
            published_at=when,available_at=when,fetched_at=when,availability_basis='observed',
            archive_evidence_ref=None,archive_revision_id=None,supersedes_id=None,data=data)
    identity=revision('identity',dict(kind='instrument',issuer_id='test-issuer',symbol='TEST',isin='INE000TEST00',series='EQ',
        status='suspended' if case=='ineligible' else 'active',lot_size=10,tick_size='0.05',effective_at=stamp(start-timedelta(days=1))),stamp(start-timedelta(days=1)))
    rows=[identity,revision('member',dict(kind='membership',universe_version='test-only',valid_from_at=stamp(start),
        valid_until_at=stamp(point+timedelta(days=1)),eligible=True,reason='TEST ONLY',selection_inputs_hash=digest('test')))]
    for i in range(30):
        end=point-timedelta(days=29-i,hours=1);opened=end-timedelta(hours=4)
        if case!='calendar_gap' or i!=14:
            rows.append(revision('session-'+str(i),dict(kind='session',calendar_version='test-only',opens_at=stamp(opened),closes_at=stamp(end)),stamp(start-timedelta(days=1))))
        if case=='short' and i==0:continue
        close=D(100)+i if case!='wait' else D(100)
        if i==29 and case!='wait':close+=D(3)
        narrow=case=='narrow_range'
        if narrow:close=D(1000)+D('.05')*i+(D('.15') if i==29 else 0)
        rows.append(revision('bar-'+str(i),dict(kind='candle',interval='1d',starts_at=stamp(opened),ends_at=stamp(end),
            open=str(close-(D('.05') if narrow else D(1))),high=str(close+(D('.05') if narrow else D(1))),
            low=str(close-(D('.10') if narrow else D(2))),close=str(close),volume=2000 if i==29 else 1000,
            adjustment_basis='split_bonus_adjusted' if case=='adjusted' else 'raw'),source='test-other' if case=='mixed' and i==14 else 'test-only'))
    if case=='action':
        rows.append(revision('action',dict(kind='action',action_id='TEST-action',action_type='split',effective_at=cutoff,
            share_ratio='2',cash_per_share=None,currency='INR')))
    def persist(rows):
        scopes=list(dict.fromkeys((r.source_id,r.scope) for r in rows))
        for source,scope in scopes:
            account='history' if case=='historical_parent' and scope=='universe' else 'test'
            stream=Stream(stream_id=source+'-'+scope,source_id=source,account_ref=account,scope=scope)
            g=next(g for g in grants if (g.source_id,g.account_ref)==(source,account))
            result=ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,
                records=tuple(r.model_dump(mode='json') for r in rows if (r.source_id,r.scope)==(source,scope))),
                load_grant=lambda:g,request=access.request_for(stream),audit=lambda d:None)
            assert result['quarantined']==0
    persist(rows)
    def document(rid,body):
        rev=revision(rid,dict(kind='document',document_id=rid,document_type='filing',url='https://test.invalid/'+rid,
            content_hash=content_hash(body),locator='test',metadata_only=True))
        doc=Document(revision=rev,issuer_id='test-issuer',title='Synthetic test',attribution='SYNTHETIC TEST ONLY',
            category='annual_report' if rid=='filing' else 'coverage_review',authority='issuer_primary' if rid=='filing' else 'secondary',media_type='application/vnd.stock-evidence+json'
            if case=='adverse_event' and rid=='filing' else 'text/plain',body=body)
        stream=Stream(stream_id=rid,source_id='test-only',account_ref='test',scope='filings')
        result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,records=(doc.model_dump(mode='json'),)),access=access)
        assert result['quarantined']==0
        return rev
    filing='Fabricated filing, no market claims.'
    if case=='adverse_event':filing=json.dumps(dict(schema_version='1.0.0',text='Synthetic default claim.',facts=[],
        events=[dict(event_type='default',statement='Synthetic default claim.',status='unverified',locator='test')]))
    if case not in ('no_filing','mixed_no_filing'):rows.append(document('filing',filing))
    if case=='missing_settings':rows=[r for r in rows if r.revision_id!='identity']
    cov=[dict(requirement=name,covers_from=stamp(start),covers_through=cutoff,fresh_until=stamp(point+timedelta(days=1)),
         complete=case!='missing_'+name) for name in SCOPES]
    if case=='stale_calendar':cov[1]['fresh_until']=stamp(point-timedelta(days=1))
    review=CoverageReview(schema_version='swing-coverage-1',listing_id='NSE:TEST',revisions={r.revision_id:r.content_hash for r in rows},
        coverage=tuple(cov),grants=tuple(dict(grant_hash=digest(g.model_dump(mode='json')),policy_evidence_ref='TEST ONLY',
        retention_compliant=case!='retention',deletion_obligations_supported=case!='deletion') for g in grants),
        volume_basis='unknown' if case=='unknown_volume' else 'raw',action_free_window=True,risk_prohibited=case=='risk_prohibited')
    proof=document('review',review.model_dump_json())
    risk=demo_profile(D(100),D(90));risk.pop('entry');risk.pop('protective_exit');risk['stop_slippage']='0.05'
    risk={k:format(D(v),'f') for k,v in risk.items()}
    if case=='zero_capacity':risk['spendable_cash']='0'
    if case=='narrow_range':risk['instrument_fraction']='0.20'
    config=ViewConfig(sources=sources,listing_ids=('NSE:TEST',),swing=SwingConfig(listing_id='NSE:TEST',
        review_revision_id=proof.revision_id,review_content_hash=proof.data.content_hash,review_approval_ref='TEST ONLY',
        policy_version='TEST-research-only-1',max_price_age_seconds=1 if case=='stale_price' else 7200,risk=risk))
    return config,cutoff


def append_review(conn,config,cutoff,*,omit=()):
    """Append a newly pinned review; retain prior documents and all dependencies."""
    raw,body=conn.execute('''SELECT d.payload,b.body FROM discovery.evidence_documents d
        JOIN discovery.evidence_blobs b USING(content_hash) WHERE revision_id=%s''',
        (config.swing.review_revision_id,)).fetchone()
    review=CoverageReview.model_validate_json(body)
    rows=[Revision.model_validate(r[0]) for r in conn.execute('SELECT payload FROM discovery.revisions')]
    body=review.model_copy(update={'revisions':{r.revision_id:r.content_hash for r in rows if r.revision_id not in omit}}).model_dump_json()
    old=Revision.model_validate(raw['revision']);rid='review-'+uuid4().hex
    rev=old.model_copy(update={'revision_id':rid,'source_revision':'upstream-'+rid,
        'data':old.data.model_copy(update={'document_id':rid,'content_hash':content_hash(body)})})
    doc=Document.model_validate({**raw,'revision':rev.model_dump(mode='json'),'body':body})
    stream=Stream(stream_id=rid,source_id=rev.source_id,account_ref='test',scope='filings')
    result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,
        records=(doc.model_dump(mode='json'),)),access=source_access(config.sources,lambda:cutoff))
    assert result['quarantined']==0
    return config.model_copy(update={'swing':config.swing.model_copy(update={
        'review_revision_id':rid,'review_content_hash':rev.data.content_hash})})


def append_identity(conn,config,cutoff,*,rid='identity-current',parent='identity',effective=None,source=None):
    old=Revision.model_validate(conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s',(parent,)).fetchone()[0])
    source=source or old.source_id
    rev=old.model_copy(update={'revision_id':rid,'source_id':source,'source_revision':'upstream-'+rid,
        'sequence':old.sequence+1 if source==old.source_id else 1,
        'supersedes_id':parent if source==old.source_id else None,
        'published_at':cutoff,'available_at':cutoff,'fetched_at':cutoff,
        'data':old.data.model_copy(update={'tick_size':'0.10','lot_size':5,'effective_at':effective or cutoff})})
    stream=Stream(stream_id=rid,source_id=source,account_ref='test',scope='universe')
    access=source_access(config.sources,lambda:cutoff)
    result=ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(rev.model_dump(mode='json'),)),
        load_grant=lambda:access.load_grant(stream),request=access.request_for(stream),audit=lambda d:None)
    assert result['quarantined']==0
    return rev


def append_document(conn,config,cutoff,*,category='annual_report',authority='issuer_primary',source='test-only'):
    raw,body=conn.execute('''SELECT d.payload,b.body FROM discovery.evidence_documents d
        JOIN discovery.evidence_blobs b USING(content_hash) WHERE revision_id=%s''',(config.swing.review_revision_id,)).fetchone()
    rid='document-'+uuid4().hex;body='SYNTHETIC substantive report for regression only.'
    original=Revision.model_validate(raw['revision'])
    rev=original.model_copy(update={'revision_id':rid,'source_id':source,'source_revision':'upstream-'+rid,
        'data':original.data.model_copy(update={'document_id':rid,'content_hash':content_hash(body)})})
    doc=Document.model_validate({**raw,'revision':rev.model_dump(mode='json'),'body':body,'category':category,'authority':authority})
    stream=Stream(stream_id=rid,source_id=source,account_ref='test',scope='filings')
    result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,records=(doc.model_dump(mode='json'),)),
        access=source_access(config.sources,lambda:cutoff))
    assert result['quarantined']==0
    return rid


def test_p2_nested_reviews_never_replace_substantive_filing(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'no_filing')
        for _ in range(2):config=append_review(conn,config,cutoff)
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE',result
        assert 'filings:stored_filing_missing' in result['reasons']
        assert result['hypothetical_sizing'] is None


def test_p2_low_volatility_cap_must_be_below_target(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'narrow_range')
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['qualification']['status']=='INPUTS_QUALIFIED'
        assert result['status']=='INSUFFICIENT_EVIDENCE' or D(result['levels']['entry_cap'])<D(result['levels']['target']),result
        if result['status']=='INSUFFICIENT_EVIDENCE':assert result['hypothetical_sizing'] is None


def test_p2_current_identity_preserves_historical_parent(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        append_identity(conn,config,cutoff)
        config=append_review(conn,config,cutoff)
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='BUY',result
        assert {'identity','identity-current'}<=set(result['evidence_revisions'])
        assert D(result['levels']['entry'])==D('133.10')


@pytest.mark.parametrize('category,authority,trusted,expected',[
    ('annual_report','issuer_primary',True,'BUY'),('quarterly_report','issuer_primary',True,'BUY'),
    ('announcement','issuer_primary',True,'BUY'),('annual_report','secondary',True,'INSUFFICIENT_EVIDENCE'),
    ('annual_report','issuer_primary',False,'INSUFFICIENT_EVIDENCE'),
    ('coverage_review','secondary',True,'INSUFFICIENT_EVIDENCE')])
def test_p2_substantive_filing_requires_stored_classification_and_own_rights(isolated_url,tmp_path,category,authority,trusted,expected):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'mixed_no_filing')
        config=append_review(conn,config,cutoff)
        rid=append_document(conn,config,cutoff,category=category,authority=authority,source='test-other')
        if trusted:config=config.model_copy(update={'sources':config.sources.model_copy(update={'primary_source_ids':('test-only','test-other')})})
        config=append_review(conn,config,cutoff)
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']==expected,result
        assert rid in result['evidence_revisions']
        restrict(conn,request_id=uuid4(),kind='grant',source_id='test-other',account_ref='test',grant_id='TEST-G2',grant_version='1',reason='revoked')
        denied=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert denied['status']=='INSUFFICIENT_EVIDENCE' and not denied['evidence_revisions']


def test_p2_future_identity_not_used_and_historical_parent_remains_fenced(isolated_url,tmp_path):
    from stock_discovery_contracts.v2 import at
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'historical_parent')
        append_identity(conn,config,cutoff,rid='aaa-current')
        append_identity(conn,config,cutoff,rid='zzz-future',parent='aaa-current',
            effective=stamp(at(cutoff).replace(tzinfo=timezone.utc)+timedelta(days=1)))
        config=append_review(conn,config,cutoff)
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='BUY' and result['instrument_revision_id']=='aaa-current'
        assert {'identity','aaa-current','zzz-future'}<=set(result['evidence_revisions'])
        restrict(conn,request_id=uuid4(),kind='grant',source_id='test-only',account_ref='history',grant_id='TEST-HISTORICAL',grant_version='1',reason='revoked')
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['status']=='INSUFFICIENT_EVIDENCE'


def test_p2_ambiguous_current_providers_fail_closed(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'mixed')
        append_identity(conn,config,cutoff,rid='current-one')
        append_identity(conn,config,cutoff,rid='current-two',source='test-other')
        config=append_review(conn,config,cutoff)
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and result['instrument_revision_id'] is None


def test_p2_missing_current_pin_cannot_fall_back_to_old_settings(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        append_identity(conn,config,cutoff)
        config=append_review(conn,config,cutoff,omit=('identity-current',))
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and result['reasons']==['coverage_review_requires_refresh']


@pytest.mark.parametrize('cap,status',[('above','INSUFFICIENT_EVIDENCE'),('equal','INSUFFICIENT_EVIDENCE'),('below','BUY'),('off_grid','INSUFFICIENT_EVIDENCE')])
def test_p2_api_geometry_boundary_and_fees(isolated_url,tmp_path,monkeypatch,cap,status):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import real_research
    from app.research import db
    import stock_discovery_analysis.swing_research as module
    original=module.swing_levels
    def geometry(*args):
        levels=original(*args)
        levels['entry_cap']=levels['target']+{'above':D('.05'),'equal':D(0),'below':D('-.05'),'off_grid':D('-.051')}[cap]
        return levels
    monkeypatch.setattr(module,'swing_levels',geometry)
    token='synthetic-stk079-p2-auth-token-no-real-account'
    monkeypatch.setenv('AUTH_TOKEN',token)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        monkeypatch.setattr(real_research,'view_config',lambda:config)
        app.dependency_overrides[db]=lambda:conn
        try:
            response=TestClient(app).get('/v1/real-research/companies/NSE:TEST',params={'analysis':'swing','cutoff_at':cutoff},headers={'Authorization':'Bearer '+token})
            assert response.status_code==200
            result=response.json();assert result['status']==status,result
            if status=='BUY':
                s=result['hypothetical_sizing'];levels=result['levels'];q=s['quantity']
                assert q>0 and q%10==0 and D(levels['entry_cap'])==D(levels['target'])-D('.05')
                assert D(s['planned_loss'])==q*(D(levels['entry_cap'])-D(levels['stop'])+D('.05')+D('.20'))+D(2)
                assert D(s['planned_loss'])<=D(250)
                assert D(s['entry_cash'])==q*(D(levels['entry_cap'])+D('.10'))+D(1)
            else:assert result['levels'] is None and result['hypothetical_sizing'] is None
        finally:app.dependency_overrides.pop(db,None)


@pytest.mark.parametrize('case,status',[('buy','BUY'),('wait','WAIT'),('zero_capacity','WAIT')])
def test_stored_pipeline_and_authenticated_api(isolated_url,tmp_path,monkeypatch,case,status):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import real_research
    from app.research import db
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,case)
        before=conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']==status, result
        assert result['qualification']['status']=='INPUTS_QUALIFIED'
        assert result==research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['evidence_revisions'] and result['analysis_id']
        assert not any(result[k] for k in ('actionable','publication_authorized','paper_admission_authorized','trading_authorized'))
        if status=='BUY':
            s=result['hypothetical_sizing'];levels=result['levels']
            assert s['quantity']>0 and s['quantity']%10==0
            assert D(s['planned_loss'])<=D(250) and D(s['entry_cash'])<=D(100000)
            assert D(levels['stop'])<D(levels['entry'])<D(levels['target'])
            assert all(D(v)%D('.05')==0 for v in levels.values())
        token='synthetic-stk079-auth-test-token-long-enough'
        monkeypatch.setenv('AUTH_TOKEN',token)
        monkeypatch.setattr(real_research,'view_config',lambda:config)
        app.dependency_overrides[db]=lambda:conn
        try:
            client=TestClient(app);url='/v1/real-research/companies/NSE:TEST'
            assert client.get(url,params={'analysis':'swing','cutoff_at':cutoff}).status_code==401
            response=client.get(url,params={'analysis':'swing','cutoff_at':cutoff},headers={'Authorization':'Bearer '+token})
            assert response.status_code==200 and response.json()==result
            assert response.headers['cache-control']=='no-store'
            # Same cutoff after restriction must not return a previous BUY.
            restrict(conn,request_id=uuid4(),kind='provider',source_id='test-only',reason='revoked')
            denied=client.get(url,params={'analysis':'swing','cutoff_at':cutoff},headers={'Authorization':'Bearer '+token}).json()
            assert denied['status']=='INSUFFICIENT_EVIDENCE' and not denied['evidence_revisions']
            assert denied['levels'] is None and denied['hypothetical_sizing'] is None
        finally:app.dependency_overrides.pop(db,None)
        assert conn.execute('SELECT count(*) FROM discovery.revisions').fetchone()==before
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()==(0,)


@pytest.mark.parametrize('case', ['short','adjusted','no_filing','missing_settings','missing_corporate_actions',
    'missing_filings','missing_material_events','stale_calendar','ineligible','risk_prohibited','retention','deletion',
    'calendar_gap','action','unknown_volume','stale_price','adverse_event'])
def test_unqualified_never_reaches_strategy(isolated_url,tmp_path,monkeypatch,case):
    import stock_discovery_analysis.swing_research as module
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,case)
        monkeypatch.setattr(module,'swing_conditions',lambda *a:pytest.fail('unqualified strategy invocation'))
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and result['reasons']
        assert result['levels'] is None and result['hypothetical_sizing'] is None


@pytest.mark.parametrize('change',['missing','expired','revoked','renewed','derive','account'])
def test_current_grant_and_same_cutoff_reuse(isolated_url,tmp_path,change):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['status']=='BUY'
        path=Path(config.sources.grant_file);g=json.loads(path.read_text())[0]
        if change=='expired':g['expires_at']=cutoff
        if change=='revoked':g.update(status='revoked',revoked_at=cutoff)
        if change=='renewed':g['version']='2'
        if change=='derive':g['allowed_uses']=['store']
        if change=='account':g['account_ref']='different'
        path.write_text(json.dumps([] if change=='missing' else [g]))
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and result['evidence_revisions']==[]


def test_configuration_missing_returns_meaningful_result(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        result=research(conn,config.model_copy(update={'swing':None}),'NSE:TEST',cutoff_at=cutoff)
        assert result['reasons']==['swing_coverage_review_not_configured']


@pytest.mark.parametrize('kind',['provider','account','grant'])
def test_mixed_source_restriction_cannot_be_masked_by_permitted_majority(isolated_url,tmp_path,kind):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path,'mixed')
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['status']=='BUY'
        restrict(conn,request_id=uuid4(),kind=kind,source_id='test-other',account_ref='test' if kind!='provider' else '',
            grant_id='TEST-G2' if kind=='grant' else '',grant_version='1' if kind=='grant' else '',reason='revoked')
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and not result['evidence_revisions']
        assert 'TEST-G2' not in json.dumps(result)


@pytest.mark.parametrize('change',['wrong_pin','wrong_cutoff','revision_hash','coverage_scope','future_coverage','original_acquire'])
def test_untrusted_review_or_original_acquisition_fails_closed(isolated_url,tmp_path,change):
    # Review-content variants are made BEFORE immutable ingestion, never by
    # disabling triggers or editing a stored acquisition.
    from unittest.mock import patch
    if change in ('revision_hash','coverage_scope','future_coverage'):
        original=CoverageReview.model_dump_json
        def altered(self,*args,**kwargs):
            body=json.loads(original(self,*args,**kwargs))
            if change=='revision_hash':body['revisions']['bar-0']='0'*64
            elif change=='coverage_scope':body['coverage']=[c for c in body['coverage'] if c['requirement']!='corporate_actions']
            else:body['coverage'][0]['covers_through']='2999-01-01T00:00:00Z'
            return json.dumps(body,sort_keys=True)
        context=patch.object(CoverageReview,'model_dump_json',altered)
    else:
        from contextlib import nullcontext
        context=nullcontext()
    with psycopg.connect(isolated_url,autocommit=True) as conn, context:
        config,cutoff=setup(conn,tmp_path,'no_acquire' if change=='original_acquire' else 'buy')
        if change=='wrong_pin':config=config.model_copy(update={'swing':config.swing.model_copy(update={'review_content_hash':'0'*64})})
        if change=='wrong_cutoff':cutoff='2999-01-01T00:00:00Z'
        result=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        assert result['status']=='INSUFFICIENT_EVIDENCE' and result['levels'] is None


def test_later_observed_evidence_requires_review_refresh(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['status']=='BUY'
        original=Revision.model_validate(conn.execute("SELECT payload FROM discovery.revisions WHERE revision_id='bar-29'").fetchone()[0])
        corrected=original.model_copy(update={'revision_id':'bar-correction','source_revision':'correction',
            'sequence':2,'supersedes_id':original.revision_id})
        access=source_access(config.sources,lambda:cutoff)
        stream=Stream(stream_id='correction',source_id=corrected.source_id,account_ref='test',scope='prices')
        result=ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(corrected.model_dump(mode='json'),)),
            load_grant=lambda:access.load_grant(stream),request=access.request_for(stream),audit=lambda d:None)
        assert result['accepted']==1
        assert research(conn,config,'NSE:TEST',cutoff_at=cutoff)['reasons']==['coverage_review_requires_refresh']


def test_risk_limits_round_lots_and_change_identity(isolated_url,tmp_path):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config,cutoff=setup(conn,tmp_path)
        first=research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        for field in ('spendable_cash','instrument_exposure','existing_and_pending_risk'):
            value='1' if field=='spendable_cash' else '100000'
            risk=config.swing.risk.model_copy(update={field:value})
            changed=config.model_copy(update={'swing':config.swing.model_copy(update={'risk':risk})})
            result=research(conn,changed,'NSE:TEST',cutoff_at=cutoff)
            assert result['status']=='WAIT' and result['hypothetical_sizing']['quantity']==0
            assert result['analysis_id']!=first['analysis_id']


@pytest.mark.parametrize('isolation',['READ COMMITTED','REPEATABLE READ'])
def test_restriction_waits_until_protected_strategy_read_finishes(isolated_url,tmp_path,monkeypatch,isolation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from test_read_fences import wait_blocked
    import stock_discovery_analysis.swing_research as module
    entered=Event();release=Event();original=module.swing_conditions
    def barrier(*args):
        entered.set();assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(module,'swing_conditions',barrier)
    with psycopg.connect(isolated_url,autocommit=True) as admin, psycopg.connect(isolated_url,autocommit=True) as operator:
        config,cutoff=setup(admin,tmp_path)
        pid=operator.info.backend_pid
        def read():
            with psycopg.connect(isolated_url,autocommit=True) as conn:
                conn.execute('SET default_transaction_isolation TO '+"'"+isolation+"'")
                return research(conn,config,'NSE:TEST',cutoff_at=cutoff)
        with ThreadPoolExecutor(2) as pool:
            reading=pool.submit(read);assert entered.wait(5)
            restricting=pool.submit(restrict,operator,request_id=uuid4(),kind='provider',source_id='test-only',reason='revoked')
            try:wait_blocked(admin,pid)
            finally:release.set()
            assert reading.result(timeout=5)['status']=='BUY'
            restricting.result(timeout=5)
        assert research(admin,config,'NSE:TEST',cutoff_at=cutoff)['status']=='INSUFFICIENT_EVIDENCE'
