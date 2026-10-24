from copy import deepcopy
import pytest
from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis.governance_contracts import Experiment,split_samples
from stock_discovery_analysis.governance import holdout_overlap,summarize_arm


def manifest(eid='EXP-test'):
    h=digest('test-only')
    return dict(experiment_id=eid,hypothesis='Fixture safeguards, not investment research',horizon='swing',mode='synthetic',comparison='paired',universe=['SYN-A'],universe_ref={'id':'test','version':'1','content_hash':h},
        train={'start':'2000-01-01T00:00:00Z','end':'2001-01-01T00:00:00Z'},validation={'start':'2002-01-01T00:00:00Z','end':'2003-01-01T00:00:00Z'},test={'start':'2004-01-01T00:00:00Z','end':'2005-01-01T00:00:00Z'},
        samples=[],embargo_seconds=86400,arms=[dict(arm=a,strategy_hash=h,model_hash=h if a!='quant' else None,retrieval_hash=h if a!='quant' else None,prompt_hash=h if a!='quant' else None,policy_hash=h,cost_hash=h,risk_hash=h,candidate_selection='same frozen members') for a in ('quant','quant_rag','quant_agent')],metrics=['net_expectancy_after_costs','forecast_maturity'],stopping_rule='fixed cohort; no performance-based extension',tuning_budget=10,historical_llm_contamination='possible_uncontrolled_model_knowledge')


def parse(x):return Experiment.model_validate_json(__import__('json').dumps(x))


def sample(name,cutoff,end,group='event-A'):
    return dict(sample_id=name,listing_id='SYN-A',cutoff=cutoff,label_end=end,groups=[group],input_hash=digest('inputs'),revision_ids=[])


def test_chronology_required_and_optional_ml_blocked():
    m=manifest();m['validation']=m['train']
    with pytest.raises(ValueError,match='chronological'):parse(m)
    m=manifest();m['q_ml_enabled']=True
    with pytest.raises(ValueError):parse(m)


def test_overlapping_labels_purged_and_actual_span_embargo_required():
    m=manifest();m['samples']=[sample('overlap','2000-12-31T00:00:00Z','2002-01-02T00:00:00Z')]
    with pytest.raises(ValueError,match='embargo_below'):parse(m)
    m['embargo_seconds']=400*86400;a=split_samples(parse(m))
    assert a['excluded']==[{'sample_id':'overlap','reason':'overlapping_label_purged'}]
    assert not a['accepted']['train']


def test_group_leakage_and_independent_holdout_window():
    m=manifest();m['samples']=[sample('a','2000-01-02T00:00:00Z','2000-01-03T00:00:00Z'),sample('b','2002-01-02T00:00:00Z','2002-01-03T00:00:00Z')]
    with pytest.raises(ValueError,match='group_crosses'):split_samples(parse(m))
    a=parse(manifest());b=parse(manifest('new-name'))
    assert holdout_overlap(a,b)
    m=manifest();m['test']={'start':'2006-01-01T00:00:00Z','end':'2007-01-01T00:00:00Z'}
    assert not holdout_overlap(a,parse(m))


def test_zero_picks_missing_outcomes_and_benchmarks_not_profits():
    r=summarize_arm([],[],12)
    assert r['no_picks'] and r['not_selected']==12 and r['resolved_trades']==0
    assert r['expectancy_after_costs'] is None and r['benchmark_return'] is None
    assert r['uncertainty'] is None and r['portfolio_return'] is None
    assert not summarize_arm([],[],12,unavailable=True)['no_picks']


def test_paired_cost_and_candidate_assumptions_are_frozen():
    m=manifest();m['arms'][1]['cost_hash']=digest('other')
    with pytest.raises(ValueError,match='paired_assumptions'):parse(m)
    m['comparison']='end_to_end';assert parse(m).comparison=='end_to_end'


def test_duplicate_sample_labels_cannot_inflate_denominators():
    m=manifest();s=sample('a','2000-01-02T00:00:00Z','2000-01-03T00:00:00Z');m['samples']=[s,{**s,'sample_id':'renamed'}]
    with pytest.raises(ValueError,match='duplicate_sample_observation'):parse(m)


def test_invalid_forward_window_and_preprocessing_leakage():
    m=manifest();m['forward']=m['validation']
    with pytest.raises(ValueError,match='forward_after'):parse(m)
    m=manifest();m['arms'][1]['preprocessing_fit_split']='test'
    with pytest.raises(ValueError):parse(m)


def test_json_api_arrays_keep_strict_numeric_and_immutable_models():
    e=Experiment.model_validate(manifest());assert isinstance(e.universe,tuple)
    with pytest.raises(ValueError):e.hypothesis='rewrite'
    m=manifest();m['tuning_budget']='10'
    with pytest.raises(ValueError):Experiment.model_validate(m)


def test_boundary_embargo_and_shared_revision_groups():
    m=manifest();m['train']={'start':'2000-01-01T00:00:00Z','end':'2000-01-10T00:00:00Z'};m['validation']={'start':'2000-01-12T00:00:00Z','end':'2000-01-20T00:00:00Z'}
    m['samples']=[sample('a','2000-01-10T00:00:00Z','2000-01-11T00:00:00Z')];m['embargo_seconds']=3*86400
    assert split_samples(parse(m))['excluded'][0]['reason']=='embargo_purged'
    m=manifest();a=sample('a','2000-01-02T00:00:00Z','2000-01-03T00:00:00Z','different-A');b=sample('b','2002-01-02T00:00:00Z','2002-01-03T00:00:00Z','different-B')
    b['input_hash']=digest('different');a['revision_ids']=b['revision_ids']=['same-filing'];m['samples']=[a,b]
    with pytest.raises(ValueError,match='related_group_crosses'):split_samples(parse(m))


def test_no_entries_ambiguity_and_forecasts_use_separate_denominators():
    recs=[dict(recommendation=dict(recommendation_id=str(i),instrument={'instrument_id':str(i)},action='BUY',cohort={'arm':'quant'},research_status='not_requested',missing_evidence=[])) for i in range(4)]
    orders=[dict(recommendation_id=str(i),status=status,admission='admitted',bought=0 if status=='no_entry' else 1,forecast={'status':'provisional','return':None}) for i,status in enumerate(('no_entry','ambiguous','open'))]
    r=summarize_arm(recs,orders,4)
    assert (r['no_entry'],r['ambiguous'],r['provisional'],r['missing_outcomes'])==(1,1,1,1)
    assert r['resolved_trades']==0 and r['expectancy_after_costs'] is None
    assert r['forecast_quality']['provisional']==3 and r['forecast_quality']['missing']==1
    assert r['forecast_quality']['observed_endpoint_return']['mean'] is None


def test_paired_baseline_hashes_match_while_research_hashes_may_differ():
    m=manifest()
    for i,arm in enumerate(m['arms'][1:]):
        for field in ('model_hash','retrieval_hash','prompt_hash'):arm[field]=digest([field,i])
    assert parse(m).comparison=='paired'
    for field in ('strategy_hash','policy_hash'):
        changed=deepcopy(m);changed['arms'][1][field]=digest('different baseline')
        with pytest.raises(ValueError,match='paired_assumptions_mismatch'):parse(changed)
        changed['comparison']='end_to_end';assert parse(changed).comparison=='end_to_end'
