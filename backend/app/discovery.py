"""Authenticated additive v2 discovery readers. Legacy /api/v1 is unchanged."""
import os
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from .auth import require_auth
from .research import db
from stock_discovery_analysis.publication_store import RunRequest, enqueue, run_status, read_artifact, require_sources, now
from stock_discovery_analysis.publication_fixtures import access_for
from stock_discovery_analysis.evidence_storage import read_evidence

router=APIRouter(prefix='/v1',dependencies=[Depends(require_auth)])
Profile=Literal['swing','short_term','long_term']
Cohort=Literal['quant','quant_rag','quant_agent']


def error(status,code):
    return HTTPException(status,dict(code=code,message=code.replace('_',' '),retryable=status==503))


def authorize(conn):
    access=access_for(conn,now)
    try:require_sources(access)
    except PermissionError:raise error(403,'source_permission_denied')
    return access


@router.post('/discovery-runs',status_code=202)
def create_run(body:RunRequest,idempotency_key:str=Header(min_length=1,max_length=128),conn=Depends(db)):
    try:rid=enqueue(conn,body,idempotency_key,os.getenv('CODE_VERSION','local-unversioned'))
    except ValueError:raise error(409,'idempotency_conflict')
    return dict(run_id=rid,status_url='/v1/runs/'+rid)


@router.get('/runs/{rid}')
def status(rid:str,conn=Depends(db)):
    try:return run_status(conn,rid)
    except KeyError:raise error(404,'run_not_found')


@router.get('/discovery')
@router.get('/recommendations')
def discovery(horizon:Profile='swing',cohort:Cohort='quant',mode:Literal['synthetic']='synthetic',
              cursor:str|None=None,batch_id:str|None=None,limit:int=Query(default=20,ge=1,le=100),conn=Depends(db)):
    if cursor and not batch_id:raise error(400,'cursor_requires_batch_id')
    authorize(conn)
    latest=conn.execute("SELECT run_id FROM discovery.publication_runs WHERE request->>'horizon'=%s AND request->>'mode'='synthetic' ORDER BY created_at DESC,run_id DESC LIMIT 1",(horizon,)).fetchone()
    row=conn.execute('''SELECT payload FROM discovery.publication_batches WHERE horizon=%s AND mode=%s
        AND (%s::text IS NULL OR run_id=%s) ORDER BY published_at DESC,run_id DESC LIMIT 1''',(horizon,mode,batch_id,batch_id)).fetchone()
    current=run_status(conn,latest[0]) if latest else None
    if not row:
        if batch_id:raise error(404,'batch_not_found')
        return dict(status='failed' if current and current['status']=='failed' else 'not_run',recommendations=[],coverage=None,latest_run=current,
                    next_cursor=None,batch_id=None,labels=['MOCK','SHADOW','NON-ACTIONABLE'])
    batch=row[0]
    # Immutable batch ID pins subsequent pages even if another run publishes.
    rows=conn.execute('''SELECT recommendation_id,sort_key FROM discovery.recommendations WHERE run_id=%s AND cohort=%s
        AND (%s::text IS NULL OR sort_key>%s) ORDER BY sort_key LIMIT %s''',
        (batch['run_id'],cohort,cursor,cursor,limit+1)).fetchall()
    artifacts=[read_artifact(conn,r[0]) for r in rows[:limit]]
    recs=[a['recommendation'] for a in artifacts]
    return {**batch,'batch_id':batch['run_id'],'coverage':batch['coverage'][cohort],'recommendations':recs,'latest_run':current,
        'rankings':{a['recommendation']['recommendation_id']:a['ranking'] for a in artifacts},
        'next_cursor':rows[limit-1][1] if len(rows)>limit else None,
        'empty_reason':'no_qualifying_picks' if not recs and cursor is None else None}


@router.get('/recommendations/{rid}')
def recommendation(rid:str,conn=Depends(db)):
    try:return read_artifact(conn,rid)
    except KeyError:raise error(404,'recommendation_not_found')
    except PermissionError:raise error(403,'source_permission_denied')


@router.get('/recommendations/{rid}/comparisons')
def comparisons(rid:str,response:Response,compare_to:list[str]=Query(default=[],max_length=3),conn=Depends(db)):
    response.headers['Cache-Control']='no-store'
    a=recommendation(rid,conn);r=a['recommendation']
    if compare_to:
        ids=[rid,*compare_to]
        if len(set(ids))!=len(ids):raise error(400,'duplicate_comparison_id')
        artifacts=[a,*[recommendation(other,conn) for other in compare_to]]
        def scope(item):
            rec=item['recommendation']
            return (rec['run_id'],rec['mode'],rec['horizon']['profile'],rec['information_cutoff_at'],rec['cohort']['arm'])
        if r['mode']!='synthetic' or any(scope(item)!=scope(a) for item in artifacts):
            raise error(400,'comparison_scope_mismatch')
        # Never merge separate runs, horizons or research arms into one ranking.
        # Return only the existing frozen research fields, without future outcomes.
        artifacts.sort(key=lambda item:(item['ranking']['action_tier'],-int(item['ranking']['quant_score']),item['ranking']['listing_id']))
        return dict(items=[dict(recommendation=item['recommendation'],ranking=item['ranking'],
            metrics=item['quantitative']['metrics']) for item in artifacts],
            batch_id=r['run_id'],labels=['MOCK','SHADOW','NON-ACTIONABLE'],
            note='Frozen fictional research priority, not expected return or AI performance. No admission or execution authorization.')
    rows=conn.execute('SELECT recommendation_id FROM discovery.recommendations WHERE run_id=%s AND listing_id=%s ORDER BY cohort',
        (r['run_id'],r['instrument']['instrument_id'])).fetchall()
    return dict(recommendations=[recommendation(row[0],conn)['recommendation'] for row in rows],
                note='Same listing, horizon, cutoff and quantitative baseline; research modes remain distinct.')


@router.get('/recommendations/{rid}/evidence')
def recommendation_evidence(rid:str,conn=Depends(db)):
    a=recommendation(rid,conn)
    return dict(evidence=a['recommendation']['evidence'],citations=a['citations'],permissions=a['permissions'])


@router.get('/recommendations/{rid}/history')
def history(rid:str,response:Response,before:str|None=Query(default=None,max_length=200),limit:int=Query(default=20,ge=1,le=50),conn=Depends(db)):
    from stock_discovery_analysis.discovery_history import related_history
    response.headers['Cache-Control']='no-store'
    try:return related_history(conn,rid,before=before,limit=limit)
    except KeyError:raise error(404,'saved_evidence_not_found') from None
    except PermissionError:raise error(403,'source_permission_denied') from None
    except ValueError:raise error(409,'saved_evidence_inconsistent') from None


@router.get('/evidence/{revision_id}')
def evidence(revision_id:str,recommendation_id:str,conn=Depends(db)):
    a=recommendation(recommendation_id,conn)
    permitted=(a['research_bundle'] or {}).get('documents',[])
    if revision_id not in permitted:raise error(404,'evidence_not_in_recommendation')
    try:
        if a['recommendation']['mode']=='live_paper':
            from stock_discovery_analysis.real_publication import configured_access
            access=configured_access()
        else:access=authorize(conn)
        return read_evidence(conn,revision_id,access=access,cutoff=a['recommendation']['information_cutoff_at'],mode=a['recommendation']['mode'])
    except PermissionError:raise error(403,'source_permission_denied')


@router.get('/coverage')
def coverage(horizon:Profile='swing',cohort:Cohort='quant',conn=Depends(db)):
    result=discovery(horizon=horizon,cohort=cohort,mode='synthetic',cursor=None,batch_id=None,limit=1,conn=conn)
    return {k:v for k,v in result.items() if k not in ('recommendations','next_cursor')}
