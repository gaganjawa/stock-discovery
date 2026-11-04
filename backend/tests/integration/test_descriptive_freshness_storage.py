"""STK-082 guarded disposable PostgreSQL acceptance; fabricated evidence only."""
import json,uuid,os
from pathlib import Path
import psycopg
import pytest
from test_adjusted_research_storage import setup,isolated_url,NOW
from test_real_market import grant
from stock_discovery_analysis.real_views import company
from stock_discovery_analysis.grant_fences import restrict
pytestmark=pytest.mark.skipif(not os.getenv('STK_TEST_DATABASE_URL'),reason='requires disposable PostgreSQL')

@pytest.mark.parametrize('lag,policy,mixed,missing,available',[(0,'strict',False,False,True),(1,'one_trailing_session_v1',False,False,True),(2,'one_trailing_session_v1',False,False,False),(1,'strict',False,False,False),(1,'one_trailing_session_v1',True,False,False),(1,'one_trailing_session_v1',False,True,False)])
def test_guarded_delayed_chart(isolated_url,tmp_path,lag,policy,mixed,missing,available):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        config,listing=setup(c,tmp_path,lag=lag,mixed=mixed,missing=missing)
        config=config.model_copy(update={'descriptive_freshness_policy':policy})
        before=c.execute('select revision_id,payload from discovery.revisions order by revision_id').fetchall()
        d=company(c,config,listing,clock=lambda:NOW);r=d['adjusted_research']
        assert (r['status']=='AVAILABLE_DESCRIPTIVE_ONLY')==available
        assert bool(d['price_series'])==available
        assert d['market_readiness']['latest_session_present']==(lag==0)
        assert d['market_readiness']['descriptive_freshness']==r['freshness']
        assert not r['paper_admission_authorized'] and not r['execution_qualified'] and not d['actionable']
        assert not d['recommendations'] and d['paper_position_status']=='not_created'
        assert all(q['action']=='INSUFFICIENT_EVIDENCE' for q in d['quantitative'].values())
        assert before==c.execute('select revision_id,payload from discovery.revisions order by revision_id').fetchall()

@pytest.mark.parametrize('denial',['missing','expired','revoked','fenced','retention'])
def test_delay_never_bypasses_authorization(isolated_url,tmp_path,denial):
    with psycopg.connect(isolated_url,autocommit=True) as c:
        config,listing=setup(c,tmp_path,lag=1)
        config=config.model_copy(update={'descriptive_freshness_policy':'one_trailing_session_v1'})
        if denial=='fenced':restrict(c,request_id=uuid.uuid4(),kind='provider',source_id='upstox',reason='revoked')
        elif denial=='retention':config=config.model_copy(update={'sources':config.sources.model_copy(update={'retention_days':366})})
        else:
            g=grant().model_dump(mode='json')
            if denial=='expired':g['expires_at']='2026-10-18T00:00:00Z'
            if denial=='revoked':g.update(status='revoked',revoked_at=NOW)
            Path(config.sources.grant_file).write_text(json.dumps([] if denial=='missing' else [g]))
        with pytest.raises(PermissionError):company(c,config,listing,clock=lambda:NOW)
