"""Freeze before reveal; persisted runs survive process restarts."""
import json
import hashlib
from datetime import datetime,timezone
from psycopg.types.json import Jsonb
from .dataset import Dataset,canonical,from_payload
from .strategy import analyze
from .replay import simulate,dt
from .evaluation import summarize,portfolio
from .portfolio import replay_portfolio
from .reports import validation_report
from .splits import split_report


def json_value(value): return json.loads(canonical(value))


def load_dataset(conn,version):
    row=conn.execute('SELECT manifest FROM research.datasets WHERE dataset_version=%s',(version,)).fetchone()
    if row is None: raise KeyError('dataset not found')
    dataset=from_payload(row[0]['payload'])
    if dataset.version!=version: raise ValueError('dataset hash mismatch')
    return dataset


def freeze(conn,dataset: Dataset,instrument_id: str,cutoff: datetime,code_version: str) -> dict:
    analysis=json_value(analyze(dataset,instrument_id,cutoff,code_version=code_version))
    r=analysis['recommendation']
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(r['run_id'],))
        existing=conn.execute('SELECT manifest FROM research.runs WHERE run_id=%s',(r['run_id'],)).fetchone()
        if existing: return existing[0]['analysis']
        conn.execute('''INSERT INTO research.runs(run_id,mode,information_cutoff_at,started_at,completed_at,status,
            dataset_version,code_version,strategy_version,manifest) VALUES (%s,%s,%s,%s,%s,'completed',%s,%s,%s,%s)''',
            (r['run_id'],r['mode'],r['information_cutoff_at'],r['generated_at'],r['generated_at'],dataset.version,
             code_version,r['strategy']['version'],Jsonb({'analysis':analysis,'dataset_version':dataset.version})))
        conn.execute('''INSERT INTO research.decisions(recommendation_id,instrument_id,run_id,schema_version,
            information_cutoff_at,generated_at,decision_available_at,action,position_effect,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (r['recommendation_id'],instrument_id,r['run_id'],r['schema_version'],r['information_cutoff_at'],
             r['generated_at'],r['decision_available_at'],r['action'],r['position_effect'],Jsonb(r)))
    return analysis


def read_frozen(conn,recommendation_id):
    row=conn.execute('''SELECT r.manifest FROM research.runs r JOIN research.decisions d USING(run_id)
        WHERE d.recommendation_id=%s''',(recommendation_id,)).fetchone()
    if row is None: raise KeyError('recommendation not found')
    return row[0]['analysis']


def reveal(conn,recommendation_id,evaluated_at=None):
    a=read_frozen(conn,recommendation_id)
    d=load_dataset(conn,a['recommendation']['versions']['dataset'])
    now=evaluated_at or datetime.now(timezone.utc)
    result=simulate(a,d,now)
    # Content identity ignores wall-clock timestamp, preserving the first equivalent evaluation.
    fingerprint={k:v for k,v in result.items() if k!='evaluated_at'}
    oid='SYN-OUT-'+hashlib.sha256(canonical(fingerprint).encode()).hexdigest()
    with conn.transaction():
        for kind in ('forecast','trade'):
            payload=json_value(result if kind=='trade' else {**result['forecast'],'schema_version':'1.1.0','synthetic':True})
            conn.execute(f'''INSERT INTO research.{kind}_outcomes
                (outcome_id,recommendation_id,evaluated_at,evaluator_version,observation_dataset,status,payload)
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                (oid+'-'+kind,recommendation_id,now,result['evaluator_version'],d.version,result[kind]['status'],Jsonb(payload)))
        stored=conn.execute('SELECT payload FROM research.trade_outcomes WHERE outcome_id=%s',(oid+'-trade',)).fetchone()[0]
    return stored


def cohort_metadata(r):
    values=dict(dataset=r['versions']['dataset'],code=r['versions']['code'],
                strategy=r['strategy']['version'],configuration=r['strategy']['config_version'])
    return {'id':hashlib.sha256(canonical(values).encode()).hexdigest(),**values}


def scorecard(conn,cohort=None):
    records=conn.execute('''SELECT d.payload,o.payload FROM research.decisions d LEFT JOIN LATERAL
        (SELECT payload FROM research.trade_outcomes WHERE recommendation_id=d.recommendation_id
         ORDER BY evaluated_at DESC,outcome_id DESC LIMIT 1) o ON true ORDER BY d.generated_at,d.recommendation_id''').fetchall()
    cohorts={}
    for r,_ in records:
        group=cohort_metadata(r)
        cohorts.setdefault(group['id'],{**group,'count':0})['count']+=1
    if cohort is not None:
        if cohort not in cohorts: raise ValueError('Unknown scorecard version group')
        records=[(r,o) for r,o in records if cohort_metadata(r)['id']==cohort]
    rows=[]; detail=[]; portfolio_records=[]
    for r,o in records:
        t=o['trade'] if o else {}; f=o['forecast'] if o else {}
        portfolio_records.append((read_frozen(conn,r['recommendation_id']),o))
        closed=t.get('status')=='closed'; buy=r['action']=='BUY'
        entered=bool(t.get('fills')) if o else None
        if t.get('status') not in ('closed','open','ambiguous','no_entry'): entered=None
        evaluated=dt(o['evaluated_at']) if o else None
        forecast_due=bool(r['forecast'] and evaluated and evaluated>=dt(r['forecast']['end_at']))
        entry_due=bool(buy and evaluated and evaluated>=dt(r['execution']['entry_expires_at']))
        row=dict(id=r['recommendation_id'],action=r['action'],forecast_status=f.get('status','pending'),
            direction=f.get('direction_matches'),target_status='not_applicable',target=None,entry=entered,
            trade_status=t.get('status','missing'),reason=t.get('reason'),target_first=t.get('reason')=='target' if closed else None,
            net=t.get('net_pnl'),forecast_due=forecast_due,target_due=False,entry_due=entry_due,trade_due=entered is True and forecast_due)
        rows.append(row)
        curve=o.get('equity_curve',[]) if o else []
        detail.append({'recommendation_id':r['recommendation_id'],'status':t.get('status','missing'),
                       'portfolio':portfolio(curve),'exclusions':o.get('exclusions',[]) if o else ['not_evaluated']})
    split_audit=split_report(load_dataset(conn,records[0][0]['versions']['dataset']),[a for a,_ in portfolio_records]) if records and len({cohort_metadata(r)['id'] for r,_ in records})==1 else {'status':'unavailable','reason':'select_one_nonempty_version_group'}
    return json_value({'chronological_validation':split_audit,'cohorts':sorted(cohorts.values(),key=lambda c:c['id']),'selected_cohort':cohort,**summarize(rows),'eligibility':rows,'isolated_trade_portfolios':detail,
        'portfolio':replay_portfolio(portfolio_records),
        'validation_report':validation_report(rows,[a for a,_ in portfolio_records]),
        'benchmark':{'return':None,'reason':'no_permitted_comparable_benchmark'},'cash_benchmark_return':'0',
        'promotion':{'status':'insufficient_evidence','reason':'synthetic software tests; EP-1 requires at least 30 complete months and approved policy'},
        'label':'SYNTHETIC DEMO — no profitability inference'})
