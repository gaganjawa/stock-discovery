"""Local supervision controls around the existing D3-04 worker, not a scheduler."""
import fcntl
import json
import os
import resource
import shutil
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from stock_discovery_contracts.v2 import Ref, check, digest
from stock_discovery_contracts.rights import cleanup_plan
from stock_discovery_analysis.scheduling import ScheduleCalendar, ScheduleConfig, TradingSession, IST, utc, stamp
from stock_discovery_analysis.revision_storage import Stream, ingest_next
from stock_discovery_analysis.publication_store import now
from .real_market import access_for, latest
from .providers.upstox import Upstox, RevisionPages, observed_revision


def atomic(path, value):
    path=Path(path); temp=path.with_suffix(path.suffix+'.tmp')
    with open(temp,'w',opener=lambda p,f:os.open(p,f,0o600)) as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def singleton(account):
    # Common path even when a second invocation supplies a different state directory.
    path=Path('/tmp')/f'stk-pilot-{os.getuid()}-{digest(account)[:16]}.lock'
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd);raise RuntimeError('pilot_worker_already_running') from None
    return os.fdopen(fd,'w')  # Keep open for the lifetime of the worker, including idle.


def next_occurrence(schedule, clock):
    for i,s in enumerate(schedule.calendar.sessions[:-1]):
        due=utc(s.closes_at)+timedelta(minutes=30)
        if due>utc(clock):return stamp(due)
    return None


def renew_calendar(conn, schedule, pilot, *, clock=now, factory=Upstox, pause=time.sleep):
    """All dated responses must validate before atomically replacing planning coverage."""
    access=access_for(pilot.market,clock)
    stream=Stream(stream_id='PILOT-CALENDAR-'+digest(clock()),source_id='upstox',account_ref=pilot.market.account_ref,scope='calendar')
    access.require(stream,('acquire','derive','store'))
    today=utc(clock()).astimezone(IST).date()
    # Keep a bounded catch-up window; do not invent calendar closure from an error.
    start=max(date.fromisoformat(schedule.starts_on),today-timedelta(days=7))
    end=today+timedelta(days=14);observations={};records=[];calls=0
    def gate():
        nonlocal calls
        code='pilot_request:'+digest(pilot.market.account_ref)
        recent=conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code=%s AND at>%s::timestamptz-interval '30 minutes'",(code,clock())).fetchone()[0]
        minute=conn.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code=%s AND at>%s::timestamptz-interval '1 minute'",(code,clock())).fetchone()[0]
        check(recent<800 and minute<90 and calls<23,'source_rate_limited')
        conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (NULL,%s,%s)',(clock(),code));calls+=1;pause(.7)
    client=factory(access=access,token=Path(pilot.market.token_file).read_text().strip(),request_gate=gate)
    try:
        for offset in range((end-start).days+1):
            day=(start+timedelta(days=offset)).isoformat();item=client.session(stream,day)
            observations[day]=None if item is None else item.model_dump(mode='json')
            if item:records.append(observed_revision(item,listing='NSE',fetched=clock(),previous=latest(conn,item,'NSE')))
        access.require(stream,('acquire','derive','store'))
        sessions=tuple(TradingSession(opens_at=x['opens_at'],closes_at=x['closes_at']) for x in observations.values() if x)
        check(any(utc(s.opens_at)>utc(clock()) for s in sessions),'next_session_unavailable')
        observed=clock();ref=Ref(id='upstox-observed-pilot-calendar',version=observed,content_hash=digest([s.model_dump() for s in sessions]))
        calendar=ScheduleCalendar(ref=ref,available_at=observed,starts_on=start.isoformat(),ends_on=end.isoformat(),sessions=sessions)
        renewed=ScheduleConfig.model_validate_json(json.dumps({**schedule.model_dump(mode='json'),'starts_on':start.isoformat(),'calendar':calendar.model_dump(mode='json')}))
        _,request=access.require(stream,('store',))
        ingest_next(conn,stream,RevisionPages(records),load_grant=lambda:access.load_grant(stream),request=request,audit=access.audit,clock=clock)
        return renewed,dict(observed_at=observed,requests=calls,dates=observations,previous_calendar_hash=schedule.calendar.ref.content_hash)
    finally:client.close()


class Operations:
    def __init__(self,directory,schedule,pilot,clock=now):
        self.path=Path(directory);self.path.mkdir(mode=0o700,parents=False,exist_ok=True)
        check(not self.path.is_symlink() and self.path.stat().st_uid==os.getuid() and not self.path.stat().st_mode&0o077,'private_operations_directory_required')
        self.pilot=pilot;self.clock=clock;self.base=schedule
        self.state=self.read('health.json',{})
        saved=self.read('schedule.json',None)
        self.schedule=ScheduleConfig.model_validate_json(json.dumps(saved)) if saved else schedule
        check(self.schedule.scope_id==schedule.scope_id and self.schedule.input_hash==schedule.input_hash and self.schedule.code_version==schedule.code_version,'operations_configuration_mismatch')
        self.started=clock();self.last=time.time();self.last_mono=time.monotonic()
        self.event('worker_started')

    def read(self,name,default):
        try:return json.loads((self.path/name).read_text())
        except FileNotFoundError:return default

    def event(self,code):
        # Only our own non-source operational diagnostics; fixed ring bounds growth.
        f=self.path/'operations.jsonl'
        check(not f.is_symlink(),'diagnostic_symlink_refused')
        rotated=False
        if f.exists() and f.stat().st_size>256*1024:
            rotated=True
            for i in range(3,0,-1):
                old=self.path/f'operations.{i}.jsonl'
                if old.exists():
                    if i==3:old.unlink()
                    else:old.replace(self.path/f'operations.{i+1}.jsonl')
            f.replace(self.path/'operations.1.jsonl')
        with open(f,'a',opener=lambda p,flags:os.open(p,flags,0o600)) as out:
            out.write(json.dumps(dict(at=self.clock(),event=code,disposable_log_rotation=rotated))+'\n')

    def preflight(self,conn):
        wall=time.time();mono=time.monotonic()
        gap=wall-self.last;delta=gap-(mono-self.last_mono)
        if gap>120 or abs(delta)>30:
            self.state['last_resume_gap_seconds']=round(gap,2);self.state['resume_detected_at']=self.clock();self.event('pause_or_sleep_resume_detected')
        self.last=wall;self.last_mono=mono
        usage=resource.getrusage(resource.RUSAGE_SELF)
        size=conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]
        disk=shutil.disk_usage(self.path)
        self.state['resources']=dict(database_bytes=size,free_disk_bytes=disk.free,worker_cpu_seconds=usage.ru_utime+usage.ru_stime,worker_peak_rss_bytes=usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024),operations_bytes=sum(p.stat().st_size for p in self.path.iterdir() if p.is_file()))
        check(size<2*1024**3 and disk.free>2*1024**3 and self.state['resources']['operations_bytes']<64*1024**2,'resource_high_water_stop')
        access=access_for(self.pilot.market,self.clock)
        stream=Stream(stream_id='PILOT-OPERATIONS',source_id='upstox',account_ref=self.pilot.market.account_ref,scope='calendar')
        grant=access.load_grant(stream);plan=cleanup_plan(grant,self.clock())
        self.state['retention']=dict(status='review_required' if plan else 'within_grant',original_data_deleted=False,disposable_log_limit_bytes=4*256*1024)
        if plan:
            self.state['retention'].update(reason=plan.reason,delete_by_at=plan.delete_by_at)
            raise PermissionError('retention_review_required_no_original_deletion')
        oldest=conn.execute("SELECT min((payload->>'fetched_at')::timestamptz) FROM discovery.revisions WHERE source_id='upstox' AND payload->>'availability_basis'='observed'").fetchone()[0]
        if oldest and (utc(self.clock())-oldest).total_seconds()>=grant.retention_days*86400:
            self.state['retention']['status']='age_limit_review_required';raise PermissionError('retention_review_required_no_original_deletion')
        for scope in ('universe','calendar','prices','financial_facts','filings'):
            access.require(stream.model_copy(update={'scope':scope}),('derive','store'))
        # Refresh daily, on resume/expiry, and before the remaining horizon is short.
        previous=self.state.get('calendar_checked_at')
        due=not previous or (utc(self.clock())-utc(previous)).total_seconds()>=86400 or (date.fromisoformat(self.schedule.calendar.ends_on)-utc(self.clock()).astimezone(IST).date()).days<4
        retry=self.state.get('calendar_retry_at')
        if due and (not retry or utc(self.clock())>=utc(retry)):
            self.state['calendar_retry_at']=stamp(utc(self.clock())+timedelta(hours=1))
            self.save('checking_calendar')  # Persist retry deadline even if the provider/crash interrupts.
            renewed,report=renew_calendar(conn,self.schedule,self.pilot,clock=self.clock)
            atomic(self.path/('calendar-'+digest(report)+'.json'),report);atomic(self.path/'schedule.json',renewed.model_dump(mode='json'))
            self.schedule=renewed;self.state['calendar_checked_at']=self.clock();self.state.pop('calendar_retry_at',None);self.event('calendar_renewed')
        # Unknown or outdated current calendar must never permit new source work.
        check(self.state.get('calendar_checked_at') and (utc(self.clock())-utc(self.state['calendar_checked_at'])).total_seconds()<86400,'calendar_refresh_required')
        check(not __import__('stock_discovery_analysis.scheduling',fromlist=['calendar_issues']).calendar_issues(self.schedule,self.clock()),'calendar_coverage_unknown')
        return self.schedule

    def save(self,status,result=None):
        self.state.update(at=self.clock(),started_at=self.started,pid=os.getpid(),status=status,scope_id=self.schedule.scope_id,calendar_through=self.schedule.calendar.ends_on,next_occurrence_at=next_occurrence(self.schedule,self.clock()),persistent_startup='not_activated_by_this_program')
        if result:self.state['last_tick']=result
        atomic(self.path/'health.json',self.state)
