"""Descriptive uncertainty and grouped reports, never signal probabilities."""
from decimal import Decimal as D
from .evaluation import summarize


def wilson(successes:int,count:int):
    if not 0<=successes<=count: raise ValueError('invalid counts')
    if not count: return {'lower':None,'upper':None,'reason':'no_eligible_observations'}
    z=D('1.96');n=D(count);p=D(successes)/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*((p*(1-p)/n+z*z/(4*n*n)).sqrt())/denominator
    return {'lower':max(D(0),center-half),'upper':min(D(1),center+half),
            'method':'95% Wilson descriptive interval; independence assumption may fail for overlapping trades'}


def validation_report(rows,analyses):
    lookup={a['recommendation']['recommendation_id']:a for a in analyses}
    groups={}
    for row in rows:
        a=lookup[row['id']]; r=a['recommendation']; f=a['indicators']
        regime='unknown'
        if f.get('ema10') is not None and f.get('ema30') is not None:
            regime='ema_uptrend' if D(f['ema10'])>D(f['ema30']) else 'ema_not_uptrend'
        for dimension,label in [('horizon',r['horizon']['profile']),('sector','unclassified_synthetic'),('regime',regime),('strategy',r['strategy']['version'])]:
            groups.setdefault(dimension+':'+label,[]).append(row)
    result={}
    for group,items in groups.items():
        metrics=summarize(items);m=metrics['direction']
        result[group]={'sample_count':len(items),'metrics':metrics,'direction_interval':wilson(int(m['numerator']),m['denominator'])}
    return {'groups':result,'status':'software_validation_only',
            'limitations':['Fictional sector and price history; no market inference','EP-1 real-experiment coverage and policy approval absent','No tuning or promotion based on synthetic outcomes']}
