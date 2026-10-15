"""STK-001/002/003: strict wire contracts and deterministic relational checks.

Structural validation alone is not publication approval. Use validate_bundle for
snapshot/calendar/reference checks. No data acquisition or policy activation.
"""
from __future__ import annotations

import calendar
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Timestamp = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
Number = Annotated[str, StringConstraints(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")]
Mode = Literal["synthetic", "historical_reconstructed", "live_paper"]
Arm = Literal["quant", "quant_rag", "quant_agent", "traditional_ml"]
Profile = Literal["swing", "short_term", "long_term"]
PolicyKind = Literal["strategy", "horizon", "research", "risk", "cost", "retrieval", "schedule", "universe"]


def check(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def at(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="after")
    def valid_timestamps(self):
        # Validate dates, not merely their lexical shape, in every nested record.
        for key, value in self.__dict__.items():
            if key.endswith("_at") and value is not None:
                at(value)
        return self


class Ref(Strict):
    id: Text
    version: Text
    content_hash: Hash


class Policy(Strict):
    schema_version: Literal["2.0.0"]
    ref: Ref
    kind: PolicyKind
    profile: Profile
    status: Literal["unconfigured", "fixture", "approved"]
    effective_at: Timestamp
    # Typed, bounded parameters rather than an arbitrary executable configuration.
    parameters: Annotated[list["Parameter"], Field(min_length=1)]
    approval_ref: Text | None

    @model_validator(mode="after")
    def consistency(self):
        check(len({p.name for p in self.parameters}) == len(self.parameters), "duplicate parameter")
        check(self.ref.content_hash == digest([p.model_dump() for p in self.parameters]), "policy hash mismatch")
        check((self.approval_ref is not None) == (self.status == "approved"), "policy approval mismatch")
        return self


class Parameter(Strict):
    name: Text
    value: Number | None
    unit: Text
    unavailable_reason: Text | None

    @model_validator(mode="after")
    def availability(self):
        check((self.value is None) == (self.unavailable_reason is not None), "parameter availability")
        return self


class PolicyRefs(Strict):
    strategy: Ref
    horizon: Ref
    research: Ref
    risk: Ref
    cost: Ref
    retrieval: Ref
    schedule: Ref
    universe: Ref


class Horizon(Strict):
    schema_version: Literal["2.0.0"]
    profile: Profile
    minimum: int
    maximum: int
    units: Literal["trading_sessions", "calendar_months", "calendar_years"]
    duration: int
    review_cadence: Literal["each_session", "weekly", "monthly"]
    anchor_at: Timestamp
    holding_end_at: Timestamp
    next_review_at: Timestamp
    entry_expires_at: Timestamp
    calendar_ref: Ref

    @model_validator(mode="after")
    def range_and_clocks(self):
        expected = {"swing": (2, 10, "trading_sessions"), "short_term": (1, 3, "calendar_months"), "long_term": (1, 5, "calendar_years")}[self.profile]
        check((self.minimum, self.maximum, self.units) == expected, "horizon range/units")
        check(self.review_cadence == {"swing": "each_session", "short_term": "weekly", "long_term": "monthly"}[self.profile], "review cadence")
        check(self.minimum <= self.duration <= self.maximum, "horizon duration")
        check(at(self.anchor_at) < at(self.entry_expires_at) <= at(self.holding_end_at), "horizon expiry")
        check(at(self.anchor_at) < at(self.next_review_at) <= at(self.holding_end_at), "horizon review")
        return self


class Instrument(Strict):
    instrument_id: Text
    issuer_id: Text
    symbol: Text
    exchange: Literal["SYNTHETIC_NSE", "NSE"]
    series: Literal["EQ"]
    isin: Text | None
    currency: Literal["INR"]
    exchange_timezone: Literal["Asia/Kolkata"]
    lot_size: Annotated[int, Field(gt=0)]


class Strategy(Strict):
    id: Text
    version: Text
    config_version: Text


class Cohort(Strict):
    arm: Arm
    config_hash: Hash
    capability: Literal["technical_only", "researched", "predictive"]
    shadow: bool


class Evidence(Strict):
    evidence_id: Text
    revision_id: Text
    instrument_id: Text
    kind: Literal["closed_candles", "filing", "news", "fact"]
    source_ref: Text
    source_version: Text
    locator: Text
    published_at: Timestamp
    available_at: Timestamp
    fetched_at: Timestamp
    period_end_at: Timestamp | None
    availability_basis: Literal["fictional_fixture", "observed", "verified_archive"]
    archive_verification_ref: Text | None
    summary: Text


class Missing(Strict):
    requirement: Text
    reason: Text
    blocking: bool


class Rationale(Strict):
    summary: Text
    evidence_ids: list[Text]


class Versions(Strict):
    code: Text
    dataset: Text
    model: Text | None
    prompt: Text | None


class Quality(Strict):
    coverage: Number | None
    freshness: Literal["fresh", "stale", "unknown"]
    source_quality: Literal["primary", "secondary", "mixed", "unknown"]
    claim_support: Number | None
    contradiction_ids: list[Text]
    uncertainty: list[Text]
    missing_required: list[Text]

    @model_validator(mode="after")
    def fractions(self):
        for value in (self.coverage, self.claim_support):
            check(value is None or Decimal(0) <= Decimal(value) <= Decimal(1), "quality fraction")
        return self


class Condition(Strict):
    code: Text
    explanation: Text
    evidence_ids: list[Text]


class Conditions(Strict):
    entry: list[Condition]
    invalidation: list[Condition]
    review: Annotated[list[Condition], Field(min_length=1)]
    expires_at: Timestamp


class Valuation(Strict):
    low: Number
    high: Number
    currency: Literal["INR"]
    valued_at: Timestamp
    assumptions: Annotated[list[Text], Field(min_length=1)]
    calculation_ids: Annotated[list[Text], Field(min_length=1)]

    @model_validator(mode="after")
    def price_range(self):
        check(0 < Decimal(self.low) <= Decimal(self.high), "valuation range")
        return self


class Execution(Strict):
    profile: Profile
    side: Literal["OPEN_LONG"]
    entry_type: Literal["buy_stop", "limit", "next_open"]
    entry_price: Number
    stop_price: Number
    target_price: Number | None
    earliest_entry_at: Timestamp
    entry_expires_at: Timestamp
    time_exit_at: Timestamp
    assumptions_ref: Ref

    @model_validator(mode="after")
    def prices(self):
        check(0 < Decimal(self.stop_price) < Decimal(self.entry_price), "long price barriers")
        check(self.target_price is None or Decimal(self.entry_price) < Decimal(self.target_price), "long target")
        check(at(self.earliest_entry_at) < at(self.entry_expires_at) <= at(self.time_exit_at), "execution window")
        return self


class Risk(Strict):
    eligibility: Literal["eligible", "blocked", "unknown"]
    binding_constraints: list[Text]
    risk_ref: Text | None
    capital_profile_ref: Text | None


class Admission(Strict):
    status: Literal["not_requested", "admitted", "blocked", "expired"]
    reservation_ref: Text | None
    reason: Text
    quantity: Annotated[int, Field(gt=0)] | None

    @model_validator(mode="after")
    def quantity_only_when_admitted(self):
        admitted = self.status == "admitted"
        check((self.quantity is not None) == admitted, "quantity requires admission")
        check((self.reservation_ref is not None) == admitted, "reservation requires admission")
        return self


class Recommendation(Strict):
    schema_version: Literal["2.0.0"]
    recommendation_id: Text
    synthetic: bool
    mode: Mode
    run_id: Text
    instrument: Instrument
    strategy: Strategy
    horizon: Horizon
    information_cutoff_at: Timestamp
    generated_at: Timestamp
    decision_available_at: Timestamp
    availability_simulated: bool
    action: Literal["BUY", "WATCH", "AVOID", "INSUFFICIENT_EVIDENCE"]
    cohort: Cohort
    candidate_origin: Literal["quant", "event", "both"]
    event_ids: list[Text]
    snapshot_id: Text
    baseline_ref: Text
    research_status: Literal["not_requested", "succeeded", "failed", "unavailable"]
    research_ref: Text | None
    validation_ref: Text | None
    judge_ref: Text | None
    research_unavailable_reason: Text | None
    policy_refs: PolicyRefs
    evidence: list[Evidence]
    missing_evidence: list[Missing]
    rationale: Rationale
    versions: Versions
    evidence_quality: Quality
    conditions: Conditions
    valuation: Valuation | None
    execution: Execution | None
    risk_context: Risk
    paper_admission: Admission
    action_reason_codes: Annotated[list[Text], Field(min_length=1)]
    revises_id: Text | None
    revision_reason: Text | None

    @model_validator(mode="after")
    def semantics(self):
        cutoff, generated, available = map(at, (self.information_cutoff_at, self.generated_at, self.decision_available_at))
        check(cutoff < available and cutoff <= generated, "decision clocks")
        check(self.synthetic == (self.mode == "synthetic"), "synthetic mode mismatch")
        check(self.availability_simulated == (self.mode != "live_paper"), "availability mode")
        if self.mode == "live_paper":
            check(generated <= available, "backdated live publication")
        else:
            check(available <= generated, "simulated availability exceeds generation")
        check((self.instrument.exchange == "SYNTHETIC_NSE") == self.synthetic, "instrument mode")
        check((self.instrument.isin is None) == self.synthetic, "instrument identity")
        check((self.revises_id is None) == (self.revision_reason is None), "revision reason")
        check(self.revises_id != self.recommendation_id, "self revision")
        check(bool(self.event_ids) == (self.candidate_origin in ("event", "both")), "event origin")
        check(self.horizon.anchor_at == self.decision_available_at, "holding anchor")
        check(self.conditions.expires_at == self.horizon.entry_expires_at, "condition expiry")
        ids = {e.evidence_id for e in self.evidence}
        check(len(ids) == len(self.evidence), "duplicate evidence")
        citations = self.rationale.evidence_ids + [i for c in self.conditions.entry + self.conditions.invalidation + self.conditions.review for i in c.evidence_ids]
        check(set(citations) <= ids, "unknown citation")
        for evidence in self.evidence:
            check(evidence.instrument_id == self.instrument.instrument_id, "evidence issuer mismatch")
            pub, avail, fetched = map(at, (evidence.published_at, evidence.available_at, evidence.fetched_at))
            check(pub <= avail <= cutoff and avail <= fetched <= generated, "future evidence")
            if self.mode == "live_paper":
                check(fetched <= cutoff and evidence.availability_basis == "observed", "late live fetch")
            elif self.mode == "synthetic":
                check(evidence.availability_basis == "fictional_fixture", "fictional provenance required")
            else:
                check(evidence.availability_basis == "verified_archive" and evidence.archive_verification_ref is not None, "unverified historical revision")
            if evidence.kind == "closed_candles":
                check(evidence.period_end_at is not None and at(evidence.period_end_at) <= pub, "unclosed bar")
        refs = (self.research_ref, self.validation_ref, self.judge_ref)
        success = self.research_status == "succeeded"
        check((all(r is not None for r in refs) and self.research_unavailable_reason is None) if success else (all(r is None for r in refs) and self.research_unavailable_reason is not None), "research reference availability")
        ai = self.cohort.arm in ("quant_rag", "quant_agent")
        check(not success or (ai and self.cohort.capability == "researched"), "research cohort")
        check(self.cohort.arm != "quant" or self.cohort.capability == "technical_only", "quant capability")
        check(self.cohort.arm != "traditional_ml" or self.cohort.capability == "predictive", "ML capability")
        if success:
            check(self.versions.model is not None and self.versions.prompt is not None, "missing research versions")
        if self.action == "BUY":
            check(bool(self.evidence) and bool(self.rationale.evidence_ids), "BUY evidence required")
            check(self.execution is not None and bool(self.conditions.entry) and bool(self.conditions.invalidation), "BUY plan required")
            check(not any(m.blocking for m in self.missing_evidence) and not self.evidence_quality.missing_required, "blocking missing evidence")
            check(not ai or success, "failed AI cannot BUY")
            check(self.risk_context.eligibility != "blocked", "research risk prohibition")
        else:
            check(self.execution is None, "non-BUY execution")
        if self.execution:
            x = self.execution
            check(x.profile == self.horizon.profile and x.time_exit_at == self.horizon.holding_end_at and x.entry_expires_at == self.horizon.entry_expires_at, "execution horizon mismatch")
            check(at(x.earliest_entry_at) > available, "entry before publication")
            check(x.assumptions_ref == self.policy_refs.cost, "execution cost policy")
        admission = self.paper_admission
        if admission.status == "admitted":
            check(self.action == "BUY" and not self.cohort.shadow, "non-actionable admission")
            check(self.risk_context.eligibility == "eligible" and self.risk_context.risk_ref is not None and self.risk_context.capital_profile_ref is not None, "missing admission risk/capital")
            check(admission.quantity % self.instrument.lot_size == 0, "whole lots required")
        if self.valuation:
            check(at(self.valuation.valued_at) <= cutoff, "future valuation")
        return self


class Outcome(Strict):
    schema_version: Literal["2.0.0"]
    outcome_id: Text
    recommendation_id: Text
    mode: Mode
    horizon: Horizon
    cohort: Cohort
    evaluated_at: Timestamp
    observation_cutoff_at: Timestamp
    observation_manifest_ref: Ref
    evaluator_ref: Ref
    cost_policy_ref: Ref
    status: Literal["provisional", "matured", "no_entry", "ambiguous", "unavailable", "not_applicable"]
    reason_codes: Annotated[list[Text], Field(min_length=1)]
    realized_return: Number | None
    thesis_result: Literal["supported", "invalidated", "unknown"]
    supersedes_outcome_id: Text | None

    @model_validator(mode="after")
    def maturity(self):
        check(at(self.observation_cutoff_at) <= at(self.evaluated_at), "future outcome observation")
        if self.status == "matured":
            check(at(self.horizon.holding_end_at) <= at(self.observation_cutoff_at), "immature endpoint")
        if self.status in ("ambiguous", "unavailable", "not_applicable", "no_entry"):
            check(self.realized_return is None, "unavailable return is not zero")
        check(self.supersedes_outcome_id != self.outcome_id, "self outcome revision")
        return self


class ReferenceRecord(Strict):
    id: Text
    kind: Literal["baseline", "research", "validation", "judge", "event", "calculation", "risk", "capital", "reservation", "archive", "contradiction"]
    snapshot_id: Text
    instrument_id: Text
    assessment_id: Text | None
    passed: bool | None
    quantity: Annotated[int, Field(gt=0)] | None


class Snapshot(Strict):
    snapshot_id: Text
    mode: Mode
    information_cutoff_at: Timestamp
    calendar_ref: Ref
    # Complete pinned session closes through every represented holding endpoint.
    session_closes: Annotated[list[Timestamp], Field(min_length=1)]
    evidence: list[Evidence]
    references: list[ReferenceRecord]
    policies: list[Policy]


class ObservationManifest(Strict):
    ref: Ref
    mode: Mode
    observation_cutoff_at: Timestamp
    revision_ids: Annotated[list[Text], Field(min_length=1)]

    @model_validator(mode="after")
    def manifest_hash(self):
        check(len(set(self.revision_ids)) == len(self.revision_ids), "duplicate observation revision")
        check(self.ref.content_hash == digest(self.revision_ids), "observation manifest hash")
        return self


class Bundle(Strict):
    schema_version: Literal["2.0.0"]
    snapshot: Snapshot
    recommendations: list[Recommendation]
    outcomes: list[Outcome]
    observation_manifests: list[ObservationManifest]
    evaluator_refs: list[Ref]


def resolve_endpoint(h: Horizon, sessions: list[str]) -> str:
    closes = [at(s) for s in sessions]
    anchor = at(h.anchor_at)
    if h.profile == "swing":
        after = [s for s in closes if s > anchor]
        check(len(after) >= h.duration, "incomplete calendar")
        return after[h.duration - 1].strftime("%Y-%m-%dT%H:%M:%SZ")
    months = h.duration * (12 if h.profile == "long_term" else 1)
    index = anchor.year * 12 + anchor.month - 1 + months
    year, month = index // 12, index % 12 + 1
    target = date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))
    check(closes[-1].date() >= target, "incomplete calendar")
    return max(s for s in closes if s.date() <= target).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_bundle(payload: dict) -> Bundle:
    """Validate frozen relations; never fetch missing references or infer policies."""
    bundle = Bundle.model_validate(payload)
    snap = bundle.snapshot
    closes = snap.session_closes
    check(closes == sorted(set(closes)), "calendar ordering/duplicates")
    for close in closes:
        at(close)
    check(snap.calendar_ref.content_hash == digest(closes), "changed calendar")
    refs = {r.id: r for r in snap.references}
    check(len(refs) == len(snap.references), "duplicate reference")
    evidence = {e.evidence_id: e for e in snap.evidence}
    check(len(evidence) == len(snap.evidence), "duplicate snapshot evidence")
    policies = {p.ref.id: p for p in snap.policies}
    check(len(policies) == len(snap.policies), "duplicate policy")
    recs = {r.recommendation_id: r for r in bundle.recommendations}
    check(len(recs) == len(bundle.recommendations), "duplicate recommendation")
    for rec in recs.values():
        check((rec.snapshot_id, rec.mode, rec.information_cutoff_at) == (snap.snapshot_id, snap.mode, snap.information_cutoff_at), "snapshot mismatch")
        h = rec.horizon
        check(h.calendar_ref == snap.calendar_ref, "calendar reference")
        check(h.holding_end_at == resolve_endpoint(h, closes), "holding endpoint differs from frozen calendar")
        for item in rec.evidence:
            check(evidence.get(item.evidence_id) == item, "evidence revision not in snapshot")
        def resolve(ref_id, kind):
            if ref_id is None:
                return None
            record = refs.get(ref_id)
            check(record is not None and record.kind == kind and record.snapshot_id == snap.snapshot_id and record.instrument_id == rec.instrument.instrument_id, "unresolved or foreign " + kind)
            return record
        resolve(rec.baseline_ref, "baseline")
        for field, kind in ((rec.research_ref, "research"), (rec.validation_ref, "validation"), (rec.judge_ref, "judge")):
            record = resolve(field, kind)
            if record:
                check(record.assessment_id == rec.research_ref, "assessment mismatch")
                check(record.passed is True, "failed research validation/judge")
        for ref_id in rec.event_ids:
            resolve(ref_id, "event")
        for item in rec.evidence:
            resolve(item.archive_verification_ref, "archive")
        for ref_id in rec.evidence_quality.contradiction_ids:
            resolve(ref_id, "contradiction")
        for ref_id in rec.valuation.calculation_ids if rec.valuation else []:
            resolve(ref_id, "calculation")
        risk_record = resolve(rec.risk_context.risk_ref, "risk")
        reservation_record = resolve(rec.paper_admission.reservation_ref, "reservation")
        if rec.paper_admission.status == "admitted":
            for record in (risk_record, reservation_record):
                check(record.passed is True and record.quantity == rec.paper_admission.quantity, "admission differs from risk/reservation")
        resolve(rec.risk_context.capital_profile_ref, "capital")
        resolve(rec.paper_admission.reservation_ref, "reservation")
        for kind in PolicyRefs.model_fields:
            ref = getattr(rec.policy_refs, kind)
            policy = policies.get(ref.id)
            check(policy is not None and policy.ref == ref and policy.kind == kind and policy.profile == h.profile, "policy reference mismatch")
            check(at(policy.effective_at) <= at(rec.information_cutoff_at), "future policy")
            if rec.action == "BUY":
                check(policy.status == ("fixture" if rec.synthetic else "approved"), "unconfigured BUY policy")
                check(all(p.value is not None for p in policy.parameters), "missing policy parameter")
        if rec.revises_id:
            old = recs.get(rec.revises_id)
            check(old is not None and old.instrument == rec.instrument and at(old.generated_at) < at(rec.generated_at), "invalid recommendation revision")
    outcomes = {o.outcome_id: o for o in bundle.outcomes}
    check(len(outcomes) == len(bundle.outcomes), "duplicate outcome")
    manifests = {m.ref.id: m for m in bundle.observation_manifests}
    check(len(manifests) == len(bundle.observation_manifests), "duplicate observation manifest")
    check(len({r.id for r in bundle.evaluator_refs}) == len(bundle.evaluator_refs), "duplicate evaluator")
    for outcome in outcomes.values():
        manifest = manifests.get(outcome.observation_manifest_ref.id)
        check(manifest is not None and manifest.ref == outcome.observation_manifest_ref and manifest.mode == outcome.mode and manifest.observation_cutoff_at == outcome.observation_cutoff_at, "unresolved observation manifest")
        check(outcome.evaluator_ref in bundle.evaluator_refs, "unresolved evaluator")
        rec = recs.get(outcome.recommendation_id)
        check(rec is not None, "unresolved outcome recommendation")
        check((outcome.mode, outcome.horizon, outcome.cohort, outcome.cost_policy_ref) == (rec.mode, rec.horizon, rec.cohort, rec.policy_refs.cost), "outcome cohort/horizon/policy mismatch")
        check(at(outcome.evaluated_at) >= at(rec.generated_at), "outcome before generation")
        if outcome.realized_return is not None:
            check(rec.paper_admission.status == "admitted", "return without paper admission")
        if rec.action != "BUY":
            check(outcome.status in ("not_applicable", "unavailable"), "non-BUY trade outcome")
        if outcome.supersedes_outcome_id:
            old = outcomes.get(outcome.supersedes_outcome_id)
            check(old is not None and old.recommendation_id == outcome.recommendation_id and at(old.evaluated_at) < at(outcome.evaluated_at), "invalid outcome revision")
    return bundle


def parse_json(text: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            check(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def reject(value):
        raise ValueError("non-JSON constant: " + value)
    payload = json.loads(text, object_pairs_hook=unique, parse_constant=reject)
    check(isinstance(payload, dict), "record object required")
    return payload


def read_record(text: str, *, kind: Literal["recommendation", "outcome"], accepted_versions: set[str]):
    """Explicit version negotiation. Legacy reads are lossless, not v2 migrations.

Legacy integrity continues to be checked by the existing v1 validators/replay;
this boundary intentionally does not pretend to revalidate arbitrary v1 records.
"""
    payload = parse_json(text)
    version = payload.get("schema_version")
    check(version in accepted_versions, "contract version not negotiated")
    check(kind in ("recommendation", "outcome"), "unknown record kind")
    if version == "2.0.0":
        return (Recommendation if kind == "recommendation" else Outcome).model_validate(payload)
    allowed = {"1.0.0"} if kind == "recommendation" else {"1.0.0", "1.1.0"}
    check(version in allowed, "unsupported contract version")
    return payload


class CohortSummary(Strict):
    """Failure-inclusive denominators; no investment metrics are computed here."""
    schema_version: Literal["2.0.0"]
    mode: Mode
    profile: Profile
    cohort: Cohort
    decisions: Annotated[int, Field(ge=0)]
    buy: Annotated[int, Field(ge=0)]
    watch: Annotated[int, Field(ge=0)]
    avoid: Annotated[int, Field(ge=0)]
    insufficient_evidence: Annotated[int, Field(ge=0)]
    research_failed: Annotated[int, Field(ge=0)]
    eligible: Annotated[int, Field(ge=0)]
    resolved: Annotated[int, Field(ge=0)]
    missing: Annotated[int, Field(ge=0)]
    ambiguous: Annotated[int, Field(ge=0)]
    provisional: Annotated[int, Field(ge=0)]
    no_entry: Annotated[int, Field(ge=0)]
    net_expectancy: Number | None
    metric_unavailable_reason: Text | None

    @model_validator(mode="after")
    def denominators(self):
        check(self.decisions == self.buy + self.watch + self.avoid + self.insufficient_evidence, "action denominator")
        check(self.research_failed <= self.decisions, "research failure count")
        check(self.eligible == self.resolved + self.missing + self.ambiguous + self.provisional + self.no_entry, "outcome denominator")
        check(self.eligible <= self.buy, "eligible exceeds BUY count")
        check((self.net_expectancy is None) == (self.metric_unavailable_reason is not None), "metric availability")
        check(self.resolved > 0 or self.net_expectancy is None, "zero resolved metric")
        return self
