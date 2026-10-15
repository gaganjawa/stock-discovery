"""D3-02 rights gate: no network, provider credentials or implicit activation.

Infrastructure must supply the current grant and trusted operation time, and
recheck before each use. A grant is evidence-backed configuration, not evidence
that a provider actually granted rights. No real grants ship with this module.
"""
from datetime import timedelta
from typing import Annotated, Callable, Literal, TypeVar

from pydantic import Field, model_validator

from .v2 import Strict, Text, Timestamp, at, check

Use = Literal[
    "acquire", "store", "extract", "derive", "embed", "external_ai",
    "historical_replay", "paper_evaluation", "export", "backup", "train",
]
Scope = Literal[
    "prices", "universe", "calendar", "corporate_actions", "benchmark",
    "filings", "news", "financial_facts",
]
Region = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
Positive = Annotated[int, Field(gt=0)]


class Grant(Strict):
    schema_version: Literal["1.0.0"]
    grant_id: Text
    version: Text
    source_id: Text
    account_ref: Text
    status: Literal["pending", "active", "denied", "revoked"]
    synthetic: bool
    approval_evidence_ref: Text | None
    valid_from_at: Timestamp
    expires_at: Timestamp
    revoked_at: Timestamp | None
    allowed_uses: tuple[Use, ...]
    scopes: tuple[Scope, ...]
    regions: tuple[Region, ...]
    external_processors: tuple[Text, ...]
    retention_days: Positive | None
    deletion_deadline_days: Annotated[int, Field(ge=0)] | None
    attribution: Text | None
    max_units_per_operation: Positive | None
    # Explicit permission for retaining metadata-only audit tombstones on deletion.
    audit_tombstones_permitted: bool

    @model_validator(mode="after")
    def consistency(self):
        check(at(self.valid_from_at) < at(self.expires_at), "grant validity interval")
        check((self.revoked_at is not None) == (self.status == "revoked"), "revocation clock")
        for items in (self.allowed_uses, self.scopes, self.regions, self.external_processors):
            check(len(set(items)) == len(items), "duplicate grant scope")
        if self.status == "active":
            check(self.approval_evidence_ref is not None, "approval evidence required")
            check(bool(self.allowed_uses) and bool(self.scopes) and bool(self.regions), "active scope required")
            check(self.retention_days is not None and self.deletion_deadline_days is not None, "retention/deletion terms required")
            check(self.attribution is not None and self.max_units_per_operation is not None, "attribution/quota terms required")
        if self.synthetic:
            check(self.source_id.startswith("SYN-") and self.account_ref.startswith("SYN-"), "fictional source/account required")
        return self


class UseRequest(Strict):
    source_id: Text
    account_ref: Text
    scope: Scope
    # May be unknown so the gate can produce an explicit denial audit event.
    uses: Annotated[tuple[Text, ...], Field(min_length=1)]
    region: Region
    destination_region: Region | None
    processor_ref: Text | None
    requested_at: Timestamp
    synthetic: bool
    units: Positive
    retention_days: Positive
    attribution_present: bool

    @model_validator(mode="after")
    def unique_uses(self):
        check(len(set(self.uses)) == len(self.uses), "duplicate requested use")
        return self


class GrantDecision(Strict):
    allowed: bool
    code: Literal[
        "allowed", "grant_missing", "grant_not_active", "grant_not_yet_valid",
        "grant_expired", "source_account_mismatch", "synthetic_mismatch",
        "scope_denied", "use_denied", "region_denied", "destination_required",
        "destination_denied", "processor_denied", "retention_exceeded",
        "attribution_missing", "operation_limit_exceeded",
    ]
    grant_id: Text | None
    grant_version: Text | None
    source_id: Text
    requested_at: Timestamp
    uses: tuple[Text, ...]


def authorize(grant: Grant | None, request: UseRequest) -> GrantDecision:
    """Pure, fail-closed decision. Combined uses require every permission."""
    def result(code):
        return GrantDecision(
            allowed=code == "allowed", code=code,
            grant_id=grant.grant_id if grant else None,
            grant_version=grant.version if grant else None,
            source_id=request.source_id, requested_at=request.requested_at,
            uses=request.uses,
        )

    if grant is None:
        return result("grant_missing")
    if grant.status != "active":
        return result("grant_not_active")
    if (grant.source_id, grant.account_ref) != (request.source_id, request.account_ref):
        return result("source_account_mismatch")
    if grant.synthetic != request.synthetic:
        return result("synthetic_mismatch")
    if at(request.requested_at) < at(grant.valid_from_at):
        return result("grant_not_yet_valid")
    if at(request.requested_at) >= at(grant.expires_at):
        return result("grant_expired")
    if request.scope not in grant.scopes:
        return result("scope_denied")
    if not set(request.uses) <= set(grant.allowed_uses):
        return result("use_denied")
    if request.region not in grant.regions:
        return result("region_denied")
    if set(request.uses) & {"external_ai", "export", "backup"}:
        if request.destination_region is None:
            return result("destination_required")
    if request.destination_region is not None and request.destination_region not in grant.regions:
        return result("destination_denied")
    if "external_ai" in request.uses:
        if request.processor_ref not in grant.external_processors:
            return result("processor_denied")
    elif request.processor_ref is not None:
        # External processing cannot be concealed as local extraction/embedding.
        return result("use_denied")
    if request.retention_days > grant.retention_days:
        return result("retention_exceeded")
    if not request.attribution_present:
        return result("attribution_missing")
    if request.units > grant.max_units_per_operation:
        return result("operation_limit_exceeded")
    return result("allowed")


T = TypeVar("T")


def guarded_use(
    load_current_grant: Callable[[], Grant | None],
    request: UseRequest,
    audit: Callable[[GrantDecision], None],
    operation: Callable[[], T],
) -> T:
    """Audit then invoke only if allowed; reload grants for every operation.

No reusable authorization token is returned. This synchronous boundary does not
solve concurrent revocation, aggregate quotas or spend reservation; production
adapters must add transactional checks in later packages. Audit failure prevents
operation. Never pass credential values or source text into the decision log.
"""
    decision = authorize(load_current_grant(), request)
    audit(decision)
    if not decision.allowed:
        raise PermissionError(decision.code)
    return operation()


class CleanupPlan(Strict):
    stop_processing: Literal[True]
    delete_content: Literal[True]
    include_derived_and_backups: Literal[True]
    keep_metadata_tombstone: bool
    deadline_days: Annotated[int, Field(ge=0)]
    delete_by_at: Timestamp
    reason: Literal["revoked", "expired", "permission_unknown"]


def cleanup_plan(grant: Grant | None, now: Timestamp) -> CleanupPlan | None:
    """Plan only: D3-03 storage and D3-12 backups implement actual deletion.

Unknown terms conservatively request immediate deletion with no retained audit
metadata. A content-free tombstone still requires explicit permission.
"""
    clock = at(now)
    if grant and grant.status == "active" and at(grant.valid_from_at) <= clock < at(grant.expires_at):
        return None
    reason = "permission_unknown"
    if grant and grant.status == "revoked":
        reason = "revoked"
    elif grant and clock >= at(grant.expires_at):
        reason = "expired"
    anchor = at(grant.revoked_at) if reason == "revoked" else at(grant.expires_at) if reason == "expired" else clock
    days = (grant.deletion_deadline_days or 0) if grant and reason != "permission_unknown" else 0
    deadline = anchor + timedelta(days=days)
    return CleanupPlan(
        stop_processing=True, delete_content=True, include_derived_and_backups=True,
        keep_metadata_tombstone=grant.audit_tombstones_permitted if grant and reason != "permission_unknown" else False,
        deadline_days=days, delete_by_at=deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
        reason=reason,
    )
