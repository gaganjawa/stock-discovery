"""D3-03 atomic pages, quarantine and append-only snapshot persistence.

Call with an idle connection. Adapters are injected; this package ships only a
fictional adapter. Rights checked before fetching, storing and snapshot reuse.
"""
import json
from typing import Annotated, Protocol

from psycopg.types.json import Jsonb
from pydantic import Field

from stock_discovery_contracts.rights import Grant, UseRequest, authorize
from stock_discovery_contracts.v2 import Ref, Strict, Text, check, at, digest
from .revisions import Revision, Snapshot, make_snapshot


class Stream(Strict):
    stream_id: Text
    source_id: Text
    account_ref: Text
    scope: Text


class Page(Strict):
    cursor: Text | None
    next_cursor: Text | None
    complete: bool
    records: Annotated[tuple[dict, ...], Field(max_length=100)]


class PageAdapter(Protocol):
    def fetch(self, cursor: str | None, limit: int) -> Page: ...


class SyntheticPageAdapter:
    def __init__(self, pages: tuple[Page, ...]):
        self.pages = {p.cursor: p for p in pages}
        check(len(self.pages) == len(pages), 'duplicate fixture cursor')
        for p in pages:
            for row in p.records:
                check(row.get('availability_basis') == 'fictional_fixture', 'fictional adapter only')

    def fetch(self, cursor, limit):
        page = self.pages[cursor]
        check(len(page.records) <= limit, 'adapter page limit')
        return page


def wire(model):
    return model.model_dump(mode='json')


def permission(grant, request, stream, uses, audit):
    check((request.source_id, request.account_ref, request.scope) ==
          (stream.source_id, stream.account_ref, stream.scope), 'stream request mismatch')
    # Infrastructure chooses uses; caller cannot downgrade store to acquire.
    req = UseRequest.model_validate({**request.model_dump(), 'uses': tuple(uses)})
    decision = authorize(grant, req)
    audit(decision)
    if not decision.allowed:
        raise PermissionError(decision.code)


def ingest_page(conn, stream: Stream, page: Page, *, load_grant, request, audit, permit=None):
    """Validated page and checkpoint commit together; bad rows retain hashes only."""
    grant = load_grant()
    permission(grant, request, stream, ('store',), audit)
    from .grant_fences import capture, enforce, sanitized_fence_errors
    permit = permit or capture(conn, grant, request)
    check(len(page.records) <= request.units, 'page exceeds reserved operation units')
    check(page.complete == (page.next_cursor is None), 'completion/cursor mismatch')
    check(page.complete or page.cursor != page.next_cursor, 'cursor did not advance')
    content_hash = digest(wire(page))
    cursor_key = page.cursor or ''
    with sanitized_fence_errors(), conn.transaction():
        enforce(conn, permit, load_grant(), request)
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('D3-stream:'+stream.stream_id,))
        conn.execute('''INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope)
            VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
            (stream.stream_id, stream.source_id, stream.account_ref, stream.scope))
        state = conn.execute('SELECT source_id,account_ref,scope,cursor,complete FROM discovery.streams WHERE stream_id=%s FOR UPDATE', (stream.stream_id,)).fetchone()
        check(state[:3] == (stream.source_id,stream.account_ref,stream.scope), 'stream identity conflict')
        old = conn.execute('SELECT content_hash,accepted,quarantined FROM discovery.pages WHERE stream_id=%s AND cursor_key=%s', (stream.stream_id,cursor_key)).fetchone()
        if old:
            conn.execute('SELECT discovery.check_ingestion_page(%s,%s)', (stream.stream_id,cursor_key))
            check(old[0] == content_hash, 'changed page on retry')
            return {'accepted': old[1], 'quarantined': old[2], 'reused': True}
        check(not state[4] and state[3] == page.cursor, 'stale or completed stream cursor')
        if page.next_cursor is not None:
            check(conn.execute('SELECT 1 FROM discovery.pages WHERE stream_id=%s AND cursor_key=%s', (stream.stream_id,page.next_cursor)).fetchone() is None, 'cursor cycle')
        conn.execute('INSERT INTO discovery.grants VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                     (grant.grant_id,grant.version,Jsonb(wire(grant))))
        stored_grant = conn.execute('SELECT payload FROM discovery.grants WHERE grant_id=%s AND version=%s', (grant.grant_id,grant.version)).fetchone()[0]
        check(stored_grant == wire(grant), 'grant version conflict')
        accepted = quarantined = 0
        for position, raw in enumerate(page.records):
            reason = None
            try:
                record = Revision.model_validate(raw)
            except ValueError:
                reason = 'invalid_record'
            if reason is None:
                if record.source_id != stream.source_id or record.scope != stream.scope:
                    reason = 'source_scope_mismatch'
                elif (record.availability_basis == 'fictional_fixture') != request.synthetic:
                    reason = 'mode_mismatch'
                elif at(record.fetched_at) > at(request.requested_at):
                    reason = 'future_fetch'
            if reason is None:
                old_record = conn.execute('SELECT payload,stream_id FROM discovery.revisions WHERE revision_id=%s', (record.revision_id,)).fetchone()
                collision = conn.execute('SELECT revision_id FROM discovery.revisions WHERE source_id=%s AND logical_key=%s AND (sequence=%s OR source_revision=%s)', (record.source_id,record.logical_key,record.sequence,record.source_revision)).fetchone()
                if old_record:
                    conn.execute('SELECT discovery.check_revision_grant(%s)', (record.revision_id,))
                if old_record and old_record[0] != wire(record):
                    reason = 'revision_identity_conflict'
                elif collision and collision[0] != record.revision_id:
                    reason = 'source_revision_conflict'
            if reason is None and record.instrument_revision_id:
                parent = conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s', (record.instrument_revision_id,)).fetchone()
                if parent is None:
                    reason = 'instrument_reference_missing'
                else:
                    instrument = Revision.model_validate(parent[0])
                    if instrument.data.kind != 'instrument' or instrument.listing_id != record.listing_id or at(instrument.available_at) > at(record.available_at):
                        reason = 'instrument_reference_mismatch'
            if reason is None and record.supersedes_id:
                parent = conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s', (record.supersedes_id,)).fetchone()
                if parent is None:
                    reason = 'previous_revision_missing'
                else:
                    previous = Revision.model_validate(parent[0])
                    if (previous.source_id, previous.logical_key) != (record.source_id,record.logical_key) or previous.sequence >= record.sequence or at(previous.available_at) > at(record.available_at):
                        reason = 'invalid_revision_chain'
            if reason:
                conn.execute('INSERT INTO discovery.quarantine VALUES (%s,%s,%s,%s,%s)',
                             (stream.stream_id,cursor_key,position,digest(raw),reason))
                quarantined += 1
                continue
            conn.execute('''INSERT INTO discovery.revisions VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                (record.revision_id,stream.stream_id,record.source_id,record.source_revision,record.logical_key,record.sequence,
                 record.data.kind,record.listing_id,record.available_at,grant.grant_id,grant.version,
                 record.instrument_revision_id,record.supersedes_id,record.content_hash,Jsonb(wire(record))))
            actual = conn.execute('SELECT payload,stream_id FROM discovery.revisions WHERE revision_id=%s', (record.revision_id,)).fetchone()
            check(actual is not None and actual[0] == wire(record), 'concurrent revision conflict')
            conn.execute('INSERT INTO discovery.stream_revisions VALUES (%s,%s) ON CONFLICT DO NOTHING', (stream.stream_id,record.revision_id))
            accepted += 1
        conn.execute('INSERT INTO discovery.ingestion_grants VALUES (%s,%s,%s,%s)',
                     (stream.stream_id,cursor_key,grant.grant_id,grant.version))
        conn.execute('INSERT INTO discovery.pages VALUES (%s,%s,%s,%s,%s,%s,%s)',
                     (stream.stream_id,cursor_key,content_hash,page.next_cursor,page.complete,accepted,quarantined))
        conn.execute('UPDATE discovery.streams SET cursor=%s,complete=%s WHERE stream_id=%s',
                     (page.next_cursor,page.complete,stream.stream_id))
    return {'accepted': accepted, 'quarantined': quarantined, 'reused': False}


def ingest_next(conn, stream, adapter: PageAdapter, *, load_grant, request, audit, clock):
    request = UseRequest.model_validate({**request.model_dump(), 'requested_at': clock()})
    grant = load_grant()
    permission(grant,request,stream,('acquire',),audit)
    from .grant_fences import capture
    permit = capture(conn,grant,request,('acquire','store'))
    with conn.transaction():
        state = conn.execute('SELECT cursor,complete FROM discovery.streams WHERE stream_id=%s', (stream.stream_id,)).fetchone()
    if state and state[1]:
        with conn.transaction():
            for row in conn.execute('SELECT cursor_key FROM discovery.pages WHERE stream_id=%s ORDER BY cursor_key',(stream.stream_id,)):
                conn.execute('SELECT discovery.check_ingestion_page(%s,%s)',(stream.stream_id,row[0]))
        return {'complete': True}
    cursor = state[0] if state else None
    page = adapter.fetch(cursor,min(request.units,100))
    check(page.cursor == cursor, 'adapter cursor mismatch')
    request = UseRequest.model_validate({**request.model_dump(), 'requested_at': clock()})
    return ingest_page(conn,stream,page,load_grant=load_grant,request=request,audit=audit,permit=permit)


def freeze_snapshot(conn, *, streams, load_grant, requests, audit, mode, cutoff,
                    created_at, universe_version, calendar_version):
    check(streams and len({s.stream_id for s in streams}) == len(streams), 'unique streams required')
    grant_refs = {}
    for stream in streams:
        request = requests[stream.stream_id]
        check(request.synthetic == (mode == 'synthetic'), 'snapshot mode mismatch')
        check(request.requested_at == created_at, 'snapshot rights clock mismatch')
        uses = ('derive', 'historical_replay') if mode == 'historical_reconstructed' else ('derive',)
        current_grant = load_grant(stream)
        permission(current_grant,request,stream,uses,audit)
        ref = Ref(id=current_grant.grant_id,version=current_grant.version,content_hash=digest(wire(current_grant)))
        grant_refs[(ref.id,ref.version)] = ref
    ids = sorted(s.stream_id for s in streams)
    with conn.transaction():
        # Sorted locks provide a consistent point-in-time view of all included streams.
        for stream_id in ids:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('D3-stream:'+stream_id,))
        for stream in streams:
            conn.execute('INSERT INTO discovery.streams(stream_id,source_id,account_ref,scope) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING', (stream.stream_id,stream.source_id,stream.account_ref,stream.scope))
        states = conn.execute('SELECT stream_id,source_id,account_ref,scope,complete FROM discovery.streams WHERE stream_id=ANY(%s)', (ids,)).fetchall()
        by_id = {s[0]: s for s in states}
        for stream in streams:
            if stream.stream_id in by_id:
                check(by_id[stream.stream_id][1:4] == (stream.source_id,stream.account_ref,stream.scope), 'snapshot stream mismatch')
        complete = len(states) == len(ids) and all(s[4] for s in states)
        records = [Revision.model_validate(row[0]) for row in conn.execute('SELECT DISTINCT r.payload FROM discovery.revisions r JOIN discovery.stream_revisions sr USING(revision_id) WHERE sr.stream_id=ANY(%s) AND r.available_at<=%s', (ids,cutoff))]
        quarantined = conn.execute('SELECT count(*) FROM discovery.quarantine WHERE stream_id=ANY(%s)', (ids,)).fetchone()[0]
        for row in conn.execute('SELECT DISTINCT g.payload FROM discovery.grants g JOIN discovery.revisions r ON (r.grant_id,r.grant_version)=(g.grant_id,g.version) JOIN discovery.stream_revisions sr USING(revision_id) WHERE sr.stream_id=ANY(%s) AND r.available_at<=%s', (ids,cutoff)):
            g = Grant.model_validate_json(json.dumps(row[0]))
            ref = Ref(id=g.grant_id,version=g.version,content_hash=digest(wire(g)))
            previous = grant_refs.get((ref.id,ref.version))
            check(previous is None or previous == ref, 'snapshot grant conflict')
            grant_refs[(ref.id,ref.version)] = ref
        missing_scopes = {'universe','prices','calendar','corporate_actions'} - {s.scope for s in streams}
        issues = ['missing_scope:' + s for s in sorted(missing_scopes)]
        if quarantined:
            issues.append('quarantined_records')
        if not complete:
            issues.append('incomplete_streams')
        snapshot = make_snapshot(records,mode=mode,cutoff=cutoff,created_at=created_at,
                                 universe_version=universe_version,calendar_version=calendar_version,
                                 stream_ids=ids,grant_refs=tuple(grant_refs[k] for k in sorted(grant_refs)),streams_complete=complete,issues=issues)
        conn.execute('INSERT INTO discovery.snapshots VALUES (%s,%s) ON CONFLICT DO NOTHING', (snapshot.snapshot_id,Jsonb(wire(snapshot))))
        actual = conn.execute('SELECT payload FROM discovery.snapshots WHERE snapshot_id=%s', (snapshot.snapshot_id,)).fetchone()[0]
        check(actual == wire(snapshot), 'snapshot identity conflict')
        for r in snapshot.revisions + snapshot.dependencies:
            conn.execute('INSERT INTO discovery.snapshot_items VALUES (%s,%s) ON CONFLICT DO NOTHING', (snapshot.snapshot_id,r.revision_id))
    return snapshot


def read_snapshot(conn, snapshot_id, *, load_grant, requests, audit):
    """Recheck current rights before retrieving the stored source content."""
    metadata = conn.execute("SELECT payload->'stream_ids',payload->>'mode' FROM discovery.snapshots WHERE snapshot_id=%s", (snapshot_id,)).fetchone()
    if metadata is None:
        raise KeyError('snapshot not found')
    for stream_id in metadata[0]:
        row = conn.execute('SELECT source_id,account_ref,scope FROM discovery.streams WHERE stream_id=%s', (stream_id,)).fetchone()
        check(row is not None, 'missing snapshot stream')
        stream = Stream(stream_id=stream_id,source_id=row[0],account_ref=row[1],scope=row[2])
        request = requests[stream_id]
        check(request.synthetic == (metadata[1] == 'synthetic'), 'snapshot read mode mismatch')
        uses = ('derive','historical_replay') if metadata[1]=='historical_reconstructed' else ('derive',)
        permission(load_grant(stream),request,stream,uses,audit)
    row = conn.execute('SELECT payload FROM discovery.snapshots WHERE snapshot_id=%s', (snapshot_id,)).fetchone()
    if row is None:
        raise KeyError('snapshot not found')
    snapshot = Snapshot.model_validate_json(json.dumps(row[0]))
    payload = wire(snapshot)
    check(digest({k:v for k,v in payload.items() if k!='snapshot_id'}) == snapshot_id, 'snapshot hash mismatch')
    return snapshot
