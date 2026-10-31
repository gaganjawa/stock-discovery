"""Bounded development benchmark using existing runtime, receipts and statistics.

Never a live research route, independent human holdout or publication authority.
"""
import json,re,time
from copy import deepcopy
from typing import Literal
from psycopg.types.json import Jsonb
from psycopg.pq import TransactionStatus
from stock_discovery_contracts.v2 import Strict,Text,at,check,digest
from stock_discovery_analysis.rag_contracts import Budget
from stock_discovery_analysis.rag_research import reserve
from stock_discovery_analysis.publication_store import now
from .providers.table_spans import cell_reference,verify_cell


class Proposal(Strict):
    status: Literal['extracted','insufficient_evidence']
    value: Text|None
    unit: Text|None
    scope: Text|None
    period: Text|None
    evidence_id: Text|None
    quote: Text|None


PROMPT=('Extract the requested row and reporting-period column only from the supplied disclosure excerpt. '
    'Return status extracted with the numeric value as a string (no thousands separators), unit INR_crore, '
    'scope consolidated, the requested period label and provided evidence_id. Quote the ENTIRE selected '
    'row exactly with spaces around |, including all its numeric columns. Do not use outside knowledge. '
    'If the requested period is absent, the same row is duplicated/conflicting or context is insufficient, '
    'return insufficient_evidence and set all other fields to JSON null. No calculations or investment advice.')
PROMPT+=(' The column_labels array maps one-to-one to the numeric cells after the row label. '
    'Use that decoded two-level header to choose the requested column, not another year or quarter. '
    'For insufficient_evidence every other field, INCLUDING evidence_id, must be null. '
    'Produce valid JSON; escape quotation marks and newlines inside JSON strings.')
PROMPT_HASH=digest([PROMPT,Proposal.model_json_schema()])
VALIDATOR_VERSION='table-span-dev-1.1'
BUDGET=Budget(account='M2-span-development',max_run_units=20000,max_day_units=200000,max_month_units=2000000,max_output_units=1800,max_seconds=120)


def cases(text,profile):
    out=[]
    for key,period in [('annual-current','Year ended March 31, 2025'),('annual-prior','Year ended March 31, 2024'),('missing-period','Year ended March 31, 2027'),('conflict','Year ended March 31, 2025')]:
        data=text;pin=deepcopy(profile)
        if key=='conflict':
            data+='Total revenue from operations | 1 | 2 | 3 | 4\n';pin['text_hash']=digest(data)
        try:expected=cell_reference(data,pin,'Total revenue from operations',period)
        except ValueError:expected=None
        out.append(dict(case_id=key,text=data,profile=pin,period=period,expected=expected,
            source_kind='adversarial_mutation' if key=='conflict' else 'captured_public_excerpt'))
    return out


def run_case(conn,case,*,source,cutoff,provider,budget=BUDGET,clock=now):
    check(conn.autocommit and conn.info.transaction_status==TransactionStatus.IDLE,'durable_evaluation_requires_idle_autocommit')
    check(provider.local_only and provider.cost_per_unit==0,'local_zero_api_cost_only')
    check(at(source['captured_at'])<=at(cutoff),'source_not_observed_at_cutoff')
    check(at(cutoff)<=at(clock()),'future_evaluation_cutoff')
    check(digest(case['text'])==case['profile']['text_hash'],'source_snapshot_changed')
    check({k:v for k,v in case['profile'].items() if k!='text_hash'}=={k:v for k,v in source['profile'].items() if k!='text_hash'},'source_profile_changed')
    try:reference=cell_reference(case['text'],case['profile'],'Total revenue from operations',case['period'])
    except ValueError:reference=None
    check(case['expected']==reference,'evaluation_reference_changed')
    top,years=case['profile']['headers']
    columns=[top[1 if i<2 else 2]+' '+year for i,year in enumerate(years[1:])]
    request=json.dumps(dict(instruction=PROMPT,schema=Proposal.model_json_schema(),bundle=dict(
        source_text=case['text'],column_labels=columns,target_row='Total revenue from operations',period=case['period'],
        evidence_id=case['profile']['evidence_id'],scope=case['profile']['scope'],unit=case['profile']['unit'],cutoff_at=cutoff)))
    check(len(request.encode())+budget.max_output_units<=budget.max_run_units,'evaluation_input_budget')
    identity=dict(validator_version=VALIDATOR_VERSION,serialized_request_hash=digest(request),case=case,source=source,cutoff=cutoff,model=provider.ref.model_dump(),prompt_hash=PROMPT_HASH,budget=budget.model_dump())
    request_hash=digest(identity);run_id='M2-DEV-SPAN-'+request_hash
    fresh=reserve(conn,run_id,request_hash,budget,clock())
    if not fresh:
        row=conn.execute('SELECT payload FROM discovery.rag_results WHERE run_id=%s',(run_id,)).fetchone()
        check(row is not None,'ambiguous_evaluation_reservation_no_retry')
        return row[0]
    start=time.monotonic();proposal=None;error=None;accepted=False;denial=None;raw=None
    try:
        raw=provider.assess(request,max_output_units=budget.max_output_units,deadline=start+budget.max_seconds)
        check(isinstance(raw,str) and len(raw.encode())<=budget.max_output_units and time.monotonic()<start+budget.max_seconds,'evaluation_output_budget')
        proposal=Proposal.model_validate_json(raw).model_dump()
        if proposal['status']=='insufficient_evidence':
            check(all(v is None for k,v in proposal.items() if k!='status'),'invalid_abstention_fields')
        elif case['expected'] is not None:
            check(isinstance(proposal['value'],str) and re.fullmatch(r'-?\d+(?:\.\d+)?',proposal['value']) is not None,'invalid_canonical_number')
            try:verify_cell(proposal,case['expected']);accepted=True
            except ValueError as e:denial=str(e)
        else:denial='reference_insufficient_or_conflicting'
    except (ValueError,RuntimeError,TimeoutError) as e:error=type(e).__name__
    if raw is None:raw=getattr(provider,'last_response',None)
    result=dict(case_id=case['case_id'],expected=case['expected'],proposal=proposal,accepted=accepted,error=error,denial=denial,
        model=provider.ref.model_dump(),validator_version=VALIDATOR_VERSION,prompt_hash=PROMPT_HASH,request_hash=request_hash,source_hash=case['profile']['text_hash'],
        source_kind=case['source_kind'],cutoff_at=cutoff,human_verified=False,holdout=False,actionable=False,
        latency_ms=round((time.monotonic()-start)*1000),raw_response=raw,
        accounting=dict(input_bytes=len(request.encode()),output_bytes=len(raw.encode()) if isinstance(raw,str) else None,
            reserved_units=budget.max_run_units,reservation_released=False,actual_cost_usd='0'))
    conn.execute('INSERT INTO discovery.rag_results VALUES(%s,NULL,%s)',(run_id,Jsonb(result)))
    return result
