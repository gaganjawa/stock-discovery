"""Incremental actual prices through D3-02 grants and D3-03 PostgreSQL storage.

Requires permitted observed calendar sessions already in D3-03, not fabricated
weekdays. Returns ingestion evidence only; never publishes or admits a position.
"""
import json
from datetime import date, timedelta, timezone
from pathlib import Path
from typing import Annotated
from pydantic import Field
from stock_discovery_contracts.rights import Grant, UseRequest
from stock_discovery_contracts.v2 import Strict, Text, at, check, digest
from stock_discovery_analysis.evidence_storage import Access, stored_stream
from stock_discovery_analysis.revision_storage import Stream, ingest_next
from stock_discovery_analysis.revisions import Revision, InstrumentData
from stock_discovery_analysis.publication_store import now
from .providers.upstox import Upstox, RevisionPages, observed_revision


class MarketConfig(Strict):
    account_ref: Text
    grant_file: Text
    token_file: Text
    symbols: Annotated[tuple[Text,...], Field(min_length=1,max_length=100)] = ('INFY',)
    lookback_days: Annotated[int,Field(ge=40,le=366)] = 365
    retention_days: Annotated[int,Field(ge=1,le=3650)]
    region: Text = 'IN'
    refresh_calendar: bool = False
    financial_statements: bool = False


def access_for(config, clock=now, audit=lambda decision:None):
    def load(stream):
        grants=[Grant.model_validate_json(json.dumps(g)) for g in json.loads(Path(config.grant_file).read_text())]
        matches=[g for g in grants if (g.source_id,g.account_ref)==(stream.source_id,stream.account_ref)]
        check(len(matches)<=1,'ambiguous_source_grant')
        return matches[0] if matches else None
    def request(stream):
        return UseRequest(source_id=stream.source_id,account_ref=stream.account_ref,scope=stream.scope,
            uses=('acquire',),region=config.region,destination_region=None,processor_ref=None,
            requested_at=clock(),synthetic=False,units=100,retention_days=config.retention_days,attribution_present=True)
    return Access(load_grant=load,request_for=request,audit=audit,clock=clock)


def latest(conn, data, listing):
    # Use the domain logical key, shared by all revision kinds.
    probe=observed_revision(data,listing=listing,fetched=now(),parent='probe' if data.kind not in ('instrument','session') else None)
    row=conn.execute('SELECT payload FROM discovery.revisions WHERE source_id=%s AND logical_key=%s ORDER BY sequence DESC LIMIT 1',
                     ('upstox',probe.logical_key)).fetchone()
    return Revision.model_validate(row[0]) if row else None


def ingest_prices(conn, config, *, clock=now, adapter_factory=Upstox):
    """One bounded observation batch; adjusted history is refreshed in full."""
    config=MarketConfig.model_validate(config)
    audit=[]; access=access_for(config,clock,audit.append)
    lock='REAL-001:'+config.account_ref
    check(conn.autocommit,'dedicated_autocommit_connection_required')
    if not conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0]:
        return dict(status='busy',actionable=False)
    adapter=None
    try:
        cycle=clock()
        def stream(scope, listing='universe'):
            return Stream(stream_id='REAL-'+digest([cycle,scope,listing,config.account_ref]),source_id='upstox',
                          account_ref=config.account_ref,scope=scope)
        identity_stream=stream('universe')
        access.require(identity_stream,('acquire','derive','store'))
        token=Path(config.token_file).read_text().strip()
        check(bool(token),'upstox_credentials_missing')
        adapter=adapter_factory(access=access,token=token)
        identities=adapter.instruments(identity_stream,config.symbols)
        # Only eligible observed sessions with current rights. No SYN calendar.
        sessions={}
        for rid,raw in conn.execute("SELECT revision_id,payload FROM discovery.revisions WHERE kind='session' AND payload->>'availability_basis'='observed' AND available_at<=%s",(cycle,)):
            r=Revision.model_validate(raw)
            if at(r.fetched_at)>at(cycle):continue
            access.require(stored_stream(conn,rid),('derive',))
            from zoneinfo import ZoneInfo
            day=at(r.data.opens_at).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()
            pair=(r.data.opens_at,r.data.closes_at)
            check(day not in sessions or sessions[day]==pair,'ambiguous_calendar_session')
            sessions[day]=pair
        check(bool(sessions),'observed_calendar_unavailable')
        reports=[]
        def save(s, records):
            pages=RevisionPages(records);results=[]
            while True:
                _,request=access.require(s,('store',))
                result=ingest_next(conn,s,pages,load_grant=lambda:access.load_grant(s),request=request,audit=access.audit,clock=clock)
                results.append(result)
                check(not result.get('quarantined'),'source_records_quarantined')
                state=conn.execute('SELECT complete FROM discovery.streams WHERE stream_id=%s',(s.stream_id,)).fetchone()
                if state and state[0]:return results
        for identity in identities:
            fetched=clock();listing='NSE:'+identity['isin']
            data=InstrumentData(kind='instrument',issuer_id=identity['isin'],symbol=identity['symbol'],isin=identity['isin'],
                series='EQ',status='active',lot_size=identity['lot_size'],tick_size=identity['tick_size'],effective_at=fetched)
            prior=latest(conn,data,listing)
            # BOD refresh is not a corporate identity change.
            if prior:data=data.model_copy(update={'effective_at':prior.data.effective_at})
            instrument=observed_revision(data,listing=listing,fetched=fetched,previous=prior)
            save(stream('universe',listing),(instrument,))
            price_stream=stream('prices',listing)
            access.require(price_stream,('acquire','derive','store'))
            end=max(date.fromisoformat(day) for day,(_,closes) in sessions.items() if at(closes)<=at(cycle))
            start=end-timedelta(days=config.lookback_days)
            # V3 back-adjustments can change any earlier bar; refresh the full
            # configured window rather than merging a short overlap with old bases.
            observations=adapter.candles(price_stream,instrument,start.isoformat(),end.isoformat(),sessions)
            records=tuple(observed_revision(d,listing=listing,fetched=f,parent=instrument.revision_id,previous=latest(conn,d,listing)) for d,f in observations)
            stored=save(price_stream,records)
            received={r.data.starts_at for r in records}
            gaps=[day for day,(opens,closes) in sessions.items() if start.isoformat()<=day<=end.isoformat() and opens not in received]
            reports.append(dict(**identity,listing_id=listing,from_date=start.isoformat(),to_date=end.isoformat(),
                candles=len(records),missing_sessions=sorted(gaps),storage=stored))
        return dict(status='partial' if any(r['missing_sessions'] for r in reports) else 'ingested',
                    fetched_at=clock(),instruments=reports,actionable=False,mode='live_paper',
                    research_status='not_run',rights_audit=[d.model_dump() for d in audit])
    finally:
        if adapter:adapter.close()
        conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))


def handlers(schedule, config):
    """D3-04 price ingestion stage; downstream unqualified stages stay blocked."""
    from stock_discovery_analysis.schedule_runner import JobFailure
    check(schedule.mode=='live_paper','real_scheduler_requires_live_paper')
    config=MarketConfig.model_validate(config)
    check(schedule.input_hash==digest(config.model_dump(mode='json')),'real_config_hash_mismatch')
    def ingest(conn, job, clock):
        try:
            if config.refresh_calendar:ingest_calendar(conn,config,clock=clock)
            result=ingest_prices(conn,config,clock=clock)
            if config.financial_statements and result['status']!='busy':
                result['financials']=ingest_configured_financials(conn,config,result,clock=clock)
        except FileNotFoundError:
            raise JobFailure('credentials') from None
        if result['status']=='busy':raise JobFailure('readiness')
        return result,'snapshot'
    def blocked(conn, job, clock):
        raise JobFailure('policy')
    return {'ingest':ingest,'snapshot':blocked,'screen':blocked,'event_poll':blocked,'reassess':blocked}


def ingest_calendar(conn, config, *, clock=now):
    """Explicit bounded refresh of dated sessions for the configured price window."""
    import time
    from zoneinfo import ZoneInfo
    config=MarketConfig.model_validate(config)
    check(conn.autocommit,'dedicated_autocommit_connection_required')
    access=access_for(config,clock)
    cycle=clock();end=at(cycle).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).date()
    start=end-timedelta(days=config.lookback_days+7)
    # Include today's dated session; ingest_prices excludes it until its close.
    # Include a closure buffer before the latest observed trading session.
    # At most 52 dates keeps a run within the documented conservative per-minute budget.
    check(config.lookback_days<=44,'calendar_refresh_limit_44_days')
    stream=Stream(stream_id='REAL-CALENDAR-'+digest([cycle,config.account_ref]),source_id='upstox',account_ref=config.account_ref,scope='calendar')
    access.require(stream,('acquire','derive','store'))
    client=None
    lock='REAL-001:'+config.account_ref
    check(conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0],'real_ingestion_busy')
    try:
        client=Upstox(access=access,token=Path(config.token_file).read_text().strip())
        records=[];closed=[]
        for offset in range((end-start).days+1):
            day=(start+timedelta(days=offset)).isoformat()
            data=client.session(stream,day)
            if data is None:closed.append(day)
            else:
                records.append(observed_revision(data,listing='NSE',fetched=clock(),previous=latest(conn,data,'NSE')))
            time.sleep(.65)
        _,request=access.require(stream,('store',))
        result=ingest_next(conn,stream,RevisionPages(records),load_grant=lambda:access.load_grant(stream),request=request,audit=access.audit,clock=clock)
        check(not result.get('quarantined'),'calendar_quarantined')
        return dict(from_date=start.isoformat(),to_date=end.isoformat(),observed_sessions=len(records),closed_dates=closed,storage=result)
    finally:
        if client:client.close()
        conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))


def ingest_configured_financials(conn,config,market_result,*,clock=now):
    """Eligible D3-04 ingestion only; publication still requires actual policies."""
    from .providers.upstox_financials import ingest_financials
    config=MarketConfig.model_validate(config)
    access=access_for(config,clock);lock='REAL-001:'+config.account_ref
    check(conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0],'real_ingestion_busy')
    client=None
    try:
        results=[]
        for item in market_result['instruments']:
            row=conn.execute("SELECT payload FROM discovery.revisions WHERE source_id='upstox' AND listing_id=%s AND kind='instrument' ORDER BY sequence DESC LIMIT 1",(item['listing_id'],)).fetchone()
            check(row is not None,'observed_instrument_required')
            identity=Revision.model_validate(row[0])
            access.require(stored_stream(conn,identity.revision_id),('derive',))
            if client is None:client=Upstox(access=access,token=Path(config.token_file).read_text().strip())
            results.extend(ingest_financials(conn,client,identity,config.account_ref))
        return results
    finally:
        if client:client.close()
        conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))
