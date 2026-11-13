"""Opt-in bounded candidate price refresh; no webhook or live service changes."""
import argparse
import json
import time
from datetime import timedelta
from pathlib import Path
from typing import Annotated
from pydantic import Field, model_validator
import psycopg
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import Strict, Text, digest, check
from stock_discovery_analysis import candidate_price_store as jobs
from stock_discovery_analysis.publication_store import now
from stock_discovery_analysis.scheduling import utc, IST
from stock_discovery_analysis.schedule_store import finish, retry, fenced_row, StaleLease
from stock_discovery_analysis.runtime import setting
from .real_market import MarketConfig, ingest_prices, ingest_calendar
from .providers.upstox import Upstox, UpstreamAccessRejected


class RefreshConfig(Strict):
    market: MarketConfig
    scanner_keys: Annotated[tuple[Text,...],Field(min_length=1,max_length=10)]
    candidate_days: Annotated[int,Field(ge=1,le=7)] = 3
    max_symbols: Annotated[int,Field(ge=1,le=100)] = 20

    @model_validator(mode='after')
    def bounds(self):
        check(self.market.lookback_days<=44,'candidate_calendar_window_limit')
        check(not self.market.financial_statements and not self.market.corporate_actions,
              'candidate_refresh_prices_only')
        return self


def identity(config):
    return digest([jobs.VERSION,config.model_dump(mode='json')])


def retry_reason(exc):
    if isinstance(exc,UpstreamAccessRejected):return exc.reason
    if isinstance(exc,PermissionError):return 'rights'
    if isinstance(exc,FileNotFoundError):return 'credentials'
    if isinstance(exc,TimeoutError):return 'transient'
    if str(exc) in ('source_rate_limited','upstox_rate_limited','upstox_http_500','upstox_http_502','upstox_http_503','upstox_http_504','upstox_unavailable'):return 'transient'
    if str(exc).startswith(('instrument_missing_or_ambiguous','observed_calendar_unavailable','unverified_market_session')):return 'readiness'
    return 'permanent'


def cycle(conn, config, *, clock=now, factory=Upstox, pause=time.sleep):
    config=RefreshConfig.model_validate(config)
    check(conn.autocommit,'dedicated_autocommit_connection_required')
    check(conn.execute('SELECT version_num FROM alembic_version').fetchone()==('0017',),'schema_0017_required')
    # Same account lock as existing ingestion; separate processes cannot overlap.
    lock='REAL-001:'+config.market.account_ref
    if not conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0]:
        return dict(status='busy',provider_requests=0)
    try:
        started=clock();day=utc(started).astimezone(IST).date();since=day-timedelta(days=config.candidate_days-1)
        key=identity(config)
        jobs.supersede(conn,key,day.isoformat(),started)
        # Explicit market.symbols is the existing acquisition allowlist, not a new
        # permission source. The configured scanner must also have observed a match.
        symbols=[r[0] for r in conn.execute('''SELECT DISTINCT symbol FROM discovery.candidates
            WHERE scanner_key=ANY(%s) AND session_date BETWEEN %s AND %s AND first_observed_at<=%s
            AND symbol=ANY(%s) ORDER BY symbol''',
            (list(config.scanner_keys),since,day,started,list(config.market.symbols))).fetchall()]
        outside=conn.execute("""SELECT count(DISTINCT symbol) FROM discovery.candidates
            WHERE scanner_key=ANY(%s) AND session_date BETWEEN %s AND %s AND first_observed_at<=%s
            AND NOT(symbol=ANY(%s))""",(list(config.scanner_keys),since,day,started,list(config.market.symbols))).fetchone()[0]
        selection=dict(eligible_symbols=len(symbols),outside_configured_universe=outside)
        target=conn.execute("""SELECT max((payload->'data'->>'closes_at')::timestamptz)::date
            FROM discovery.revisions WHERE source_id='upstox' AND kind='session'
            AND available_at<=%s AND (payload->>'fetched_at')::timestamptz<=%s
            AND (payload->'data'->>'closes_at')::timestamptz<=%s""",(started,started,started)).fetchone()[0]
        target=target.isoformat() if target else None
        prior=conn.execute("""SELECT payload->>'symbol',status,result FROM discovery.schedule_jobs
            WHERE payload->>'code_version'=%s AND payload->>'schedule_hash'=%s
            AND payload->>'refresh_day'=%s""",(jobs.VERSION,key,day.isoformat())).fetchall()
        # A morning success cannot suppress a refresh after another session closes.
        known={symbol for symbol,status,result in prior if status!='completed'
               or target is None or (result or {}).get('latest_session','')>=target}
        jobs.enqueue(conn,key,[s for s in symbols if s not in known][:config.max_symbols],
                     day.isoformat(),started,target_session=target,scanner_keys=config.scanner_keys)
        job=jobs.claim(conn,key,clock())
        if job is None:return dict(status='idle',provider_requests=0,selection=selection,queue=jobs.status(conn,key))
        calls=0
        def gate():
            nonlocal calls
            pause(.7)
            fenced_row(conn,job,clock())
            code='pilot_request:'+digest(config.market.account_ref)
            count,minute=conn.execute('''SELECT count(*),count(*) FILTER(WHERE at>%s::timestamptz-interval '1 minute')
                FROM discovery.schedule_audit WHERE code=%s AND at>%s::timestamptz-interval '30 minutes' ''',
                (clock(),code,clock())).fetchone()
            check(count<800 and minute<90 and calls<60,'source_rate_limited')
            # Autocommit before the HTTP request: crashes never refund quota.
            conn.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',
                         (job['job_id'],clock(),code));calls+=1
        class Client(factory):
            def __init__(self,**kwargs):super().__init__(**kwargs,request_gate=gate)
        try:
            market=config.market.model_copy(update={'symbols':(job['payload']['symbol'],)})
            calendar_key=digest([key,'calendar',day.isoformat()])
            saved=conn.execute('SELECT 1 FROM discovery.schedule_outbox WHERE event_key=%s',(calendar_key,)).fetchone()
            if not saved:
                calendar=ingest_calendar(conn,market,clock=clock,adapter_factory=Client,pause=lambda _:None)
                # Only a complete validated refresh can become a reusable receipt.
                with conn.transaction():
                    fenced_row(conn,job,clock())
                    conn.execute('''INSERT INTO discovery.schedule_outbox VALUES (%s,%s,'candidate_calendar',%s,%s)
                        ON CONFLICT DO NOTHING''',(calendar_key,job['job_id'],Jsonb(calendar),clock()))
            result=ingest_prices(conn,market,clock=clock,adapter_factory=Client)
            records=result.get('instruments',[])
            complete=(result['status']=='ingested' and len(records)==1
                and records[0]['symbol']==job['payload']['symbol'] and records[0]['candles']>=30
                and not records[0]['missing_sessions'])
            summary=dict(status='ingested' if complete else 'partial',symbol=job['payload']['symbol'],
                candles=records[0]['candles'] if len(records)==1 else 0,
                latest_session=records[0]['to_date'] if len(records)==1 else None,
                price_stream_id=records[0].get('price_stream_id') if len(records)==1 else None,
                missing_sessions=records[0]['missing_sessions'] if len(records)==1 else [],
                provider_requests=calls,selection=selection,actionable=False)
            if not complete:
                with conn.transaction():
                    fenced_row(conn,job,clock())
                    conn.execute('UPDATE discovery.schedule_jobs SET result=%s WHERE job_id=%s',(Jsonb(summary),job['job_id']))
                    if job['attempts']>=3:finish(conn,job,clock(),status='partial',result=summary,error_code='price_coverage_incomplete')
                    else:retry(conn,job,clock(),reason='readiness')
                return {**summary,'job_id':job['job_id']}
            jobs.complete(conn,job,summary,config.scanner_keys,since,clock())
            return {**summary,'job_id':job['job_id'],'research_status':'queued'}
        except StaleLease:
            return dict(status='lease_lost',provider_requests=calls,selection=selection)
        except Exception as exc:
            reason=retry_reason(exc)
            try:state=retry(conn,job,clock(),reason=reason,retry_after_seconds=60 if reason=='transient' else 0)
            except StaleLease:state='lease_lost'
            return dict(status=state,reason=reason,error_type=type(exc).__name__,provider_requests=calls,selection=selection)
    finally:conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    config=RefreshConfig.model_validate_json(args.config.read_text())
    from .pilot_operations import singleton
    with singleton(config.market.account_ref):
        serve(config,args.once)


def serve(config, once):
    while True:
        with psycopg.connect(setting('DATABASE_URL'),autocommit=True,connect_timeout=5) as conn:
            result=cycle(conn,config)
        print(json.dumps(result),flush=True)
        if once:return
        time.sleep(60)


if __name__=='__main__':main()
