import os
from datetime import timedelta
import pytest
import psycopg
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest
from stock_discovery_analysis.service import freeze,read_frozen,load_dataset,reveal,scorecard
URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated database')


def test_freeze_before_reveal_and_restart_roundtrip():
    assert URL.rsplit('/',1)[-1]=='stk013_test'
    d=demo_dataset(); cutoff=d.calendar.sessions[39].closes_at+timedelta(minutes=1)
    with psycopg.connect(URL,autocommit=True) as db:
        ingest(db,d,page_size=50)
        a=freeze(db,d,'SYN-ALPHA',cutoff,'test')
        assert freeze(db,d,'SYN-ALPHA',cutoff,'test')==a
        assert 'trade' not in a and 'outcome' not in a
    with psycopg.connect(URL,autocommit=True) as db:
        rid=a['recommendation']['recommendation_id']
        assert load_dataset(db,d.version)==d
        assert read_frozen(db,rid)==a
        out=reveal(db,rid)
        assert reveal(db,rid)==out
        assert read_frozen(db,rid)==a
        assert scorecard(db)['action_counts']['BUY']>=1
