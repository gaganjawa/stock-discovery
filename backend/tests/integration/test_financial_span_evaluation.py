"""Scripted pipeline regressions; actual inference is a separate development run."""
import json
from unittest.mock import patch
from pathlib import Path
import psycopg
import pytest
from test_rag_research import isolated_url as _isolated_url
from stock_discovery_analysis.rag_research import MockResearchProvider
from worker.financial_span_evaluation import cases,run_case,BUDGET


@pytest.fixture
def isolated_url():yield from _isolated_url.__wrapped__()


def data():
    root=Path(__file__).resolve().parents[3]/'docs/research-quality/sources'
    source=json.loads((root/'sec-infy-2025-revenue-excerpt.json').read_text())
    return source,cases((root/'sec-infy-2025-revenue-excerpt.txt').read_text(),source['profile'])


class Model(MockResearchProvider):
    calls=0
    def assess(self,request,**kw):
        self.calls+=1;b=json.loads(request)['bundle'];source,rows=data()
        row=next(c for c in rows if c['period']==b['period'] and c['text']==b['source_text'])
        if row['expected'] is None:return json.dumps(dict(status='insufficient_evidence',**dict.fromkeys(['value','unit','scope','period','evidence_id','quote'])))
        return json.dumps(dict(status='extracted',**{k:row['expected'][k] for k in ['value','unit','scope','period','evidence_id','quote']}))


def test_durable_cases_cache_and_no_inference_on_future_source(isolated_url):
    source,rows=data();model=Model()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        results=[run_case(db,c,source=source,cutoff=source['captured_at'],provider=model) for c in rows]
        assert [r['accepted'] for r in results]==[True,True,False,False]
        assert not any(r['error'] for r in results)
        assert model.calls==4
        assert run_case(db,rows[0],source=source,cutoff=source['captured_at'],provider=model)==results[0]
        assert model.calls==4 and db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(4,)
        with pytest.raises(ValueError,match='not_observed'):run_case(db,rows[0],source=source,cutoff='2000-01-01T00:00:00Z',provider=model)
        assert model.calls==4


def test_budget_exhaustion_is_not_reset(isolated_url):
    source,rows=data();model=Model();b=BUDGET.model_copy(update={'account':'SYN-limited-span','max_day_units':20000,'max_month_units':20000})
    with psycopg.connect(isolated_url,autocommit=True) as db:
        run_case(db,rows[0],source=source,cutoff=source['captured_at'],provider=model,budget=b)
        with pytest.raises(ValueError,match='budget exhausted'):run_case(db,rows[1],source=source,cutoff=source['captured_at'],provider=model,budget=b)
        assert model.calls==1 and db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(1,)


def test_changed_gold_or_source_profile_cannot_become_authority(isolated_url):
    source,rows=data();model=Model();bad={**rows[0],'expected':{**rows[0]['expected'],'value':'999'}}
    with psycopg.connect(isolated_url,autocommit=True) as db:
        with pytest.raises(ValueError,match='reference_changed'):run_case(db,bad,source=source,cutoff=source['captured_at'],provider=model)
        bad={**rows[0],'profile':{**rows[0]['profile'],'unit':'USD'}}
        with pytest.raises(ValueError,match='profile_changed'):run_case(db,bad,source=source,cutoff=source['captured_at'],provider=model)
        assert model.calls==0 and db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(0,)


def test_ambiguous_prior_receipt_never_repeats_inference(isolated_url):
    source,rows=data();model=Model()
    # Persist a reservation, then inject a crash before the result INSERT.
    from worker.financial_span_evaluation import Proposal
    with psycopg.connect(isolated_url,autocommit=True) as db:
        with patch.object(Proposal,'model_validate_json',side_effect=OSError('synthetic crash')):
            with pytest.raises(OSError):
                run_case(db,rows[0],source=source,cutoff=source['captured_at'],provider=model)
        before=model.calls
        with pytest.raises(ValueError,match='ambiguous_evaluation_reservation_no_retry'):
            run_case(db,rows[0],source=source,cutoff=source['captured_at'],provider=model)
        assert model.calls==before
        assert db.execute('SELECT count(*) FROM discovery.rag_reservations').fetchone()==(1,)
        assert db.execute('SELECT count(*) FROM discovery.rag_results').fetchone()==(0,)
    with psycopg.connect(isolated_url) as db:
        with pytest.raises(ValueError,match='requires_idle_autocommit'):
            run_case(db,rows[1],source=source,cutoff=source['captured_at'],provider=model)
        assert model.calls==before


def test_noncanonical_numeric_output_is_not_counted_as_verified(isolated_url):
    class CommaModel(Model):
        def assess(self,*args,**kwargs):
            result=json.loads(super().assess(*args,**kwargs));result['value']='162,990'
            return json.dumps(result)
    source,rows=data()
    with psycopg.connect(isolated_url,autocommit=True) as db:
        result=run_case(db,rows[0],source=source,cutoff=source['captured_at'],provider=CommaModel())
        assert not result['accepted'] and result['error']=='ValueError'
