"""STK-014/074/079: rehearse the retained REAL 0013 -> 0015 recovery on invented rows only."""
import json
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg.types.json import Jsonb

from test_migration_reconciliation import migration_database as _migration_database, snapshot, ROOT, URL, legacy_0013_config
from test_adjusted_research_storage import EARLIER
from test_real_market import grant, NOW
from stock_discovery_analysis.real_views import company, ViewConfig
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.revisions import InstrumentData, SessionData, CandleData
from stock_discovery_analysis.revision_storage import wire
from stock_discovery_contracts.v2 import digest
from worker.providers.upstox import observed_revision, RevisionPages

pytestmark = pytest.mark.skipif(not URL, reason='requires disposable PostgreSQL')
LISTING = 'NSE:INE009A01021'


@pytest.fixture
def migration_database(monkeypatch):
    yield from _migration_database.__wrapped__(monkeypatch)


def legacy_0013(tmp_path):
    old = legacy_0013_config(tmp_path)
    command.upgrade(old, 'head')


def seed_stream(conn, g, stream_id, scope, records):
    """Mirror pre-0015 ingestion: pages and revisions exist, no page attribution rows."""
    conn.execute('INSERT INTO discovery.grants VALUES (%s,%s,%s) ON CONFLICT DO NOTHING', (g.grant_id, g.version, Jsonb(wire(g))))
    conn.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES (%s,%s,%s,%s)', (stream_id, 'upstox', 'test', scope))
    adapter, cursor = RevisionPages(tuple(records)), None
    while True:
        page = adapter.fetch(cursor, 100)
        for raw in page.records:
            r = records[[x.revision_id for x in records].index(raw['revision_id'])]
            conn.execute('INSERT INTO discovery.revisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (r.revision_id, stream_id, r.source_id, r.source_revision, r.logical_key, r.sequence, r.data.kind, r.listing_id,
                 r.available_at, g.grant_id, g.version, r.instrument_revision_id, r.supersedes_id, r.content_hash, Jsonb(wire(r))))
            conn.execute('INSERT INTO discovery.stream_revisions VALUES (%s,%s)', (stream_id, r.revision_id))
        conn.execute('INSERT INTO discovery.pages VALUES (%s,%s,%s,%s,%s,%s,%s)',
            (stream_id, page.cursor or '', digest(wire(page)), page.next_cursor, page.complete, len(page.records), 0))
        conn.execute('UPDATE discovery.streams SET cursor=%s,complete=%s WHERE stream_id=%s', (page.next_cursor, page.complete, stream_id))
        if page.complete:
            return
        cursor = page.next_cursor


def seed_retained(conn, g):
    identity = observed_revision(InstrumentData(kind='instrument', issuer_id='TEST', symbol='TEST', isin='INE009A01021', series='EQ',
        status='active', lot_size=1, tick_size='0.05', effective_at='2026-01-01T00:00:00Z'), listing=LISTING, fetched=EARLIER)
    seed_stream(conn, g, 'legacy-universe', 'universe', [identity])
    sessions, first, later = [], [], []
    from datetime import datetime, timedelta, timezone
    for i in range(30):
        day = datetime(2026, 9, 20, tzinfo=timezone.utc) + timedelta(days=i)
        stamp = lambda h: day.replace(hour=h).strftime('%Y-%m-%dT%H:%M:%SZ')
        sessions.append(observed_revision(SessionData(kind='session', calendar_version='invented', opens_at=stamp(4), closes_at=stamp(10)), listing='NSE', fetched=NOW))
        data = CandleData(kind='candle', interval='1d', starts_at=stamp(4), ends_at=stamp(10), open='100', high='110', low='90', close='105',
                          volume=1000, adjustment_basis='split_bonus_adjusted')
        if i < 20:
            first.append(observed_revision(data, listing=LISTING, fetched=EARLIER, parent=identity.revision_id))
        if i >= 10:
            later.append(observed_revision(data, listing=LISTING, fetched=NOW, parent=identity.revision_id, previous=first[i] if i < 20 else None))
    seed_stream(conn, g, 'legacy-calendar', 'calendar', sessions)
    seed_stream(conn, g, 'legacy-prices-A', 'prices', first)
    seed_stream(conn, g, 'legacy-prices-B', 'prices', later)


def test_retained_0013_upgrade_restores_fenced_reads_without_rewriting(migration_database, tmp_path):
    legacy_0013(tmp_path)
    g = grant()
    grants = tmp_path / 'grants.json'
    grants.write_text(json.dumps([g.model_dump(mode='json')]))
    def config(rule):
        return ViewConfig(sources=SourceConfig(grant_file=str(grants), retention_days=365), listing_ids=(LISTING,), adjusted_multi_stream=rule)
    with psycopg.connect(migration_database, autocommit=True) as conn:
        assert conn.execute('SELECT version_num FROM alembic_version').fetchone() == ('0013',)
        seed_retained(conn, g)
        # Reproduces the reported INFY state: the read fence fails closed without 0015.
        with pytest.raises(PermissionError):
            company(conn, config('disabled'), LISTING, clock=lambda: NOW)
        before = snapshot(conn)
        command.upgrade(Config(str(ROOT / 'backend/alembic.ini')), 'head')
        assert conn.execute('SELECT version_num FROM alembic_version').fetchone() == ('0017',)
        after = snapshot(conn)
        assert all(after[t] == rows for t, rows in before.items())
        assert conn.execute('SELECT kind,state,generation FROM discovery.grant_fences ORDER BY kind').fetchall() == [
            ('account', 'OPEN', 0), ('grant', 'OPEN', 0), ('provider', 'OPEN', 0)]
        assert conn.execute('SELECT count(*) FROM discovery.ingestion_grants').fetchone() == (0,)
        strict = company(conn, config('disabled'), LISTING, clock=lambda: NOW)['adjusted_research']
        assert strict['status'] == 'UNAVAILABLE' and strict['unavailable_reasons'] == ['batch_identity_missing_or_ambiguous']
        approved = company(conn, config('approved_v1'), LISTING, clock=lambda: NOW)
        research = approved['adjusted_research']
        assert research['status'] == 'UNAVAILABLE' and not approved['price_series']
        assert 'adjusted_vintage_unverified' in research['unavailable_reasons']
        assert not research['execution_qualified'] and not research['historical_pit_qualified']
        assert snapshot(conn) == after
