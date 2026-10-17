"""STK-052/070/071/072: closed tool surface and versioned shadow judge contracts."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, Ref, Hash, check, digest
from .rag_contracts import Assessment, Category


class Search(Strict):
    name: Literal['retrieve']
    text: Annotated[str, Field(min_length=1,max_length=1000)]
    categories: Annotated[tuple[Category,...],Field(min_length=1,max_length=4)]


class Conflicts(Strict):
    name: Literal['inspect_conflicts']


class Ratio(Strict):
    name: Literal['calculate_ratio']
    numerator_id: Hash
    denominator_id: Hash


Tool = Annotated[Search | Conflicts | Ratio, Field(discriminator='name')]


class Step(Strict):
    tool: Tool | None = None
    assessment: Assessment | None = None

    @model_validator(mode='after')
    def one_operation(self):
        check((self.tool is None)!=(self.assessment is None),'exactly one tool or final assessment')
        return self


class AgentPolicy(Strict):
    version: Literal['1.0.0'] = '1.0.0'
    max_tool_calls: Annotated[int, Field(ge=0,le=4)] = 4
    max_tool_bytes: Annotated[int, Field(gt=0,le=64000)] = 32000
    max_tool_rows: Annotated[int, Field(gt=0,le=100)] = 100
    max_context_bytes: Annotated[int, Field(gt=0,le=200000)] = 64000

    @property
    def ref(self):
        return Ref(id='bounded-research',version=self.version,content_hash=digest(self.model_dump(mode='json')))


class Rubric(Strict):
    version: Literal['1.0.0'] = '1.0.0'
    dimensions: tuple[Text,...] = ('claim_support','contradictions','negative_evidence','completeness','causal_support','abstention')
    calibration: Literal['unconfigured'] = 'unconfigured'
    human_holdout_approved: Literal[False] = False

    @model_validator(mode='after')
    def frozen_dimensions(self):
        check(self.dimensions==('claim_support','contradictions','negative_evidence','completeness','causal_support','abstention'), 'rubric version mismatch')
        return self

    @property
    def ref(self):
        return Ref(id='research-support',version=self.version,content_hash=digest(self.model_dump(mode='json')))


class ClaimJudgment(Strict):
    claim_index: Annotated[int,Field(ge=0,lt=40)]
    support: Literal['supported','unsupported','uncertain']
    evidence_ids: tuple[Text,...]
    reason: Literal['direct_support','unsupported_inference','contradicted','missing_premises','uncertain']


class JudgeReport(Strict):
    rubric: Ref
    claims: Annotated[tuple[ClaimJudgment,...],Field(max_length=40)]
    contradictions: Literal['addressed','missed','unknown']
    negative_evidence: Literal['addressed','missed','unknown']
    completeness: Literal['complete','incomplete','unknown']
    causal_support: Literal['no_causal_claim','supported','unsupported','unknown']
    abstention: Literal['appropriate','inappropriate','unknown']
    # No prices, position sizes, probabilities, financial values or action fields.
