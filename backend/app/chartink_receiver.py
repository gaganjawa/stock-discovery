"""Optional small receiver entrypoint; do not publish the research application.

Run with --no-access-log: Chartink supports a URL, not documented auth headers.
Public deployment/TLS is a separate owner-authorized operation.
"""
import asyncio
import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends, Query, Response
from starlette.concurrency import run_in_threadpool
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.chartink import Scanner, normalize, MAX_BYTES
from stock_discovery_analysis import candidate_store as store
from .research import db
from .security import LoginLimiter
from . import chartink_diagnostics
from stock_discovery_analysis.chartink_diagnostics import decode_payload

app=FastAPI(title='Candidate receiver',docs_url=None,redoc_url=None,openapi_url=None)
limiter=LoginLimiter()


def check_secret(supplied, name):
    if os.environ.get('CHARTINK_RECEIVER_ENABLED')!='true':
        raise HTTPException(503,'Candidate receiver is disabled')
    try: expected=setting(name)
    except OSError: raise HTTPException(503,'Receiver is not configured') from None
    if len(expected)<32:raise HTTPException(503,'Receiver is not configured')
    if not hmac.compare_digest(supplied.encode(),expected.encode()):raise HTTPException(401,'Receiver authentication required')


@app.middleware('http')
async def headers(request, call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['Referrer-Policy']='no-referrer'
    return response


def ingest(conn, body):
    try:
        scanner=Scanner.model_validate_json(Path(os.environ['CHARTINK_SCANNER_CONFIG']).read_text())
    except (KeyError,OSError,ValueError):raise HTTPException(503,'Scanner configuration unavailable') from None
    payload=None
    try:
        payload=decode_payload(body)
        envelope=normalize(payload,scanner,datetime.now(timezone.utc))
    except (ValueError,UnicodeError,RecursionError) as exc:
        code=str(exc) if str(exc) in {'invalid_payload_fields','invalid_payload_values','scanner_identity_mismatch',
            'invalid_symbol','invalid_symbol_price_count','invalid_trigger_price','invalid_trigger_time',
            'scanner_authorization_expired','timezone_required','duplicate_payload_field',
            'invalid_provider_test_payload','invalid_columns_count','invalid_columns_fields',
            'column_symbol_mismatch','conflicting_payload_versions','invalid_enrichment_text',
            'invalid_enrichment_number','invalid_enrichment_range'} else 'invalid_json'
        chartink_diagnostics.record(payload,code)
        store.reject(conn,hashlib.sha256(body).hexdigest(),code)
        raise HTTPException(422,code) from None
    try:
        receipt=store.accept(conn,envelope)
        return {**receipt,'delivery_kind':envelope.get('delivery_kind','candidate_alert')}

    except OverflowError:raise HTTPException(503,'Candidate inbox capacity reached; operator action required') from None
    except ValueError as exc:
        if str(exc)=='event_too_large':
            raise HTTPException(413,'Normalized candidate event exceeds storage limit') from None
        if str(exc) in {'scanner_version_content_conflict','event_identity_conflict'}:
            raise HTTPException(409,'Candidate event conflicts with stored identity') from None
        raise


def webhook_auth(capability:str,request:Request):
    # Unauthenticated flood protection per process; valid calls share DB throttling.
    try:check_secret(capability,'CHARTINK_WEBHOOK_SECRET')
    except HTTPException:
        if not limiter.allow(request.client.host if request.client else 'unknown'):
            raise HTTPException(429,'Too many authentication attempts',headers={'Retry-After':'60'})
        raise


@app.post('/hooks/chartink/{capability}',status_code=202,dependencies=[Depends(webhook_auth)])
async def receive(request:Request,conn=Depends(db)):
    if not await run_in_threadpool(store.rate_allowed,conn):
        raise HTTPException(429,'Receiver rate limit',headers={'Retry-After':'60'})
    if request.headers.get('content-type','').split(';')[0].strip()!='application/json':
        raise HTTPException(415,'JSON required')
    if request.headers.get('content-encoding','identity')!='identity':raise HTTPException(415,'Compression not supported')
    body=bytearray()
    try:
        async with asyncio.timeout(10):
            async for part in request.stream():
                body.extend(part)
                if len(body)>MAX_BYTES:raise HTTPException(413,'Payload too large')
    except TimeoutError:raise HTTPException(408,'Receiver body timeout') from None
    return await run_in_threadpool(ingest,conn,bytes(body))


def feed_auth(request:Request):
    check_secret(request.headers.get('Authorization','').removeprefix('Bearer '),'CHARTINK_PULL_SECRET')


@app.get('/candidate-feed',dependencies=[Depends(feed_auth)])
def retrieve(request:Request,after:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=25),conn=Depends(db)):
    if not store.rate_allowed(conn):raise HTTPException(429,'Receiver rate limit',headers={'Retry-After':'60'})
    return store.feed(conn,after,limit)


@app.get('/healthz')
def health(conn=Depends(db)):
    # Internal container check only; reverse proxy does not publish this route.
    conn.execute('SELECT 1 FROM discovery.candidate_events LIMIT 1')
    return {'database':'available','receiver_enabled':os.environ.get('CHARTINK_RECEIVER_ENABLED')=='true'}


@app.get('/candidate-health',dependencies=[Depends(feed_auth)])
def operational_health(after:int=Query(0,ge=0),conn=Depends(db)):
    if not store.rate_allowed(conn):raise HTTPException(429,'Receiver rate limit')
    count,high,last,lag,oldest=conn.execute('''SELECT count(*),coalesce(max(sequence),0),
      max(received_at),count(*) FILTER (WHERE sequence>%s),
      min(received_at) FILTER (WHERE sequence>%s) FROM discovery.candidate_events''',(after,after)).fetchone()
    tests=conn.execute("SELECT count(*) FROM discovery.candidate_events WHERE envelope->>'version'='chartink-provider-test-v1'").fetchone()[0]
    rejected=conn.execute('SELECT count(*) FROM discovery.candidate_rejections').fetchone()[0]
    return dict(database='available',stored_events=count,capacity=store.MAX_EVENTS,
        provider_test_events=tests,candidate_delivery_events=count-tests,
        high_water=high,events_after_cursor=lag,oldest_unpulled_at=oldest,
        last_receipt_at=last,rejection_records=rejected,
        coverage='unknown_partial_alerts',cursor_ahead=after>high,
        rejection_diagnostics=chartink_diagnostics.read())
