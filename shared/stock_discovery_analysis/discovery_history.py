"""Read existing publication relationships; never evaluate, infer or admit."""
import json
from contextlib import contextmanager
from urllib.parse import quote

import psycopg
from stock_discovery_contracts.rights import Grant,authorize
from stock_discovery_contracts.v2 import check,digest
from .publication_store import read_artifact,now
from .publication_fixtures import access_for
from .revision_storage import Stream
from .grant_fences import identity,database_request
from .governance_contracts import Trial


@contextmanager
def authorized_history(conn):
    """All locks and final rights checks survive assembly of the whole response."""
    seen={}
    def read(rid):
        artifact=read_artifact(conn,rid)
        seen[rid]=artifact
        if artifact['recommendation']['mode']=='synthetic':
            permissions=artifact['permissions']
            check(bool(permissions),'history_permissions_missing')
            grants={scope:Grant.model_validate_json(json.dumps(raw)) for scope,raw in permissions.items()}
            for key in sorted({identity(g) for g in grants.values()}):
                conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)',key)
            for source in sorted({g.source_id for g in grants.values()}):
                row=conn.execute('SELECT revoked FROM discovery.publication_source_controls WHERE source_id=%s FOR SHARE',(source,)).fetchone()
                if row is None or row[0]:raise PermissionError('history_source_restricted')
            access=access_for(conn,now)
            for scope,original in grants.items():
                stream=Stream(stream_id='history',source_id=original.source_id,account_ref=original.account_ref,scope=scope)
                current=access.load_grant(stream)
                if current is None or identity(current)!=identity(original):raise PermissionError('history_grant_unavailable')
                request=database_request(conn,access.request_for(stream),('store','derive'))
                if not authorize(original,request).allowed or not authorize(current,request).allowed:
                    raise PermissionError('history_grant_denied')
        return artifact
    try:
        with conn.transaction():
            conn.execute("SET LOCAL lock_timeout='5s'")
            yield read
            # All dependency locks have now been acquired. Refresh earlier rights
            # after later dependencies, without registering/reopening any scope.
            for rid in sorted(seen):read(rid)
    except psycopg.Error:raise PermissionError('history_access_unavailable') from None


def related_history(conn,rid,*,before=None,limit=20):
    check(1<=limit<=50,'invalid_history_limit')
    with authorized_history(conn) as read:
        artifact=read(rid);r=artifact['recommendation']
        scope=(r['instrument']['instrument_id'],r['horizon']['profile'],r['cohort']['arm'],r['mode'])
        cursor=None
        if before:
            previous=read(before)['recommendation']
            check((previous['instrument']['instrument_id'],previous['horizon']['profile'],previous['cohort']['arm'],previous['mode'])==scope,'history_cursor_scope')
            cursor=previous['information_cutoff_at']
        rows=conn.execute('''SELECT recommendation_id FROM discovery.recommendations
            WHERE listing_id=%s AND horizon=%s AND cohort=%s AND payload->>'mode'=%s
            AND (%s::timestamptz IS NULL OR ((payload->>'information_cutoff_at')::timestamptz,recommendation_id)<(%s,%s))
            ORDER BY (payload->>'information_cutoff_at')::timestamptz DESC,recommendation_id DESC LIMIT %s''',
            (*scope,cursor,cursor,before,limit+1)).fetchall()
        records=[]
        for (key,) in rows[:limit]:
            saved=read(key)['recommendation']
            records.append(dict(recommendation_id=key,cutoff_at=saved['information_cutoff_at'],generated_at=saved['generated_at'],
                action=saved['action'],selected=key==rid))
        outcomes=[]
        ledgers=conn.execute('''SELECT DISTINCT ON (portfolio_id) portfolio_id,sequence,event_hash,event_at,state
            FROM paper.ledger WHERE state->'orders' ? %s ORDER BY portfolio_id,sequence DESC LIMIT 21''',(rid,)).fetchall()
        check(len(ledgers)<=20,'history_portfolio_limit')
        for pid,seq,hashed,event_at,state in ledgers:
            for dependency in sorted(state['orders']):read(dependency)
            validate_order(state['orders'][rid],artifact)
            outcomes.append(dict(portfolio_id=pid,sequence=seq,event_hash=hashed,observed_at=state['asof'],available_at=state['available_at'],
                recorded_at=event_at.isoformat(),url=f'/v1/paper-portfolio/{quote(pid,safe="")}/outcomes/{quote(rid,safe="")}?sequence={seq}&expected_hash={hashed}'))
        trials=conn.execute('''SELECT trial_id,experiment_id,request_hash,request FROM discovery.experiment_trials
            WHERE request->'arms' @> %s::jsonb ORDER BY experiment_id,registered_at,trial_id LIMIT 51''',
            (json.dumps([{'recommendation_ids':[rid]}]),)).fetchall()
        check(len(trials)<=50,'history_trial_limit')
        evaluations=[]
        for tid,eid,hashed,raw in trials:
            trial=Trial.model_validate_json(json.dumps(raw))
            check(digest(raw)==hashed and (trial.trial_id,trial.experiment_id)==(tid,eid),'history_trial_identity')
            arms=[a for a in trial.arms if rid in a.recommendation_ids]
            check(len(arms)==1 and (arms[0].arm,arms[0].publication_run_id)==(r['cohort']['arm'],r['run_id']),'history_trial_scope')
            evaluations.append(dict(experiment_id=eid,trial_id=tid,request_hash=hashed,phase=trial.split,
                status='registered_results_not_opened'))
        return dict(recommendation_id=rid,cutoff_at=r['information_cutoff_at'],listing_id=scope[0],horizon=scope[1],cohort=scope[2],mode=scope[3],
            records=records,next_cursor=rows[limit-1][0] if len(rows)>limit else None,outcomes=outcomes,evaluations=evaluations,
            outcome_status='recorded_hidden_until_reveal' if outcomes else 'unavailable_no_recorded_outcome',
            evaluation_status='registered_reference_only' if evaluations else 'unavailable_no_registered_trial',
            legacy_replay=dict(status='unavailable',reason='no_explicit_dataset_relationship'),
            limitations=['Saved historical evidence retains its original cutoff; opening it is not a freshness or current BUY qualification.',
                'Only existing immutable records are linked. No inference, evaluation, holdout opening, publication or admission occurs.',
                'SYN-D309 publication records and legacy Replay datasets are separate. No instrument mapping is inferred.'])


def validate_order(order,artifact):
    r=artifact['recommendation']
    check((order['recommendation_id'],order['listing_id'],order['information_cutoff_at'],order['decision_hash'],order['snapshot_id'])==
        (r['recommendation_id'],r['instrument']['instrument_id'],r['information_cutoff_at'],digest(r),r['snapshot_id']),'history_outcome_identity')


def recorded_outcome(conn,pid,rid,sequence,expected_hash):
    """Reveal an already recorded ledger revision; no evaluation or latest-state substitution."""
    with authorized_history(conn) as read:
        artifact=read(rid)
        rows=conn.execute('''SELECT sequence,event_at,kind,payload,state,event_hash,previous_hash FROM paper.ledger
            WHERE portfolio_id=%s AND sequence<=%s ORDER BY sequence''',(pid,sequence)).fetchall()
        if not rows or rows[-1][0]!=sequence:raise KeyError('outcome_not_found')
        check(rows[-1][5]==expected_hash,'history_ledger_hash')
        state=rows[-1][4];order=state['orders'].get(rid)
        if order is None:raise KeyError('outcome_not_found')
        history=[]
        for seq,event_at,kind,payload,stored,hashed,previous in rows:
            for dependency in sorted(stored['orders']):read(dependency)
            if rid in stored['orders']:validate_order(stored['orders'][rid],artifact)
            if payload.get('recommendation_id')==rid or any(c['recommendation_id']==rid for c in payload.get('changes',[])):
                excerpt={**payload}
                if 'changes' in excerpt:excerpt['changes']=[c for c in excerpt['changes'] if c['recommendation_id']==rid]
                history.append(dict(sequence=seq,at=event_at.isoformat(),kind=kind,payload=excerpt,payload_scope='recommendation_excerpt',event_hash=hashed,previous_hash=previous))
        return dict(portfolio_id=pid,sequence=sequence,event_hash=expected_hash,outcome=order,history=history,
            observation_cutoff_at=state['asof'],knowledge_cutoff_at=state['available_at'],
            labels=['RECORDED','RESEARCH ONLY','NON-ACTIONABLE'],
            limitations=['Recorded portfolio observation; forecast maturity and execution outcomes remain separate.',
                'Later ledger revisions are excluded. No outcome evaluation or paper admission is performed by this read.'])
