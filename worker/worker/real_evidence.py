"""Opt-in real filing -> D3-06 -> D3-07/08 orchestration; no mock fallback."""
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Text, check, digest
from stock_discovery_analysis.real_access import SourceConfig, source_access
from stock_discovery_analysis.revision_storage import Stream
from stock_discovery_analysis.revisions import Revision
from stock_discovery_analysis.evidence_storage import ingest_next_evidence
from stock_discovery_analysis.rag_contracts import Query, RetrievalPolicy, Budget
from stock_discovery_analysis.rag_research import run_research
from stock_discovery_analysis.agent_storage import run_investigation
from stock_discovery_analysis.publication_store import now
from .providers.documents import FilingSpec, OfficialDocument
from .providers.ollama import Ollama

class EvidenceConfig(Strict):
    sources: SourceConfig
    filings: Annotated[tuple[FilingSpec,...],Field(min_length=0,max_length=100)]
    queries: Annotated[tuple[Query,...],Field(min_length=1,max_length=300)]
    model: Text = 'qwen2.5-coder:7b'
    embedding_model: Text = 'nomic-embed-text:latest'
    judge_model: Text | None = None
    mode: Literal['rag','agent'] = 'rag'
    retrieval: RetrievalPolicy = RetrievalPolicy(max_chunks=2,max_documents=3,max_bytes=12000)
    budget: Budget
    context: Annotated[int,Field(ge=1024,le=16384)] = 16384


def run(conn, config, *, clock=now, adapter_factory=OfficialDocument, model_factory=Ollama):
    config=EvidenceConfig.model_validate(config)
    check(conn.autocommit,'dedicated_autocommit_connection_required')
    check(all(q.mode=='live_paper' for q in config.queries),'real_queries_only')
    if config.mode=='agent':check(config.judge_model and config.judge_model!=config.model,'independent_judge_required')
    access=source_access(config.sources,clock)
    lock='real-evidence:'+digest(config.sources.model_dump())
    check(conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',(lock,)).fetchone()[0],'real_evidence_busy')
    providers=[]
    try:
        ingestion=[]
        for spec in config.filings:
            prior=conn.execute("SELECT payload FROM discovery.revisions WHERE source_id=%s AND listing_id=%s AND kind='document' AND payload->'data'->>'document_id'=%s ORDER BY sequence DESC LIMIT 1",
                (spec.source_id,spec.listing_id,spec.document_id)).fetchone()
            stream=Stream(stream_id='REAL-DOC-'+digest([spec.model_dump(),clock()]),source_id=spec.source_id,account_ref=spec.account_ref,scope='filings')
            adapter=adapter_factory(spec,access=access,stream=stream,previous=Revision.model_validate(prior[0]) if prior else None)
            try:result=ingest_next_evidence(conn,stream,adapter,access=access)
            finally:adapter.close()
            check(result.get('status')=='complete','real_filing_quarantined')
            ingestion.append(result)
        # Clock is frozen only after the documents have actually been observed.
        cutoff=clock(); results=[]
        provider=model_factory(config.model,context=config.context,max_input_bytes=config.context*2);providers.append(provider)
        embeddings=model_factory(config.embedding_model);providers.append(embeddings)
        judge=None
        if config.mode=='agent':
            judge=model_factory(config.judge_model,context=config.context,max_input_bytes=config.context*2);providers.append(judge)
        for query in config.queries:
            # Configuration supplies query intent, never a backdated availability claim.
            query=Query.model_validate_json(json.dumps({**query.model_dump(mode='json'),'cutoff_at':cutoff}))
            key='REAL-RAG-'+digest([query.model_dump(),config.model_dump(),cutoff])
            if config.mode=='agent':
                result=run_investigation(conn,run_id=key,query=query,retrieval_policy=config.retrieval,access=access,
                    budget=config.budget,provider=provider,judge=judge,embeddings=embeddings)
            else:
                result=run_research(conn,run_id=key,query=query,policy=config.retrieval,access=access,
                    budget=config.budget,provider=provider,embeddings=embeddings)
            results.append(dict(run_id=key,listing_id=query.listing_id,horizon=query.horizon,result=result))
        return dict(status='partial',actionable=False,ingestion=ingestion,research=results,
            publication='not_published',tracking='not_configured',
            limitation='Research results are not v2 recommendations or prospective predictions; market/policy/publication acceptance remains required.')
    finally:
        for provider in providers:provider.close()
        conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock,))
