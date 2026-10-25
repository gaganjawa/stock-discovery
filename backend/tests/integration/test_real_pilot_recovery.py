"""Fabricated provider failures against disposable durable jobs; not live acceptance."""
import json
from copy import deepcopy
from types import SimpleNamespace
import psycopg
import pytest
from test_rag_research import isolated_url as rag_database
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


@pytest.fixture
def isolated_url():
    # Each recovery scenario owns a fresh database; never clear immutable history.
    yield from rag_database.__wrapped__()


@pytest.fixture
def pilot_case(isolated_url,tmp_path,monkeypatch):
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
    model_calls=[];initializations=[];closed=[];metadata=[];model_digest=['a'*64];init_failure=[False];ambiguous=[False]
    class Model:
        def __init__(self,name,**kwargs):
            initializations.append(name)
            if init_failure[0] and name==config.evidence.embedding_model:raise RuntimeError('model_not_installed')
            self.ref=Ref(id=name,version=model_digest[0],content_hash=model_digest[0])
        def close(self):closed.append(self.ref.id)
        @classmethod
        def installed_refs(cls,requests):
            metadata.append(True)
            return {role:Ref(id=name,version=model_digest[0],content_hash=model_digest[0]) for role,name,kwargs in requests}
    monkeypatch.setattr(pilot,'Ollama',Model)
    def research(conn,cfg,clock,model_factory):
        assert model_factory(cfg.model,context=cfg.context,max_input_bytes=cfg.context*2,max_model_bytes=cfg.max_model_bytes).ref.id==cfg.model
        assert model_factory(cfg.embedding_model).ref.id==cfg.embedding_model
        model_calls.append(cfg.context)
        if ambiguous[0]:raise KeyboardInterrupt('simulated crash after intent')
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
        yield SimpleNamespace(**locals())


def test_financial_failure_then_recovery_preserves_attempts(pilot_case):
    c=pilot_case
    conn,config,schedule,current,fail,calls,model_calls=c.conn,c.config,c.schedule,c.current,c.fail,c.calls,c.model_calls
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


def another_job(c,number):
    schedule=c.schedule.model_copy(update={'schedule_id':f'fixture-renewal-{number}'})
    slot=resolve_occurrences(schedule,NOW)[0]
    materialize(c.conn,(slot,),c.current[0])
    job=claim(c.conn,c.current[0],schedule.code_version,schedule_hash=digest(schedule.model_dump(mode='json')))
    assert job is not None
    return job,pilot.handlers(schedule,c.config)['ingest']


@pytest.mark.parametrize('change',['digest','prompt','validator'])
def test_same_cutoff_identity_reuse_and_budget_survives_replacement_job(pilot_case,monkeypatch,change):
    c=pilot_case;c.fail[0]=False
    job,handler=another_job(c,1)
    first,_=handler(c.conn,job,lambda:c.current[0])
    assert first['status']=='completed' and len(c.model_calls)==1
    finish(c.conn,job,c.current[0],status='completed',result=first)
    initializations=len(c.initializations);requests=len(c.calls)
    job,handler=another_job(c,2)
    reused,_=handler(c.conn,job,lambda:c.current[0])
    assert reused['status']=='completed' and 'reused_scan' in reused
    assert len(c.initializations)==initializations and len(c.calls)==requests and len(c.metadata)==1
    finish(c.conn,job,c.current[0],status='completed',result=reused)
    if change=='digest':c.model_digest[0]='b'*64
    elif change=='prompt':monkeypatch.setattr(pilot.factual_research,'PROMPT_HASH','b'*64)
    else:monkeypatch.setattr(pilot.rag_research,'VALIDATOR_VERSION','next')
    job,handler=another_job(c,3)
    changed,_=handler(c.conn,job,lambda:c.current[0])
    assert changed['status']=='partial' and 'reused_scan' not in changed
    assert changed['research_identity']!=first['research_identity']
    assert changed['rows'][0]['research']['status']=='occurrence_research_budget_exhausted'
    assert len(c.model_calls)==1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0]==1
    assert changed['publication']=='blocked_existing_qualification_gates'
    assert changed['positions']==changed['prospective_references']==0 and changed['actionable'] is False
    stored=c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan' AND payload->>'status'='completed'").fetchall()
    assert stored==[(first,)]


def test_model_initialization_failure_recovers_without_consuming_inference_budget(pilot_case):
    c=pilot_case;c.fail[0]=False;c.init_failure[0]=True
    job,handler=another_job(c,1)
    with pytest.raises(pilot.JobFailure,match='readiness'):handler(c.conn,job,lambda:c.current[0])
    first=c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan'").fetchone()[0]
    assert first['status']=='partial' and first['rows'][0]['research']['status']=='initialization_failed'
    assert c.closed==[c.config.evidence.model] and not c.model_calls
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0]==0
    assert retry(c.conn,job,c.current[0],reason='readiness')=='retry_wait'
    c.current[0]='2026-10-15T12:15:00Z';c.init_failure[0]=False
    job=claim(c.conn,c.current[0],c.schedule.code_version)
    result,_=handler(c.conn,job,lambda:c.current[0])
    assert job['attempts']==2 and result['status']=='completed' and len(c.model_calls)==1
    scans=c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan' ORDER BY payload->>'attempt'").fetchall()
    assert len(scans)==2 and scans[0][0]==first
    assert result['actionable'] is False and result['positions']==0


def test_ambiguous_intent_never_repeats_inference(pilot_case):
    c=pilot_case;c.fail[0]=False;c.ambiguous[0]=True
    job,handler=another_job(c,1)
    with pytest.raises(KeyboardInterrupt):handler(c.conn,job,lambda:c.current[0])
    assert len(c.model_calls)==1 and len(c.closed)==2
    assert retry(c.conn,job,c.current[0],reason='readiness')=='retry_wait'
    c.current[0]='2026-10-15T12:15:00Z';c.ambiguous[0]=False
    job=claim(c.conn,c.current[0],c.schedule.code_version)
    result,_=handler(c.conn,job,lambda:c.current[0])
    assert result['status']=='partial' and result['rows'][0]['research']['status']=='ambiguous_prior_attempt'
    assert len(c.model_calls)==1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research_intent'").fetchone()[0]==1
    assert c.conn.execute("SELECT count(*) FROM discovery.schedule_outbox WHERE kind='pilot_research'").fetchone()[0]==0
    assert not result['actionable'] and result['positions']==0
    finish(c.conn,job,c.current[0],status='partial',result=result)
    c.model_digest[0]='b'*64
    job,handler=another_job(c,2)
    changed,_=handler(c.conn,job,lambda:c.current[0])
    assert changed['status']=='partial' and changed['rows'][0]['research']['status']=='occurrence_research_budget_exhausted'
    assert len(c.model_calls)==1


def test_scan_without_selected_research_reuses_without_model_access(pilot_case):
    c=pilot_case;c.fail[0]=False
    c.config=c.config.model_copy(update={'max_research':0})
    c.schedule=c.schedule.model_copy(update={'input_hash':pilot.pilot_hash(c.config)})
    job,handler=another_job(c,1)
    result,_=handler(c.conn,job,lambda:c.current[0])
    assert result['status']=='completed'
    finish(c.conn,job,c.current[0],status='completed',result=result)
    job,handler=another_job(c,2)
    reused,_=handler(c.conn,job,lambda:c.current[0])
    assert 'reused_scan' in reused and not c.initializations and not c.metadata and not c.model_calls


def test_legacy_completed_scan_with_failed_initialization_is_not_reused(pilot_case):
    c=pilot_case;c.fail[0]=False
    job,handler=another_job(c,1)
    legacy=dict(status='completed',scheduled_cutoff=job['payload']['information_cutoff_at'],rows=[dict(status='observed',errors=[],research=dict(status='failed'))])
    pilot.receipt(c.conn,job,'pilot_scan',1,legacy,lambda:c.current[0])
    finish(c.conn,job,c.current[0],status='completed',result=legacy)
    job,handler=another_job(c,2)
    result,_=handler(c.conn,job,lambda:c.current[0])
    assert result['status']=='completed' and 'reused_scan' not in result and len(c.model_calls)==1
    assert c.conn.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_scan' ORDER BY created_at,event_key").fetchall().count((legacy,))==1
