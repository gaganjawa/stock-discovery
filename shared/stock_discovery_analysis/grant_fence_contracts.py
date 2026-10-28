"""Access restriction decisions are independent of destructive authorization."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Hash, check

Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r'^[A-Za-z0-9_.:@/-]+$')]


class FenceScope(Strict):
    kind: Literal['provider', 'account', 'grant']
    source_id: Identifier
    account_ref: Identifier | None = None
    grant_id: Identifier | None = None
    grant_version: Identifier | None = None

    @model_validator(mode='after')
    def shape(self):
        check((self.account_ref is not None) == (self.kind != 'provider'), 'fence_account_scope')
        check((self.grant_id is not None) == (self.kind == 'grant'), 'fence_grant_scope')
        check((self.grant_version is not None) == (self.kind == 'grant'), 'fence_version_scope')
        return self


class RestrictionRequest(FenceScope):
    request_id: UUID
    reason: Literal['revoked', 'policy_unverified', 'deletion_pending', 'expired']
    policy_hash: Hash | None = None
    deletion_authorized: Literal[False] = False
