"""PostgreSQL persistence; explicit migrations and no provider access."""
from dataclasses import asdict
import hashlib
import json
import time
from psycopg.types.json import Jsonb
from .dataset import Dataset, canonical


def ingest(conn, dataset: Dataset, *, page_size: int = 100, page_delay: float = 0) -> str:
    """Commit each page with its checkpoint; retry resumes committed pages.

    Caller supplies an idle connection. Each page is independently atomic.
    Source calls belong to adapters; this importer accepts validated fixtures only.
    """
    if not 1<=page_size<=10000 or page_delay<0: raise ValueError('invalid ingestion limits')
    version=dataset.version
    with conn.transaction():
        existing=conn.execute('SELECT manifest FROM research.datasets WHERE dataset_version=%s',(version,)).fetchone()
        if existing:
            if existing[0]!=json.loads(canonical(dataset.manifest())): raise ValueError('dataset version collision')
            return version
    with conn.transaction():
        for inst in dataset.instruments:
            values=(inst.instrument_id,inst.isin,inst.exchange,inst.series,inst.synthetic)
            conn.execute('''INSERT INTO research.instruments(instrument_id,isin,exchange,series,synthetic)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',values)
            row=conn.execute('SELECT instrument_id,isin,exchange,series,synthetic FROM research.instruments WHERE instrument_id=%s',(inst.instrument_id,)).fetchone()
            if row != values: raise ValueError('instrument identity conflict')
    for offset in range(0,len(dataset.candles),page_size):
        page=dataset.candles[offset:offset+page_size]
        digest=hashlib.sha256(canonical([asdict(c) for c in page]).encode()).hexdigest()
        with conn.transaction():
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(version,))
            previous=conn.execute('SELECT digest FROM research.ingestion_pages WHERE dataset_version=%s AND page_number=%s',(version,offset)).fetchone()
            if previous:
                if previous[0]!=digest: raise ValueError('changed ingestion page size/content')
                continue
            for c in page:
                p=c.provenance
                cid=hashlib.sha256(canonical(asdict(c)).encode()).hexdigest()
                values=(cid,c.instrument_id,p.source_ref,p.source_version,'1d',c.starts_at,c.ends_at,
                        p.available_at,p.fetched_at,p.availability_basis,'raw',c.adjustment_version,
                        c.open,c.high,c.low,c.close,c.volume)
                conn.execute('INSERT INTO research.candles VALUES ('+','.join(['%s']*17)+') ON CONFLICT DO NOTHING',values)
                actual=conn.execute('SELECT * FROM research.candles WHERE candle_id=%s',(cid,)).fetchone()
                if actual!=values: raise ValueError('candle identity collision or changed source revision')
            conn.execute('INSERT INTO research.ingestion_pages(dataset_version,page_number,digest) VALUES (%s,%s,%s)',(version,offset,digest))
        if page_delay: time.sleep(page_delay)
    with conn.transaction():
        manifest=json.loads(canonical(dataset.manifest()))
        conn.execute('INSERT INTO research.datasets(dataset_version,manifest) VALUES (%s,%s) ON CONFLICT DO NOTHING',(version,Jsonb(manifest)))
        if conn.execute('SELECT manifest FROM research.datasets WHERE dataset_version=%s',(version,)).fetchone()[0]!=manifest:
            raise ValueError('dataset version collision')
    return version
