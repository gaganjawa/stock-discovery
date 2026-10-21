"""Disposable database contract acceptance only; all provider values are fabricated.

These artificial active grants are test fixtures, not provider permission evidence.
"""
import json
import psycopg
from types import SimpleNamespace
from test_rag_research import isolated_url
from worker.real_market import MarketConfig,ingest_prices,handlers
from worker.providers.upstox import observed_revision,RevisionPages
from stock_discovery_analysis.revisions import SessionData,CandleData
from stock_discovery_analysis.revision_storage import Stream,ingest_next
from stock_discovery_contracts.rights import Grant,UseRequest
from stock_discovery_contracts.v2 import digest
import pytest

NOW='2026-10-19T12:00:00Z'


def grant():
    return Grant(schema_version='1.0.0',grant_id='test-only-upstox',version='1',source_id='upstox',account_ref='test',
        status='active',synthetic=False,approval_evidence_ref='TEST FIXTURE ONLY - NOT PROVIDER PERMISSION',
        valid_from_at='2026-01-01T00:00:00Z',expires_at='2027-01-01T00:00:00Z',revoked_at=None,
        allowed_uses=('acquire','store','derive'),scopes=('prices','universe','calendar'),regions=('IN',),
        external_processors=(),retention_days=365,deletion_deadline_days=0,attribution='Test only',
        max_units_per_operation=100,audit_tombstones_permitted=True)


def test_adjusted_full_window_ingestion_and_revocation(isolated_url,tmp_path):
    g=grant(); gf=tmp_path/'grants.json';gf.write_text(json.dumps([g.model_dump()]))
    tf=tmp_path/'token';tf.write_text('test-token-not-real')
    config=MarketConfig(account_ref='test',grant_file=str(gf),token_file=str(tf),retention_days=365)
    calls=[]
    class Provider:
        def __init__(self,**kw):self.access=kw['access']
        def close(self):pass
        def instruments(self,stream,symbols):
            return [dict(symbol='INFY',name='Test Infosys identity',isin='INE009A01021',instrument_key='NSE_EQ|INE009A01021',lot_size=1,tick_size='0.05')]
        def candles(self,stream,instrument,start,end,sessions):
            calls.append((start,end))
            return ((CandleData(kind='candle',interval='1d',starts_at='2026-10-16T03:45:00Z',ends_at='2026-10-16T10:00:00Z',
                open='100',high='110',low='90',close='105',volume=100,adjustment_basis='split_bonus_adjusted'),self.access.clock()),)
    with psycopg.connect(isolated_url,autocommit=True) as conn:
        session=observed_revision(SessionData(kind='session',calendar_version='test-calendar',opens_at='2026-10-16T03:45:00Z',closes_at='2026-10-16T10:00:00Z'),listing='NSE',fetched=NOW)
        stream=Stream(stream_id='test-real-calendar',source_id='upstox',account_ref='test',scope='calendar')
        request=UseRequest(source_id='upstox',account_ref='test',scope='calendar',uses=('acquire','store'),region='IN',destination_region=None,processor_ref=None,requested_at=NOW,synthetic=False,units=100,retention_days=365,attribution_present=True)
        ingest_next(conn,stream,RevisionPages((session,)),load_grant=lambda:g,request=request,audit=lambda d:None,clock=lambda:NOW)
        first=ingest_prices(conn,config,clock=lambda:NOW,adapter_factory=Provider)
        assert first['status']=='ingested' and first['instruments'][0]['candles']==1
        assert first['research_status']=='not_run' and first['actionable'] is False
        second=ingest_prices(conn,config,clock=lambda:'2026-10-20T12:00:00Z',adapter_factory=Provider)
        assert calls[-1]==calls[0]  # Full window, not a seven-day overlap.
        assert conn.execute("SELECT count(*) FROM discovery.revisions WHERE kind='candle' AND source_id='upstox'").fetchone()[0]==2
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()[0]==0
        gf.write_text('[]')
        with pytest.raises(PermissionError,match='grant_missing'):
            ingest_prices(conn,config,clock=lambda:NOW,adapter_factory=Provider)


def test_scheduler_rejects_mode_and_configuration_drift(tmp_path):
    config=MarketConfig(account_ref='test',grant_file='/missing',token_file='/missing',retention_days=1)
    with pytest.raises(ValueError,match='live_paper'):handlers(SimpleNamespace(mode='synthetic'),config)
    with pytest.raises(ValueError,match='hash_mismatch'):handlers(SimpleNamespace(mode='live_paper',input_hash='x'),config)
    installed=handlers(SimpleNamespace(mode='live_paper',input_hash=digest(config.model_dump(mode='json'))),config)
    from stock_discovery_analysis.schedule_runner import JobFailure
    with pytest.raises(JobFailure):installed['snapshot'](None,None,None)
