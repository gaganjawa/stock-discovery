"""Invented observed-mode records only; no market/provider acceptance."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import json
import pytest
from stock_discovery_analysis.adjusted_research import verify_pages,describe,AdjustedResearch
from stock_discovery_analysis.revision_fixtures import fixture_records
from stock_discovery_analysis.revision_storage import Page
from stock_discovery_analysis.revisions import Revision
from stock_discovery_analysis.data import Provenance
from stock_discovery_contracts.v2 import digest,at

NOW='2026-10-19T12:00:00Z'

def fixture():
    template=fixture_records()[3].model_dump(mode='json');bars=[]
    for i in range(30):
        day=datetime(2026,9,20,tzinfo=timezone.utc)+timedelta(days=i)
        stamp=lambda h:day.replace(hour=h).strftime("%Y-%m-%dT%H:%M:%SZ")
        r={**template,'revision_id':f'TEST-{i:02}','source_id':'upstox','source_revision':f'upstream-{i}',
           'listing_id':'NSE:TEST','published_at':NOW,'available_at':NOW,'fetched_at':NOW,'availability_basis':'observed',
           'data':{**template['data'],'starts_at':stamp(4),'ends_at':stamp(10),'adjustment_basis':'split_bonus_adjusted'}}
        bars.append(Revision.model_validate(r))
    rows=[(r.model_dump(mode='json'),'test-grant','1') for r in bars]
    page=Page(cursor=None,next_cursor=None,complete=True,records=tuple(r[0] for r in rows))
    pages=[('',digest(page.model_dump(mode='json')),None,True,30,0)]
    stream=('test-stream','upstox','prices',True)
    return bars,rows,stream,pages

class Result:
    def __init__(self,rows):self.rows=rows
    def fetchall(self):return self.rows
    def fetchone(self):return self.rows[0] if self.rows else None

class Conn:
    def __init__(self,rows,stream,pages):self.rows,self.stream,self.pages=rows,stream,pages
    def execute(self,sql,params):
        if 'DISTINCT stream_id' in sql:return Result([(self.stream[0],)])
        if 'FROM discovery.streams' in sql:return Result([self.stream])
        if 'FROM discovery.pages' in sql:return Result(self.pages)
        return Result(self.rows)

def run(*,historical=False,change=None):
    bars,rows,stream,pages=fixture()
    readiness=dict(required_sessions=30,observed_bars=30,missing_sessions=[],unverified_bar_sessions=[],latest_session_present=True,
                   duplicate_bars=False,warmup_complete=True,calendar_completeness='not_attested_by_session_list')
    if change:change(bars,rows,pages,readiness)
    def prov(r):
        return Provenance(r.source_id,r.source_revision,*(at(t).replace(tzinfo=timezone.utc) for t in (r.published_at,r.available_at,r.fetched_at)),'observed_live')
    return describe(Conn(rows,stream,pages),'NSE:TEST',bars,[],readiness,NOW,historical_request=historical,provenance=prov)

def test_verified_pages_support_descriptive_prices_only():
    r=run();assert r.status=='AVAILABLE_DESCRIPTIVE_ONLY'
    assert r.metrics['sma20']=='105' and r.metrics['relative_volume20'] is None
    assert r.volume_basis=='unknown' and r.batch.response_hash is None
    assert not r.actionable and not r.execution_qualified and not r.historical_pit_qualified
    assert not r.publication_authorized and not r.paper_admission_authorized
    assert r==AdjustedResearch.model_validate_json(r.model_dump_json())

@pytest.mark.parametrize('change',[
 lambda b,r,p,c:p.clear(),
 lambda b,r,p,c:p.__setitem__(0,('', '0'*64,None,True,30,0)),
 lambda b,r,p,c:r.pop(),
 lambda b,r,p,c:b.reverse(),
 lambda b,r,p,c:c.update(missing_sessions=[NOW]),
 lambda b,r,p,c:c.update(latest_session_present=False),
 lambda b,r,p,c:c.update(warmup_complete=False),
 lambda b,r,p,c:r[0][0].update(fetched_at='2026-10-20T12:00:00Z'),
])
def test_missing_mixed_or_invalid_evidence_fails_closed(change):
    r=run(change=change);assert r.status=='UNAVAILABLE' and not r.metrics and r.unavailable_reasons

def test_historical_request_cannot_reuse_adjusted_snapshot():
    r=run(historical=True)
    assert r.status=='UNAVAILABLE' and 'historical_adjusted_research_not_supported' in r.unavailable_reasons

@pytest.mark.parametrize('field',['actionable','execution_qualified','historical_pit_qualified','publication_authorized','paper_admission_authorized'])
def test_result_cannot_claim_execution_or_admission(field):
    raw=run().model_dump();raw[field]=True
    with pytest.raises(ValueError):AdjustedResearch.model_validate(raw)

def test_no_relative_volume_or_unavailable_metrics():
    raw=run().model_dump();raw['metrics']['relative_volume20']='2'
    with pytest.raises(ValueError):AdjustedResearch.model_validate(raw)
    raw=run().model_dump();raw['status']='UNAVAILABLE'
    with pytest.raises(ValueError):AdjustedResearch.model_validate(raw)

def test_paginated_batch_identity_is_independent_of_receipt_query_order():
    bars,rows,stream,_=fixture();pages=[]
    for i in (0,15):
        p=Page(cursor=str(i) if i else None,next_cursor='15' if i==0 else None,complete=i==15,
               records=tuple(r[0] for r in rows[i:i+15]))
        pages.append((p.cursor or '',digest(p.model_dump(mode='json')),p.next_cursor,p.complete,15,0))
    assert verify_pages(bars,rows,stream,pages)==verify_pages(bars,rows,stream,list(reversed(pages)))

def test_future_observation_with_valid_receipt_still_fails():
    def change(bars,rows,pages,coverage):
        for i,b in enumerate(bars):
            bars[i]=b.model_copy(update={'fetched_at':'2026-10-20T12:00:00Z'})
            rows[i]=(bars[i].model_dump(mode='json'),'test-grant','1')
        p=Page(cursor=None,next_cursor=None,complete=True,records=tuple(r[0] for r in rows))
        pages[0]=('',digest(p.model_dump(mode='json')),None,True,30,0)
    r=run(change=change)
    assert r.status=='UNAVAILABLE' and not r.metrics and r.batch is None

def test_adjusted_result_is_not_a_recommendation():
    from stock_discovery_contracts.v2 import Recommendation
    with pytest.raises(ValueError):Recommendation.model_validate_json(run().model_dump_json())

@pytest.mark.parametrize('section,field,value',[
 ('session_coverage','missing_sessions',[NOW]),
 ('session_coverage','unverified_bar_sessions',[NOW]),
 ('session_coverage','duplicate_bars',True),
 ('session_coverage','warmup_complete',False),
 ('session_coverage','latest_session_present',False),
 ('session_coverage','observed_bars',29),
 ('session_coverage','required_sessions',29),
 ('session_coverage','required_sessions',31),
 ('metrics','relative_volume20','2'),
])
def test_deserialization_rejects_contradictory_available_coverage(section,field,value):
    raw=run().model_dump(mode='json');raw[section][field]=value
    with pytest.raises(ValueError):AdjustedResearch.model_validate_json(json.dumps(raw))

@pytest.mark.parametrize('key',['sma20','ema10','ema30','atr14','relative_volume20','breakout20','support20',None])
def test_deserialization_requires_complete_metric_keys(key):
    raw=run().model_dump(mode='json')
    if key is None:raw['metrics']={}
    else:del raw['metrics'][key]
    with pytest.raises(ValueError):AdjustedResearch.model_validate_json(json.dumps(raw))

def test_deserialization_rejects_insufficient_observations():
    raw=run().model_dump(mode='json');raw['observations'].pop();raw['session_coverage']['observed_bars']=29
    with pytest.raises(ValueError):AdjustedResearch.model_validate_json(json.dumps(raw))

@pytest.mark.parametrize('with_metrics',[True,False])
def test_unavailable_state_requires_reasons_and_empty_metrics(with_metrics):
    raw=run().model_dump(mode='json');raw['status']='UNAVAILABLE'
    if with_metrics:raw['unavailable_reasons']=['session_coverage_unavailable']
    else:raw['metrics']={}
    with pytest.raises(ValueError):AdjustedResearch.model_validate_json(json.dumps(raw))

def test_nullable_indicators_and_unavailable_result_round_trip():
    raw=run().model_dump(mode='json');raw['metrics']={key:None for key in raw['metrics']}
    result=AdjustedResearch.model_validate_json(json.dumps(raw))
    assert result==AdjustedResearch.model_validate_json(result.model_dump_json())
    result=run(historical=True)
    assert result==AdjustedResearch.model_validate_json(result.model_dump_json())
