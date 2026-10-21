"""D3-10 observation-only shadow references. Never touches portfolios or fills."""
import json
from psycopg.types.json import Jsonb
from stock_discovery_contracts.v2 import Recommendation, check, digest, at
from .publication_store import now,read_artifact
from .revisions import Revision
from .evidence_storage import stored_stream

VERSION='real-shadow-1.0.0'


def register(conn,artifact):
    r=Recommendation.model_validate_json(json.dumps(artifact['recommendation']))
    check(r.mode=='live_paper' and r.cohort.shadow and r.paper_admission.status=='blocked','real_shadow_required')
    bars=artifact['input_manifest']['bars']
    last=max(bars,key=lambda b:b['ends_at']) if bars else None
    ref_id='SHADOW-'+digest([r.recommendation_id,VERSION])
    payload=dict(reference_id=ref_id,recommendation_id=r.recommendation_id,mode='live_paper',actionable=False,
        publication_at=r.decision_available_at,information_cutoff_at=r.information_cutoff_at,
        horizon=r.horizon.model_dump(),conditions=r.conditions.model_dump(),model_versions=r.versions.model_dump(),
        source_revision_ids=artifact['source_revision_ids'],evaluator_version=VERSION,
        forecast_reference_price=last['close'] if last else None,forecast_reference_at=last['ends_at'] if last else None,
        prediction='up' if r.action=='BUY' else None,forecast_end_at=r.horizon.holding_end_at,
        status='pending_future_observation',paper_admission='blocked')
    conn.execute('INSERT INTO paper.shadow_references VALUES (%s,%s,%s)',(ref_id,r.recommendation_id,Jsonb(payload)))
    return payload


def observe(conn,reference_id,access,*,clock=now):
    """Append only genuinely later, currently permitted D3-03 observations.

    A correction changes the input hash and appends a superseding outcome.
    Missing sessions/actions never become a synthetic zero or performance result.
    """
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(reference_id,))
        row=conn.execute('SELECT payload FROM paper.shadow_references WHERE reference_id=%s',(reference_id,)).fetchone()
        if not row:raise KeyError(reference_id)
        ref=row[0];evaluated=clock();artifact=read_artifact(conn,ref['recommendation_id'],access)
        r=artifact['recommendation'];listing=r['instrument']['instrument_id']
        for rid in ref['source_revision_ids']:
            stream=stored_stream(conn,rid);access.require(stream,('paper_evaluation','store'))
            if stream.scope=='filings':access.require(stream.model_copy(update={'scope':'financial_facts'}),('paper_evaluation','store'))
        rows=conn.execute("""SELECT DISTINCT ON (source_id,logical_key) payload FROM discovery.revisions
            WHERE listing_id=%s AND kind IN ('candle','action') AND payload->>'availability_basis'='observed'
            AND available_at<=%s AND (payload->>'fetched_at')::timestamptz<=%s
            ORDER BY source_id,logical_key,sequence DESC""",(listing,evaluated,evaluated)).fetchall()
        observations=[];actions=[]
        for raw, in rows:
            revision=Revision.model_validate(raw)
            if revision.data.kind=='candle':
                if not (at(ref['publication_at'])<at(revision.data.starts_at)<at(revision.data.ends_at)<=at(evaluated)):continue
                observations.append(revision)
            else:
                if not at(ref['publication_at'])<at(revision.data.effective_at)<=at(evaluated):continue
                actions.append(revision)
            access.require(stored_stream(conn,revision.revision_id),('derive','paper_evaluation','store'))
        if not observations:return dict(reference_id=reference_id,status='pending_future_observation',outcome_created=False)
        observations.sort(key=lambda r:r.data.ends_at)
        check(len({r.data.ends_at for r in observations})==len(observations),'ambiguous_observation_sources')
        observed=observations[-1].data.ends_at
        # Every retained session must be in the actual pinned calendar.
        calendar=artifact['input_manifest']['calendar']['sessions']
        expected={s['closes_at'].replace('+00:00','Z') for s in calendar if at(ref['publication_at'])<at(s['opens_at'].replace('+00:00','Z')) and at(s['closes_at'].replace('+00:00','Z'))<=at(observed)}
        actual={b.data.ends_at for b in observations}
        reason='waiting_for_horizon_endpoint';status='provisional';price_return=matches=None
        if any(b.data.adjustment_basis != 'raw' or b.source_id == 'upstox' for b in observations):
            status='unavailable';reason='observation_adjustment_basis_unqualified'
        elif expected!=actual:status='unavailable';reason='missing_or_unverified_session'
        elif actions:status='unavailable';reason='corporate_action_requires_qualified_adjustment'
        elif ref['prediction'] is None:status='not_applicable';reason='no_directional_prediction_was_published'
        elif ref['forecast_reference_price'] is None:status='unavailable';reason='no_reference_price'
        elif at(observed)>=at(ref['forecast_end_at']):
            # Current source coverage must support a no-action conclusion. The
            # real action/coverage adapter is not qualified in this delivery.
            status='unavailable';reason='current_corporate_action_coverage_unqualified'
        ids=sorted(b.revision_id for b in observations+actions)
        hashed=digest([ref,ids,VERSION])
        previous=conn.execute('SELECT payload FROM paper.shadow_outcomes WHERE reference_id=%s AND input_hash=%s',(reference_id,hashed)).fetchone()
        if previous:return previous[0]
        last=conn.execute('SELECT sequence,outcome_id FROM paper.shadow_outcomes WHERE reference_id=%s ORDER BY sequence DESC LIMIT 1',(reference_id,)).fetchone()
        sequence=last[0]+1 if last else 1;oid='SHADOW-OUT-'+digest([reference_id,hashed,sequence])
        outcome=dict(outcome_id=oid,reference_id=reference_id,sequence=sequence,evaluator_version=VERSION,
            status=status,reason=reason,evaluated_at=evaluated,observation_cutoff_at=observed,observation_revision_ids=ids,
            supersedes_outcome_id=last[1] if last else None,forecast_price_return=price_return,direction_matches=matches,
            simulated_execution=None,actionable=False)
        from .real_publication import authorize_artifact
        authorize_artifact(conn,artifact,access)
        for rid in ref['source_revision_ids']+ids:
            stream=stored_stream(conn,rid);access.require(stream,('paper_evaluation','store'))
            if stream.scope=='filings':access.require(stream.model_copy(update={'scope':'financial_facts'}),('paper_evaluation','store'))
        conn.execute('INSERT INTO paper.shadow_outcomes VALUES (%s,%s,%s,%s,%s,%s)',(oid,reference_id,sequence,hashed,evaluated,Jsonb(outcome)))
        return outcome


def pending(conn,access,*,clock=now):
    results=[]
    for rid, in conn.execute('SELECT reference_id FROM paper.shadow_references ORDER BY reference_id LIMIT 100'):
        try:results.append(observe(conn,rid,access,clock=clock))
        except PermissionError:results.append(dict(reference_id=rid,status='blocked',reason='source_permission_denied'))
    return results


def history(conn,recommendation_id,access):
    # Reading receipts must recheck both original and later observation rights.
    read_artifact(conn,recommendation_id,access)
    row=conn.execute('SELECT reference_id,payload FROM paper.shadow_references WHERE recommendation_id=%s',(recommendation_id,)).fetchone()
    if not row:return None
    outcomes=[r[0] for r in conn.execute('SELECT payload FROM paper.shadow_outcomes WHERE reference_id=%s ORDER BY sequence DESC',(row[0],))]
    for outcome in outcomes:
        for rid in outcome['observation_revision_ids']:access.require(stored_stream(conn,rid),('derive','paper_evaluation'))
    return dict(reference=row[1],outcomes=outcomes,status=outcomes[0]['status'] if outcomes else 'pending_future_observation')
