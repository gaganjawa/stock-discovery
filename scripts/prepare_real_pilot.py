"""Freeze an owner-local bounded watchlist and observed D3-04 calendar; no grants."""
import argparse,json,time,os
from datetime import timedelta
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.publication_store import now
from stock_discovery_analysis.scheduling import ScheduleCalendar,ScheduleConfig,SchedulePolicy,TradingSession,utc
from stock_discovery_contracts.v2 import Ref,digest,check
from stock_discovery_analysis.revision_storage import Stream,ingest_next
from worker.providers.upstox import Upstox,RevisionPages,observed_revision
from worker.real_market import MarketConfig,access_for,ingest_calendar,latest
from worker.real_pilot import PilotConfig,select_watchlist
from worker.real_evidence import EvidenceConfig
from stock_discovery_analysis.real_views import ViewConfig


def main():
 p=argparse.ArgumentParser();p.add_argument('--market',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--view',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--size',type=int,default=12);p.add_argument('--anchor',action='append',default=[]);p.add_argument('--code-version',required=True);a=p.parse_args()
 check(not a.output.exists(),'output_directory_already_exists');a.output.mkdir(mode=0o700)
 market=MarketConfig.model_validate_json(a.market.read_text());access=access_for(market)
 stream=Stream(stream_id='PILOT-UNIVERSE-'+digest(now()),source_id='upstox',account_ref=market.account_ref,scope='universe')
 access.require(stream,('acquire','derive','store'));client=Upstox(access=access,token=Path(market.token_file).read_text().strip())
 try:
  rows,_=client.instrument_master(stream);universe=select_watchlist(rows,a.size,tuple(a.anchor));universe['observed_at']=now();universe['account_ref']=market.account_ref;universe['version']=digest(universe)
 finally:client.close()
 with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as db:
  report=ingest_calendar(db,market.model_copy(update={'lookback_days':44}))
  today=utc(now()).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).date();future={};records=[];client=Upstox(access=access,token=Path(market.token_file).read_text().strip())
  cs=stream.model_copy(update={'stream_id':'PILOT-FUTURE-'+digest(now()),'scope':'calendar'})
  access.require(cs,('acquire','derive','store'))
  try:
   for offset in range(8):
    day=(today+timedelta(days=offset)).isoformat();data=client.session(cs,day);future[day]=None if data is None else data.model_dump(mode='json')
    if data:records.append(observed_revision(data,listing='NSE',fetched=now(),previous=latest(db,data,'NSE')))
    time.sleep(.7)
   _,request=access.require(cs,('store',));ingest_next(db,cs,RevisionPages(records),load_grant=lambda:access.load_grant(cs),request=request,audit=access.audit,clock=now)
  finally:client.close()
  sessions=tuple(TradingSession(opens_at=r['opens_at'],closes_at=r['closes_at']) for r in future.values() if r)
  check(len(sessions)>=2,'future_exchange_sessions_unavailable')
  available=now();ref=Ref(id='upstox-observed-pilot-calendar',version=available,content_hash=digest([s.model_dump() for s in sessions]))
  calendar=ScheduleCalendar(ref=ref,available_at=available,starts_on=today.isoformat(),ends_on=max(future),sessions=sessions)
 evidence=EvidenceConfig.model_validate_json(a.evidence.read_text());view=ViewConfig.model_validate_json(a.view.read_text()).model_copy(update={'listing_ids':tuple(m['listing_id'] for m in universe['members']),'pilot_scope_id':'REAL-001-PILOT-'+universe['version']})
 config=PilotConfig(market=market.model_copy(update={'symbols':tuple(m['symbol'] for m in universe['members']),'lookback_days':50}),view=view,evidence=evidence,universe=universe)
 schedule=ScheduleConfig(schema_version='1.0.0',schedule_id='REAL-001-PILOT',scope_id=view.pilot_scope_id,input_hash=digest(config.model_dump(mode='json')),code_version=a.code_version,mode='live_paper',calendar=calendar,policy=SchedulePolicy(version='D3-04-pilot-1',ready_delay_minutes=30,readiness_retry_minutes=15,swing_stop_before_open_minutes=60,short_term_window_minutes=1440,long_term_window_minutes=1440,event_window_start_hour=8,event_window_end_hour=20,max_events_per_call=1),horizons=('swing',),starts_on=today.isoformat())
 for name,value in [('pilot.json',config.model_dump(mode='json')),('schedule.json',schedule.model_dump(mode='json')),('view.json',view.model_dump(mode='json')),('preparation.json',dict(calendar=report,future= future,universe=universe,bootstrap_requests=61))]:
  f=a.output/name;f.write_text(json.dumps(value,indent=2));f.chmod(0o600)
 print(json.dumps({'members':len(universe['members']),'label':universe['label'],'calendar_through':max(future),'schedule_id':schedule.schedule_id,'automatic_run':'not_yet_observed'}))
if __name__=='__main__':main()
