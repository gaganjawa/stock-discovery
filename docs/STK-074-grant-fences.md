# STK-014/074 — durable grant fences: ingestion slice

This additive implementation restricts access. It does not delete content,
resolve provider-policy questions, authorize retention, or approve REAL-001
operations, publication, paper admission or trading.

## Database contracts

Migration `0015`, following the existing single head `0014`, adds:

- `discovery.grant_fences`: provider, provider/account, and exact
  source/account/grant/version scopes, with `OPEN`/`FENCED` and generation.
- `discovery.restriction_requests`: immutable UUID-keyed operator decisions,
  opaque scope reference, fixed reason code, optional policy-document hash,
  database timestamp and resulting generation. `deletion_authorized` is always
  false. No raw policy document, provider response or exception text is stored.
- `discovery.ingestion_grants`: immutable page-to-acquisition-grant dependencies,
  committed with the page and its revisions/extracted evidence.

`OPEN` means no restriction has been recorded. It is **not** a source grant.
Use-specific authorization, exact grant identity and database-time validity are
still required. Registration creates only missing scope rows, never reopens or
changes an existing row. Provider and account fences apply to new grant versions.
Unknown or missing scope rows fail closed when checked.

Database enforcement also checks the data scope, independently of Python:
instrument/membership → universe, candle → prices, action → corporate_actions,
session → calendar, and filing/news documents → filings/news. Original stream
scope must match the revision and its acquisition grant. Destination membership
must preserve that data scope. Page grants must authorize their stream scope;
evidence batches additionally require a filing/news scope and store/extract/derive
uses. Financial facts retain their additional financial_facts requirement.
Missing, malformed or unknown required scopes deny the write.

Existing immutable acquisition grants initialize their three scope rows during
migration without modifying historical data. New ingestion explicitly initializes
scope rows after validating the supplied grant. Expired/revoked grants cannot
persist content merely because their rows say OPEN.

Legacy pages have no retrospectively invented grant attribution. Reuse of an
unattributed legacy page is blocked. A new, verified acquisition under a new
stream can proceed; existing revisions remain attributable to their original
acquisition grant. New dependencies cannot be attached to an already existing
page by the ordinary ingestion path. No historical source records are rewritten.

Downgrade refuses when restriction decisions or new ingestion dependencies exist.
An empty new control schema can be downgraded/re-upgraded without changing old
records. Existing migration bodies and immutability triggers are unchanged. The
NOLOGIN operator role is left in place on downgrade; no login membership is
created or removed automatically.

## Operator authority

`restrict()` invokes the SQL restriction function. PostgreSQL authenticates the
connection; the function requires **session_user** membership in the
`stk_restriction_operator` role (or an already privileged database administrator).
A caller-supplied actor string, `SET ROLE`, application flag or repaired provider
credential is not authority. Deployment must explicitly assign this membership
and schema USAGE to an approved operator login. Workers must not receive this
membership or ownership/direct mutation privileges on the control tables.

There is no HTTP endpoint, role-membership bootstrap, release, reopening or
content-deletion function in this slice. Existing owner web authentication does
not automatically become database restriction authority.

Valid reasons are revoked, expired, policy_unverified and deletion_pending. A
policy hash is a reference, not proof of legal clearance. Unknown policy may
restrict access but cannot authorize destruction. The scope/audit hash is an
opaque linkage token, not an anonymization or lawful-retention claim.

UUID request identity, scope, reason, policy hash and authenticated operator must
match on replay. One effective OPEN-to-FENCED transition increments generation.
Further distinct requests against the same fenced scope append an already-fenced
decision without incrementing it. Duplicate identical requests append nothing.
The state change and decision commit together; failures roll both back.

## Transaction boundary and ordering

1. Capture grant identity and provider/account/version generations before external
   acquisition. Database time is used in addition to existing application clocks.
2. Hold no long transaction solely for network/model work when using the normal
   dedicated autocommit ingestion connections.
3. Inside final persistence, reload the grant, compare the captured identity and
   generations, take PostgreSQL FOR SHARE locks in provider, account, grant order,
   then revalidate rights and expiry using fresh database time after any wait.
4. Fence activation locks its scope FOR UPDATE. Its state change conflicts with
   the writer's locks. All content/dependencies commit or roll back together.
5. Deferred database triggers recheck acquisition grants, expiry and fences for
   revisions, stream membership, pages, quarantine, evidence blobs, documents,
   chunks, facts, claims and evidence batches. Membership writes also pin the
   destination stream identity and check/lock its provider and account fences;
   missing destination scopes deny the write. Original grant checks remain
   mandatory. Registered, unfenced cross-stream membership stays supported;
   registration itself still confers no additional source-use permission.
   Stream ID, source, account and scope are immutable at the database boundary;
   cursor/completion updates remain permitted. Deployments should additionally
   grant ingestion roles only column-level UPDATE on cursor and complete, not
   identity columns. The current role bootstrap does not grant discovery UPDATE
   privileges; this migration does not broaden them.
   An orphan blob is rejected. Shared
   blob reuse checks existing owners; another grant cannot hide a fenced owner.

A writer already holding the locks may commit before a waiting fence. Activation
is acknowledged only after its own transaction commits. Once acknowledged, stale
writers cannot commit protected content. Transactions started at repeatable-read
isolation must handle serialization failure rather than continuing with stale
rows. PostgreSQL remains the enforcement boundary, not a process-local mutex.

Nested caller transactions retain locks until the outer transaction ends. Keep
those transactions bounded; use operator statement/lock timeouts appropriate to
the deployment and retry the same UUID after a timeout/ambiguous acknowledgement.
This slice does not implement an activation deadline queue or alert delivery.
A transaction failure never reports a successful fence activation.

Database-time expiry is rechecked by deferred triggers at finalization. This is
an authorization/commit-order guarantee, not a promise to erase data or retract
an already transmitted network request at a precise wall-clock instant.
Each protected operation captures its dependency list, acquires the applicable
locks, then performs a final validation pass with fresh database time and no new
row locks. This includes later destination-account locks, instrument/supersession
grants, page grants and shared-blob owners. The validation-only SQL helpers are
not standalone authorization leases; persistence triggers perform the lock pass.
Dependency traversal is stable, but callers batching restrictions in opposite
scope orders can still deadlock. PostgreSQL aborts a participant; callers must
roll back the whole transaction and explicitly replay the original request IDs.
Serialization failures likewise must not be caught and treated as authorization.

## Ingestion adapter integration

`ingest_next` and `ingest_next_evidence` capture before adapter fetch and pass the
permit into final persistence. Direct page ingestion also checks the database.
Real price and calendar adapters bind their Access object to an ingestion
connection and recheck before each acquisition/use. Financial endpoint ingestion
pins the permit before fetching its response. Pilot request/receipt accounting
and STK-075 recovery logic are not reset or rewritten.

Restrictions cannot be cleared by worker restart or retry. Renewed grant identity
cannot replace an in-flight permit. Reusing an existing revision/page additionally
checks its original acquisition grant. Restriction failures stay fail-closed.
Page retry and completed-stream checks also validate the original grants of all
member revisions, including revisions deduplicated under another grant version
before restriction. Dependencies remain immutable. Because membership is stored
per stream rather than per page, this deliberately denies reuse of any page in
a stream containing a restricted revision. It does not change unrelated readers.

## Deliberately unprotected boundaries

This is not complete lifecycle enforcement:

- Standalone snapshot creation and stored-content read APIs do not yet consult
  these durable fences; their existing source-rights checks remain in force.
- RAG/agent caches, research results, immutable intents, completed-scan reuse,
  scheduler receipts, publication, shadow/paper outcomes and governance outputs
  do not yet all carry/check complete fence-generation dependencies.
- Binding an ingestion Access object provides additional checks at that call
  site; it does not make every research or scheduler path fence-aware.
- STK-075 recovery authorization does not itself check a deletion fence. A later
  protected ingestion rejects restricted work. No automatic recovery is added.
- Filesystem copies, extraction temporary files, model memory/caches, exports,
  backups, WAL, restored databases and stale external workers are not covered.
- An old backup can restore pre-restriction state. Restore quarantine and a
  current independent restriction ledger remain mandatory future work.
- Database owners/superusers able to change schemas or disable triggers remain
  trusted administrators, not constrained application principals.

STK-074's synthetic read-only manifest contract is unchanged. New tables may be
reported as unsupported inventory until a separately reviewed manifest extension.
The manifest is never restriction, deletion or retention authority.

## Synthetic validation

Tests use a task-owned disposable PostgreSQL cluster and synthetic/mocked inputs.
They cover all scope levels, before-fetch/after-fetch restriction, database lock
ordering with a deterministic worker/operator barrier, restart, duplicate
requests, explicit role authority, expiry, renewal, shared blobs, raw inserts,
rollback, budget preservation and no publication/trading side effects. INSERT-only
role regressions cover fenced/missing destination scopes, permitted membership,
and both commit orderings of concurrent destination fencing and membership.
The destination identity is locked until the membership INSERT commits, and a
database trigger rejects later identity changes even for non-owner roles with
table-level UPDATE privileges. Regressions exercise concurrent INSERT/UPDATE,
overlapping grant versions followed by restriction, and expiry while waiting for
fence locks. Waiters are observed through PostgreSQL blocking-PID queries; expiry
tests wait for the actual database deadline rather than assuming thread timing.
Round-2 regressions additionally cover INSERT-capable non-owner roles using
insufficient scopes, scope mismatches, unknown/missing scopes, all valid revision
scope mappings, financial-fact permissions, expiry during a later destination or
instrument-grant lock, repeatable-read revocation, and opposite-order restriction
transactions with atomic rollback and idempotent audited replay.

Migration tests cover clean, D3-11 and legacy REAL histories; scope initialization;
unattributed legacy pages; empty-control-schema rollback/re-upgrade; and refusal
to discard restriction/dependency history. These tests are not real-provider or
operational acceptance evidence. Provider policy and audit retention remain
UNVERIFIED; REAL-001 remains PARTIAL.
