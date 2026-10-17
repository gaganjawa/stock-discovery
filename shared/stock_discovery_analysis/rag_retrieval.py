"""Bounded PostgreSQL lexical + local embedding retrieval over D3-06 evidence.

Adapters are trusted installed code. Evidence text is untrusted data, never tools
or instructions. No remote model, download, provider key or network activation.
"""
import re
from decimal import Decimal, Context, localcontext
from typing import Protocol

from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import Ref, at, check, digest
from .evidence_storage import read_evidence, stored_stream
from .rag_contracts import Query, RetrievalPolicy, Citation, Fact, Hit, Bundle

CONTEXT = Context(prec=34)


def number(value):
    return format(value, 'f')


class Embeddings(Protocol):
    ref: Ref
    local_only: bool
    cost_per_unit: Decimal

    def embed(self, texts: tuple[str, ...], *, deadline: float) -> tuple[tuple[Decimal, ...], ...]: ...


class MockEmbeddings:
    """Small frozen synonym vocabulary for tests; not a qualified financial model."""
    vocabulary = (('earnings', 'profit', 'income'), ('revenue', 'sales'),
                  ('debt', 'leverage', 'borrowing'), ('cash', 'liquidity'),
                  ('auditor', 'audit'), ('default', 'insolvency'))
    ref = Ref(id='SYN-semantic-vocabulary', version='1.0.0', content_hash=digest(vocabulary))
    local_only = True
    cost_per_unit = Decimal('0')

    def embed(self, texts, *, deadline):
        return tuple(tuple(Decimal(sum(re.findall(r'\w+', text.lower()).count(word) for word in group))
                           for group in self.vocabulary) for text in texts)


def cosine(left, right):
    check(bool(left) and len(left)==len(right)<=4096, 'embedding dimensions')
    check(all(isinstance(x, Decimal) and x.is_finite() and abs(x)<=Decimal('1e20') for x in (*left,*right)), 'invalid embedding')
    with localcontext(CONTEXT):
        denominator = sum(x*x for x in left)*sum(x*x for x in right)
        return sum(x*y for x,y in zip(left,right))/denominator.sqrt() if denominator else Decimal('0')


def allocate_candidates(ranked, events, policy):
    """Stable per-horizon occurrence allocation; caller supplies eligible ranks."""
    policy = RetrievalPolicy.model_validate_json(policy.model_dump_json())
    ranked = tuple(dict.fromkeys(ranked))
    events = tuple(dict.fromkeys(events))
    selected = list(events[:policy.event_slots])
    for candidate in (*ranked, *events):
        if candidate not in selected and len(selected)<policy.max_candidates:
            selected.append(candidate)
    return dict(selected=tuple(selected), omitted=tuple(x for x in dict.fromkeys((*ranked,*events)) if x not in selected),
                cap=policy.max_candidates, reserved_event_slots=policy.event_slots, policy=policy.ref.model_dump())


def authorized_documents(conn, query, policy, access, purpose='derive'):
    check(at(query.cutoff_at)<=at(access.clock()), 'future observation cutoff')
    basis = {'synthetic':'fictional_fixture', 'live_paper':'observed', 'historical_reconstructed':'verified_archive'}[query.mode]
    # Rank revisions only after provenance/fetch eligibility. Category filtering
    # follows revision selection so a correction cannot resurrect an older body.
    rows = conn.execute('''WITH eligible AS (
        SELECT d.revision_id,d.payload,r.available_at,r.sequence,r.logical_key,r.source_id,
          row_number() OVER (PARTITION BY r.source_id,r.logical_key ORDER BY r.sequence DESC,r.revision_id) AS n
        FROM discovery.evidence_documents d JOIN discovery.revisions r USING(revision_id)
        WHERE d.issuer_id=%s AND r.listing_id=%s AND r.available_at<=%s
          AND r.payload->>'availability_basis'=%s
          AND (%s<>'live_paper' OR r.payload->>'fetched_at'<=%s)
    ) SELECT revision_id FROM eligible WHERE n=1 AND payload->>'category'=ANY(%s)
      ORDER BY revision_id LIMIT %s''', (query.issuer_id, query.listing_id, query.cutoff_at,
        basis, query.mode, query.cutoff_at, list(query.categories), policy.max_documents+1)).fetchall()
    check(len(rows)<=policy.max_documents, 'document scan cap exceeded; narrow query')
    result = []
    for (rid,) in rows:
        item = read_evidence(conn, rid, access=access, cutoff=query.cutoff_at, mode=query.mode, purpose=purpose)
        check(item['document']['issuer_id']==query.issuer_id, 'issuer mismatch')
        # Identity-source permissions are independent of document permissions.
        identity = item['document']['revision']['instrument_revision_id']
        access.require(stored_stream(conn, identity), ('derive',))
        result.append(item)
    return result


def citation(item, evidence_id, locator, excerpt=None):
    doc = item['document']
    return Citation(evidence_id=evidence_id, revision_id=doc['revision']['revision_id'], locator=locator,
                    source_url=doc['revision']['data']['url'], attribution=doc['attribution'],excerpt=excerpt)


def financial_facts(documents, query):
    result = []
    for item in documents:
        for fact in item['facts']:
            if query.required_metrics and fact['metric'] not in query.required_metrics:
                continue
            if fact['scope']!=query.scope:
                continue
            if query.period_end_at and (fact['period_start_at'],fact['period_end_at'],fact['period_kind']) != (query.period_start_at,query.period_end_at,query.period_kind):
                continue
            result.append(Fact(**{k:fact[k] for k in ('fact_id','metric','value','missing_reason','unit','period_start_at','period_end_at','period_kind','scope')},
                               citation=citation(item,fact['fact_id'],fact['locator']),source_locator=fact.get('source_locator'),
                               formula=fact.get('formula'),input_fact_ids=tuple(fact.get('input_fact_ids',()))))
    return tuple(sorted(result, key=lambda f:f.fact_id))


def conflicts(facts):
    groups = {}
    for f in facts:
        if f.value is not None:
            key = (f.metric,f.unit,f.period_start_at,f.period_end_at,f.period_kind,f.scope)
            groups.setdefault(key, []).append(f)
    return tuple(tuple(sorted(f.fact_id for f in group)) for _,group in sorted(groups.items())
                 if len({Decimal(f.value) for f in group})>1)


def calculate_ratio(numerator: Fact, denominator: Fact):
    """Auditable same-period/scope/unit ratio; unavailable is never zero."""
    for key in ('unit','period_start_at','period_end_at','period_kind','scope'):
        check(getattr(numerator,key)==getattr(denominator,key), 'incompatible calculation '+key)
    missing = 'missing_input' if numerator.value is None or denominator.value is None else 'zero_denominator' if Decimal(denominator.value)==0 else None
    with localcontext(CONTEXT):
        value = None if missing else number(Decimal(numerator.value)/Decimal(denominator.value))
    record = dict(formula='ratio-v1', input_fact_ids=[numerator.fact_id,denominator.fact_id], value=value,
                  unit='ratio', missing_reason=missing, scope=numerator.scope, period_start_at=numerator.period_start_at,
                  period_end_at=numerator.period_end_at, period_kind=numerator.period_kind,
                  citations=[f.citation.model_dump(mode='json') for f in (numerator,denominator)])
    return dict(calculation_id=digest(record), **record)


def retrieve(conn, query, policy, *, access, embeddings=None, deadline=float('inf'), monotonic=None):
    from time import monotonic as clock
    clock = monotonic or clock
    query = Query.model_validate_json(query.model_dump_json())
    policy = RetrievalPolicy.model_validate_json(policy.model_dump_json())
    check(clock()<deadline, 'retrieval deadline')
    docs = authorized_documents(conn,query,policy,access)
    fresh = [d for d in docs if (at(query.cutoff_at)-at(d['document']['revision']['available_at'])).total_seconds()<=policy.max_age_days*86400]
    omitted = ['stale:'+d['document']['revision']['revision_id'] for d in docs if d not in fresh]
    docs = fresh
    chunks = {c['chunk_id']:(d,c) for d in docs for c in d['chunks']}
    # Bound embedding and lexical inputs before processing text.
    input_bytes = len(query.text.encode())+sum(len(c['text'].encode()) for _,c in chunks.values())
    check(input_bytes<=policy.max_bytes, 'retrieval input byte cap')
    ids = sorted(chunks)
    lexical = dict(conn.execute('''SELECT chunk_id, ts_rank_cd(to_tsvector('english'::regconfig,payload->>'text'),
            plainto_tsquery('english'::regconfig,%s))::text
        FROM discovery.evidence_chunks WHERE chunk_id=ANY(%s)
          AND to_tsvector('english'::regconfig,payload->>'text') @@ plainto_tsquery('english'::regconfig,%s)
        ORDER BY chunk_id''',(query.text,ids,query.text)).fetchall()) if ids else {}
    semantic = {}
    embedding_ref = None
    embedding_units = 0
    if embeddings is not None:
        check(embeddings.local_only and embeddings.cost_per_unit==0, 'remote/paid embeddings disabled')
        try:
            for d in docs:
                read_evidence(conn,d['document']['revision']['revision_id'],access=access,cutoff=query.cutoff_at,mode=query.mode,purpose='embed')
        except PermissionError:
            omitted.append('semantic:embedding_permission_denied')
        else:
            check(clock()<deadline, 'embedding deadline')
            vectors = embeddings.embed((query.text,)+tuple(chunks[i][1]['text'] for i in ids),deadline=deadline)
            check(clock()<deadline, 'embedding deadline')
            check(len(vectors)==len(ids)+1, 'embedding row count')
            for i,vec in zip(ids,vectors[1:]):
                score = cosine(vectors[0],vec)
                if score>0:
                    semantic[i] = number(score)
            embedding_ref = embeddings.ref
            embedding_units = input_bytes  # Conservative UTF-8 byte upper bound, not a tokenizer estimate.
    else:
        omitted.append('semantic:not_configured')
    # Collapse syndicated text before ranks; duplicates cannot push independent
    # counterevidence out of top-k. Retain every attribution/locator.
    groups = {}
    for cid,(d,c) in chunks.items():
        key = digest(re.findall(r'\w+',c['text'].lower()))
        groups.setdefault(key, []).append(cid)
    def primary(cid):
        doc = chunks[cid][0]['document']
        return doc['authority']=='issuer_primary' and doc['revision']['source_id'] in access.primary_source_ids
    representatives = {}
    aliases = {}
    for members in groups.values():
        members.sort(key=lambda i:(not primary(i),i))
        representatives[members[0]] = members
        aliases.update({i:members[0] for i in members})
    def ranked(scores):
        collapsed = {}
        for cid,value in scores.items():
            key = aliases[cid]
            collapsed[key] = max(collapsed.get(key,Decimal('-1')),Decimal(value))
        order = sorted(collapsed,key=lambda i:(collapsed[i].copy_negate(),not primary(i),i))
        return collapsed, {cid:n for n,cid in enumerate(order,1)}
    ls,lr = ranked(lexical)
    ss,sr = ranked(semantic)
    hits = []
    with localcontext(CONTEXT):
        for cid in sorted(lr.keys()|sr.keys()):
            d,c = chunks[cid]
            score = sum(Decimal(weight)/(policy.rrf_k+ranks[cid]) for weight,ranks in
                        ((policy.lexical_weight,lr),(policy.semantic_weight,sr)) if cid in ranks)
            hits.append(Hit(chunk_id=cid,text=c['text'],primary=primary(cid),
                citations=tuple(citation(chunks[i][0],i,chunks[i][1]['locator'],chunks[i][1]['text']) for i in representatives[cid]),
                lexical_score=number(ls[cid]) if cid in ls else None,semantic_score=number(ss[cid]) if cid in ss else None,
                lexical_rank=lr.get(cid),semantic_rank=sr.get(cid),fused_score=number(score)))
    hits.sort(key=lambda h:(Decimal(h.fused_score).copy_negate(),not h.primary,h.chunk_id))
    omitted.extend('chunk_cap:'+h.chunk_id for h in hits[policy.max_chunks:])
    hits = hits[:policy.max_chunks]
    facts = financial_facts(docs,query)
    present = {d['document']['category'] for d in docs}
    missing = ['category:'+c for c in query.categories if c not in present]
    missing += ['metric:'+m for m in query.required_metrics if not any(f.metric==m and f.value is not None for f in facts)]
    if not hits:
        missing.append('relevant_text')
    requirements = len(query.categories)+len(query.required_metrics)+1
    with localcontext(CONTEXT):
        coverage = number(Decimal(requirements-len(missing))/requirements)
    bundle = Bundle(query=query,ranking=policy.ref,embedding=embedding_ref,
        retrieval_mode='hybrid' if embedding_ref else 'lexical_only',documents=tuple(sorted(d['document']['revision']['revision_id'] for d in docs)),
        hits=tuple(hits),facts=facts,missing=tuple(missing),contradictions=conflicts(facts),omitted=tuple(sorted(omitted)),
        source_count=len({d['document']['revision']['source_id'] for d in docs}),coverage=coverage,embedding_input_units=embedding_units)
    check(len(bundle.model_dump_json().encode())<=policy.max_bytes, 'bundle byte cap')
    check(clock()<deadline, 'retrieval deadline')
    # Recheck all rights after search and immediately before storage/use.
    for rid in bundle.documents:
        read_evidence(conn,rid,access=access,cutoff=query.cutoff_at,mode=query.mode)
        if embedding_ref:
            read_evidence(conn,rid,access=access,cutoff=query.cutoff_at,mode=query.mode,purpose='embed')
        stream = stored_stream(conn,rid)
        access.require(stream, ('store',))
        if any(f.citation.revision_id==rid for f in bundle.facts):
            access.require(stream.model_copy(update={'scope':'financial_facts'}), ('store',))
    conn.execute('INSERT INTO discovery.rag_bundles VALUES (%s,%s) ON CONFLICT DO NOTHING',
                 (bundle.content_hash,Jsonb(bundle.model_dump(mode='json'))))
    return bundle
