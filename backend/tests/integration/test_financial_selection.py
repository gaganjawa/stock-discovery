import json
import psycopg
import pytest
from test_financial_span_evaluation import isolated_url as _isolated_url,data
from stock_discovery_analysis.rag_research import MockResearchProvider
from worker.financial_span_evaluation import BUDGET
from worker.financial_selection import run

@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()

class Selector(MockResearchProvider):
    calls=0
    def assess(self,request,**kwargs):
        self.calls+=1;b=json.loads(request)['bundle']
        matches=[c['cell_id'] for c in b['cells'] if c['row_label']==b['requested_row'] and c['period']==b['requested_period']]
        return json.dumps({'cell_id':matches[0] if len(matches)==1 else 'ABSTAIN'})


def test_hybrid_durable_results_and_cache(isolated_url):
    source,cases=data();p=Selector()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        results=[run(db,c,source=source,cutoff=source['captured_at'],provider=p,budget=BUDGET,selection_mode='model') for c in cases]
        assert [r['accepted'] for r in results]==[True,True,False,False]
        assert all(r['contract_valid'] and not r['error'] for r in results)
        assert all(json.loads(r['raw_response'])['cell_id']=='ABSTAIN' for r in results[2:])
        assert run(db,cases[0],source=source,cutoff=source['captured_at'],provider=p,budget=BUDGET,selection_mode='model')==results[0]
        assert p.calls==4 and db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(4,)
        with pytest.raises(ValueError,match='temporal'):run(db,cases[0],source=source,cutoff='2000-01-01T00:00:00Z',provider=p,budget=BUDGET,selection_mode='model')
        assert p.calls==4


def test_failed_call_is_retained_without_refund(isolated_url):
    class Failed(Selector):
        def assess(self,*a,**kw):self.calls+=1;raise RuntimeError('synthetic runtime failure')
    source,cases=data();p=Failed()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        r=run(db,cases[0],source=source,cutoff=source['captured_at'],provider=p,budget=BUDGET,selection_mode='model')
        assert r['error']=='RuntimeError' and not r['accepted']
        assert run(db,cases[0],source=source,cutoff=source['captured_at'],provider=p,budget=BUDGET,selection_mode='model')==r and p.calls==1
        assert db.execute('SELECT sum(units) FROM discovery.rag_reservations').fetchone()==(20000,)


def test_wrong_selection_is_rejection_not_model_abstention(isolated_url):
    class Wrong(Selector):
        def assess(self,request,**kwargs):
            self.calls+=1;b=json.loads(request)['bundle']
            return json.dumps({'cell_id':b['cells'][0]['cell_id']})
    source,cases=data();p=Wrong()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        for case in cases[2:]:
            r=run(db,case,source=source,cutoff=source['captured_at'],provider=p,budget=BUDGET,selection_mode='model')
            assert r['contract_valid'] and r['error']=='ValueError'
            assert not r['accepted'] and r['proposal'] is None
        assert db.execute('SELECT count(*),sum(units) FROM discovery.rag_reservations').fetchone()==(2,40000)


def test_default_exact_route_no_model_reservation_or_database_mutation(isolated_url):
    class Never(Selector):
        def assess(self,*args,**kwargs):raise AssertionError('exact lookup must not infer')
    source,cases=data()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        results=[run(db,c,source=source,cutoff=source['captured_at'],provider=Never(),budget=BUDGET) for c in cases]
        assert [r['accepted'] for r in results]==[True,True,False,False]
        assert all(r['model_calls']==0 and r['model'] is None and r['reserved_units']==0 for r in results)
        changed={**cases[0],'expected':{'value':'wrong developer label'}}
        assert run(db,changed,source=source,cutoff=source['captured_at'])==results[0]
        assert db.execute('SELECT count(*) FROM discovery.rag_results').fetchone()==(0,)
        assert db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(0,)
        with pytest.raises(ValueError,match='temporal'):run(db,cases[0],source=source,cutoff='2000-01-01T00:00:00Z')
        bad={**cases[0],'profile':{**cases[0]['profile'],'scope':'standalone'}}
        with pytest.raises(ValueError,match='profile_changed'):run(db,bad,source=source,cutoff=source['captured_at'])


def test_exact_concurrent_reuse_preserves_prior_model_accounting(isolated_url):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    source,cases=data();barrier=Barrier(2)
    with psycopg.connect(isolated_url,autocommit=True) as db:
        prior=run(db,cases[0],source=source,cutoff=source['captured_at'],provider=Selector(),budget=BUDGET,selection_mode='model')
    def invoke():
        with psycopg.connect(isolated_url,autocommit=True) as db:
            barrier.wait(timeout=10)
            return run(db,cases[0],source=source,cutoff=source['captured_at'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(invoke);b=pool.submit(invoke);assert a.result(timeout=20)==b.result(timeout=20)
    with psycopg.connect(isolated_url,autocommit=True) as db:
        assert db.execute('SELECT count(*),sum(units) FROM discovery.rag_reservations').fetchone()==(1,20000)
        assert db.execute('SELECT count(*) FROM discovery.rag_results').fetchone()==(1,)
        assert db.execute('SELECT payload FROM discovery.rag_results WHERE run_id=%s',('M2-HYBRID-'+prior['request_hash'],)).fetchone()[0]==prior
