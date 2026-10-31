"""Fabricated observed-mode contract acceptance; no real-source qualification."""
import json
from dataclasses import replace
import httpx
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from stock_discovery_contracts.rights import Grant
from stock_discovery_analysis.real_access import SourceConfig,source_access
from stock_discovery_analysis.real_views import ViewConfig,company
from stock_discovery_analysis.revisions import Revision,InstrumentData
from stock_discovery_analysis.revision_storage import Stream,Page,ingest_page
from stock_discovery_analysis.rag_research import MockResearchProvider
from stock_discovery_analysis.rag_retrieval import MockEmbeddings
from stock_discovery_analysis.rag_contracts import Query,Budget
from worker.real_evidence import EvidenceConfig,run
from worker.providers.documents import FilingSpec,OfficialDocument

@pytest.fixture
def isolated_url():
    yield from _isolated_url.__wrapped__()


NOW='2026-10-19T12:00:00Z'
HTML='<h1>Consolidated annual earnings INR crore</h1><table><tr><th>Metric</th><th>2026</th></tr><tr><td>Revenue</td><td>100</td></tr><tr><td>Earnings</td><td>20</td></tr></table>'


def setup(conn,tmp_path,*,extra_scopes=(),extra_uses=()):
    grant=Grant(schema_version='1.0.0',grant_id='p2-test',version='1',source_id='test-official',account_ref='test',status='active',synthetic=False,
        approval_evidence_ref='FABRICATED TEST ONLY',valid_from_at='2026-01-01T00:00:00Z',expires_at='2027-01-01T00:00:00Z',revoked_at=None,
        allowed_uses=('acquire','store','extract','derive','embed'),scopes=('universe','filings','financial_facts'),regions=('IN',),external_processors=(),
        retention_days=365,deletion_deadline_days=0,attribution='Test attribution',max_units_per_operation=100,audit_tombstones_permitted=True)
    grant=grant.model_copy(update={'scopes':grant.scopes+extra_scopes,'allowed_uses':grant.allowed_uses+extra_uses})
    path=tmp_path/'grants.json';path.write_text(json.dumps([grant.model_dump(mode='json')]))
    sources=SourceConfig(grant_file=str(path),retention_days=365,primary_source_ids=('test-official',))
    access=source_access(sources,lambda:NOW)
    identity=Revision(schema_version='1.0.0',revision_id='P2-identity',source_id='test-official',source_revision='1',sequence=1,
        listing_id='NSE:test',instrument_revision_id=None,published_at=NOW,available_at=NOW,fetched_at=NOW,availability_basis='observed',
        archive_evidence_ref=None,archive_revision_id=None,supersedes_id=None,
        data=InstrumentData(kind='instrument',issuer_id='test-issuer',symbol='TEST',isin='INE009A01021',series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at=NOW))
    stream=Stream(stream_id='P2-identity',source_id='test-official',account_ref='test',scope='universe')
    g,request=access.require(stream,('store',))
    ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(identity.model_dump(mode='json'),)),load_grant=lambda:g,request=request,audit=lambda d:None)
    extraction=dict(table_header=['Metric','2026'],column_header='2026',unit_marker='INR crore',scope_marker='Consolidated',unit='INR_crore',scope='consolidated',
        period_start_at='2025-04-01T00:00:00Z',period_end_at='2026-03-31T00:00:00Z',period_kind='annual',rows={'revenue':'Revenue','earnings':'Earnings'})
    spec=FilingSpec(source_id='test-official',account_ref='test',url='https://www.sec.gov/Archives/edgar/data/1067491/test.htm',issuer_id='test-issuer',listing_id='NSE:test',
        instrument_revision_id='P2-identity',document_id='P2-doc',title='Fabricated annual results',attribution='Test attribution',published_at='2026-06-15T15:03:56Z',category='annual_report',format='html_table',extraction=extraction)
    query=Query(issuer_id='test-issuer',listing_id='NSE:test',horizon='short_term',mode='live_paper',cutoff_at=NOW,text='earnings',categories=('annual_report',),
        required_metrics=('revenue','earnings'),period_start_at=extraction['period_start_at'],period_end_at=extraction['period_end_at'],period_kind='annual')
    return EvidenceConfig(sources=sources,filings=(spec,),queries=(query,),budget=Budget(account='P2-test'))


def test_document_to_existing_rag_and_rights_aware_view(isolated_url,tmp_path):
    def adapter(spec,**kw):return OfficialDocument(spec,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML)),**kw)
    def model(name,**kw):
        instance=MockEmbeddings() if 'embed' in name else MockResearchProvider()
        instance.close=lambda:None
        return instance
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=setup(conn,tmp_path)
        bad=config.model_copy(update={'queries':(config.queries[0].model_copy(update={'mode':'synthetic'}),)})
        with pytest.raises(ValueError,match='real_queries_only'):run(conn,bad,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
        result=run(conn,config,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
        research=result['research'][0]['result']
        assert research['status']=='completed' and research['provider_called'] is True
        assert research['validator']['deterministic']=='passed'
        assert result['publication']=='not_published' and result['actionable'] is False
        view=ViewConfig(sources=config.sources,listing_ids=('NSE:test',))
        detail=company(conn,view,'NSE:test',clock=lambda:NOW)
        assert detail['symbol']=='TEST' and detail['price_series']==[]
        assert len(detail['financial_facts'])==3  # two reported facts plus deterministic margin
        assert all(f['source_unit']=='INR_crore' for f in detail['financial_facts'] if f['metric']!='net_margin')
        assert detail['analysis_history'][0]['result']['validator']['deterministic']=='passed'
        assert all(q['action']=='INSUFFICIENT_EVIDENCE' for q in detail['quantitative'].values())
        assert detail['recommendations']==[] and detail['prospective_status']=='not_configured'
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()[0]==0
        with pytest.raises(psycopg.Error):
            with conn.transaction():conn.execute("UPDATE discovery.rag_results SET payload='{}'::jsonb")
        # Current grant removal hides already-stored facts and model output.
        from pathlib import Path
        Path(config.sources.grant_file).write_text('[]')
        with pytest.raises(PermissionError):company(conn,view,'NSE:test',clock=lambda:NOW)


@pytest.mark.parametrize('wrong_value',[False,True])
def test_filing_text_to_model_proposal_independent_verification_and_company_report(isolated_url,tmp_path,wrong_value):
    """Invented filing text and scripted model only; not financial accuracy evidence."""
    from stock_discovery_analysis.evidence import content_hash
    from pathlib import Path
    class Rows(OfficialDocument):
        def fetch(self,*a,**kw):
            page=super().fetch(*a,**kw);d=page.records[0];body=json.loads(d['body'])
            body['text']='\n'.join(f"{f['metric']} = {f['value']} {f['unit']}; {f['period_start_at']}/{f['period_end_at']}; {f['period_kind']}; {f['scope']}" for f in body['facts'])
            text=json.dumps(body);rev=d['revision'];rid='EXTRACTION-TEST-'+content_hash(text)
            rev={**rev,'revision_id':rid,'source_revision':rid,'data':{**rev['data'],'content_hash':content_hash(text)}}
            return page.model_copy(update={'records':({**d,'revision':rev,'body':text},)})
    class Extractor(MockResearchProvider):
        calls=0
        def assess(self,request,**kw):
            self.calls+=1
            context=json.loads(request)['bundle'];assert context['candidates']==[]
            c=context['source_passages'][0];quote=c['text'].splitlines()[0]
            value,periods,kind,scope=quote.split('; ');metric,number,unit=value.replace(' = ',' ').split()
            first,last=periods.split('/')
            locator=next(x['locator'] for x in context['reference_locators'] if x['metric']==metric and x['revision_id']==c['revision_id'])
            proposal=dict(issuer_id=context['issuer_id'],listing_id=context['listing_id'],revision_id=c['revision_id'],evidence_id=c['evidence_id'],quote=quote,
                fact=dict(metric=metric,value='999' if wrong_value else number,missing_reason=None,unit=unit,period_start_at=first,period_end_at=last,period_kind=kind,scope=scope,locator=locator))
            return json.dumps(dict(factual_claims=[],interpretations=[],extracted_claims=[proposal]))
    def adapter(spec,**kw):return Rows(spec,transport=httpx.MockTransport(lambda r:httpx.Response(200,text=HTML)),**kw)
    providers={}
    def model(name,**kw):
        p=MockEmbeddings() if 'embed' in name else Extractor();p.close=lambda:None;providers[name]=p;return p
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=setup(conn,tmp_path).model_copy(update={'factual_report':True,'extraction_only':True})
        result=run(conn,config,clock=lambda:NOW,adapter_factory=adapter,model_factory=model)
        r=result['research'][0]['result'];assert r['status']=='completed' and r['provider_called']
        report=r['factual_report'];assert bool(report['accepted_claims']) is not wrong_value
        assert bool(report['rejected_claims']) is wrong_value
        if not wrong_value:
            c=report['accepted_claims'][0]
            assert c['validation']=='deterministic_filing_fact_and_passage_parity' and c['extracted_fields']['fact']['unit']=='INR_crore'
            assert c['text'].split(';')[0].endswith('1000000000 INR')
        detail=company(conn,ViewConfig(sources=config.sources,listing_ids=('NSE:test',)), 'NSE:test',clock=lambda:NOW)
        assert detail['analysis_history'][0]['result']['factual_report']==report
        assert not report['qualified'] and not result['actionable'] and not detail['recommendations']
        from stock_discovery_analysis.rag_research import run_research
        access=source_access(config.sources,lambda:NOW)
        kwargs=dict(run_id=result['research'][0]['run_id'],query=config.queries[0],policy=config.retrieval,access=access,
            budget=config.budget,provider=providers[config.model],embeddings=providers[config.embedding_model],factual_report=True)
        assert run_research(conn,**kwargs,extraction_only=True)['cache_reused']
        assert providers[config.model].calls==1
        with pytest.raises(ValueError,match='identity conflict'):run_research(conn,**kwargs,extraction_only=False)
        assert conn.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(1,)
        Path(config.sources.grant_file).write_text('[]')
        with pytest.raises(PermissionError):run_research(conn,**kwargs,extraction_only=True)
