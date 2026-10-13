"""Frozen EMA/volume/breakout baseline. No probability or real-order capability."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR
import hashlib
from .dataset import Dataset, canonical
from .indicators import features
from .risk import demo_profile, sizing

STRATEGY_VERSION='ema-breakout-1.0.2'
CONFIG_VERSION='SYN-EMA10-30-RVOL20-1.5-ATR14-2R-v1'


def stamp(t): return t.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def tick(value, up=False):
    return value.quantize(D('.01'),rounding=ROUND_CEILING if up else ROUND_FLOOR)


def analyze(dataset: Dataset, instrument_id: str, cutoff: datetime, *, code_version: str,
            generated_at: datetime|None=None) -> dict:
    bars=dataset.asof(instrument_id,cutoff)
    quality=list(dataset.quality(instrument_id,cutoff,30))
    f=features(bars) if not quality else {}
    ready=cutoff+timedelta(minutes=1)
    future=[s for s in dataset.calendar.sessions if s.opens_at>ready]
    if len(future)<5: quality.append('calendar_horizon_unavailable')
    conditions=bool(f and f['ema10']>f['ema30'] and bars[-1].close>f['breakout20'] and f['relative_volume20']>=D('1.5'))
    action='INSUFFICIENT_EVIDENCE' if quality else ('BUY' if conditions else 'WAIT')
    execution=None; forecast=None; risk=None
    if action=='BUY':
        entry=tick(bars[-1].high+D('.01'),True)
        stop=tick(entry-2*f['atr14'])
        target=tick(entry+2*(entry-stop),True)
        entry_cap=tick(entry*D('1.01'),True)
        if stop<=D('.05'):
            quality.append('invalid_stop'); action='INSUFFICIENT_EVIDENCE'
        else:
            risk=sizing(demo_profile(entry_cap,stop-D('.05')))
            risk.update(entry_cap=entry_cap,stop_fill_assumption=stop-D('.05'),profile='SYN-RISK-1-empty-portfolio',
                        risk_reward=(target-entry)/(entry-stop))
            if not risk['quantity']: action='WAIT'
            else:
                execution={'entry':{'type':'buy_stop','trigger_price':str(entry),'condition':f'Next-session breakout; fill cap INR {entry_cap}; synthetic only'},
                    'entry_expires_at':stamp(future[2].opens_at),
                    'stop':{'price':str(stop),'condition':'Protective stop after entry; gaps can exceed planned loss'},
                    'targets':[{'price':str(target),'exit_fraction':'1'}], 'max_holding_sessions':3,
                    'time_exit':'close_of_last_holding_session','quantity':risk['quantity'],
                    'assumptions_version':'SYN-daily-costs-v1'}
                forecast={'direction':'up','reference_price':str(bars[-1].close),'reference_at':stamp(bars[-1].ends_at),
                          'end_at':stamp(future[4].closes_at),'definition_version':'SYN-direction-v1'}
    if quality:
        explanation='Rules not eligible for a recommendation: '+', '.join(quality)+'.'
    else:
        checks=[('EMA10 > EMA30',f['ema10']>f['ema30']),
                ('Close > prior 20-session high',bars[-1].close>f['breakout20']),
                ('Relative volume >= 1.5',f['relative_volume20']>=D('1.5'))]
        explanation='; '.join(label+': '+('met' if passed else 'not met') for label,passed in checks)+'.'
        if risk is not None and not risk['quantity']:
            explanation+=' No entry: sizing permits zero shares.'
    identity=next(i for i in dataset.instruments if i.instrument_id==instrument_id)
    run_id='SYN-RUN-'+hashlib.sha256(canonical([dataset.version,instrument_id,stamp(cutoff),STRATEGY_VERSION,CONFIG_VERSION,code_version]).encode()).hexdigest()[:32]
    evidence=[]
    if bars:
        p=bars[-1].provenance
        evidence=[{'evidence_id':'closed-bars','kind':'daily_ohlcv','source_ref':p.source_ref,'source_version':p.source_version,
            'locator':f'{instrument_id}:through:{stamp(bars[-1].ends_at)}','published_at':stamp(p.published_at),
            'available_at':stamp(p.available_at),'fetched_at':stamp(p.fetched_at),'availability_basis':p.availability_basis,
            'summary':f'{len(bars)} eligible fictional daily bars; raw prices; calendar quality gate applied'}]
    r={'recommendation_id':run_id.replace('RUN','REC'),'schema_version':'1.0.0','synthetic':True,'mode':'synthetic','run_id':run_id,
       'instrument':{'instrument_id':instrument_id,'symbol':instrument_id,'exchange':identity.exchange,'series':identity.series,
                     'isin':None,'currency':'INR','exchange_timezone':'Asia/Kolkata'},
       'strategy':{'id':'ema-volume-breakout','version':STRATEGY_VERSION,'config_version':CONFIG_VERSION},
       'horizon':{'profile':'swing','forecast_end_at':stamp(future[4].closes_at) if len(future)>=5 else None},
       'information_cutoff_at':stamp(cutoff),'generated_at':stamp(generated_at or datetime.now(timezone.utc)),
       'decision_available_at':stamp(ready),'earliest_executable_entry_at':stamp(future[0].opens_at) if action=='BUY' else None,
       'action':action,'position_effect':'OPEN_LONG' if action=='BUY' else 'NONE','holding':None,'execution':execution,'forecast':forecast,
       'evidence':evidence,'missing_evidence':[{'requirement':q,'reason':q,'blocking':True} for q in quality],
       'rationale':{'summary':explanation+' Decision: '+action,
                    'evidence_ids':['closed-bars'] if evidence else [],'contradictions':[],
                    'invalidation':'No entry before next session; cancel gap above cap or target; unsupported corporate-action windows excluded.'},
       'versions':{'dataset':dataset.version,'code':code_version,'model':None,'prompt':None},
       'risk_context':{'status':'synthetic_only','reason':'SYN-RISK-1 empty fictional portfolio; no live allocation approved'},
       'revises_id':None,'revision_reason':None}
    return {'recommendation':r,'indicators':f,'sizing':risk,'is_actionable':False,'label':dataset.label}
