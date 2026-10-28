"""STK-014/074 ingestion restrictions. OPEN never substitutes for source rights."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timezone

import psycopg
from stock_discovery_contracts.rights import UseRequest, authorize


@dataclass(frozen=True)
class IngestionPermit:
    identity: tuple[str, str, str, str]
    generations: tuple[int, ...]


def identity(grant):
    return grant.source_id, grant.account_ref, grant.grant_id, grant.version


def database_request(conn, request, uses):
    clock = conn.execute('SELECT clock_timestamp()').fetchone()[0]
    return UseRequest.model_validate({**request.model_dump(), 'uses': tuple(uses),
        'requested_at': clock.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})


@contextmanager
def sanitized_fence_errors():
    try:
        yield
    except psycopg.errors.InsufficientPrivilege:
        raise PermissionError('ingestion_access_restricted') from None


def capture(conn, grant, request, uses=('store',)):
    """Initialize lock rows only after ordinary rights validation; never reopen.

    Call before external work. With autocommit, the short locks release here.
    An enclosing caller transaction retains them until its own commit/rollback.
    """
    with sanitized_fence_errors(), conn.transaction():
        decision = authorize(grant, database_request(conn, request, uses))
        if not decision.allowed:
            raise PermissionError(decision.code)
        key = identity(grant)
        conn.execute('SELECT discovery.register_grant_fences(%s,%s,%s,%s)', key)
        generations = conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)', key).fetchone()[0]
        decision = authorize(grant, database_request(conn, request, uses))
        if not decision.allowed:
            raise PermissionError(decision.code)
        return IngestionPermit(key, tuple(generations))


def enforce(conn, permit, grant, request, uses=('store',)):
    """Must run inside the persistence transaction; holds locks to commit."""
    if grant is None or permit.identity != identity(grant):
        raise PermissionError('ingestion_grant_changed')
    with sanitized_fence_errors():
        generations = conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)', permit.identity).fetchone()[0]
        if tuple(generations) != permit.generations:
            raise PermissionError('ingestion_generation_changed')
        decision = authorize(grant, database_request(conn, request, uses))
        if not decision.allowed:
            raise PermissionError(decision.code)


def restrict(conn, *, request_id, kind, source_id, account_ref='', grant_id='', grant_version='',
             reason, policy_hash=None):
    """Operator-only SQL boundary authenticates session_user; no caller actor string.

    No release/deletion API exists. UUID idempotency keys and fixed reason codes
    prevent source content from entering audit records.
    """
    from .grant_fence_contracts import RestrictionRequest
    try:
        body = RestrictionRequest(request_id=request_id, kind=kind, source_id=source_id,
            account_ref=account_ref or None, grant_id=grant_id or None, grant_version=grant_version or None,
            reason=reason, policy_hash=policy_hash)
    except ValueError:
        raise ValueError('invalid_restriction_request') from None
    try:
        with sanitized_fence_errors(), conn.transaction():
            return conn.execute('SELECT discovery.restrict_grant_scope(%s,%s,%s,%s,%s,%s,%s,%s)',
                (body.request_id,kind,source_id,account_ref,grant_id,grant_version,reason,policy_hash)).fetchone()[0]
    except psycopg.Error:
        raise ValueError('restriction_request_failed') from None


def ingestion_access(conn, access):
    # Bind only ingestion adapters, not unrelated read/research configuration.
    from dataclasses import replace
    return replace(access, fence_conn=conn, fence_permits={})
