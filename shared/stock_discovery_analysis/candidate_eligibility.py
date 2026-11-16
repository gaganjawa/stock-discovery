"""STK-014 / STK-094: public qualification facts, never acquisition authorization."""

from datetime import date, datetime
import re


def valid_session(value):
    if not isinstance(value,str):return False
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
            date.fromisoformat(value)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",value):
            datetime.fromisoformat(value.replace("Z","+00:00"))
        else:return False
    except ValueError:return False
    return True


def qualification(row, *, current=False):
    research=row.get('research') or {}
    reasons=list(research.get('reasons',[]))
    identity=research.get('identity_status')=='verified_stored_nse_eq'
    denied='source_permission_denied' in reasons
    market=research.get('market_data') or {}
    technical=research.get('technical') or {}
    freshness=(market.get('freshness') or {}).get('status','not_checked')
    available=(research.get('status')=='completed'
               and technical.get('status')=='AVAILABLE_DESCRIPTIVE_ONLY')
    coverage=technical.get('session_coverage')
    coverage_ready=(coverage is None or (
        coverage.get('warmup_complete') is True
        and coverage.get('latest_session_present') is True
        and not coverage.get('missing_sessions')
        and not coverage.get('unverified_bar_sessions')
        and coverage.get('duplicate_bars') is False))
    # Reasons are data-readiness failures; descriptive limitations (e.g. volume)
    # live separately and continue to block signals, not qualified price evidence.
    qualified=(current and available and identity and not denied and freshness=='current'
               and market.get('warmup_complete') is True
               and valid_session(market.get('latest_session'))
               and not reasons and not technical.get('unavailable_reasons')
               and coverage_ready)
    job=row.get('price_refresh') or {}
    status=job.get('status')
    refresh_state={'queued':'pending','running':'pending','retry_wait':'pending',
                   'completed':'completed','failed':'failed','missed':'blocked',
                   'blocked':'blocked'}.get(status,'not_recorded')
    # A prior job proves only historical admission. The API has no authority to
    # certify today's private worker allowlist, account grants, token or quota.
    return dict(
        discovered=True,
        identity='verified_nse_eq' if identity else 'unverified',
        universe='eligible_nse_eq' if identity else 'not_verified',
        source_permission='denied' if denied else 'permitted_stored_research' if identity else 'not_verified',
        refresh_eligibility='previously_admitted_not_current_authorization' if job else 'not_verified',
        refresh_state=refresh_state,
        refresh_reason=job.get('reason') or (None if job else 'no_refresh_job_recorded_scope_not_verified'),
        research_eligibility='eligible_stored_research' if identity and not denied else 'blocked_or_unverified',
        research_state=research.get('status',row.get('research_status','pending')),
        evidence_basis='current_stored_review' if current else 'last_stored_analysis',
        evaluated_at=research.get('analyzed_at'),
        latest_observed_price_session=market.get('latest_session'),
        latest_qualified_price_session=market.get('latest_session') if qualified else None,
        completeness='warmup_complete' if market.get('warmup_complete') else 'insufficient_or_unavailable',
        freshness=freshness,
        blockers=reasons,
        signal='unqualified',signal_reason='volume_basis_unverified_not_a_complete_strategy_signal',
        actionable=False)
