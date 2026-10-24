"""Owner-authenticated experiment governance; no model or broker calls."""
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Header,Query
from stock_discovery_contracts.v2 import Strict,Text
from stock_discovery_analysis import governance as store
from stock_discovery_analysis.governance_contracts import Experiment,Trial
from .auth import require_auth
from .research import db

router=APIRouter(prefix='/v1/experiments',dependencies=[Depends(require_auth)])


def invoke(fn,*args):
    try:return fn(*args)
    except KeyError:raise HTTPException(404,'Experiment or trial not found') from None
    except PermissionError:raise HTTPException(403,'Source permission denied') from None
    except ValueError as exc:raise HTTPException(409,dict(code=store.safe_error(exc),message='Experiment validation failed',retryable=False)) from None


@router.post('')
def register(body:Experiment,key:str=Header(alias='Idempotency-Key'),conn=Depends(db)):
    if key!=body.experiment_id:raise HTTPException(409,'idempotency_key_must_equal_experiment_id')
    return invoke(store.register,conn,body)


@router.get('')
def listing(cursor:str|None=None,limit:int=Query(default=100,ge=1,le=100),conn=Depends(db)):
    params=[];where=''
    if cursor:
        point=conn.execute('SELECT registered_at,experiment_id FROM discovery.experiments WHERE experiment_id=%s',(cursor,)).fetchone()
        if not point:raise HTTPException(404,'Experiment cursor not found')
        where=' WHERE (registered_at,experiment_id)<(%s,%s)';params.extend(point)
    rows=conn.execute("SELECT experiment_id,manifest_hash,registered_at,manifest->>'horizon',manifest->>'comparison' FROM discovery.experiments"+where+" ORDER BY registered_at DESC,experiment_id DESC LIMIT %s",(*params,limit+1)).fetchall()
    return dict(experiments=[dict(experiment_id=r[0],manifest_hash=r[1],registered_at=r[2].isoformat(),horizon=r[3],comparison=r[4]) for r in rows[:limit]],
        next_cursor=rows[limit-1][0] if len(rows)>limit else None,q_ml_enabled=False)


@router.get('/{eid}')
def detail(eid:str,conn=Depends(db)):
    e,a=invoke(store.load,conn,eid)
    trials=[dict(trial_id=r[0],request=r[1],result=invoke(store.authorize_result,conn,r[2]) if r[2] else None) for r in conn.execute('SELECT t.trial_id,t.request,r.payload FROM discovery.experiment_trials t LEFT JOIN discovery.experiment_results r USING(trial_id) WHERE experiment_id=%s ORDER BY registered_at,trial_id',(eid,)).fetchall()]
    return dict(manifest=e.model_dump(mode='json'),split_audit=a,promotion=invoke(store.promotion,conn,eid),
        history=[dict(sequence=r[0],kind=r[1],payload=r[2],at=r[3].isoformat()) for r in conn.execute('SELECT sequence,kind,payload,recorded_at FROM discovery.experiment_events WHERE experiment_id=%s ORDER BY sequence',(eid,)).fetchall()],
        trials=trials)


@router.post('/{eid}/trials')
def trial(eid:str,body:Trial,key:str=Header(alias='Idempotency-Key'),conn=Depends(db)):
    if key!=body.trial_id:raise HTTPException(409,'idempotency_key_must_equal_trial_id')
    if body.experiment_id!=eid:raise HTTPException(409,'experiment_id_mismatch')
    return invoke(store.begin_trial,conn,body)


@router.post('/{eid}/trials/{tid}/evaluate')
def evaluate(eid:str,tid:str,key:str=Header(alias='Idempotency-Key'),conn=Depends(db)):
    if key!=tid:raise HTTPException(409,'idempotency_key_must_equal_trial_id')
    row=conn.execute('SELECT experiment_id FROM discovery.experiment_trials WHERE trial_id=%s',(tid,)).fetchone()
    if not row or row[0]!=eid:raise HTTPException(404,'Trial not found')
    return invoke(store.evaluate,conn,tid)


class Control(Strict):
    action: Literal['pause','rollback','request_promotion']
    reason: Text
    target: Text | None = None


@router.post('/{eid}/controls')
def control(eid:str,body:Control,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=200),conn=Depends(db)):
    return invoke(store.control,conn,eid,body.action,body.reason,body.target,key)
