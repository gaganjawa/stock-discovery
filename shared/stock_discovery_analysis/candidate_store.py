"""STK-094 durable bounded inbox and candidate timeline on existing PostgreSQL.

All writes use a short transaction; the worker claims one row with SKIP LOCKED.
No network or model clients live here. A crash rolls the claim back for replay.
"""
from datetime import datetime, timezone
from psycopg.types.json import Jsonb
from .chartink import digest

MAX_EVENTS = 10000
# Separate from the 64 KiB transport cap: typed enrichment expands each row.
# Combined with MAX_EVENTS this bounds retained serialized envelope data.
MAX_EVENT_BYTES = 1024 * 1024


def accept(conn, envelope):
    # Use the exact jsonb text representation checked by migration 0017. Python
    # JSON differs for Unicode escapes, numeric exponents and object formatting.
    size=conn.execute('SELECT octet_length(%s::jsonb::text)',(Jsonb(envelope),)).fetchone()[0]
    if size>MAX_EVENT_BYTES: raise ValueError('event_too_large')
    with conn.transaction():
        # Also serializes feed sequence assignment/commit, avoiding cursor gaps.
        conn.execute("SELECT pg_advisory_xact_lock(94001)")
        registered=conn.execute('''SELECT envelope->>'scanner_key' FROM discovery.candidate_events
          WHERE envelope->'scanner'->>'scan_url'=%s AND envelope->'scanner'->>'version'=%s
          AND envelope->'scanner'->>'mode'=%s LIMIT 1''',
          (envelope['scanner']['scan_url'],envelope['scanner']['version'],envelope['scanner']['mode'])).fetchone()
        if registered and registered[0]!=envelope['scanner_key']:raise ValueError('scanner_version_content_conflict')
        prior=conn.execute('SELECT envelope FROM discovery.candidate_events WHERE event_id=%s', (envelope['event_id'],)).fetchone()
        if prior:
            # A duplicate receipt has a different receipt clock, but the same content.
            for key in ('scanner_key','session_date','payload_hash','symbols','completeness','mode'):
                if prior[0][key]!=envelope[key]:raise ValueError('event_identity_conflict')
            conn.execute('UPDATE discovery.candidate_event_state SET deliveries=least(deliveries+1,1000000) WHERE event_id=%s', (envelope['event_id'],))
            return dict(event_id=envelope['event_id'],duplicate=True)
        if conn.execute('SELECT count(*) FROM discovery.candidate_events').fetchone()[0]>=MAX_EVENTS:
            raise OverflowError('candidate_inbox_capacity_reached')
        conn.execute('INSERT INTO discovery.candidate_events(event_id,received_at,envelope) VALUES (%s,%s,%s)',
                     (envelope['event_id'],envelope['received_at'],Jsonb(envelope)))
        conn.execute('INSERT INTO discovery.candidate_event_state(event_id) VALUES (%s)',(envelope['event_id'],))
        # Commit-coupled wake-up only; rows remain the durable source of truth.
        conn.execute("SELECT pg_notify('stk_candidates', '')")
    return dict(event_id=envelope['event_id'],duplicate=False)


def rate_allowed(conn):
    # Shared across receiver processes; bounded to one persisted counter.
    with conn.transaction():
        row=conn.execute('''INSERT INTO discovery.candidate_rate VALUES (1,clock_timestamp(),1)
          ON CONFLICT(id) DO UPDATE SET
            attempts=CASE WHEN candidate_rate.window_at<clock_timestamp()-interval '1 minute' THEN 1 ELSE least(candidate_rate.attempts+1,61) END,
            window_at=CASE WHEN candidate_rate.window_at<clock_timestamp()-interval '1 minute' THEN clock_timestamp() ELSE candidate_rate.window_at END
          RETURNING attempts''').fetchone()
        return row[0]<=60


def reject(conn, payload_hash, reason):
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(94002)')
        # Keep only hashes/codes, never attacker payloads or URL secrets.
        conn.execute('''DELETE FROM discovery.candidate_rejections WHERE payload_hash IN
          (SELECT payload_hash FROM discovery.candidate_rejections ORDER BY received_at DESC OFFSET 999)''')
        conn.execute('INSERT INTO discovery.candidate_rejections(payload_hash,reason) VALUES (%s,%s) ON CONFLICT DO NOTHING', (payload_hash,reason))


def feed(conn, after=0, limit=25):
    if after<0 or not 1<=limit<=25:raise ValueError('invalid_feed_bounds')
    rows=conn.execute('SELECT sequence,envelope FROM discovery.candidate_events WHERE sequence>%s ORDER BY sequence LIMIT %s',(after,limit)).fetchall()
    return dict(events=[dict(sequence=s,envelope=e) for s,e in rows],next_cursor=rows[-1][0] if rows else after)


def materialize_one(conn):
    with conn.transaction():
        # Multiple deliveries can touch the same candidate; single bounded writer.
        if not conn.execute('SELECT pg_try_advisory_xact_lock(94003)').fetchone()[0]: return None
        row=conn.execute('''SELECT e.event_id,e.envelope FROM discovery.candidate_events e
          JOIN discovery.candidate_event_state s USING(event_id) WHERE s.status='pending'
          ORDER BY e.sequence FOR UPDATE OF s SKIP LOCKED LIMIT 1''').fetchone()
        if not row:return None
        eid,e=row
        try:
            with conn.transaction():
                if e.get('version')=='chartink-provider-test-v1':
                    if e.get('delivery_kind')!='provider_test' or e['symbols']:
                        raise ValueError('invalid_provider_test_envelope')
                    conn.execute("UPDATE discovery.candidate_event_state SET status='completed',error_code=NULL WHERE event_id=%s",(eid,))
                    return eid  # Never create a session, candidate, match or research run.
                conn.execute('''INSERT INTO discovery.candidate_sessions VALUES (%s,%s,%s)
                  ON CONFLICT(scanner_key,session_date) DO UPDATE SET completeness=CASE
                    WHEN excluded.completeness='partial_unverified' THEN candidate_sessions.completeness ELSE excluded.completeness END''',
                  (e['scanner_key'],e['session_date'],e['completeness']))
                for symbol in e['symbols']:
                    cid=digest([e['scanner_key'],e['session_date'],symbol])
                    conn.execute('''INSERT INTO discovery.candidates(candidate_id,scanner_key,session_date,symbol,exchange,first_observed_at,last_observed_at)
                      VALUES (%s,%s,%s,%s,'NSE',%s,%s) ON CONFLICT(candidate_id) DO UPDATE SET
                      first_observed_at=least(candidates.first_observed_at,excluded.first_observed_at),
                      last_observed_at=greatest(candidates.last_observed_at,excluded.last_observed_at)''',
                      (cid,e['scanner_key'],e['session_date'],symbol,e['received_at'],e['received_at']))
                    conn.execute('INSERT INTO discovery.candidate_matches VALUES (%s,%s) ON CONFLICT DO NOTHING',(eid,cid))
                conn.execute("UPDATE discovery.candidate_event_state SET status='completed',error_code=NULL WHERE event_id=%s",(eid,))
                return eid
        except Exception as exc:
            conn.execute("UPDATE discovery.candidate_event_state SET status='failed',error_code=%s WHERE event_id=%s",(type(exc).__name__[:60],eid))
            return eid


def research_one(conn, analyze):
    with conn.transaction():
        if not conn.execute('SELECT pg_try_advisory_xact_lock(94005)').fetchone()[0]:return None
        row=conn.execute('''SELECT candidate_id,symbol,session_date FROM discovery.candidates
          WHERE research_status='pending' AND attempts<3 AND retry_at<=now()
          ORDER BY session_date DESC,first_observed_at,candidate_id FOR UPDATE SKIP LOCKED LIMIT 1''').fetchone()
        if not row:return None
        cid,symbol,session=row
        try:
            with conn.transaction():
                if conn.execute('SELECT count(*) FROM discovery.candidate_research_runs').fetchone()[0]>=50000:
                    raise OverflowError('candidate_research_capacity_reached')
                result=analyze(conn,symbol,session)
                conn.execute('INSERT INTO discovery.candidate_research_runs(run_id,candidate_id,result) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                             (digest([cid,result]),cid,Jsonb(result)))
            conn.execute('''UPDATE discovery.candidates SET research_status=%s,result=%s,listing_id=%s,
              error_code=NULL,attempts=attempts+1 WHERE candidate_id=%s''',
              (result['status'],Jsonb(result),result.get('listing_id'),cid))
        except Exception as exc:
            conn.execute('''UPDATE discovery.candidates SET attempts=attempts+1,
              research_status=CASE WHEN attempts>=2 THEN 'failed' ELSE 'pending' END,
              error_code=%s,retry_at=now()+interval '30 seconds' WHERE candidate_id=%s''',(type(exc).__name__[:60],cid))
        return cid


def retry(conn, cid):
    # Owner-triggered retry after new evidence/permissions; duplicates never reset work.
    return conn.execute('''UPDATE discovery.candidates SET research_status='pending',attempts=0,
      retry_at=now(),error_code=NULL,result=NULL WHERE candidate_id=%s AND research_status IN ('blocked','failed','completed')
      RETURNING candidate_id''',(cid,)).fetchone() is not None


def rows(conn, *, session=None, scanner_key=None, limit=100, offset=0):
    if not 1<=limit<=100 or not 0<=offset<=5000000:raise ValueError('invalid_page')
    if session is None:
        session=conn.execute('SELECT max(session_date) FROM discovery.candidate_sessions WHERE (%s::text IS NULL OR scanner_key=%s)',(scanner_key,scanner_key)).fetchone()[0]
    records=conn.execute('''SELECT c.candidate_id,c.scanner_key,c.session_date,c.symbol,c.first_observed_at,
      c.last_observed_at,c.research_status,c.result,c.error_code,s.completeness,
      EXISTS(SELECT FROM discovery.candidates p WHERE p.scanner_key=c.scanner_key AND p.symbol=c.symbol
        AND p.session_date=(SELECT max(session_date) FROM discovery.candidate_sessions WHERE scanner_key=c.scanner_key AND session_date<c.session_date)),
      (SELECT completeness FROM discovery.candidate_sessions WHERE scanner_key=c.scanner_key AND session_date<c.session_date ORDER BY session_date DESC LIMIT 1),
      (SELECT e.envelope FROM discovery.candidate_matches m JOIN discovery.candidate_events e USING(event_id)
       WHERE m.candidate_id=c.candidate_id ORDER BY e.sequence LIMIT 1)
      FROM discovery.candidates c JOIN discovery.candidate_sessions s USING(scanner_key,session_date)
      WHERE c.session_date=%s AND (%s::text IS NULL OR c.scanner_key=%s)
      ORDER BY c.symbol,c.candidate_id LIMIT %s OFFSET %s''',(session,scanner_key,scanner_key,limit,offset)).fetchall()
    result=[]
    for cid,key,day,symbol,first,last,status,research,error,complete,continuing,previous,envelope in records:
        label=conn.execute('''SELECT e.envelope->'labels'->>%s FROM discovery.candidate_matches m JOIN discovery.candidate_events e USING(event_id) WHERE m.candidate_id=%s AND e.envelope->'labels' ? %s ORDER BY e.sequence DESC LIMIT 1''',(symbol,cid,symbol)).fetchone()
        snapshot=conn.execute('''SELECT e.envelope FROM discovery.candidate_matches m JOIN discovery.candidate_events e USING(event_id) WHERE m.candidate_id=%s ORDER BY e.received_at DESC,e.event_id DESC LIMIT 1''',(cid,)).fetchone()[0]
        result.append(dict(chartink_snapshot=snapshot.get('enrichment',{}).get(symbol),watchlist_key='CHARTINK:'+key+':'+symbol,source_label=label[0] if label else None,candidate_id=cid,scanner_key=key,session_date=day.isoformat(),symbol=symbol,
          first_observed_at=first.isoformat(),last_observed_at=last.isoformat(),research_status=status,
          research=research,error_code=error,completeness=complete,
          match_status='continuing_observed' if continuing else 'new_vs_previous_snapshot' if previous in ('verified_fixture_snapshot','verified_complete_snapshot') else 'new_observed_vs_previous_results' if previous else 'first_observed_unverified',
          comparison_basis='previous_represented_session_not_certified_previous_trading_session',
          scanner=envelope['scanner'],source_url=envelope['source_url'],timestamp_basis=envelope['timestamp_basis'],mode=envelope['mode']))
    count=conn.execute('SELECT count(*) FROM discovery.candidates WHERE session_date=%s AND (%s::text IS NULL OR scanner_key=%s)',(session,scanner_key,scanner_key)).fetchone()[0]
    return dict(rows=result,total=count,session_date=str(session) if session else None,
                delivery_status='observed_partial_or_snapshot' if count else 'missing_delivery_not_verified_zero',
                limit=limit,offset=offset,actionable=False,historical_pit_qualified=False)


def retry_event(conn,eid):
    return conn.execute("UPDATE discovery.candidate_event_state SET status='pending',error_code=NULL WHERE event_id=%s AND status='failed' RETURNING event_id",(eid,)).fetchone() is not None


def asof_candidates(conn,scanner_key,cutoff):
    """Only matches actually received by T; never a complete historical universe."""
    records=conn.execute("SELECT envelope FROM discovery.candidate_events WHERE received_at<=%s AND envelope->>'scanner_key'=%s ORDER BY received_at,sequence LIMIT 10000",(cutoff,scanner_key)).fetchall()
    return dict(events=[r[0] for r in records],cutoff=cutoff,complete=False,evaluation_eligible=False)
