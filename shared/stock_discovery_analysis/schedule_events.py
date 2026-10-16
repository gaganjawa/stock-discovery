"""Bounded event hooks for trusted normalized evidence, never model tool output."""
from datetime import timedelta
from typing import Literal

from stock_discovery_contracts.v2 import Strict, Text, Timestamp, check, digest
from .scheduling import occurrence, utc
from .schedule_store import enqueue, put_occurrence


class MaterialEvent(Strict):
    listing_id: Text
    source_revision_id: Text
    event_type: Literal['earnings', 'restatement', 'default', 'auditor_change', 'regulatory_action']
    observed_at: Timestamp


def nominate(conn, config, events, now, *, read_authorized_snapshot):
    """Caller reloads current rights before returning an immutable D3-03 snapshot.

    D3-06 supplies authenticated, deterministically classified normalized events.
    No external fetch, text classification, or permission inference happens here.
    """
    check(len(events) <= config.policy.max_events_per_call, 'event batch limit')
    snapshot = read_authorized_snapshot()
    check(snapshot.mode == config.mode and snapshot.complete and utc(snapshot.information_cutoff_at) <= utc(now), 'event universe unavailable')
    members = {r.listing_id for r in snapshot.revisions if r.data.kind == 'membership'
               and r.data.universe_version == snapshot.universe_version and r.data.eligible}
    members -= set(snapshot.excluded_listings)
    documents = {r.revision_id:r for r in snapshot.revisions if r.data.kind == 'document'}
    jobs = []
    with conn.transaction():
        # Serialize coalescing and deduplication across concurrent pollers.
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('events:'+config.scope_id,))
        for event in events:
            check(isinstance(event, MaterialEvent), 'typed material event required')
            check(event.listing_id in members, 'outside eligible universe')
            source = documents.get(event.source_revision_id)
            check(source is not None and source.listing_id == event.listing_id, 'unvalidated issuer/source')
            check(utc(source.available_at) <= utc(event.observed_at) <= utc(now), 'event availability')
            key = digest([event.listing_id,event.source_revision_id,event.event_type])
            if conn.execute('SELECT 1 FROM discovery.material_events WHERE event_key=%s', (key,)).fetchone():
                continue
            # One dispatch job retains every source. Reassessment fans out only to configured horizons.
            bucket = int(utc(now).timestamp()) // 900
            extra = dict(listing_id=event.listing_id, horizons=list(config.horizons),
                         bucket=bucket, snapshot_id=snapshot.snapshot_id)
            existing = conn.execute("""SELECT job_id FROM discovery.schedule_jobs
                WHERE stage='reassess' AND status='queued' AND payload->>'schedule_hash'=%s
                AND payload->'extra'->>'listing_id'=%s AND payload->'extra'->>'bucket'=%s
                ORDER BY job_id LIMIT 1""", (digest(config.model_dump(mode='json')),event.listing_id,str(bucket))).fetchone()
            if existing:
                jid = existing[0]
            else:
                item = occurrence(config,'event_poll',None,utc(now),utc(now),utc(now)+timedelta(hours=1))
                put_occurrence(conn,item)
                # A source arriving after an earlier job started gets its own reassessment.
                jid = enqueue(conn,item,'reassess',now,extra={**extra,'first_event_key':key})
            conn.execute('INSERT INTO discovery.material_events VALUES (%s,%s,%s,%s,%s,%s)',
                         (key,event.listing_id,event.source_revision_id,event.event_type,event.observed_at,jid))
            if event.event_type in ('restatement','default','auditor_change','regulatory_action'):
                conn.execute('INSERT INTO discovery.admission_pauses VALUES (%s,%s,%s)',
                             (key,event.listing_id,'adverse_event_requires_reassessment'))
            jobs.append(jid)
    return tuple(jobs)


def admission_paused(conn, listing_id):
    """Fail-closed admission signal for D3-10; never edits historical decisions."""
    return conn.execute('SELECT 1 FROM discovery.admission_pauses WHERE listing_id=%s LIMIT 1', (listing_id,)).fetchone() is not None
