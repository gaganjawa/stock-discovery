import os
import pytest
import psycopg
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.storage import ingest

URL=os.getenv('STK_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='requires disposable migrated database')


def test_ingestion_is_idempotent_and_pins_manifest():
    assert URL.rsplit('/',1)[-1]=='stk013_test'
    d=demo_dataset()
    with psycopg.connect(URL,autocommit=True) as db:
        version=ingest(db,d,page_size=50)
        assert ingest(db,d,page_size=50)==version
        assert db.execute("SELECT count(*) FROM research.candles WHERE source_ref='fixture:daily-demo'").fetchone()[0]==300
        manifest=db.execute('SELECT manifest FROM research.datasets WHERE dataset_version=%s',(version,)).fetchone()[0]
        assert manifest['candle_count']==300
        assert len(manifest['payload']['mappings'])==3
        with pytest.raises(psycopg.errors.CheckViolation),db.transaction():
            db.execute('UPDATE research.datasets SET manifest=manifest')
        with pytest.raises(ValueError): ingest(db,d,page_size=100)
