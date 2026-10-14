from copy import deepcopy
from datetime import timedelta
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze,stamp
from stock_discovery_analysis.splits import split_report


def test_chronological_assignments_gap_and_end_of_calendar():
    d=demo_dataset()
    indices=[59,60,64,65,79,80,84,85,94,95]
    analyses=[analyze(d,'SYN-ALPHA',d.calendar.sessions[i].closes_at+timedelta(minutes=1),code_version='test') for i in indices]
    report=split_report(d,analyses)
    ids={i:a['recommendation']['recommendation_id'] for i,a in zip(indices,analyses)}
    assert report['windows']['development']['recommendation_ids']==[ids[59]]
    assert report['windows']['validation']['recommendation_ids']==sorted([ids[65],ids[79]])
    assert report['windows']['test']['recommendation_ids']==sorted([ids[85],ids[94]])
    exclusions={e['id']:e['reason'] for e in report['exclusions']}
    for i in [60,64,80,84]: assert exclusions[ids[i]]=='boundary_gap'
    assert exclusions[ids[95]]=='label_horizon_outside_calendar'


def test_extended_labels_and_unsupported_config_are_excluded():
    d=demo_dataset()
    a=analyze(d,'SYN-ALPHA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),code_version='test')
    b=deepcopy(a); b['recommendation']['execution']['max_holding_sessions']=10
    assert split_report(d,[b])['exclusions'][0]['reason']=='label_exceeds_frozen_policy'
    b=deepcopy(a); b['recommendation']['forecast']['end_at']=stamp(d.calendar.sessions[50].closes_at)
    assert split_report(d,[b])['exclusions'][0]['reason']=='label_exceeds_frozen_policy'
    b=deepcopy(a); b['recommendation']['strategy']['config_version']='unknown'
    assert split_report(d,[b])['exclusions'][0]['reason']=='unsupported_label_policy'


def test_split_audit_identity_order_independence_and_duplicate_rejection():
    import pytest
    d=demo_dataset()
    analyses=[analyze(d,symbol,d.calendar.sessions[39].closes_at+timedelta(minutes=1),code_version='test') for symbol in ('SYN-ALPHA','SYN-BETA')]
    report=split_report(d,analyses)
    assert report==split_report(d,list(reversed(analyses)))
    changed=deepcopy(analyses)
    changed[0]['realized_profit']='999999'
    assert split_report(d,changed)==report
    changed[0]['recommendation']['strategy']['config_version']='unsupported'
    assert split_report(d,changed)['audit_id']!=report['audit_id']
    with pytest.raises(ValueError,match='duplicate recommendation'):
        split_report(d,[analyses[0],analyses[0]])


def test_unknown_dataset_split_policy_is_not_silently_reinterpreted():
    from dataclasses import replace
    d=replace(demo_dataset(),split_version='unknown-policy')
    assert split_report(d,[])=={'status':'unavailable','reason':'unsupported_dataset_split_policy'}
