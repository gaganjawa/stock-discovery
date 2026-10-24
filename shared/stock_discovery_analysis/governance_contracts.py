"""D3-11 preregistration; existing v2 research/outcome contracts stay unchanged."""
from datetime import timedelta
from typing import Annotated, Literal, get_origin
from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, Hash, Timestamp, Profile, Mode, Ref, check, at

ARMS=('quant','quant_rag','quant_agent')
Split=Literal['train','validation','test','forward']


class Wire(Strict):
    @model_validator(mode='before')
    @classmethod
    def json_arrays(cls,value):
        # FastAPI decodes JSON first; accept arrays without coercing strict scalars.
        if isinstance(value,dict):
            return {k:tuple(v) if isinstance(v,list) and k in cls.model_fields and get_origin(cls.model_fields[k].annotation) is tuple else v for k,v in value.items()}
        return value


class Window(Wire):
    start: Timestamp
    end: Timestamp
    @model_validator(mode='after')
    def ordered(self):
        check(at(self.start)<at(self.end),'invalid_split_interval');return self


class Sample(Wire):
    sample_id: Text
    listing_id: Text
    cutoff: Timestamp
    label_end: Timestamp
    # Event/document clusters, not an assumption of independent daily rows.
    groups: Annotated[tuple[Text,...],Field(min_length=1)]
    input_hash: Hash
    revision_ids: tuple[Text,...]
    @model_validator(mode='after')
    def clocks(self):
        check(at(self.cutoff)<at(self.label_end),'invalid_label_span');return self


class ArmConfig(Wire):
    arm: Literal['quant','quant_rag','quant_agent']
    strategy_hash: Hash
    model_hash: Hash | None
    retrieval_hash: Hash | None
    prompt_hash: Hash | None
    policy_hash: Hash
    cost_hash: Hash
    risk_hash: Hash
    candidate_selection: Text
    preprocessing_fit_split: Literal['train'] = 'train'
    @model_validator(mode='after')
    def research(self):
        check(self.arm=='quant' or all((self.model_hash,self.retrieval_hash,self.prompt_hash)),'research_artifacts_required');return self


class Thresholds(Wire):
    minimum_samples: Annotated[int,Field(gt=0)] | None = None
    forward_days: Annotated[int,Field(gt=0)] | None = None
    coverage: Annotated[float,Field(ge=0,le=1)] | None = None
    max_drawdown: Annotated[float,Field(ge=0,le=1)] | None = None
    cost_stress: Annotated[float,Field(ge=1)] | None = None
    benchmark_criterion: Text | None = None
    research_quality_approval: Ref | None = None
    strategy_approval: Ref | None = None


class Experiment(Wire):
    experiment_id: Text
    hypothesis: Text
    horizon: Profile
    mode: Mode
    comparison: Literal['paired','end_to_end']
    universe: Annotated[tuple[Text,...],Field(min_length=1,max_length=10000)]
    universe_ref: Ref
    train: Window
    validation: Window
    test: Window
    forward: Window | None = None
    samples: Annotated[tuple[Sample,...],Field(max_length=10000)]
    embargo_seconds: Annotated[int,Field(ge=0)]
    arms: Annotated[tuple[ArmConfig,...],Field(min_length=3,max_length=3)]
    metrics: Annotated[tuple[Text,...],Field(min_length=1)]
    stopping_rule: Text
    tuning_budget: Annotated[int,Field(ge=1,le=1000)]
    benchmark_ref: Ref | None = None
    thresholds: Thresholds = Field(default_factory=Thresholds)
    historical_llm_contamination: Literal['possible_uncontrolled_model_knowledge']
    q_ml_enabled: Literal[False] = False
    @model_validator(mode='after')
    def splits(self):
        check(at(self.train.end)<at(self.validation.start) and at(self.validation.end)<at(self.test.start),'chronological_split_order')
        check(self.forward is None or self.mode!='historical_reconstructed','historical_reconstruction_is_not_forward')
        check(self.forward is None or at(self.test.end)<at(self.forward.start),'forward_after_holdout')
        check(len({(s.listing_id,s.cutoff) for s in self.samples})==len(self.samples),'duplicate_sample_observation')
        check(len(set(self.universe))==len(self.universe),'duplicate_universe')
        check({a.arm for a in self.arms}==set(ARMS),'three_mandatory_arms')
        check(len({s.sample_id for s in self.samples})==len(self.samples),'duplicate_samples')
        check(all(s.listing_id in self.universe for s in self.samples),'sample_outside_universe')
        span=max(((at(s.label_end)-at(s.cutoff)).total_seconds() for s in self.samples),default=0)
        check(self.embargo_seconds>=span,'embargo_below_actual_maximum_label_span')
        if self.comparison=='paired':
            check(len({(a.cost_hash,a.risk_hash,a.candidate_selection) for a in self.arms})==1,'paired_assumptions_mismatch')
        return self


def split_samples(experiment):
    """Purge labels and embargo earlier decisions; preserve exclusions in the ledger."""
    accepted={k:[] for k in ('train','validation','test','forward') if getattr(experiment,k) is not None};excluded=[];groups={}
    for s in experiment.samples:
        name=next((k for k in accepted if at(getattr(experiment,k).start)<=at(s.cutoff)<=at(getattr(experiment,k).end)),None)
        reason=None
        if name is None:reason='outside_split'
        else:
            following='validation' if name=='train' else 'test' if name=='validation' else None
            if following and at(s.label_end)>=at(getattr(experiment,following).start):reason='overlapping_label_purged'
            elif following and at(s.cutoff)+timedelta(seconds=experiment.embargo_seconds)>=at(getattr(experiment,following).start):reason='embargo_purged'
            elif name!='forward' and at(s.label_end)>at(getattr(experiment,name).end):reason='label_outside_split_purged'
        if reason:excluded.append(dict(sample_id=s.sample_id,reason=reason));continue
        clusters=[('declared',g) for g in s.groups]+[('snapshot',s.input_hash)]+[('revision',rid) for rid in s.revision_ids]
        for g in clusters:
            check(g not in groups or groups[g]==name,'related_group_crosses_splits')
            groups[g]=name
        accepted[name].append(s.sample_id)
    return dict(accepted=accepted,excluded=excluded,maximum_label_span_seconds=max(((at(s.label_end)-at(s.cutoff)).total_seconds() for s in experiment.samples),default=0),embargo_seconds=experiment.embargo_seconds)


class ArmInput(Wire):
    arm: Literal['quant','quant_rag','quant_agent']
    publication_run_id: Text | None
    recommendation_ids: tuple[Text,...]
    # Pin an immutable D3-10 ledger revision; never silently read newest outcomes.
    portfolio_id: Text | None = None
    ledger_sequence: Annotated[int,Field(ge=1)] | None = None
    @model_validator(mode='after')
    def refs(self):
        check((self.portfolio_id is None)==(self.ledger_sequence is None),'ledger_reference_pair')
        check(not self.recommendation_ids or self.publication_run_id is not None,'publication_reference_required')
        check(len(set(self.recommendation_ids))==len(self.recommendation_ids),'duplicate_decisions');return self


class Trial(Wire):
    trial_id: Text
    experiment_id: Text
    split: Split
    selected_validation_trial: Text | None = None
    arms: Annotated[tuple[ArmInput,...],Field(min_length=3,max_length=3)]
    forward_samples: Annotated[tuple[Sample,...],Field(max_length=10000)] = ()
    outcome_cutoff: Timestamp
    @model_validator(mode='after')
    def mandatory(self):
        at(self.outcome_cutoff)
        check(self.split=='forward' or not self.forward_samples,'forward_samples_only_in_forward_trial')
        check(len({(s.listing_id,s.cutoff) for s in self.forward_samples})==len(self.forward_samples),'duplicate_sample_observation')
        check({a.arm for a in self.arms}==set(ARMS),'three_mandatory_arms')
        check(self.split!='test' or self.selected_validation_trial is not None,'validation_selection_required');return self
