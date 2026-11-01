from copy import deepcopy
from stock_discovery_analysis.fold_reporting import aggregate_folds


def fold(name,start,end,*,phase='validation',policy='same',sample='s',pnl='5'):
    f=dict(fold_id=name,status='completed',phase=phase,mode='synthetic',horizon='swing',comparison='paired',
        universe_hash='universe',versions={a:policy for a in ('quant','quant_rag','quant_agent')},evaluator_hash='evaluator',
        sample_keys=[[sample,start,'hash-'+sample]],sample_window={'start':start,'end':end},arms={a:{} for a in ('quant','quant_rag','quant_agent')})
    p={a:dict(policy_hash='policy',eligible=True,decision_ids=[name+a],orders=[dict(status='closed',realized_pnl=pnl,entry_cost='100',admission='admitted',forecast={'status':'matured'})]) for a in f['arms']}
    return f,p


def test_disjoint_compatible_counts_reuse_existing_trade_metrics_not_return_compounding():
    a,pa=fold('a','2025-01-01T00:00:00Z','2025-01-02T00:00:00Z',sample='a',pnl='10')
    b,pb=fold('b','2025-02-01T00:00:00Z','2025-02-02T00:00:00Z',sample='b',pnl='-5')
    rows=aggregate_folds([a,b],{'a':pa,'b':pb})
    assert len(rows)==3
    for r in rows:
        assert r['status']=='available' and r['samples']==2 and r['metrics']['resolved_trades']==2
        assert r['metrics']['win_rate']=='0.5' and r['metrics']['expectancy_after_costs']=='2.5'
        assert r['metrics']['profit_factor']=='2'
        assert r['portfolio_return'] is r['maximum_drawdown'] is r['benchmark_return'] is None


def test_repeated_samples_or_overlapping_labels_are_not_aggregated():
    a,pa=fold('a','2025-01-01T00:00:00Z','2025-01-03T00:00:00Z')
    b,pb=fold('b','2025-01-02T00:00:00Z','2025-01-04T00:00:00Z',sample='b')
    result=aggregate_folds([a,b],{'a':pa,'b':pb})
    assert all(r['reason']=='overlapping_or_repeated_fold_evidence' and r['metrics'] is None for r in result)
    b['sample_window']={'start':'2025-02-01T00:00:00Z','end':'2025-02-02T00:00:00Z'}
    b['sample_keys']=a['sample_keys']
    assert all(r['status']=='unavailable' for r in aggregate_folds([a,b],{'a':pa,'b':pb}))


def test_phases_configurations_and_arms_are_never_pooled_and_inputs_unchanged():
    a,pa=fold('a','2025-01-01T00:00:00Z','2025-01-02T00:00:00Z')
    b,pb=fold('b','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',phase='test',policy='other')
    before=deepcopy([a,b,pa,pb]);r=aggregate_folds([a,b],{'a':pa,'b':pb})
    assert len(r)==6 and {x['phase'] for x in r}=={'validation','test'}
    assert [a,b,pa,pb]==before


def test_missing_outcome_or_immature_fold_blocks_aggregation_without_dropping_fold():
    a,pa=fold('a','2025-01-01T00:00:00Z','2025-01-02T00:00:00Z')
    pa['quant']['eligible']=False
    r=aggregate_folds([a],{'a':pa})
    q=next(x for x in r if x['arm']=='quant')
    assert q['fold_ids']==['a'] and q['metrics'] is None and q['reason']=='incomplete_fold_evidence'
