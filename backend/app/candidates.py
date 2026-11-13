"""Authenticated candidates in the existing Research Workbench."""
from datetime import date
from fastapi import APIRouter, Depends, Response, Query, HTTPException
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.candidate_research import permitted_result
from .auth import require_auth
from .research import db
from .real_research import view_config

router=APIRouter(prefix='/v1/real-research/candidates',dependencies=[Depends(require_auth)])


@router.get('')
def candidates(response:Response,session:date|None=None,scanner:str|None=Query(None,max_length=64),
               limit:int=Query(100,ge=1,le=100),offset:int=Query(0,ge=0,le=5000000),conn=Depends(db)):
    response.headers['Cache-Control']='no-store'
    try:config=view_config()
    except HTTPException:config=None
    result=store.rows(conn,session=session,scanner_key=scanner,limit=limit,offset=offset)
    for row in result['rows']:
        row['research']=permitted_result(conn,config,row['research'])
        if row['research']:row['research_status']=row['research']['status']
    result['inbox']={s:n for s,n in conn.execute('SELECT status,count(*) FROM discovery.candidate_event_state GROUP BY status')}
    result['failed_events']=[dict(event_id=e,error_code=c) for e,c in conn.execute("SELECT event_id,error_code FROM discovery.candidate_event_state WHERE status='failed' LIMIT 20")]
    return result


@router.get('/swing-review')
def swing_review(response:Response,session:date|None=None,scanner:str|None=Query(None,max_length=64),
                 limit:int=Query(20,ge=1,le=20),offset:int=Query(0,ge=0,le=5000000),conn=Depends(db)):
    from stock_discovery_analysis.candidate_swing import page
    response.headers['Cache-Control']='no-store'
    try:config=view_config()
    except HTTPException:config=None
    return page(conn,config,store.rows(conn,session=session,scanner_key=scanner,limit=limit,offset=offset))


@router.post('/{candidate_id}/retry',status_code=202)
def retry(candidate_id:str,response:Response,conn=Depends(db)):
    response.headers['Cache-Control']='no-store'
    if not store.retry(conn,candidate_id):raise HTTPException(409,'Candidate unavailable or already pending')
    return dict(status='pending',acquisition='disabled')


@router.post('/events/{event_id}/retry',status_code=202)
def retry_event(event_id:str,response:Response,conn=Depends(db)):
    response.headers['Cache-Control']='no-store'
    if not store.retry_event(conn,event_id):raise HTTPException(409,'Event unavailable or not failed')
    return dict(status='pending')
