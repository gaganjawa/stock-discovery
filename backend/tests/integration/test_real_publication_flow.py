"""Fabricated observed records exercise real code paths; not INFY acceptance."""
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import psycopg
import pytest
from test_rag_research import isolated_url
from test_real_evidence import setup
from test_real_publication import arguments
from stock_discovery_analysis.real_views import ViewConfig,company
from stock_discovery_analysis.real_access import source_access
from stock_discovery_analysis.real_publication import publish
from stock_discovery_analysis.shadow_tracking import observe,history
from stock_discovery_analysis.revisions import Revision,CandleData,SessionData
from stock_discovery_analysis.revision_storage import Stream,Page,ingest_page

CLOCK='2026-10-20T12:00:00Z'


def insert(conn,config,data,rid,stamp,listing='NSE:test',sequence=1,supersedes=None):
    revision=Revision(schema_version='1.0.0',revision_id=rid,source_id='test-official',source_revision=rid,sequence=sequence,
        listing_id=listing,instrument_revision_id=None if listing=='NSE' else 'P2-identity',published_at=stamp,available_at=stamp,fetched_at=stamp,
        availability_basis='observed',archive_evidence_ref=None,archive_revision_id=None,supersedes_id=supersedes,data=data)
    access=source_access(config.sources,lambda:stamp)
    stream=Stream(stream_id='p3-'+rid,source_id='test-official',account_ref='test',scope=revision.scope)
    g,request=access.require(stream,('store',))
    result=ingest_page(conn,stream,Page(cursor=None,next_cursor=None,complete=True,records=(revision.model_dump(mode='json'),)),load_grant=lambda:g,request=request,audit=lambda d:None)
    return revision


def prepared(conn,tmp_path):
    # All original revisions must be acquired under the intended permissions;
    # a newer grant cannot retroactively authorize the stored identity.
    evidence=setup(conn,tmp_path,extra_scopes=('prices','calendar','corporate_actions'),extra_uses=('paper_evaluation',))
    policies=tmp_path/'policies.json';policies.write_text(json.dumps([p.model_dump(mode='json') for p in arguments()['real']['policies']]))
    config=ViewConfig(sources=evidence.sources,listing_ids=('NSE:test',),policy_file=str(policies))
    for i in range(25):
        day=datetime(2026,10,12,tzinfo=timezone.utc)+timedelta(days=i)
        if day.weekday()>4:continue
        start=day.strftime('%Y-%m-%dT03:45:00Z');end=day.strftime('%Y-%m-%dT10:00:00Z')
        insert(conn,config,SessionData(kind='session',calendar_version='fabricated',opens_at=start,closes_at=end),'test-session-'+str(i),'2026-10-19T12:00:00Z','NSE')
    insert(conn,config,bar('2026-10-19'),'test-bar-before','2026-10-19T12:00:00Z')
    return config


def bar(day,close='105'):
    return CandleData(kind='candle',interval='1d',starts_at=day+'T03:45:00Z',ends_at=day+'T10:00:00Z',open='100',high='110',low='90',close=close,volume=100,adjustment_basis='raw')


def test_publication_idempotence_clock_revocation_and_shadow_receipts(isolated_url,tmp_path,monkeypatch):
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        config=prepared(conn,tmp_path);clock=lambda:CLOCK
        artifact=publish(conn,config,'NSE:test','swing','p3-test','test',clock=clock)
        r=artifact['recommendation'];rid=r['recommendation_id']
        assert r['decision_available_at']==CLOCK and r['information_cutoff_at']<CLOCK
        assert r['action']=='INSUFFICIENT_EVIDENCE' and r['execution'] is None
        assert publish(conn,config,'NSE:test','swing','p3-test','test',clock=lambda:'2026-10-21T12:00:00Z')==artifact
        with pytest.raises(ValueError,match='idempotency_conflict'):publish(conn,config,'NSE:test','long_term','p3-test','test',clock=clock)
        access=source_access(config.sources,clock)
        ref=history(conn,rid,access)['reference']['reference_id']
        assert observe(conn,ref,access,clock=clock)['status']=='pending_future_observation'
        assert conn.execute('SELECT count(*) FROM paper.shadow_outcomes').fetchone()[0]==0
        insert(conn,config,bar('2026-10-21'),'test-bar-after','2026-10-21T12:00:00Z')
        assert observe(conn,ref,access,clock=clock)['status']=='pending_future_observation'  # not genuinely available yet
        later=lambda:'2026-10-21T13:00:00Z';access=source_access(config.sources,later)
        result=observe(conn,ref,access,clock=later)
        assert result['status']=='not_applicable' and result['forecast_price_return'] is None
        assert observe(conn,ref,access,clock=later)==result
        insert(conn,config,bar('2026-10-21','106'),'test-bar-correction','2026-10-21T12:30:00Z',sequence=2,supersedes='test-bar-after')
        revised=observe(conn,ref,access,clock=later)
        assert revised['sequence']==2 and revised['supersedes_outcome_id']==result['outcome_id']
        detail=company(conn,config,'NSE:test',clock=later)
        assert detail['recommendations'][0]['recommendation']==r
        assert len(detail['recommendations'][0]['tracking']['outcomes'])==2
        from fastapi.testclient import TestClient
        from app.main import app
        from app.research import db
        config_path=tmp_path/'view.json';config_path.write_text(config.model_dump_json())
        monkeypatch.setenv('REAL_RESEARCH_VIEW_CONFIG',str(config_path))
        monkeypatch.setenv('AUTH_TOKEN','test-real-owner-key-over-thirty-two-characters')
        app.dependency_overrides[db]=lambda:conn
        try:
            with TestClient(app) as client:
                headers={'Authorization':'Bearer test-real-owner-key-over-thirty-two-characters'}
                response=client.get('/v1/recommendations/'+rid,headers=headers)
                assert response.status_code==200 and response.json()['recommendation']==r
                assert client.get('/v1/recommendations/'+rid).status_code==401
        finally:app.dependency_overrides.clear()
        assert conn.execute('SELECT count(*) FROM paper.portfolios').fetchone()[0]==0
        for table in ('shadow_references','shadow_outcomes'):
            with pytest.raises(psycopg.Error):conn.execute('UPDATE paper.'+table+" SET payload='{}'")
        Path(config.sources.grant_file).write_text('[]')
        with pytest.raises(PermissionError):observe(conn,ref,access,clock=later)
        with pytest.raises(PermissionError):company(conn,config,'NSE:test',clock=later)
        with pytest.raises(PermissionError):publish(conn,config,'NSE:test','swing','p3-test','test',clock=later)
