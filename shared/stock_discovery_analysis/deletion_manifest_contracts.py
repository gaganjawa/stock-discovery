"""STK-074 synthetic inspection contracts; no deletion authority or source text."""
from typing import Annotated, Literal

from pydantic import Field
from stock_discovery_contracts.v2 import Strict, Hash, Timestamp

Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r'^[A-Za-z0-9_.:-]+$')]
SyntheticIdentifier = Annotated[str, Field(max_length=160, pattern=r'^SYN-[A-Za-z0-9_.:-]+$')]


class GrantScope(Strict):
    source_id: SyntheticIdentifier
    account_ref: SyntheticIdentifier
    grant_id: Identifier
    grant_version: Identifier


class ManifestRequest(GrantScope):
    schema_version: Literal['1.0.0'] = '1.0.0'
    synthetic: Literal[True] = True
    trigger: Literal['expiry', 'revocation']
    as_of_at: Timestamp


class ArtifactRef(Strict):
    artifact_type: Identifier
    # Primary-key values in database primary-key order. No arbitrary predicates.
    key: Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=3)]


class ExternalCopy(Strict):
    """Caller-supplied fixture registry metadata, never a path to open or delete."""
    copy_id: SyntheticIdentifier
    kind: Literal['filesystem', 'backup']
    synthetic: Literal[True] = True
    dependencies: Annotated[tuple[ArtifactRef, ...], Field(max_length=100)] = ()
    grants: Annotated[tuple[GrantScope, ...], Field(max_length=100)] = ()
    lineage_complete: bool = False


class Dependency(Strict):
    artifact_type: str
    identifier: Hash
    reason: Literal['foreign_key', 'json_reference', 'source_scope_only', 'copied_text_candidate',
                    'blob_owner', 'stream_member', 'container_member', 'registered_copy']


class ManifestArtifact(Strict):
    artifact_type: str
    # Opaque identity, not a content digest. Raw IDs/paths/quotes never leave the reader.
    identifier: Hash
    source_linkage: tuple[Hash, ...]
    relationship: Literal['exclusive_in_known_graph', 'shared', 'unknown']
    dependency_reasons: tuple[Dependency, ...]
    lineage_issues: tuple[str, ...]
    proposed_disposition: Literal['review_exclusive', 'review_shared', 'resolve_lineage']
    deletion_authorized: Literal[False] = False
    retention_authorized: Literal[False] = False


class DeletionManifest(Strict):
    schema_version: Literal['1.0.0'] = '1.0.0'
    synthetic: Literal[True] = True
    target: Hash
    trigger: Literal['expiry', 'revocation']
    as_of_at: Timestamp
    artifacts: tuple[ManifestArtifact, ...]
    unresolved_artifacts: tuple[ManifestArtifact, ...]
    inspected_tables: tuple[str, ...]
    limitations: tuple[str, ...]
    policy_status: Literal['UNVERIFIED'] = 'UNVERIFIED'
    complete: Literal[False] = False
    actionable: Literal[False] = False
    manifest_hash: Hash
