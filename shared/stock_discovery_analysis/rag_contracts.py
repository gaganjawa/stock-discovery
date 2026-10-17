"""STK-052/053/074: bounded, immutable fixed-RAG wire contracts."""
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, Hash, Number, Timestamp, Mode, Profile, Ref, check, digest

Positive = Annotated[int, Field(gt=0)]
Category = Literal['announcement', 'annual_report', 'quarterly_report', 'news']


class RetrievalPolicy(Strict):
    version: Literal['1.0.0'] = '1.0.0'
    lexical_weight: Number = '1'
    semantic_weight: Number = '1'
    rrf_k: Positive = 60
    max_documents: Annotated[int, Field(gt=0, le=100)] = 30
    max_chunks: Annotated[int, Field(gt=0, le=20)] = 20
    max_bytes: Annotated[int, Field(gt=0, le=200000)] = 64000
    max_age_days: Positive = 400
    max_candidates: Annotated[int, Field(gt=0, le=10)] = 10
    event_slots: Annotated[int, Field(ge=0, le=10)] = 2

    @model_validator(mode='after')
    def valid(self):
        check(Decimal(self.lexical_weight)>0 and Decimal(self.semantic_weight)>=0, 'ranking weights')
        check(self.event_slots<=self.max_candidates, 'event allocation')
        return self

    @property
    def ref(self):
        return Ref(id='hybrid-rrf', version=self.version, content_hash=digest(self.model_dump(mode='json')))


class Query(Strict):
    issuer_id: Text
    listing_id: Text
    horizon: Profile
    mode: Mode
    cutoff_at: Timestamp
    text: Annotated[str, Field(min_length=1, max_length=1000)]
    categories: Annotated[tuple[Category, ...], Field(min_length=1)]
    required_metrics: tuple[Text, ...] = ()
    period_start_at: Timestamp | None = None
    period_end_at: Timestamp | None = None
    period_kind: Literal['annual', 'quarter', 'instant'] | None = None
    scope: Literal['consolidated', 'standalone'] = 'consolidated'

    @model_validator(mode='after')
    def valid(self):
        check(len(set(self.categories))==len(self.categories), 'duplicate categories')
        check(len(set(self.required_metrics))==len(self.required_metrics), 'duplicate metrics')
        check(not self.required_metrics or all((self.period_start_at,self.period_end_at,self.period_kind)), 'financial period required')
        if self.period_end_at:
            check(self.period_start_at is not None and self.period_start_at<=self.period_end_at<=self.cutoff_at, 'financial cutoff')
        return self


class Citation(Strict):
    evidence_id: Text
    revision_id: Text
    locator: Text
    source_url: Text
    attribution: Text
    excerpt: Text | None = None


class Fact(Strict):
    fact_id: Hash
    metric: Text
    value: Number | None
    missing_reason: Text | None
    unit: Text
    period_start_at: Timestamp
    period_end_at: Timestamp
    period_kind: Literal['annual', 'quarter', 'instant']
    scope: Literal['consolidated', 'standalone']
    citation: Citation
    source_locator: Text | None = None
    formula: Text | None = None
    input_fact_ids: tuple[Hash, ...] = ()


class Hit(Strict):
    chunk_id: Hash
    text: Text
    primary: bool
    citations: Annotated[tuple[Citation, ...], Field(min_length=1)]
    lexical_score: Number | None
    semantic_score: Number | None
    lexical_rank: Positive | None
    semantic_rank: Positive | None
    fused_score: Number


class Bundle(Strict):
    schema_version: Literal['1.0.0'] = '1.0.0'
    query: Query
    ranking: Ref
    embedding: Ref | None
    retrieval_mode: Literal['hybrid', 'lexical_only']
    documents: tuple[Text, ...]
    hits: tuple[Hit, ...]
    facts: tuple[Fact, ...]
    missing: tuple[Text, ...]
    contradictions: tuple[tuple[Text, ...], ...]
    omitted: tuple[Text, ...]
    source_count: Annotated[int, Field(ge=0)]
    coverage: Number
    embedding_input_units: Annotated[int, Field(ge=0)]

    @property
    def content_hash(self):
        return digest(self.model_dump(mode='json'))


class Claim(Strict):
    kind: Literal['quote', 'financial', 'inference']
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    citations: Annotated[tuple[Citation, ...], Field(min_length=1, max_length=20)]
    fact: Fact | None = None


class Assessment(Strict):
    schema_version: Literal['1.0.0'] = '1.0.0'
    issuer_id: Text
    horizon: Profile
    action: Literal['BUY', 'WATCH', 'AVOID', 'INSUFFICIENT_EVIDENCE']
    claims: Annotated[tuple[Claim, ...], Field(max_length=40)]
    missing: tuple[Text, ...]
    contradictions: tuple[tuple[Text, ...], ...]
    actionable: Literal[False] = False
    paper_admission: Literal['blocked'] = 'blocked'


class Budget(Strict):
    account: Text
    max_run_units: Positive = 200000
    max_day_units: Positive = 2000000
    max_month_units: Positive = 20000000
    max_output_units: Positive = 12000
    max_seconds: Annotated[int, Field(gt=0, le=120)] = 120
    max_run_cost: Number = '0'
    max_day_cost: Number = '0'
    max_month_cost: Number = '0'

    @model_validator(mode='after')
    def valid(self):
        check(self.max_output_units<self.max_run_units<=self.max_day_units<=self.max_month_units, 'budget units')
        check(Decimal('0')<=Decimal(self.max_run_cost)<=Decimal(self.max_day_cost)<=Decimal(self.max_month_cost), 'budget costs')
        return self
