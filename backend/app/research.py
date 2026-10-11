import hmac
import os
from datetime import datetime,time,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel,Field
import psycopg
from .auth import require_auth,secret,session
from stock_discovery_analysis.dataset import demo_dataset,canonical
from stock_discovery_analysis.service import load_dataset,freeze,read_frozen,reveal,scorecard,json_value
from stock_discovery_analysis.jobs import enqueue

router=APIRouter(prefix='/api/v1')


def db():
    url=os.getenv('DATABASE_URL')
    if not url: raise HTTPException(503,'Database is not configured')
    try:
        with psycopg.connect(url,autocommit=True,connect_timeout=3) as conn: yield conn
    except psycopg.Error: raise HTTPException(503,'Database unavailable or migrations pending')


class Login(BaseModel): token: str=Field(max_length=512)
class Selection(BaseModel):
    dataset_version: str=Field(max_length=100)
    instrument_id: str=Field(max_length=80)
    date: str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$')


@router.post('/session')
def login(body: Login,response:Response):
    if not hmac.compare_digest(body.token.encode(),secret().encode()): raise HTTPException(401,'Invalid access key')
    response.set_cookie('stk_session',session(),httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','true')=='true',max_age=8*3600)
    return {'authenticated':True}


@router.get('/session',dependencies=[Depends(require_auth)])
def session_status(): return {'authenticated':True}


@router.delete('/session',dependencies=[Depends(require_auth)])
def logout(response:Response):
    response.delete_cookie('stk_session'); return {'authenticated':False}


@router.get('/dashboard',dependencies=[Depends(require_auth)])
def dashboard(conn=Depends(db)):
    datasets=[r[0] for r in conn.execute("SELECT manifest-'payload' FROM research.datasets ORDER BY created_at DESC")]
    rows=[r[0] for r in conn.execute('SELECT payload FROM research.decisions ORDER BY information_cutoff_at DESC,recommendation_id LIMIT 100')]
    jobs=[dict(zip(('job_id','kind','status','attempts','error_code','result'),r)) for r in conn.execute('SELECT job_id,kind,status,attempts,error_code,result FROM research.jobs ORDER BY created_at DESC LIMIT 20')]
    return {'datasets':datasets,'recommendations':rows,'jobs':jobs,'data_status':'synthetic_only','freshness':'Historical fictional fixtures; no live feed',
            'latest_analysis_date':max((r['information_cutoff_at'] for r in rows),default=None)}


@router.post('/initialize',dependencies=[Depends(require_auth)])
def initialize(conn=Depends(db)):
    return {'job_id':enqueue(conn,'ingest',{'fixture_version':'daily-demo-v1'})}


@router.get('/datasets/{version}',dependencies=[Depends(require_auth)])
def dataset_info(version:str,conn=Depends(db)):
    try: d=load_dataset(conn,version)
    except KeyError: raise HTTPException(404,'Dataset not found')
    return {'version':d.version,'instruments':[i.instrument_id for i in d.instruments],
            'dates':[s.closes_at.date().isoformat() for s in d.calendar.sessions],
            'default_date':d.calendar.sessions[39].closes_at.date().isoformat()}


def selection(body,conn):
    try:
        d=load_dataset(conn,body.dataset_version)
        day=datetime.strptime(body.date,'%Y-%m-%d').date()
    except (KeyError,ValueError): raise HTTPException(400,'Unknown dataset or invalid date')
    if body.instrument_id not in {i.instrument_id for i in d.instruments}: raise HTTPException(400,'Unknown synthetic instrument')
    s=next((s for s in d.calendar.sessions if s.closes_at.date()==day),None)
    if s is None: raise HTTPException(400,'Date is outside the pinned session calendar')
    return d,s.closes_at+timedelta(minutes=1)


@router.post('/analysis',dependencies=[Depends(require_auth)])
def analysis(body:Selection,conn=Depends(db)):
    d,cutoff=selection(body,conn)
    a=freeze(conn,d,body.instrument_id,cutoff,os.getenv('CODE_VERSION','local-unversioned'))
    return {**a,'candles':chart(d.asof(body.instrument_id,cutoff))}


def chart(bars):
    return [{'time':c.ends_at.date().isoformat(),**{k:float(getattr(c,k)) for k in ('open','high','low','close')}} for c in bars]


@router.get('/analysis/{rid}',dependencies=[Depends(require_auth)])
def frozen(rid:str,conn=Depends(db)):
    try: return read_frozen(conn,rid)
    except KeyError: raise HTTPException(404,'Recommendation not found')


@router.post('/analysis/{rid}/reveal',dependencies=[Depends(require_auth)])
def reveal_prices(rid:str,conn=Depends(db)):
    try:
        a=read_frozen(conn,rid); out=reveal(conn,rid)
        d=load_dataset(conn,a['recommendation']['versions']['dataset'])
    except KeyError: raise HTTPException(404,'Recommendation not found')
    return {**out,'candles':chart(d.asof(a['recommendation']['instrument']['instrument_id'],datetime.now(timezone.utc)))}


@router.post('/scan',dependencies=[Depends(require_auth)])
def scan(body:Selection,conn=Depends(db)):
    d,cutoff=selection(body,conn)
    return {'job_id':enqueue(conn,'scan',{'dataset_version':d.version,'cutoff':cutoff.isoformat()})}


@router.post('/replay-job',dependencies=[Depends(require_auth)])
def replay_job(body:Selection,conn=Depends(db)):
    d,cutoff=selection(body,conn)
    return {'job_id':enqueue(conn,'replay',{'dataset_version':d.version,'instrument_id':body.instrument_id,'cutoff':cutoff.isoformat()})}


@router.get('/scorecard',dependencies=[Depends(require_auth)])
def scores(conn=Depends(db)): return scorecard(conn)


class Batch(BaseModel):
    dataset_version: str=Field(max_length=100)
    dates: list[str]=Field(min_length=1,max_length=10)


@router.post('/experiments',dependencies=[Depends(require_auth)])
def experiments(body:Batch,conn=Depends(db)):
    try: d=load_dataset(conn,body.dataset_version)
    except KeyError: raise HTTPException(404,'Dataset not found')
    requests=[]
    for day in body.dates:
        for instrument in d.instruments:
            chosen=Selection(dataset_version=d.version,instrument_id=instrument.instrument_id,date=day)
            _,cutoff=selection(chosen,conn)
            requests.append({'dataset_version':d.version,'instrument_id':instrument.instrument_id,'cutoff':cutoff.isoformat()})
    with conn.transaction():
        jobs=[enqueue(conn,'replay',payload) for payload in requests]
    return {'job_ids':jobs,'label':'Synthetic software validation; failed outcomes retained'}


@router.get('/experiments/export',dependencies=[Depends(require_auth)])
def export(conn=Depends(db)):
    return {'label':'Synthetic research audit export','decisions':[r[0] for r in conn.execute('SELECT payload FROM research.decisions')],
            'outcomes':[r[0] for r in conn.execute('SELECT payload FROM research.trade_outcomes')],
            'runs':[r[0] for r in conn.execute('SELECT manifest FROM research.runs')],
            'scorecard':scorecard(conn)}
