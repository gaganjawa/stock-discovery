# STK-074 — synthetic read-only deletion manifest

This is a dependency-inspection tool, not deletion implementation or operational
acceptance. Provider policy, deletion authority and the asserted expiry/revocation
trigger remain **UNVERIFIED**. Publication, paper admission and trading are unchanged.

## Entry point and contract

`stock_discovery_analysis.deletion_manifest.manifest(connection, request,
external_copies=())` returns a strict `DeletionManifest`. It has no API route, job
handler, filesystem crawler or production activation switch. It never persists a
manifest or invokes providers, models, deletion or publication.

Supply source ID, account reference, grant ID, grant version, a simulated `expiry`
or `revocation` trigger and explicit `as_of_at`. Source/account must use `SYN-`
identities. An exact stored synthetic grant must exist. Current stored grants are
not amended, and the trigger is not treated as evidence that permissions changed.
`as_of_at` is supplied inspection context, not a historical data-visibility filter:
the manifest inventories all supported records in the current database snapshot.

Only an idle autocommit connection to a disposable database named `stk013_test`,
`stk013_test_*` or `stk074_manifest_*` is accepted. Mixed real/synthetic grants,
observed revisions and explicitly non-synthetic modes are rejected. Synthetic
labelling is trusted fixture metadata, not proof that arbitrary supplied text is
fictional; never point this tool at private data, even in a renamed database.

The reader uses a repeatable-read, read-only PostgreSQL transaction, a five-second
statement timeout, 10,000-row/16-MiB uncompressed JSON inventory limits, at most 100
grants and 50,000 dependency edges, and bounded exact text comparisons. Exceeding a
bound fails rather than emitting a truncated manifest.
Inputs and DB failures are reduced to fixed error codes without input/row text.

Each artifact includes its type, an opaque identity derived from table/type and
primary key, grant-scope linkage tokens, dependency reasons, lineage issues,
relationship and proposed review disposition. `artifact_token()` and `scope_token()`
allow fixture callers to resolve identities without printing keys or source content.
They are not erasure receipts or legally approved audit tombstones.

- `exclusive_in_known_graph` means only one grant was found in supported lineage.
  It is not a statement of legal ownership or proof of complete lineage.
- `shared` means more than one grant contributes; independent retention rights
  must still be established.
- `unknown` and `resolve_lineage` disclose unresolved or unpinned relationships.
- `deletion_authorized` and `retention_authorized` are always false. The overall
  manifest is always non-actionable and incomplete for the full data lifecycle.

Artifacts dependent on the target are separated from unresolved artifacts whose
relationship to the target cannot be decided. Unresolved entries are not assertions
that the target owns them. Output excludes raw IDs, paths, source text, numbers,
grant documents and excerpts. Only fixed reason codes and opaque identifiers leave
the inspector. Sorting and hashing exclude runtime clocks and request order: repeated
requests over the same snapshot/registration metadata produce identical output.

## Traversal and coverage

The existing discovery/paper primary keys and foreign keys supply relational edges.
Versioned JSON reference fields add citations, document/fact/input IDs, snapshots,
research runs, bundles, recommendations, jobs and experiment relationships.
Known aggregate ownership links include snapshot members, worker receipts, research
reservations, publication batches and portfolio/experiment children.

Evidence blobs derive ownership from every referencing document. A shared blob does
not propagate ownership back into an unrelated provider's document. Stream metadata
collects its revision memberships; it does not relabel all revisions under the first
grant encountered. Missing references and source-only references without a pinned
grant/version remain explicit issues. In particular, streams/pages do not record
the grant used for each acquisition. When multiple source/account grants exist,
their scope is conservatively unresolved even if member revisions have exact
acquisition grants; this does not relabel those revisions.

JSON attributions are resolved independently using source/account/grant/version
fields in the same object. A co-located stored revision can corroborate those
fields; a citation elsewhere cannot erase unknown or conflicting attribution.
Other matching scopes remain uncertain candidates, including full scopes supplied
in JSON. Unregistered sources and invalid qualifiers are explicit lineage issues.
Plain text is not parsed as authoritative provenance.

Exact matching of chunks of at least 24 characters to copied JSON text identifies
possible unlinked excerpts. Such matches are labelled uncertain, including common
text shared by providers. Paraphrases, short excerpts, numerical copies without
provenance and unknown JSON keys cannot be conclusively attributed.

Supported tables cover revisions/grants/streams, ingestion pages/quarantine,
evidence bodies/documents/chunks/facts/claims/batches, snapshots, RAG/agent results,
scheduler metadata/receipts, publication, paper and experiment records. The existing
legacy `research` schema and future unrecognised tables are explicitly uninspected;
their presence is reported using opaque table tokens. No table/schema is created.

`ExternalCopy` is optional synthetic registry metadata: an opaque `SYN-` copy ID,
`filesystem` or `backup` kind, database or registered-copy `ArtifactRef` dependencies and/or exact grant
scopes. There is deliberately no path, URL or content field. Missing registrations,
broken references and incomplete registration assertions are unresolved. Registry
completeness cannot be independently proven. No files or backup services are read.
All copy nodes are registered before resolving dependencies. Forward references and
cycles are independent of registration order; missing references propagate uncertainty.
Cycles without a grant anchor remain unattributed. Cycles never establish completeness
or deletion/retention authorization.

Unsupported locations include unregistered files/exports/logs, temporary extraction
files, Ollama process/cache state, WAL, volume snapshots and physical media. There
is no claim that a manifest covers or erases those locations.

## Validation and next dependencies

`backend/tests/test_deletion_manifest_contracts.py` tests input, connection and privacy guards.
`backend/tests/integration/test_deletion_manifest.py` uses existing ingestion with
synthetic grants/documents and structural downstream fixtures in disposable
PostgreSQL. It checks provider/account/grant-version isolation, shared blobs, mixed
research, copied citations/text, missing lineage, external registrations,
determinism, read-only transaction settings and whole-database before/after equality.
No real financial performance or operational deletion acceptance is asserted.

The integration harness creates isolated databases without issuing deletion,
truncation or trigger-disabling SQL. Run it only in disposable PostgreSQL and remove
the task-owned container afterwards; database cleanup belongs to that harness.

Next work requires policy verification (STK-004/006/007), authoritative artifact/file
registration and unknown-lineage resolution, then separately approved deletion
authority, fences, audit policy and restore reconciliation (STK-014/015/074/075).
Those capabilities are deliberately absent from this ticket.
