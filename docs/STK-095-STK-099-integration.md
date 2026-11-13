# STK-095 / STK-099 — D3-03/04/09/12 integrated acceptance

Temporary branch: `integration/stk-095-stk-099`. Exact parents:

- PR #48: `b3d64e8db56ad9d07ce8586ce06ae90d4b4a2101`
- PR #49: `f3d6bd833b3da7a7ed0a7d7190cd055846788134`

This is isolated software verification, not a deployment or real-market claim.
Neither PR branch nor main is changed; the narrowly scoped push trigger runs the
existing complete CI workflow without another PR.

## Reconciliation

The only textual conflict was SIMPLE-BOARD.md; both histories are retained.
candidate_store.accept retains exact PostgreSQL JSONB size validation and the
commit-coupled empty notification. Provider-test receipts remain isolated from
candidate/session/research materialization. worker.candidates retains strict
hosted readable-config requirements, validate_page reuse and remote_pull control,
plus bounded one-event HTTPS pages and new-envelope normalization.

Two integration-only schema blockers were corrected: hosted API health now
requires 0017; backup accepts only reviewed 0016/0017 snapshots (to support both
pre-migration recovery and post-migration backups). Unknown versions still fail.
No grants or historical migrations are changed.

## Verification scope

Full CI runs all PostgreSQL integration, application/worker, script, HTTPS/browser
checks and Linux x86_64 hosted Compose rehearsal. Existing PR #48 checks retain
paper creation/admission/observation, immutable ledger/source controls, watchlist
export fail-closed behavior, readable ViewConfig, and real stored research paths
under API/worker roles. No provider/LLM calls are permitted.

The hosted rehearsal uses provider_alert transport with fabricated symbols and
values in the observed Chartink row shape. It verifies 35/40/50/150-column batches,
original documented payloads and exact provider-test receipts, duplicate delivery,
worker downtime/restart, cursor preservation, candidate/private UI/watchlist flow,
internal-only networks and identical backup/restore table/sequence fingerprints.
A separate container probe exercises 30 stored bars and denied permissions, not
merely an absent-configuration shortcut. Total intake: six events (one provider
probe), 276 candidates, 276 stored identity-path research results. The probe adds
no candidates and is not market evidence.

Two-database regressions cover interrupted bridge transaction rollback, retained
cursor identity, large-envelope replay, provider-test isolation and an old v1
receiver receipt without NOTIFY after image rollback. Existing notification and
reconnect tests prove wakeups are commit-coupled and missed hints recover by scan.
The schema-0017 boundary/immutability/migration suite and unchanged restricted
receiver, inbox reader, worker and API permissions are included.

Exact-head CI results belong in the final handoff; pending tests are not passes.

## Approved-release sequence (requires explicit owner approval)

1. Record and privately verify both database identities and cluster fingerprint:
   `chartink_inbox` owned by the existing receiver owner, and
   `stk_real001_private` owned by `stk_app_owner`. Preserve the existing PostgreSQL
   cluster/volume; the receiver must never access the research database. Preserve
   the exact receiver URL as the cursor key and all existing credentials.
2. Freeze writers for consistent backups and verify restore into new isolated
   databases. Compare table fingerprints, sequences, candidate state and cursors.
   Include private configuration and watchlist exports. Never overwrite a target.
3. Rehearse 0016→0017 on restored copies, then use the established owner migrator
   on BOTH approved targets before enabling larger-envelope writers. Verify the
   Alembic head and validated 1 MiB JSONB CHECK. Lock timeout rolls back safely.
   Neither runtime role receives DDL privileges; do not relax fences or restamp.
4. Activate the compatible worker and API first, using preserved cursor identity,
   valid readable research config and unchanged role grants. Keep one consumer;
   quiesce the old Mac writer before hosted activation. Verify old v1 replay.
5. Activate the compatible receiver image last. Verify isolated provider-test
   semantics separately from genuine delivery; then perform owner-approved
   live-alert and Mac-powered-off acceptance without altering the webhook URL.

On receiver-image rollback retain schema 0017 and the compatible worker for stored
new-envelope backlog. Old v1 events remain consumable without notifications.
Never reset cursors or delete immutable rows. Schema downgrade validates the old
bound and fails atomically if any larger row remains. Do not resume a stale Mac
copy: reconcile/restore the current verified application data and cursor first.

## Remaining release blockers

- Owner review/merge and explicit production migration/cutover authorization.
- Encrypted off-server backup, tested recovery/key custody and verified restore
  of both database identities, private configuration and watchlist.
- External monitoring/alerts for DB/API/worker health, backlog/cursor lag, disk,
  resource pressure and backup age; a tested alert path independent of the VPS.
- Representative VPS capacity rehearsal on restored data with actual stored
  research paths, peak/burst/backlog load, backup overlap and agreed headroom.
  CI resource samples are synthetic, not qualification of the selected VPS.
- Final frozen Mac export, private access verification and genuine Chartink
  delivery with the Mac off. Provider-test or synthetic success cannot clear it.
- Provider/source/model rights and real-research qualification remain unchanged.
- The hosted candidate worker does not execute queued paper observations or
  publication jobs. Those APIs are permission-tested, but their separate execution
  worker still needs an authorized Mac-independent operating design/activation.
  Optional legacy financial fixture-seeding remains denied under the API role.

Recommended owner merge order: PR #49 first (schema/adapter/compatibility), then
update PR #48 onto that result and include the integration-fix commit(s), rerun its
exact-head checks, and review/merge PR #48. Do not merge this temporary branch as a
substitute for owner review. Merge order does not authorize deployment.
