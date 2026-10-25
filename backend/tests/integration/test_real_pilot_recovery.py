"""Fabricated provider failures against disposable durable jobs; not live acceptance."""
import json
from copy import deepcopy
from types import SimpleNamespace
import psycopg
import pytest
from test_rag_research import isolated_url
from test_real_market import grant
from worker import real_pilot as pilot
from worker.providers import upstox_financials
from worker.providers.upstox import observed_revision,RevisionPages
from stock_discovery_analysis.revisions import InstrumentData
from stock_discovery_analysis.revision_storage import Stream,ingest_next
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.rag_contracts import Budget
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.scheduling import resolve_occurrences
from stock_discovery_analysis.schedule_store import materialize,claim,retry,finish
from stock_discovery_contracts.v2 import digest,Ref

NOW='2026-10-15T12:00:00Z'


def test_financial_failure_then_recovery_preserves_attempts(isolated_url,tmp_path,monkeypatch):
    g=grant();gf=tmp_path/'grants.json';gf.write_text(json.dumps([g.model_dump()]))
    tf=tmp_path/'token';tf.write_text('fabricated-token')
    members=[dict(symbol=f'T{i:02}',isin=f'INE{i:09}',listing_id=f'NSE:INE{i:09}') for i in range(10)]
    universe={'members':members};universe['version']=digest(universe)
    sources=SourceConfig(grant_file=str(gf),retention_days=365)
    config=pilot.PilotConfig(market=pilot.MarketConfig(account_ref='test',grant_file=str(gf),token_file=str(tf),retention_days=365,symbols=tuple(m['symbol'] for m in members)),
        view=ViewConfig(sources=sources,listing_ids=tuple(m['listing_id'] for m in members)),
        evidence=pilot.EvidenceConfig(sources=sources,filings=(),queries=(pilot.query_for(None,members[0],'long_term',NOW),),budget=Budget(account='fixture'),factual_report=True),
        universe=universe,max_research=1)
    schedule=fixture_config().model_copy(update={'mode':'live_paper','input_hash':pilot.pilot_hash(config)})
    current=[NOW];fail=[True];calls=[]
    monkeypatch.setenv('DATABASE_URL',isolated_url);monkeypatch.delenv('DATABASE_URL_FILE',raising=False)
    class Provider:
        def __init__(self,**kwargs):pass
        def close(self):pass
    monkeypatch.setattr(pilot,'Upstox',Provider)
    monkeypatch.setattr(pilot,'ingest_prices',lambda *a,**k:dict(status='ingested',instruments=[dict(candles=30)]))
    def financial(conn,client,identity,account,endpoints):
        calls.append((identity.listing_id,endpoints[0]))
        if fail[0] and endpoints[0]=='income-statement':raise RuntimeError('upstox_timeout')
    monkeypatch.setattr(upstox_financials,'ingest_financials',financial)
    detail=dict(financial_facts=[],documents=[],cutoff_at=NOW,market_readiness=dict(latest_session_present=True,input_revision_ids=[]),price_features={},publication_blockers=[])
    monkeypatch.setattr(pilot,'company',lambda *a,**k:deepcopy(detail))
    monkeypatch.setattr(pilot,'retrieve',lambda *a,**k:SimpleNamespace(documents=()))
    monkeypatch.setattr(pilot,'candidates',lambda bundle:[])
    monkeypatch.setattr(pilot,'screening',lambda *a:{})
    def rank(rows):rows[0]['screening']={'long_term':{'rank':1}}
    monkeypatch.setattr(pilot,'rank_rows',rank)
    model_calls=[]
    class Model:
        def __init__(self,name,**kwargs):self.ref=Ref(id=name,version='fixture-1',content_hash='a'*64)
        def close(self):pass
    monkeypatch.setattr(pilot,'Ollama',Model)
    def research(conn,cfg,clock,model_factory):
        assert model_factory(cfg.model,context=cfg.context,max_input_bytes=cfg.context*2,max_model_bytes=cfg.max_model_bytes).ref.id==cfg.model
        assert model_factory(cfg.embedding_model).ref.id==cfg.embedding_model
        model_calls.append(cfg.context)
        return dict(research=[])
    monkeypatch.setattr(pilot,'research',research)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        access=pilot.access_for(config.market,lambda:NOW)
        for member in members:
            data=InstrumentData(kind='instrument',issuer_id=member['isin'],symbol=member['symbol'],isin=member['isin'],series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at=NOW)
            record=observed_revision(data,listing=member['listing_id'],fetched=NOW)
            stream=Stream(stream_id=record.revision_id,source_id='upstox',account_ref='test',scope='universe')
            _,request=access.require(stream,('store',))
            assert ingest_next(conn,stream,RevisionPages((record,)),load_grant=lambda:g,request=request,audit=lambda d:None,clock=lambda:NOW)['accepted']==1
        slot=resolve_occurrences(schedule,NOW)[0]
        jid=materialize(conn,(slot,),NOW)[0];job=claim(conn,NOW,schedule.code_version)
        handler=pilot.handlers(schedule,config)['ingest']
        with pytest.raises(pilot.JobFailure):handler(conn,job,lambda:current[0])
        first=conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE job_id=%s AND kind='pilot_scan'",(jid,)).fetchone()[0]
        assert first['status']=='partial' and first['counts']['observed']==10
        assert all(r['errors']==['income-statement:upstox_timeout'] for r in first['rows'])
        assert retry(conn,job,NOW,reason='readiness')=='retry_wait'
        current[0]='2026-10-15T12:15:00Z';fail[0]=False
        job=claim(conn,current[0],schedule.code_version);assert job['attempts']==2
        result,_=handler(conn,job,lambda:current[0])
        assert result['status']=='completed' and all(not r['errors'] for r in result['rows'])
        assert len(calls)==60
        scans=conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE job_id=%s AND kind='pilot_scan' ORDER BY payload->>'attempt'",(jid,)).fetchall()
        assert len(scans)==2 and scans[0][0]==first
        again,_=handler(conn,job,lambda:current[0])
        assert 'reused_scan' in again and len(calls)==60
        assert conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE job_id=%s AND kind='pilot_stock'",(jid,)).fetchone()[0]==20

        assert model_calls==[16384]
        assert result['rows'][0]['research']['status']=='reused_immutable_attempt'
        finish(conn,job,current[0],status='completed',result=result)
        changed=config.model_copy(update={'evidence':config.evidence.model_copy(update={'context':8192})})
        next_schedule=schedule.model_copy(update={'input_hash':pilot.pilot_hash(changed)})
        next_slot=resolve_occurrences(next_schedule,NOW)[0]
        materialize(conn,(next_slot,),current[0])
        next_job=claim(conn,current[0],schedule.code_version)
        assert next_job is not None
        changed_result,_=pilot.handlers(next_schedule,changed)['ingest'](conn,next_job,lambda:current[0])
        assert model_calls==[16384,8192]
        assert changed_result['rows'][0]['research']['fingerprint']!=result['rows'][0]['research']['fingerprint']
        assert conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research'").fetchone()[0]==2
