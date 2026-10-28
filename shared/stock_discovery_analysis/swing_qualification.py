"""STK-014: pure input qualification, never strategy or access authorization.

Trusted adapters must supply current grants, fence decisions and evidence-backed
attestations. This function performs no I/O and cannot activate a strategy.
"""
from dataclasses import asdict
from datetime import timezone
from decimal import Decimal
from typing import Literal

from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Text, Timestamp, at
from stock_discovery_contracts.rights import Grant, UseRequest, authorize
from .data import Candle, Provenance
from .calendar import Calendar
from .indicators import features
from .dataset import canonical

Requirement = Literal['prices', 'calendar', 'corporate_actions', 'instrument', 'filings', 'material_events']
SCOPES = dict(prices='prices', calendar='calendar', corporate_actions='corporate_actions',
              instrument='universe', filings='filings', material_events='news')


class InputEvidence(Strict):
    requirement: Requirement
    instrument_id: Text
    revision_id: Text
    acquisition_grant_id: Text
    acquisition_grant_version: Text
    acquisition_grant: Grant | None = None
    acquired_at: Timestamp | None = None
    revision_provenance: Provenance | None = None
    grant: Grant | None
    request: UseRequest
    observed_at: Timestamp
    covers_from: Timestamp
    covers_through: Timestamp
    fresh_until: Timestamp
    complete: bool
    # These are verified external decisions, not permissions created here.
    policy_evidence_ref: Text | None = None
    retention_compliant: bool | None = None
    deletion_obligations_supported: bool | None = None
    fences_open: bool | None = None


class SwingInputs(Strict):
    instrument_id: Text
    cutoff_at: Timestamp
    evidence: tuple[InputEvidence, ...]
    bars: tuple[Candle, ...]
    calendar: Calendar | None
    bar_revision_ids: tuple[Text, ...] = ()
    calendar_revision_id: Text | None = None
    price_basis: Literal['raw', 'split_bonus_adjusted', 'unknown'] = 'unknown'
    volume_basis: Literal['raw', 'adjusted', 'unknown'] = 'unknown'
    # First slice supports raw windows without actions only. Other bases require
    # a separately validated adjustment contract, never an inferred conversion.
    action_free_window: bool | None = None
    tick_size: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    lot_size: int | None = Field(default=None, gt=0)
    eligible: bool | None = None
    risk_prohibited: bool | None = None


class Qualification(Strict):
    status: Literal['INPUTS_QUALIFIED', 'INSUFFICIENT_EVIDENCE']
    instrument_id: Text
    cutoff_at: Timestamp
    checks: dict[str, tuple[str, ...]]
    provenance: tuple[tuple[str, str, str, str, str, str], ...]
    revision_lineage: tuple[tuple[str, str, str, str, str, str, str], ...]
    actionable: Literal[False] = False
    publication_authorized: Literal[False] = False
    paper_admission_authorized: Literal[False] = False


def qualify(inputs: SwingInputs) -> Qualification:
    """Assess one observed NSE equity window; unknowns remain explicit failures.

    No default grant, price basis, calendar coverage, tick, lot or eligibility.
    All contributing grants are evaluated independently, including mixed sources.
    Output contains linkage and reason codes, not market values or credentials.
    """
    q = inputs
    cutoff = at(q.cutoff_at).replace(tzinfo=timezone.utc)
    checks = {name: set() for name in (*SCOPES, 'history', 'adjustments', 'settings')}
    if not q.instrument_id.startswith('NSE:'):
        checks['settings'].add('nse_identity_required')
    # Use the same canonical Candle representation as quantitative input hashes.
    # Compare every candidate; never let first/last occurrence hide a conflict.
    payloads = {}
    unique = {}
    for i, candle in enumerate(q.bars):
        revision_id = q.bar_revision_ids[i] if i < len(q.bar_revision_ids) else None
        payload = canonical(asdict(candle))
        payloads.setdefault(revision_id, set()).add(payload)
        unique[(revision_id, payload)] = candle
    if any(len(values) > 1 for revision_id, values in payloads.items() if revision_id is not None):
        checks['prices'].add('conflicting_immutable_candle')
    bars = sorted(unique.values(), key=lambda b: (b.ends_at, b.starts_at, canonical(asdict(b))))
    start = bars[0].starts_at if bars else cutoff
    provenance = set()
    lineage = set()
    identities = {}
    for r in q.evidence:
        identity = (r.instrument_id, r.request.source_id, r.request.account_ref,
                    r.acquisition_grant_id, r.acquisition_grant_version, r.acquired_at,
                    r.revision_provenance,
                    r.acquisition_grant.model_dump_json() if r.acquisition_grant else None)
        identities.setdefault(r.revision_id, set()).add(identity)
    for name, scope in SCOPES.items():
        rows = [r for r in q.evidence if r.requirement == name]
        if not rows:
            checks[name].add('evidence_missing')
        for r in rows:
            g = r.grant
            provenance.add((name, r.revision_id, r.request.source_id, r.request.account_ref,
                            r.acquisition_grant_id, r.acquisition_grant_version))
            if len(identities[r.revision_id]) != 1:
                checks[name].add('conflicting_immutable_acquisition')
            original = r.acquisition_grant
            if original and (original.grant_id, original.version) != (r.acquisition_grant_id, r.acquisition_grant_version):
                checks[name].add('acquisition_grant_mismatch')
            p = r.revision_provenance
            lineage.add((r.revision_id, p.source_ref if p else '', p.source_version if p else '',
                p.published_at.isoformat() if p else '', p.available_at.isoformat() if p else '',
                p.fetched_at.isoformat() if p else '', r.acquired_at or ''))
            if p is None or r.acquired_at is None:
                checks[name].add('acquisition_provenance_missing')
            else:
                acquired = at(r.acquired_at).replace(tzinfo=timezone.utc)
                observed = at(r.observed_at).replace(tzinfo=timezone.utc)
                if acquired != p.fetched_at or not p.available_at <= acquired <= observed <= cutoff:
                    checks[name].add('acquisition_timestamp_conflict')
                if p.source_ref != r.request.source_id or p.availability_basis != 'observed_live':
                    checks[name].add('revision_provenance_mismatch')
                acquisition = authorize(original, r.request.model_copy(update={
                    'requested_at': r.acquired_at, 'uses': ('acquire',)}))
                if not acquisition.allowed:
                    checks[name].add('acquisition_rights:' + acquisition.code)
            decision = authorize(g, r.request.model_copy(update={
                'requested_at': q.cutoff_at, 'uses': tuple(sorted((set(r.request.uses) - {'acquire'}) | {'store', 'derive'}))}))
            if g and (g.grant_id, g.version) != (r.acquisition_grant_id, r.acquisition_grant_version):
                checks[name].add('acquisition_grant_mismatch')
            if not decision.allowed:
                checks[name].add('rights:' + decision.code)
            if r.request.synthetic or r.request.scope != scope or not {'acquire', 'store', 'derive'} <= set(r.request.uses):
                checks[name].add('required_real_use_scope_missing')
            if r.instrument_id != q.instrument_id:
                checks[name].add('instrument_mismatch')
            if not r.policy_evidence_ref or r.retention_compliant is not True or r.deletion_obligations_supported is not True:
                checks[name].add('retention_deletion_unverified')
            if r.fences_open is not True:
                checks[name].add('restriction_state_unverified_or_fenced')
            times = [at(t).replace(tzinfo=timezone.utc) for t in
                     (r.observed_at, r.covers_from, r.covers_through, r.fresh_until)]
            observed, first, last, fresh = times
            if observed > cutoff or first > start or last < cutoff or first > last or fresh < cutoff or not r.complete:
                checks[name].add('coverage_stale_incomplete_or_future')
    def attributed(provenance, requirement, revision_id):
        return revision_id is not None and any(
            r.requirement == requirement and r.revision_id == revision_id
            and r.revision_provenance == provenance
            and r.request.source_id == provenance.source_ref for r in q.evidence)
    if len(q.bar_revision_ids) != len(q.bars):
        checks['prices'].add('price_revision_links_missing')
    for i, b in enumerate(q.bars):
        revision_id = q.bar_revision_ids[i] if i < len(q.bar_revision_ids) else None
        if (b.instrument_id != q.instrument_id or b.ends_at > cutoff or
                b.provenance.availability_basis != 'observed_live' or not b.provenance.eligible(cutoff, live=True)):
            checks['history'].add('price_identity_or_point_in_time_invalid')
        if not attributed(b.provenance, 'prices', revision_id):
            checks['prices'].add('price_source_unattributed')
    if len({(b.starts_at, b.ends_at) for b in bars}) < 30:
        checks['history'].add('insufficient_history')
    cal = q.calendar
    if cal is None:
        checks['calendar'].add('calendar_missing')
    else:
        if cal.provenance.availability_basis != 'observed_live' or not cal.provenance.eligible(cutoff, live=True):
            checks['calendar'].add('calendar_point_in_time_invalid')
        if not attributed(cal.provenance, 'calendar', q.calendar_revision_id):
            checks['calendar'].add('calendar_source_unattributed')
        expected = [(s.opens_at, s.closes_at) for s in cal.sessions if start <= s.opens_at and s.closes_at <= cutoff]
        if not expected or [(b.starts_at, b.ends_at) for b in bars] != expected:
            checks['history'].add('closed_session_gap_duplicate_or_lag')
    if q.price_basis != 'raw' or q.volume_basis != 'raw' or any(b.adjustment_version != 'raw-v1' for b in bars):
        checks['adjustments'].add('unsupported_adjustment_basis')
    if q.action_free_window is not True:
        checks['adjustments'].add('action_effects_unqualified')
    if q.tick_size is None or q.lot_size is None or q.eligible is not True or q.risk_prohibited is not False:
        checks['settings'].add('instrument_settings_or_eligibility_unknown_or_prohibited')
    try:
        if not bars or any(v is None for v in features(tuple(bars)).values()) or any(b.volume <= 0 for b in bars):
            checks['history'].add('indicator_inputs_insufficient')
    except ValueError:
        checks['history'].add('indicator_inputs_invalid')
    return Qualification(status='INSUFFICIENT_EVIDENCE' if any(checks.values()) else 'INPUTS_QUALIFIED',
        instrument_id=q.instrument_id, cutoff_at=q.cutoff_at,
        checks={k: tuple(sorted(v)) for k, v in sorted(checks.items())}, provenance=tuple(sorted(provenance)), revision_lineage=tuple(sorted(lineage)))
