"""Authenticated portfolio API. Fictional observations cannot feed forward books."""
from fastapi import APIRouter, Depends, Header, Query, Response
from .auth import require_auth
from .research import db
from .discovery import error
from stock_discovery_analysis.paper_contracts import PortfolioConfig, Admission, AdmissionBatch, Observation
from stock_discovery_analysis import paper_store as store
from stock_discovery_analysis.paper_reporting import report

router=APIRouter(prefix='/v1/paper-portfolio',dependencies=[Depends(require_auth)])


def call(fn,*args):
    try:return fn(*args)
    except KeyError as exc:raise error(404,str(exc.args[0]))
    except PermissionError:raise error(403,'source_permission_denied')
    except ValueError as exc:raise error(409,str(exc))


@router.post('',status_code=201)
def create(body:PortfolioConfig,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    return {'portfolio_id':call(store.create,conn,body,idempotency_key)}


@router.get('')
def portfolios(conn=Depends(db)):
    return {'portfolios':[dict(portfolio_id=pid,name=config['name'],mode=config['mode']) for pid,config in
        conn.execute('SELECT portfolio_id,config FROM paper.portfolios ORDER BY created_at DESC,portfolio_id LIMIT 100')]}


@router.get('/{pid}')
def overview(pid:str,conn=Depends(db)):
    return call(report,conn,pid)


@router.post('/{pid}/admissions')
def admission(pid:str,body:Admission,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    return call(store.admit,conn,pid,body.recommendation_id,idempotency_key)


@router.post('/{pid}/observations',status_code=202)
def observations(pid:str,body:Observation,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    return {'observation_id':call(store.enqueue,conn,pid,body,idempotency_key)}


@router.post('/{pid}/fictional-session',status_code=202)
def fictional_session(pid:str,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    return {'observation_id':call(store.demo_observation,conn,pid,idempotency_key)}


@router.get('/{pid}/outcomes/{rid}')
def outcome(pid:str,rid:str,response:Response,sequence:int|None=Query(default=None,ge=1),
            expected_hash:str|None=Query(default=None,pattern='^[0-9a-f]{64}$'),conn=Depends(db)):
    response.headers['Cache-Control']='no-store'
    if sequence is not None or expected_hash is not None:
        if sequence is None or expected_hash is None:raise error(400,'pinned_outcome_reference_required')
        from stock_discovery_analysis.discovery_history import recorded_outcome
        try:return recorded_outcome(conn,pid,rid,sequence,expected_hash)
        except KeyError:raise error(404,'outcome_not_found') from None
        except PermissionError:raise error(403,'source_permission_denied') from None
        except ValueError:raise error(409,'saved_evidence_inconsistent') from None
    data=call(report,conn,pid)
    order=next((o for o in data['decisions'] if o['recommendation_id']==rid),None)
    if order is None:raise error(404,'outcome_not_found')
    return dict(outcome=order,history=[e for e in data['ledger'] if e['payload'].get('recommendation_id')==rid or
        any(c['recommendation_id']==rid for c in e['payload'].get('changes',[]))],labels=data['labels'],limitations=data['limitations'])


@router.post('/{pid}/admissions/batch')
def admission_batch(pid:str,body:AdmissionBatch,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    return call(store.admit_batch,conn,pid,body.recommendation_ids,idempotency_key)
