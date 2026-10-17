import json
import time
from decimal import Decimal
import pytest
from stock_discovery_analysis.agent_contracts import AgentPolicy,Rubric,Step,JudgeReport
from stock_discovery_analysis.agent_research import investigate,MockAgent,MockJudge,encode
from stock_discovery_analysis.agent_fixtures import labelled_cases,case_bundle,FixtureTools,ScenarioAgent
from stock_discovery_analysis.rag_contracts import Budget


def base(scenario='supported',horizon='swing'):
    return case_bundle(next(c for c in labelled_cases() if c['scenario']==scenario and c['horizon']==horizon))


def run(**changes):
    args=dict(policy=AgentPolicy(),budget=Budget(account='SYN-test'),provider=MockAgent(),judge=MockJudge(),rubric=Rubric(),tools=FixtureTools(),guard=lambda b:None)
    b=changes.pop('base',base());args.update(changes)
    return investigate(b,**args)[0]


@pytest.mark.parametrize('horizon',['swing','short_term','long_term'])
def test_shadow_and_separate_judge(horizon):
    result=run(base=base(horizon=horizon))
    assert result['status']=='completed' and result['action']=='WATCH'
    assert result['actionable'] is False and result['paper_admission']=='blocked'
    assert result['judge_model']['id']!=result['model']['id']
    assert not result['human_holdout_approved'] and result['calibration']=='unconfigured'


@pytest.mark.parametrize('scenario',['fabricated_citation','incorrect_calculation'])
def test_deterministic_failure_cannot_be_overridden(scenario):
    class Never(MockJudge):
        def judge(self,*a,**k):raise AssertionError('invalid material claim must skip judge')
    result=run(base=base(scenario),provider=ScenarioAgent(scenario),judge=Never())
    assert result['action']=='INSUFFICIENT_EVIDENCE' and result['validator']['deterministic']=='failed'
    assert result['judge'] is None


@pytest.mark.parametrize('scenario',['contradictory_filings','stale_evidence','missing_negative_evidence','insufficient_information','unsupported_causal'])
def test_missing_conflicting_and_unsupported_research_abstains(scenario):
    result=run(base=base(scenario),provider=ScenarioAgent(scenario))
    assert result['action']=='INSUFFICIENT_EVIDENCE' and not result['actionable']


def test_four_calls_include_failures_and_no_fifth_dispatch():
    class Loop(MockAgent):
        def step(self,*a,**k):return encode({'tool':{'name':'inspect_conflicts'},'assessment':None})
    class Failing:
        calls=0
        def execute(self,*a):self.calls+=1;raise ValueError('invalid request')
    tools=Failing();result=run(provider=Loop(),tools=tools)
    assert tools.calls==4 and len(result['trace'])==4
    assert all(t['status']=='failed' for t in result['trace']) and result['status']=='abstained'
    assert len(result['accounting']['calls'])==5


@pytest.mark.parametrize('tool',['shell','browse','sql','broker_order','spawn_agent'])
def test_unregistered_tools_and_extra_parameters_rejected(tool):
    with pytest.raises(ValueError):Step.model_validate_json(encode({'tool':{'name':tool,'command':'bad'},'assessment':None}))
    with pytest.raises(ValueError):Step.model_validate_json(encode({'tool':{'name':'retrieve','text':'x','categories':['news'],'cutoff_at':'2099-01-01T00:00:00Z'},'assessment':None}))


def test_token_exhaustion_skips_provider():
    class Never(MockAgent):
        def step(self,*a,**k):raise AssertionError('must stop before model')
    result=run(provider=Never(),budget=Budget(account='SYN-small',max_run_units=100,max_output_units=10))
    assert result['status']=='abstained' and not result['accounting']['calls']


def test_wall_deadline_restored_after_interruption():
    import signal
    previous=signal.getsignal(signal.SIGALRM)
    class Slow(MockAgent):
        def step(self,*a,**k):time.sleep(3);raise AssertionError('deadline must interrupt')
    result=run(provider=Slow(),budget=Budget(account='SYN-time',max_seconds=1))
    assert result['stop_reason']=='TimeoutError' and result['accounting']['calls'][0]['status']=='ambiguous'
    assert signal.getsignal(signal.SIGALRM)==previous and signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0)


def test_judge_disagreement_never_changes_to_buy():
    class Disagree(MockJudge):
        def judge(self,*a,**k):
            result=json.loads(super().judge(*a,**k));result['claims'][0]['support']='unsupported';return encode(result)
    result=run(judge=Disagree())
    assert result['validator']['deterministic']=='passed' and result['validator']['semantic']=='not_supported'
    assert result['action']=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('change',[{'action':'BUY'},{'target_price':'999'},{'claims':[]},{'completeness':'invented'}])
def test_judge_schema_coverage_and_price_limits(change):
    class Invalid(MockJudge):
        def judge(self,*a,**k):return encode({**json.loads(super().judge(*a,**k)),**change})
    assert run(judge=Invalid())['status']=='abstained'


def test_judge_cannot_invent_citations_or_change_rubric():
    class Invalid(MockJudge):
        def judge(self,*a,**k):
            r=json.loads(super().judge(*a,**k));r['claims'][0]['evidence_ids']=['invented'];return encode(r)
    assert run(judge=Invalid())['status']=='abstained'
    with pytest.raises(ValueError):Rubric(dimensions=('profitability',))


def test_source_revocation_halts_before_judge():
    calls=[]
    def guard(b):
        calls.append(1)
        if len(calls)>1:raise PermissionError('revoked')
    result=run(guard=guard)
    assert result['stop_reason']=='PermissionError' and result['judge'] is None


def test_prompt_injection_remains_quoted_evidence():
    result=run(base=base('prompt_injection'))
    assert result['status']=='completed' and result['trace']==[] and not result['actionable']


def test_local_free_independent_models_only():
    class Paid(MockJudge):cost_per_unit=Decimal('1')
    with pytest.raises(ValueError):run(judge=Paid())
    class Same(MockJudge):ref=MockAgent.ref
    with pytest.raises(ValueError):run(judge=Same())


def test_output_and_tool_byte_caps():
    class Oversize(MockAgent):
        def step(self,*a,**k):return 'x'*13000
    assert run(provider=Oversize())['status']=='abstained'
    class Once(MockAgent):
        def step(self,request,**k):
            if not json.loads(request)['trace']:return encode({'tool':{'name':'inspect_conflicts'},'assessment':None})
            return super().step(request,**k)
    result=run(provider=Once(),policy=AgentPolicy(max_tool_bytes=1))
    assert len(result['trace'])==1 and result['trace'][0]['status']=='failed'


def test_dataset_group_and_time_split_labels_are_not_human_claims():
    cases=labelled_cases();dev=[c for c in cases if c['split']=='development'];hold=[c for c in cases if c['split']=='holdout']
    assert len(cases)==54 and not ({c['issuer_family'] for c in dev}&{c['issuer_family'] for c in hold})
    assert max(c['cutoff_at'] for c in dev)<min(c['cutoff_at'] for c in hold)
    assert all(not c['human_reviewed'] and c['label_source']=='synthetic_rule_authored' for c in cases)


def test_paired_mock_evaluation_is_measured_and_not_a_calibration_claim():
    from stock_discovery_analysis.agent_evaluation import evaluate
    result=evaluate()
    assert not result['superiority_claim'] and not result['calibration_approved'] and not result['human_reviewed']
    fixed=result['arms']['fixed_rag']['overall'];agent=result['arms']['bounded_agent']['overall']
    assert fixed['cases']==agent['cases']==54
    assert fixed['material_error_false_acceptance']['numerator']==6
    assert agent['material_error_false_acceptance']['numerator']==0
    assert agent['material_error_false_acceptance_wilson95'][1]>0
    assert fixed['actual_model_cost_usd']==agent['actual_model_cost_usd']=='0'
    assert fixed['total_latency_ms']>=0 and agent['total_latency_ms']>=0


def test_expired_absolute_deadline_stops_before_sources_or_models():
    def never(bundle):raise AssertionError('expired request must not read sources')
    result=run(deadline=0,guard=never)
    assert result['status']=='abstained' and not result['accounting']['calls']
