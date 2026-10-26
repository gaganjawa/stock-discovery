"""Bounded factual watchlist research on D3-04 jobs; never strategy activation."""
import json
import re
import time
import resource
import sys
from datetime import datetime
from collections import Counter
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import psycopg
from psycopg.types.json import Jsonb
from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, check, digest
from stock_discovery_analysis.publication_store import now
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.real_views import ViewConfig, company
from stock_discovery_analysis.revision_storage import Stream
from stock_discovery_analysis.real_access import source_access
from stock_discovery_analysis.rag_retrieval import retrieve
from stock_discovery_analysis.rag_contracts import Query
from stock_discovery_analysis.factual_research import candidates
from stock_discovery_analysis import factual_research, rag_research
from stock_discovery_analysis.schedule_runner import JobFailure
from stock_discovery_analysis.schedule_store import fenced_row, StaleLease
from .real_market import MarketConfig, access_for, ingest_prices, ingest_configured_financials
from .real_evidence import EvidenceConfig, run as research
from .providers.upstox import Upstox, MASTER
from .providers.ollama import Ollama

VERSION='limited-watchlist-research-1.0.0'


def select_watchlist(rows, limit=12, anchors=()):
    """BOD EQ presence only; alphabetic sample is explicitly NOT liquidity ranking."""
    check(10<=limit<=20 and len(set(anchors))==len(anchors) and len(anchors)<=limit,'watchlist_bounds')
    eq=[r for r in rows if (r.get('segment'),r.get('exchange'),r.get('instrument_type'))==('NSE_EQ','NSE','EQ')]
    symbols=Counter(r.get('trading_symbol') for r in eq);isins=Counter(r.get('isin') for r in eq)
    valid=[];excluded=[]
    for r in eq:
        symbol=r.get('trading_symbol');isin=r.get('isin');reason=None
        if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9&-]{1,30}',symbol):reason='invalid_symbol'
        elif symbols[symbol]!=1 or isins[isin]!=1:reason='ambiguous_symbol_or_isin'
        elif not isinstance(isin,str) or not re.fullmatch(r'IN[A-Z0-9]{10}',isin) or r.get('instrument_key')!='NSE_EQ|'+isin:reason='invalid_identity'
        else:
            try:check(type(r['lot_size']) is int and r['lot_size']>0 and Decimal(str(r['tick_size'])).is_finite() and Decimal(str(r['tick_size']))>0,'invalid_trading_units')
            except (ValueError,KeyError,ArithmeticError):reason='invalid_trading_units'
        if reason:excluded.append(dict(symbol=symbol,isin=isin,reason=reason))
        else:valid.append(r)
    by_symbol={r['trading_symbol']:r for r in valid}
    check(all(s in by_symbol for s in anchors),'continuity_member_not_resolved')
    ordered=list(anchors)+[s for s in sorted(by_symbol) if s not in anchors]
    selected=ordered[:limit];check(len(selected)==limit,'insufficient_observed_EQ_listings')
    members=[dict(symbol=s,isin=by_symbol[s]['isin'],listing_id='NSE:'+by_symbol[s]['isin'],name=by_symbol[s]['name'],
                  identity_basis='current_provider_BOD_EQ_presence',liquidity='unqualified') for s in selected]
    return dict(label='LIMITED RESEARCH WATCHLIST',rule=VERSION,source_url=MASTER,master_hash=digest(rows),
        continuity_members=list(anchors),selection='continuity members then ascending symbol; no liquidity claim',
        observed_eq_count=len(eq),members=members,exclusions=excluded,
        bounded_out=[dict(symbol=s,reason='outside_bounded_alphabetic_sample') for s in ordered[limit:]],
        limitations=['BOD presence is not instrument-risk approval','Volume adjustment and spreads unverified','Not a full NSE scan'])


class PilotConfig(Strict):
    market: MarketConfig
    view: ViewConfig
    evidence: EvidenceConfig
    universe: dict
    max_research: Annotated[int,Field(ge=0,le=2)] = 1

    @model_validator(mode='after')
    def consistent(self):
        u=self.universe;check(u['version']==digest({k:v for k,v in u.items() if k!='version'}),'universe_hash_mismatch')
        members=u['members'];check(10<=len(members)<=20,'pilot_universe_bounds')
        check(tuple(m['symbol'] for m in members)==self.market.symbols,'frozen_symbols_mismatch')
        check(tuple(m['listing_id'] for m in members)==self.view.listing_ids,'frozen_listings_mismatch')
        check(self.evidence.factual_report and self.evidence.mode=='rag' and self.evidence.judge_model is None,'factual_research_only')
        check(not self.evidence.filings,'pilot_numeric_evidence_only')
        check(self.market.grant_file==self.view.sources.grant_file==self.evidence.sources.grant_file,'source_config_mismatch')
        return self


def safe_error(exc):
    if isinstance(exc,PermissionError):return 'source_permission_or_credentials_denied'
    if isinstance(exc,KeyError):
        field=str(exc.args[0])
        return 'missing_provider_field:'+field if re.fullmatch(r'[A-Za-z_]{1,50}',field) else 'missing_provider_field'
    value=str(exc)
    for prefix in ('upstox_','source_rate_','instrument_','financial_','required_statement_','unsupported_','revenue_reconciliation','tax_reconciliation','asset_reconciliation','liability_reconciliation','real_identity_','unverified_market_session','frozen_identity_changed'):
        if value.startswith(prefix):return value.split(':')[0][:100]
    return 'provider_or_validation_failure'


def query_for(config, member, horizon, cutoff):
    return Query(issuer_id=member['isin'],listing_id=member['listing_id'],horizon=horizon,mode='live_paper',cutoff_at=cutoff,
        text='historical revenue profit operating cash flow assets liabilities reconciliation',categories=('annual_report',),scope='consolidated')


def screening(detail, findings):
    """Research prioritization only. Missing required inputs get no score/rank."""
    m=detail['price_features']['metrics'];r=detail['market_readiness'];growth={}
    for f in findings:
        if f['kind']=='calculation' and f['metric'].endswith('_yoy'):
            metric=f['metric'];period=max(p['end'] for p in f['periods'])
            if metric not in growth or period>growth[metric][0]:growth[metric]=(period,f)
    result={}
    for h in ('swing','short_term','long_term'):
        missing=[];score=None;basis=[]
        if h=='swing':
            if not r['latest_session_present']:missing.append('latest_closed_session_missing')
            if not r['warmup_complete'] or r['missing_sessions'] or r['unverified_bar_sessions'] or r['duplicate_bars']:missing.append('price_window_incomplete')
            if any(m.get(k) is None for k in ('ema10','ema30','atr14','breakout20')):missing.append('technical_inputs_missing')
            if not missing:
                score=str((Decimal(m['ema10'])/Decimal(m['ema30'])-1)*100) if Decimal(m['ema30'])>0 else None
                basis=['descriptive EMA10/EMA30 percentage spread; descending, ISIN tie-break','Not approved investment ranking; volume and raw-price eligibility excluded']
        else:
            required=('revenue_yoy','earnings_yoy') if h=='short_term' else ('revenue_yoy','operating_cash_flow_yoy')
            if any(k not in growth for k in required):missing.append('comparable_historical_growth_missing')
            elif len({growth[k][0] for k in required})!=1:missing.append('growth_periods_mismatch')
            if not missing:
                score=str(min(Decimal(growth[k][1]['value']) for k in required));basis=['Minimum of two supported same-period annual growth percentages; descending, ISIN tie-break']
        result[h]=dict(ranking_eligible=score is not None,score=score,rank=None,ranking_basis=basis,missing=missing,
            assessment=detail['quantitative'][h],qualification='research_only_not_investment_suitability')
    return result


def rank_rows(rows):
    for h in ('swing','short_term','long_term'):
        eligible=[r for r in rows if r.get('screening',{}).get(h,{}).get('ranking_eligible')]
        for i,r in enumerate(sorted(eligible,key=lambda r:(-Decimal(r['screening'][h]['score']),r['isin'])),1):r['screening'][h]['rank']=i
    return rows


def receipt(conn,job,kind,key,payload,clock):
    eid=digest([job['job_id'],kind,key])
    conn.execute('INSERT INTO discovery.schedule_outbox VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                 (eid,job['job_id'],kind,Jsonb(payload),clock()))
    return conn.execute('SELECT payload FROM discovery.schedule_outbox WHERE event_key=%s',(eid,)).fetchone()[0]


def pilot_hash(config):
    wire=config.model_dump(mode='json')
    if wire['view'].get('pilot_health_file') is None:wire['view'].pop('pilot_health_file',None)
    return digest(wire)


def retryable_rows(rows):
    prefixes=('upstox_timeout','upstox_unavailable','upstox_http_5','upstox_rate_limited','source_rate_limited')
    return any(r['status']=='stale' or any(e.rsplit(':',1)[-1].startswith(prefixes) for e in r['errors']) for r in rows)


def research_fingerprint(config,row,horizon,models):
    # Installed content identities, not mutable model tags; cutoff alone does not
    # justify repeating unchanged factual research on a later daily scan.
    query=query_for(config,row,horizon,now()).model_dump(mode='json',exclude={'cutoff_at'})
    return digest(dict(listing=row['listing_id'],horizon=horizon,query=query,
        candidates=[f['candidate_id'] for f in row['financial_findings']],
        config=config.evidence.model_dump(mode='json',exclude={'queries'}),
        models={name:model.ref.model_dump(mode='json') for name,model in models.items()},
        prompt=factual_research.PROMPT_HASH,factual_version=factual_research.VERSION,
        validator=rag_research.VALIDATOR_VERSION,version=VERSION))


def model_requests(config):
    # Exact constructor contracts used by real_evidence.run; roles remain
    # separate even when both configured names refer to the same model.
    return (('research',config.model,dict(context=config.context,max_input_bytes=config.context*2,max_model_bytes=config.max_model_bytes)),
            ('embedding',config.embedding_model,{}))


def pinned_model_factory(config,models):
    requests=model_requests(config)
    def factory(name,**kwargs):
        roles=[role for role,expected,parameters in requests if name==expected and kwargs==parameters]
        check(len(roles)==1,'unexpected_model_request')
        model=models[roles[0]]
        check(model.ref.id==name,'pinned_model_identity_mismatch')
        return model
    return factory


def scan_research_identity(config,refs):
    return digest(dict(config=config.evidence.model_dump(mode='json',exclude={'queries'}),
        models={role:ref.model_dump(mode='json') for role,ref in refs.items()},
        prompt=factual_research.PROMPT_HASH,factual_version=factual_research.VERSION,
        validator=rag_research.VALIDATOR_VERSION,version=VERSION))


def research_complete(row):
    research=row['research'];status=research.get('attempt_status',research['status'])
    return status=='not_selected' or (status=='executed' and all(r['status']=='completed' for r in research.get('runs',())))


def handlers(schedule,config):
    config=PilotConfig.model_validate(config)
    check(schedule.mode=='live_paper' and schedule.input_hash==pilot_hash(config),'pilot_schedule_configuration_mismatch')
    def scan(conn,job,clock):
        # Independent committed receipts survive a worker crash / outer lease rollback.
        with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as store:
            lock='REAL-PILOT:'+config.market.account_ref
            if not store.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0]:raise JobFailure('readiness')
            started=time.monotonic();started_at=clock();calls=0;last=[0.0]
            access=access_for(config.market,clock)
            source=Stream(stream_id='PILOT-universe',source_id='upstox',account_ref=config.market.account_ref,scope='universe')
            access.require(source,('derive','store'))
            # A calendar renewal changes D3-04 occurrence hashes, never the logical research cutoff.
            # Reuse before market ingestion or inference; verify research identity with metadata only.
            prior=store.execute("""SELECT o.event_key,o.payload FROM discovery.schedule_outbox o JOIN discovery.schedule_jobs j USING(job_id)
                WHERE o.kind='pilot_scan' AND j.payload->>'scope_id'=%s AND j.payload->>'input_hash'=%s
                AND o.payload->>'scheduled_cutoff'=%s AND o.payload->>'status'='completed'
                ORDER BY o.created_at DESC LIMIT 1""",(schedule.scope_id,schedule.input_hash,job['payload']['information_cutoff_at'])).fetchone()
            if prior and not retryable_rows(prior[1]['rows']) and all(research_complete(r) for r in prior[1]['rows']):
                researched=any(r['research']['status']!='not_selected' for r in prior[1]['rows'])
                try:
                    unchanged=not researched or prior[1].get('research_identity')==scan_research_identity(config,Ollama.installed_refs(model_requests(config.evidence)))
                except Exception:
                    unchanged=False  # Unverifiable identity is never a cache hit.
                if unchanged:return dict(status='completed',reused_scan=prior[0],actionable=False),None
            # A receipt belongs to one immutable attempt, even if code/model identity changes.
            saved_scan=store.execute("SELECT payload FROM discovery.schedule_outbox WHERE event_key=%s",(digest([job['job_id'],'pilot_scan',job['attempts']]),)).fetchone()
            if saved_scan:
                if job['attempts']<3:raise JobFailure('readiness')
                return dict(status='partial',reason='attempt_exhausted_identity_unverified',actionable=False),None
            receipt(store,job,'pilot_universe','frozen',config.universe,clock)
            def gate():
                nonlocal calls
                fenced_row(store,job,clock())
                # Shared durable account ledger across per-stock adapter instances and restarts.
                code='pilot_request:'+digest(config.market.account_ref)
                count=store.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code=%s AND at>%s::timestamptz-interval '30 minutes'",(code,clock())).fetchone()[0]
                recent=store.execute("SELECT count(*) FROM discovery.schedule_audit WHERE code=%s AND at>%s::timestamptz-interval '1 minute'",(code,clock())).fetchone()[0]
                check(count<800 and recent<90 and calls<200,'source_rate_limited')
                time.sleep(max(0,.7-(time.monotonic()-last[0])));last[0]=time.monotonic()
                store.execute('INSERT INTO discovery.schedule_audit(job_id,at,code) VALUES (%s,%s,%s)',(job['job_id'],clock(),code));calls+=1
            master_cache=[]
            class Client(Upstox):
                def __init__(self,**kw):super().__init__(**kw,request_gate=gate)
                def instrument_master(self,stream):
                    self.access.require(stream,('acquire','derive'))
                    if not master_cache:master_cache.append(super().instrument_master(stream))
                    return master_cache[0]
                def instruments(self,stream,symbols):
                    values=super().instruments(stream,symbols)
                    expected={m['symbol']:m['isin'] for m in config.universe['members']}
                    check(all(expected[v['symbol']]==v['isin'] for v in values),'frozen_identity_changed')
                    return values
            rows=[]
            for member in config.universe['members']:
                fenced_row(store,job,clock())
                symbol=member['symbol'];key=[job['attempts'],symbol]
                eid=digest([job['job_id'],'pilot_stock',key])
                saved=store.execute('SELECT payload FROM discovery.schedule_outbox WHERE event_key=%s',(eid,)).fetchone()
                if saved:rows.append(saved[0]);continue
                row={**member,'status':'failed','errors':[],'research':{'status':'not_selected'},'actionable':False}
                try:
                    one=config.market.model_copy(update={'symbols':(symbol,)})
                    result=ingest_prices(store,one,clock=clock,adapter_factory=Client)
                    check(result['status']!='busy','real_ingestion_busy')
                    row['market']=result['instruments'][0]
                    # Numeric financial observations are reusable; daily price refresh does not force daily fundamentals calls.
                    old=company(store,config.view,member['listing_id'],clock=clock)
                    if not old['financial_facts'] or len(old['documents'])<3 or any((datetime.fromisoformat(clock().replace('Z','+00:00'))-datetime.fromisoformat(d['revision']['fetched_at'].replace('Z','+00:00'))).days>=7 for d in old['documents']):
                        try:
                            # The existing financial ingester accepts a provider; share the durable request gate.
                            from .providers.upstox_financials import ingest_financials,ENDPOINTS
                            from stock_discovery_analysis.revisions import Revision
                            identity=Revision.model_validate(store.execute("SELECT payload FROM discovery.revisions WHERE listing_id=%s AND kind='instrument' ORDER BY sequence DESC LIMIT 1",(member['listing_id'],)).fetchone()[0])
                            client=Client(access=access,token=Path(one.token_file).read_text().strip())
                            try:
                                for endpoint in ENDPOINTS:
                                    try:ingest_financials(store,client,identity,one.account_ref,endpoints=(endpoint,))
                                    except StaleLease:raise
                                    except Exception as exc:row['errors'].append(endpoint+':'+safe_error(exc))
                            finally:client.close()
                        except StaleLease:raise
                        except Exception as exc:row['errors'].append('financial:'+safe_error(exc))
                    detail=company(store,config.view,member['listing_id'],clock=clock)
                    bundle=retrieve(store,query_for(config,member,'long_term',clock()),config.evidence.retrieval,access=source_access(config.view.sources,clock),persist=False)
                    findings=candidates(bundle)
                    row.update(status='stale' if not detail['market_readiness']['latest_session_present'] else 'observed',
                        cutoff_at=detail['cutoff_at'],freshness=detail['market_readiness'],indicators=detail['price_features'],
                        financial_fact_count=len(detail['financial_facts']),financial_findings=findings,
                        screening=screening(detail,findings),publication_blockers=detail['publication_blockers'],
                        source_revisions=detail['market_readiness']['input_revision_ids']+list(bundle.documents))
                except StaleLease:raise
                except Exception as exc:row['errors'].append(safe_error(exc))
                rows.append(receipt(store,job,'pilot_stock',key,row,clock))
            rank_rows(rows)
            # At most configured candidates, sequential inference; no judge auto-approval.
            nominations=[]
            for h in ('swing','short_term','long_term'):
                nominations.extend((r,h) for r in sorted(rows,key=lambda r:r.get('screening',{}).get(h,{}).get('rank') or 999) if r.get('screening',{}).get(h,{}).get('rank')==1)
            used=set();research_identity=None;initialization_failed=False
            for row,h in nominations:
                if len(used)>=config.max_research:break
                if row['listing_id'] in used:continue
                used.add(row['listing_id'])
                with ExitStack() as resources:
                    models={}
                    try:
                        for role,name,kwargs in model_requests(config.evidence):
                            model=Ollama(name,**kwargs);resources.callback(model.close);models[role]=model
                    except Exception as exc:
                        initialization_failed=True
                        row['research']=dict(status='initialization_failed',error=safe_error(exc));continue
                    identity=scan_research_identity(config,{role:model.ref for role,model in models.items()})
                    check(research_identity in (None,identity),'model_identity_changed_during_scan')
                    research_identity=identity
                    fingerprint=research_fingerprint(config,row,h,models)
                    previous=store.execute("SELECT payload FROM discovery.schedule_outbox WHERE kind='pilot_research' AND payload->>'fingerprint'=%s ORDER BY created_at DESC LIMIT 1",(fingerprint,)).fetchone()
                    if previous:row['research']={**previous[0],'status':'reused_immutable_attempt','attempt_status':previous[0]['status']};continue
                    # Commit intent before inference. Ambiguous crash is not automatically billed/retried.
                    attempted=store.execute("SELECT 1 FROM discovery.schedule_outbox WHERE kind='pilot_research_intent' AND payload->>'fingerprint'=%s",(fingerprint,)).fetchone()
                    if attempted:row['research']=dict(status='ambiguous_prior_attempt',fingerprint=fingerprint);continue
                    if store.execute("""SELECT count(*) FROM discovery.schedule_outbox o JOIN discovery.schedule_jobs j USING(job_id)
                        WHERE o.kind='pilot_research_intent' AND j.payload->>'scope_id'=%s AND j.payload->>'input_hash'=%s
                        AND j.payload->>'information_cutoff_at'=%s""",(schedule.scope_id,schedule.input_hash,job['payload']['information_cutoff_at'])).fetchone()[0]>=config.max_research:
                        row['research']=dict(status='occurrence_research_budget_exhausted');continue
                    fenced_row(store,job,clock())
                    receipt(store,job,'pilot_research_intent',fingerprint,dict(fingerprint=fingerprint,status='reserved'),clock)
                    try:
                        cfg=config.evidence.model_copy(update={'queries':(query_for(config,row,h,clock()),)})
                        t=time.monotonic();result=research(store,cfg,clock=clock,model_factory=pinned_model_factory(cfg,models))
                        output=dict(fingerprint=fingerprint,status='executed',horizon=h,seconds=time.monotonic()-t,
                            runs=[dict(run_id=x['run_id'],status=x['result']['status'],accepted=len(x['result'].get('factual_report',{}).get('accepted_claims',[])),relations=len(x['result'].get('factual_report',{}).get('interpretive_findings',[]))) for x in result['research']])
                    except Exception as exc:output=dict(fingerprint=fingerprint,status='failed',error=safe_error(exc))
                    row['research']=receipt(store,job,'pilot_research',fingerprint,output,clock)
            result=dict(kind='automated_factual_research',version=VERSION,research_identity=research_identity,universe=config.universe,rows=rows,
                started_at=started_at,completed_at=clock(),duration_seconds=time.monotonic()-started,api_requests=calls,
                peak_process_memory_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                queue_depth=store.execute("SELECT count(*) FROM discovery.schedule_jobs WHERE payload->>'scope_id'=%s AND status IN ('queued','running','retry_wait')",(schedule.scope_id,)).fetchone()[0],
                occurrence_id=job['payload']['occurrence_id'],attempt=job['attempts'],scheduled_cutoff=job['payload']['information_cutoff_at'],
                catch_up=job['payload']['catch_up'],counts=dict(total=len(rows),observed=sum(r['status']=='observed' for r in rows),stale=sum(r['status']=='stale' for r in rows),failed=sum(r['status']=='failed' for r in rows)),
                calendar_through=schedule.calendar.ends_on,
                publication='blocked_existing_qualification_gates',prospective_references=0,positions=0,
                status='partial' if any(r['status']!='observed' or r['errors'] or not research_complete(r) for r in rows) else 'completed',actionable=False)
            receipt(store,job,'pilot_scan',job['attempts'],result,clock)
            retryable=initialization_failed or retryable_rows(rows)
            if retryable and job['attempts']<3:raise JobFailure('readiness')
            return result,None
    def events(conn,job,clock):
        return dict(status='partial',reason='permitted_material_event_feed_unavailable',actionable=False),None
    return {'ingest':scan,'event_poll':events}
