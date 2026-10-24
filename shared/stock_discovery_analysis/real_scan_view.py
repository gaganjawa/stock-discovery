"""Read saved factual scans with current source checks; no publication semantics."""
from .real_access import source_access
from .revision_storage import Stream
from .evidence_storage import stored_stream
from .publication_store import now


def scan_view(conn,config):
    if not config.pilot_scope_id:return dict(status='not_configured',scan=None,jobs=[])
    jobs=conn.execute("SELECT job_id,stage,status,error_code,attempts,due_at,updated_at FROM discovery.schedule_jobs WHERE payload->>'scope_id'=%s ORDER BY updated_at DESC LIMIT 30",(config.pilot_scope_id,)).fetchall()
    row=conn.execute("SELECT o.payload FROM discovery.schedule_outbox o JOIN discovery.schedule_jobs j USING(job_id) WHERE j.payload->>'scope_id'=%s AND o.kind='pilot_scan' ORDER BY o.created_at DESC,o.event_key LIMIT 1",(config.pilot_scope_id,)).fetchone()
    scan=row[0] if row else None
    if scan:
        access=source_access(config.sources)
        source=Stream(stream_id='PILOT-read',source_id='upstox',account_ref=scan['universe']['account_ref'],scope='universe')
        checked={}
        def require(stream):
            access.require(stream,('derive',))
            checked[(stream.source_id,stream.account_ref,stream.scope)]=stream
        require(source)
        for item in scan['rows']:
            if item.get('financial_fact_count',0):require(source.model_copy(update={'scope':'financial_facts'}))
            for rid in item.get('source_revisions',[]):require(stored_stream(conn,rid))
            for f in item.get('financial_findings',[]):
                for c in f['citations']:require(stored_stream(conn,c['revision_id']))
        for stream in checked.values():access.require(stream,('derive',))
    return dict(status='observed' if scan else 'awaiting_scheduled_scan',scan=scan,read_at=now(),
        jobs=[dict(job_id=j[0],stage=j[1],status=j[2],error=j[3],attempts=j[4],due_at=j[5].isoformat(),updated_at=j[6].isoformat()) for j in jobs],
        queue_depth=conn.execute("SELECT count(*) FROM discovery.schedule_jobs WHERE payload->>'scope_id'=%s AND status IN ('queued','running','retry_wait')",(config.pilot_scope_id,)).fetchone()[0],qualification='Levels 1 and 2 only; Levels 3 and 4 remain independently gated')
