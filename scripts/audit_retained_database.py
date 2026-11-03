"""STK-014/074/079: read-only audit of the retained REAL database. Prints sanitized JSON.

Never writes, migrates, deletes or calls a provider. Output contains counts, clocks,
SHA-256 fingerprints and stable digests only: no prices, payloads, tokens or account IDs.
Usage (owner, on the Mac):
  DATABASE_URL_FILE=<private file> python scripts/audit_retained_database.py \
      --listing NSE:INE009A01021 [--view-config <private view config>] > audit.json
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for part in ('backend', 'shared', 'worker'):
    sys.path.insert(0, str(ROOT / part))
SCHEMAS = ('research', 'discovery', 'paper')
FENCE_TABLES = ('discovery.grant_fences', 'discovery.restriction_requests', 'discovery.ingestion_grants')


def short(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def database_url():
    path = os.getenv('DATABASE_URL_FILE')
    return Path(path).read_text().strip() if path else os.environ['DATABASE_URL']


def fingerprints(conn):
    from psycopg import sql
    tables = conn.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname = ANY(%s) ORDER BY 1,2", (list(SCHEMAS),)).fetchall()
    result = {}
    for schema, table in tables:
        digest, rows = hashlib.sha256(), 0
        query = sql.SQL('SELECT to_jsonb(t)::text FROM {}.{} t ORDER BY 1').format(sql.Identifier(schema), sql.Identifier(table))
        with conn.cursor(name='fp_' + short(schema + table)) as cursor:
            cursor.itersize = 2000
            cursor.execute(query)
            for (text,) in cursor:
                digest.update(text.encode() + b'\n')
                rows += 1
        result[f'{schema}.{table}'] = dict(rows=rows, sha256=digest.hexdigest())
    return result


def grants(conn, now):
    result = []
    for grant_id, version, p in conn.execute('SELECT grant_id,version,payload FROM discovery.grants ORDER BY 1,2'):
        expires = datetime.fromisoformat(p['expires_at'].replace('Z', '+00:00'))
        result.append(dict(grant=short([grant_id, version]), source_id=p['source_id'], account=short(p['account_ref']),
            status=p['status'], synthetic=p['synthetic'], scopes=p['scopes'], allowed_uses=p['allowed_uses'],
            retention_days=p.get('retention_days'), valid_from_at=p['valid_from_at'], expires_at=p['expires_at'],
            days_until_expiry=round((expires - now).total_seconds() / 86400, 1)))
    return result


def price_streams(conn, listing, now, retention_days):
    rows = conn.execute("""SELECT r.stream_id,count(*),count(DISTINCT r.payload->>'fetched_at'),min(r.payload->>'fetched_at'),
        max(r.payload->>'fetched_at'),min(r.payload->'data'->>'ends_at'),max(r.payload->'data'->>'ends_at'),
        array_agg(DISTINCT r.payload->'data'->>'adjustment_basis'),s.complete,
        (SELECT count(*) FROM discovery.pages p WHERE p.stream_id=r.stream_id),
        (SELECT coalesce(sum(quarantined),0) FROM discovery.pages p WHERE p.stream_id=r.stream_id)
        FROM discovery.revisions r JOIN discovery.streams s USING(stream_id)
        WHERE r.listing_id=%s AND r.kind='candle' GROUP BY r.stream_id,s.complete ORDER BY 4,1""", (listing,)).fetchall()
    result = []
    for sid, count, clocks, first, last, start, end, basis, complete, pages, quarantined in rows:
        age = (now - datetime.fromisoformat(first.replace('Z', '+00:00'))).total_seconds() / 86400
        result.append(dict(stream=short(sid), revisions=count, fetch_clocks=clocks, fetched_from=first, fetched_to=last,
            first_session_end=start, last_session_end=end, adjustment_basis=sorted(basis), complete=complete, pages=pages,
            quarantined=int(quarantined), oldest_observation_age_days=round(age, 1),
            beyond_configured_retention=retention_days is not None and age > retention_days))
    return result


def qualification_dry_run(conn, listing):
    """Same pure verification the company view uses; reads only, no grant authorization."""
    from stock_discovery_analysis.adjusted_research import verify_pages, stream_evidence
    from stock_discovery_analysis.revisions import Revision
    rows = conn.execute("""SELECT DISTINCT ON (logical_key) payload FROM discovery.revisions
        WHERE listing_id=%s AND kind='candle' AND payload->>'availability_basis'='observed'
        ORDER BY logical_key,sequence DESC""", (listing,)).fetchall()
    bars = sorted((Revision.model_validate(r[0]) for r in rows), key=lambda r: r.data.ends_at)
    if not bars:
        return dict(selected_bars=0, result='no_observed_candles')
    ids = sorted({r[0] for r in conn.execute('SELECT DISTINCT stream_id FROM discovery.revisions WHERE revision_id=ANY(%s)', ([b.revision_id for b in bars],))})
    per_stream = {}
    for sid in ids:
        stream, stored, pages = stream_evidence(conn, sid)
        try:
            verify_pages(tuple(Revision.model_validate(r[0]) for r in stored), stored, stream, pages)
            per_stream[short(sid)] = 'verified'
        except ValueError as error:
            per_stream[short(sid)] = str(error)
    if len(ids) == 1:
        combined = 'single_stream' if set(per_stream.values()) == {'verified'} else 'single_stream_unverified'
    else:
        combined = 'adjusted_vintage_unverified'
    return dict(selected_bars=len(bars), contributing_streams=len(ids), per_stream=per_stream, combined=combined,
                note='Session boundaries, coverage and current grants are checked separately by the company view.')


def file_grant(view_config, conn, now):
    from stock_discovery_analysis.real_views import ViewConfig
    from stock_discovery_analysis.real_access import source_access
    from stock_discovery_analysis.revision_storage import Stream
    from stock_discovery_contracts.rights import authorize
    config = ViewConfig.model_validate_json(Path(view_config).read_text())
    access = source_access(config.sources, lambda: now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    result = dict(listings=len(config.listing_ids), retention_days=config.sources.retention_days,
                  adjusted_multi_stream=config.adjusted_multi_stream, streams=[])
    for sid, source, account, scope in conn.execute('SELECT stream_id,source_id,account_ref,scope FROM discovery.streams ORDER BY 1'):
        stream = Stream(stream_id=sid, source_id=source, account_ref=account, scope=scope)
        current = access.load_grant(stream)
        decision = authorize(current, access.request_for(stream)).code if current else 'no_grant_in_private_file'
        result['streams'].append(dict(stream=short(sid), source_id=source, scope=scope, derive_today=decision))
    return result


def pending_documents():
    out = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, capture_output=True, text=True).stdout
    result = []
    for line in out.splitlines():
        path = ROOT / line[3:]
        if line.startswith('??') and path.is_file():
            result.append(dict(path=line[3:], bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return result


def main():
    import psycopg
    parser = argparse.ArgumentParser()
    parser.add_argument('--listing', required=True)
    parser.add_argument('--view-config')
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    with psycopg.connect(database_url(), connect_timeout=5) as conn:
        conn.read_only = True
        version = conn.execute('SELECT version_num FROM alembic_version').fetchall()
        present = {t: conn.execute('SELECT to_regclass(%s)', (t,)).fetchone()[0] is not None for t in FENCE_TABLES}
        retention = None
        report = dict(audited_at=now.isoformat(), read_only=True, alembic_version=[v[0] for v in version],
                      required_version='0015', fence_tables=present, grants=grants(conn, now))
        if args.view_config:
            report['private_grant_file'] = file_grant(args.view_config, conn, now) if all(present.values()) else 'skipped_until_0015'
            retention = json.loads(Path(args.view_config).read_text())['sources']['retention_days']
        report['price_streams'] = price_streams(conn, args.listing, now, retention)
        report['qualification_dry_run'] = qualification_dry_run(conn, args.listing)
        report['tables'] = fingerprints(conn)
        conn.rollback()
    report['untracked_files'] = pending_documents()
    print(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main()
