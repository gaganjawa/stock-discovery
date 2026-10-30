"""D3-08 orchestrator persistence and database-enforced read-only tools."""
import json
import time
from decimal import Decimal, localcontext
from psycopg import Error as DatabaseError
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import check, digest, at
from .rag_contracts import Bundle, Fact, Query, Budget, RetrievalPolicy
from .rag_retrieval import retrieve, calculate_ratio, conflicts, CONTEXT, authorized_documents
from .rag_research import reserve, recheck, time_limit
from .agent_contracts import AgentPolicy, Rubric
from .agent_research import investigate, AGENT_PROMPT_HASH, JUDGE_PROMPT_HASH, encode


def combine(base, added, policy):
    """Evidence union, never replace counterevidence or relax original requirements."""
    for key in ('issuer_id','listing_id','horizon','mode','cutoff_at','scope','period_start_at','period_end_at','period_kind','required_metrics'):
        check(getattr(base.query,key)==getattr(added.query,key),'investigation scope change')
    check(set(base.query.categories)<=set(added.query.categories),'coverage requirements relaxed')
    hits={h.chunk_id:h for h in added.hits}
    hits.update({h.chunk_id:h for h in base.hits})
    facts={f.fact_id:f for f in (*base.facts,*added.facts)}
    missing=set(base.missing)&set(added.missing)
    missing.update(x for x in added.missing if x.startswith('category:') and x[9:] not in base.query.categories)
    if hits:missing.discard('relevant_text')
    check(len(hits)<=20 and len(hits)+len(facts)<=policy.max_tool_rows,'merged evidence row cap')
    # Conservative requirement coverage; additional investigation cannot claim
    # complete coverage of an unobserved source feed.
    with localcontext(CONTEXT):
        required=set('category:'+c for c in added.query.categories)|set('metric:'+m for m in base.query.required_metrics)|{'relevant_text'}
        coverage=format(Decimal(len(required-set(missing)))/len(required),'f')
    check(not base.embedding or not added.embedding or base.embedding==added.embedding,'embedding version changed')
    result=base.model_copy(update=dict(embedding=base.embedding or added.embedding,
        retrieval_mode='hybrid' if base.embedding or added.embedding else 'lexical_only',documents=tuple(sorted(set(base.documents)|set(added.documents))),
        hits=tuple(hits[k] for k in sorted(hits)),facts=tuple(facts[k] for k in sorted(facts)),
        missing=tuple(sorted(missing)),contradictions=conflicts(tuple(facts.values())),
        omitted=tuple(sorted(set(base.omitted)|set(added.omitted))),coverage=coverage,
        embedding_input_units=base.embedding_input_units+added.embedding_input_units))
    check(len(result.model_dump_json().encode())<=policy.max_context_bytes,'merged context cap')
    return result


class ReadOnlyTools:
    def __init__(self,conn,access,retrieval_policy,embeddings=None):
        self.conn,self.access,self.policy,self.embeddings=conn,access,retrieval_policy,embeddings

    def execute(self,tool,bundle,policy,meter):
        try:
            return self._execute(tool,bundle,policy,meter)
        except DatabaseError:
            raise RuntimeError('read-only tool database failure') from None

    def _execute(self,tool,bundle,policy,meter):
        # No caller-controlled SQL, connections, tool names or provider choices.
        check(self.conn.info.transaction_status==TransactionStatus.IDLE,'idle tool connection required')
        from .read_fences import tool_read_transaction
        with tool_read_transaction(self.conn,self.access,bundle):
            recheck(self.conn,bundle,self.access)
            if tool.name=='retrieve':
                meter.ensure(self.policy.max_bytes if self.embeddings else 0)
                q=Query.model_validate_json(encode({**bundle.query.model_dump(mode='json'),'text':tool.text,
                    'categories':sorted(set(bundle.query.categories)|set(tool.categories))}))
                added=retrieve(self.conn,q,self.policy,access=self.access,embeddings=self.embeddings,
                    deadline=meter.deadline,monotonic=meter.clock,persist=False)
                meter.charge(added.embedding_input_units)
                result=combine(bundle,added,policy)
                sources=self.conn.execute('SELECT count(DISTINCT source_id) FROM discovery.revisions WHERE revision_id=ANY(%s)',(list(result.documents),)).fetchone()[0]
                result=result.model_copy(update={'source_count':sources})
                # Versioned individual search scores/provenance remain in this
                # tool response; the final context is an evidence union.
                response={'bundle_hash':added.content_hash,'query':q.model_dump(mode='json'),
                    'hits':[h.model_dump(mode='json') for h in added.hits],
                    'missing':list(added.missing),'contradictions':[list(c) for c in added.contradictions]}
            elif tool.name=='inspect_conflicts':
                result=bundle
                response={'contradictions':[list(c) for c in bundle.contradictions],
                    'facts':[f.model_dump(mode='json') for f in bundle.facts if any(f.fact_id in c for c in bundle.contradictions)]}
            elif tool.name=='calculate_ratio':
                facts={f.fact_id:f for f in bundle.facts}
                check(tool.numerator_id in facts and tool.denominator_id in facts,'unknown calculation input')
                numerator,denominator=facts[tool.numerator_id],facts[tool.denominator_id]
                response=calculate_ratio(numerator,denominator)
                cid=response['calculation_id']
                computed=Fact(fact_id=cid,metric=f'ratio({numerator.metric},{denominator.metric})',value=response['value'],
                    missing_reason=response['missing_reason'],unit='ratio',period_start_at=numerator.period_start_at,
                    period_end_at=numerator.period_end_at,period_kind=numerator.period_kind,scope=numerator.scope,
                    citation=numerator.citation.model_copy(update={'evidence_id':cid,'locator':'calculation:'+cid,'excerpt':None}),
                    formula='ratio-v1',input_fact_ids=(numerator.fact_id,denominator.fact_id))
                facts[cid]=computed
                result=bundle.model_copy(update={'facts':tuple(facts[k] for k in sorted(facts))})
            else:
                raise ValueError('unregistered tool')
            recheck(self.conn,result,self.access)
            return result,response


def run_investigation(conn,*,run_id,query,retrieval_policy,access,budget,provider,judge,
                      embeddings=None,policy=None,rubric=None,monotonic=time.monotonic):
    """Single reserved investigation; no automatic retries after failure/crash."""
    check(conn.autocommit and conn.info.transaction_status==TransactionStatus.IDLE,'dedicated idle autocommit connection required')
    policy=AgentPolicy.model_validate_json((policy or AgentPolicy()).model_dump_json())
    rubric=Rubric.model_validate_json((rubric or Rubric()).model_dump_json())
    query=Query.model_validate_json(query.model_dump_json())
    retrieval_policy=RetrievalPolicy.model_validate_json(retrieval_policy.model_dump_json())
    budget=Budget.model_validate_json(budget.model_dump_json())
    for adapter in (provider,judge,embeddings):
        if adapter is not None:check(adapter.local_only and adapter.cost_per_unit==0,'remote/paid models disabled')
    check(provider.ref.id!=judge.ref.id,'separate judge required')
    identity=dict(query=query.model_dump(mode='json'),retrieval_policy=retrieval_policy.ref.model_dump(),
        policy=policy.ref.model_dump(),rubric=rubric.ref.model_dump(),budget=budget.model_dump(),
        agent=provider.ref.model_dump(),judge=judge.ref.model_dump(),embedding=embeddings.ref.model_dump() if embeddings else None,
        agent_prompt_hash=AGENT_PROMPT_HASH,judge_prompt_hash=JUDGE_PROMPT_HASH,primary_sources=sorted(access.primary_source_ids))
    request_hash=digest(identity)
    start=monotonic()
    deadline=start+budget.max_seconds
    with time_limit(deadline-monotonic()):
        fresh=reserve(conn,run_id,request_hash,budget,access.clock())
    if not fresh:
        row=conn.execute('SELECT payload FROM discovery.agent_results WHERE run_id=%s',(run_id,)).fetchone()
        check(row is not None,'ambiguous reservation; no automatic retry')
        check(row[0]['status']=='completed','failed run; no automatic retry')
        result=row[0]
        for key in ('baseline_hash','final_bundle_hash'):
            stored=conn.execute('SELECT payload FROM discovery.rag_bundles WHERE bundle_hash=%s',(result[key],)).fetchone()
            check(stored is not None,'cached bundle unavailable')
            bundle=Bundle.model_validate_json(encode(stored[0]))
            check(bundle.content_hash==result[key],'cached bundle integrity')
            with time_limit(deadline-monotonic()):
                recheck(conn,bundle,access)
        categories=set(query.categories)
        for entry in result['trace']:
            if entry['status']=='completed' and entry['tool']['name']=='retrieve':categories.update(entry['tool']['categories'])
        expanded=query.model_copy(update={'categories':tuple(sorted(categories))})
        with time_limit(deadline-monotonic()):
            current=authorized_documents(conn,expanded,retrieval_policy,access)
        current_ids=sorted(d['document']['revision']['revision_id'] for d in current
            if (at(query.cutoff_at)-at(d['document']['revision']['available_at'])).total_seconds()<=retrieval_policy.max_age_days*86400)
        check(current_ids==list(bundle.documents),'cached evidence changed; new run required')
        return dict(result,cache_reused=True)
    base=final=None
    result=None
    try:
        check((retrieval_policy.max_bytes if embeddings else 0)+budget.max_output_units<=budget.max_run_units,'initial embedding budget')
        with time_limit(deadline-monotonic()):
            base=retrieve(conn,query,retrieval_policy,access=access,embeddings=embeddings,deadline=deadline,monotonic=monotonic)
        def guard(bundle):
            check(monotonic()<deadline,'investigation deadline')
            recheck(conn,bundle,access)
        result,final=investigate(base,policy=policy,budget=budget,provider=provider,judge=judge,rubric=rubric,
            tools=ReadOnlyTools(conn,access,retrieval_policy,embeddings),guard=guard,deadline=deadline,
            monotonic=monotonic,initial_units=base.embedding_input_units)
        # Even failure manifests must not disclose evidence after rights denial.
        with time_limit(deadline-monotonic()):
            guard(final)
        conn.execute('INSERT INTO discovery.rag_bundles VALUES (%s,%s) ON CONFLICT DO NOTHING',
                     (final.content_hash,Jsonb(final.model_dump(mode='json'))))
    except (ValueError,PermissionError,TimeoutError,RuntimeError,OSError) as exc:
        if result is None:
            result=dict(trace=[],baseline_hash=base.content_hash if base else None,
                        validator={'deterministic':'not_completed'},
                        accounting={'actual_cost':'0','reserved_units':budget.max_run_units,'reservation_released':False})
        result.update(status='abstained',action='INSUFFICIENT_EVIDENCE',actionable=False,paper_admission='blocked',
                      stop_reason=type(exc).__name__,assessment=None,judge=None,final_bundle_hash=None)
        if isinstance(exc,PermissionError):
            result['trace']=[dict(index=t['index'],tool=t['tool']['name'],status=t['status'],trace_hash=digest(t)) for t in result['trace']]
            result.pop('missing',None)
            result.pop('contradictions',None)
        final=None
    result.update(request_hash=request_hash,configuration=identity,cache_reused=False,
                  total_latency_ms=max(0,int((monotonic()-start)*1000)))
    conn.execute('INSERT INTO discovery.agent_results VALUES (%s,%s,%s,%s)',
                 (run_id,base.content_hash if base else None,final.content_hash if final else None,Jsonb(result)))
    return result
