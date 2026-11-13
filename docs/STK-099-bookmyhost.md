# STK-099 — D3-03/04/09/12 BookMyHost application hosting

This increment prepares working code and isolated acceptance. **Production cutover
is not performed.** Issue #47 requires owner-approved host rehearsal and recovery
before changing live services. BookMyHost is the owner's explicitly selected,
already-purchased host for this increment; no hosting reselection or purchase.

## Architecture

Retain the existing Compose project `stock-discovery-chartink`, inbox database,
volume, TLS state, hostname, webhook capability and authenticated feed. Add a
separate `stk_real001_private` database in the existing PostgreSQL 16 cluster,
owned by a non-login `stk_app_owner`. Do not combine research tables with the inbox
or run a second PostgreSQL server on this small host. The coordinated release requires reviewed STK-095 code and schema 0017 on both databases. Existing API, frontend and worker images supply the application.

The receiver commits immutable event rows and an empty `stk_candidates` notification
in the same transaction. One existing worker process LISTENs on the source database
using `stk_inbox_reader` (SELECT on candidate_events only). It copies bounded pages
through the existing normalization/scanner check, commits destination events and
the existing receiver cursor together, then performs existing stored-only research.
The exact old receiver URL identifies the cursor; it is not used for network calls
in this mode. Notification loss is harmless: LISTEN commits **before** startup
catch-up, reconnection repeats catch-up, and a 30-second recovery scan also handles
missed hints, manual retries and old receiver images. A session advisory lock
prevents two new hosted workers; existing transactional locks/deduplication remain.
This follows PostgreSQL's [LISTEN startup ordering](https://www.postgresql.org/docs/16/sql-listen.html)
and [commit-delayed NOTIFY](https://www.postgresql.org/docs/16/sql-notify.html).

The public Caddy endpoint keeps the three existing receiver routes. All application
paths/assets require a separate HTTPS Basic login (bcrypt hash, per
[Caddy documentation](https://caddyserver.com/docs/caddyfile/directives/basic_auth)),
then the existing owner access key/session. Caddy strips edge Authorization before
forwarding; HttpOnly/Secure/SameSite=Strict cookies and exact-origin CSRF checks
remain. Health/docs/admin paths are not routed publicly. No database, API or web
container publishes a port. Only Caddy joins an external network. Worker/API have
no provider credentials or outbound internet; provider/model counts remain zero.
The existing Tailscale mode is unchanged; `authenticated_proxy` is explicit.

Automatic research means the existing stored-evidence research engine. Missing,
stale or unauthorized inputs remain blocked. This does not install an LLM or enable
acquisition, prediction, ranking, trading, synthetic production seeding, or paper
admission. Existing historical views and filesystem watchlists are preserved.

## Measured starting point — 11 November 2026

Read-only authenticated SSH verified Ubuntu host `bb-c417-gagan-jawa-709`, x86_64,
2 CPUs, 2,063,216,640 bytes RAM (1.92 GiB), about 1.40 GiB available,
1 GiB swap with only 274,432 bytes used, and 14,413,582,336 bytes free disk.
Receiver ~49.23 MiB, PostgreSQL ~31.45 MiB, Caddy ~11.73 MiB at idle; no observed
container OOM. Only SSH/80/443 listen externally; PostgreSQL is not published.

Existing database: `chartink_inbox`, cluster `7706856885194760225`, schema 0016,
10,640,407 bytes, **zero events** at assessment. No genuine Chartink delivery has
been verified. Project directory `/opt/stock-discovery/deploy/chartink`, secrets
`/etc/stock-discovery/chartink`, volume `stock-discovery-chartink_inbox`.
The read-only host check found no `restic` executable and no `stock-discovery*`
systemd units. Encrypted off-server recovery/alerting therefore remains unverified.

TLS/config volumes are `stock-discovery-chartink_tls` and
`stock-discovery-chartink_proxy_config`. Preserve these exact identities.

The proposed hard memory ceilings total **1,376 MiB**: PostgreSQL 512, API 256,
worker 256, receiver 192, Caddy 96, web 64. Reserve another 512 MiB for host/margin;
`stk099_preflight.py` rejects less than 1,888 MiB RAM, fewer than two CPUs, less
than 768 MiB currently available, swap pressure, OOM, public PostgreSQL, or less
than max(6 GiB, three database copies plus 2 GiB) free disk. Static preflight PASSED.
This is a small stored-only deployment, not an LLM host. Build images away from the
live 2 GiB VPS. Local ARM results cannot certify x86_64 production performance.
If x86_64 rehearsal exceeds limits, swaps materially or leaves <384 MiB host
headroom, do not cut over: practical next size is **4 GiB RAM / 2 vCPU**, with at
least 6 GiB free disk after images, two DB copies and retained backups. No upgrade
is authorized or currently proved necessary by the idle measurements.

## Data migration evidence and boundaries

STK-098 proved 6,727 rows before candidate-worker smoke. A fresh read-only backup
now has **6,728 rows excluding alembic_version**, 70 tables, three sequences, schema
0016, from Mac cluster `7695120939741798433`. SHA-256:
`15fe2c87d25dd0baca4df8fb02048ae185e7d10a80ef4b5726748217111525a9`.
All table counts/SHA-256 fingerprints and sequence last_value/is_called values
matched two separate disposable restores, including one mapping ownership to
non-superuser `stk_app_owner`. No fixture was inserted in production.

`stk099_transfer.py` verifies source cluster, stable before/after snapshots,
archive checksum, revision, all user tables and sequences. Restore uses a new
CREATE DATABASE (fails if present), a single pg_restore transaction, no clean/drop,
retained ACLs and explicit ownership. A failed restore leaves its target for
investigation; do not drop/reuse it automatically. Rehearsal names must be distinct
from final production. Retained ACLs require referenced roles to exist; the
existing receiver migrations already provide `stk_restriction_operator`, while
bootstrap supplies `stk_candidate_worker`. Never use `--no-acl` to hide failures.

Watchlists are **not in PostgreSQL**. `stk099_bundle.py` separately preserves their
JSON bytes and hashes, copies original grant/policy files without changing their
contents, and remaps only the view's file paths under `/run/private`. It preserves
source configuration as private provenance. Review grant territories before moving
data: copying an IN grant to an unapproved host territory does not grant rights.
Old pilot-health receipts are historical, not evidence that a Mac refresh job still
runs. No Mac scheduler/provider credential is needed by the stored-only worker.

## Authoritative release sequence (explicit owner authorization required)

Use the reviewed integration handoff at
[4d7dbad](https://github.com/gaganjawa/stock-discovery/blob/4d7dbadbcd5194dc1201cb11039261d2e4df6a11/docs/STK-095-STK-099-integration.md).
This PR alone does not contain schema 0017 or authorize migration.

1. Verify source database names and source cluster identifiers independently of
   the backup manifests. Verify destination identities, owners and existing volumes.
2. Freeze application writes and consumer activity in the approved window; obtain
   complete consistent backups of BOTH databases, configuration and watchlist.
   Verify hashes and encrypted off-server recovery with separately held keys.
3. Restore each backup into a new isolated target. Supply independently recorded
   `--expected-source-database` and `--expected-source-cluster` to
   `scripts/stk099_transfer.py restore`, alongside the existing container, owner,
   database, dump and restore-owner arguments. Source cluster expectations bind
   the manifest, not the destination cluster: Mac-to-VPS restoration is supported.
   Missing/mismatched expectations fail before CREATE DATABASE. Existing targets
   cannot be overwritten. Verify all table fingerprints and sequence state.
4. Rehearse 0016→0017 on BOTH isolated copies using reviewed STK-095 migration code.
   Verify immutable records, references, grants, candidate state and cursors.
5. Require reviewed compatible STK-095/API/worker/receiver images, schema-0017
   healthchecks and green integration CI before requesting production migration.
6. Only after explicit owner authorization, quiesce writes and migrate BOTH
   `chartink_inbox` and `stk_real001_private` with their owner migration identities.
   Preserve volumes, credentials and database names. No runtime DDL grants.
7. Verify schema 0017, the validated envelope constraint, permissions, fingerprints,
   sequence state and cursor identity. Preserve the exact previous receiver URL
   including trailing slash; use the existing candidate_store.digest identity.
8. Keep the existing receiver image available and healthy after schema verification.
   Activate compatible API and worker first with explicit service-only operations;
   do not run an all-services Compose up. The worker depends on receiver health:
   retain its running old image, and use reviewed `--no-deps` service updates where
   needed to prevent Compose from upgrading dependencies. Verify dependencies
   beforehand. Do not recreate/tune the database as part of image activation.
9. Confirm exactly one consumer across Mac and hosted execution; verify old-v1
   replay, durable cursor advance and authenticated UI before receiver upgrade.
10. Upgrade the receiver image last with a receiver-only `--no-deps` operation.
    Preserve the webhook URL and credentials. Verify provider-test isolation.
11. With owner approval, verify genuine delivery with the Mac powered off: durable
    inbox, one candidate/research result, cursor advance and private UI display.
    Delivery gaps have no assumed retry guarantee; retain and reconcile backlog.

On receiver rollback retain schema 0017 and compatible API/worker consumers when
expanded envelopes exist. Never delete events or reset cursors to force downgrade.
A schema downgrade must fail atomically if retained rows exceed the old bound.
For application recovery restore verified current backups into new isolated targets
first; never resume a stale Mac copy. Keep the established volume and cursor history.

### Executable operator steps for the authorized window

Keep this runbook and all reviewed files in the immutable release directory.
Resolve these values from the approved deployment record before executing commands;
source identities must come from that independent record, not from the manifest.
Prepare images, private configuration ownership, roles and grant files using the
reviewed release's existing preparation tools. Verify the frozen export and
watchlist hashes and retain the pre-migration backup manifests.

```sh
# Set absolute, persistent paths and exact reviewed values in the operator shell.
: "${RELEASE_DIR:?reviewed checkout}" "${COMPOSE_ENV:?approved persistent env file}"
: "${BASE_COMPOSE:?existing receiver compose file}" "${DB_CONTAINER:?existing container}"
: "${BACKUP_DIR:?private persistent backup directory}"
: "${APP_SOURCE_CLUSTER:?independently verified Mac source cluster}"
: "${INBOX_SOURCE_CLUSTER:?independently verified inbox cluster}"
: "${APP_OWNER_URL_FILE:?existing app owner URL secret file}"
cd "$RELEASE_DIR"
dc() {
  docker compose --env-file "$COMPOSE_ENV" -p stock-discovery-chartink \
    -f "$BASE_COMPOSE" -f "$RELEASE_DIR/deploy/bookmyhost/compose.yaml" \
    --profile receiver "$@"
}
dc config --quiet
# After separately approved write freeze, use fresh filenames; never overwrite.
# Obtain both dumps with stk099_transfer.py backup --expected-cluster SOURCE_ID.
# Run these restores on the isolated rehearsal cluster/container, never a live target.
: "${ISOLATED_DB_CONTAINER:?isolated restore container}"
python3 scripts/stk099_transfer.py restore --container "$ISOLATED_DB_CONTAINER" \
  --owner chartink_owner --database stk099_app_restore --restore-owner stk_app_owner \
  --dump "$BACKUP_DIR/app.dump" --expected-source-database stk_real001_private \
  --expected-source-cluster "$APP_SOURCE_CLUSTER"
python3 scripts/stk099_transfer.py restore --container "$ISOLATED_DB_CONTAINER" \
  --owner chartink_owner --database stk099_inbox_restore --restore-owner chartink_owner \
  --dump "$BACKUP_DIR/inbox.dump" --expected-source-database chartink_inbox \
  --expected-source-cluster "$INBOX_SOURCE_CLUSTER"
```

Verify fingerprints immediately after restore, before migration changes the
schema/version fingerprint. Rehearse `alembic upgrade 0017` against both isolated
copies using their isolated owner URL files. Verify old rows, sequences and cursors
separately after migration; do not compare a schema-0016 full fingerprint unchanged
against schema 0017. Restore checks must include encrypted off-server copies.

Only after the preceding evidence and explicit owner production authorization:

```sh
# Keep the existing receiver image; quiesce its writes during migration.
# The existing migrate service uses the inbox owner secret.
dc run --rm --no-deps migrate python -m alembic -c /app/backend/alembic.ini upgrade 0017
dc run --rm --no-deps -v "$APP_OWNER_URL_FILE:/run/app-migration-url:ro" \
  -e DATABASE_URL_FILE=/run/app-migration-url migrate \
  python -m alembic -c /app/backend/alembic.ini upgrade 0017
for target in chartink_inbox stk_real001_private; do
  docker exec "$DB_CONTAINER" psql -X -U chartink_owner -d "$target" \
    -v ON_ERROR_STOP=1 -c "SELECT current_database(),version_num FROM alembic_version" \
    -c "SELECT convalidated,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='discovery.candidate_events'::regclass AND conname='candidate_events_envelope_check'"
done
```

Require 0017 and the validated 1048576-byte CHECK in both results. Verify existing
row/sequence/cursor fingerprints, apply reviewed database-specific least-privilege
grants and test them before continuing. The existing receiver must be running and
healthy on its recorded old image. Resume only that existing image if it was
quiesced; do not recreate it from the new Compose image definition yet.

```sh
# Confirm one consumer; the previous Mac consumer must already be quiesced.
dc up -d --no-deps --no-build --wait api
dc up -d --no-deps --no-build --wait worker
# STOP HERE to verify old-v1 replay, committed cursor and worker health.
# Then activate the reviewed receiver image last.
dc up -d --no-deps --no-build --wait receiver
dc up -d --no-deps --no-build --wait web proxy
```

Record old/new image IDs and configuration hashes privately. Receiver rollback
uses its recorded old image with the same receiver-only `--no-deps` operation;
retain schema 0017 and the compatible consumer. Restore recovery always begins
on new isolated targets with explicit source expectations and fingerprint checks.
Do not drop/overwrite production targets or resume stale Mac state. Any switch
from restored copies needs a separately reviewed owner-authorized recovery plan.

## Monitoring and rollback

Use existing host monitoring to inspect `dc ps`, Docker health/OOM/restart counts,
`docker stats --no-stream`, `free -m`, `df -h`, backup age and worker health. Health
is available inside worker `/tmp/candidate-health.json`; status must be healthy
and younger than 90 seconds. `deploy/chartink/monitor.sql` gives aggregate inbox
and candidate failures; compare source high-water with the destination cursor.
Alert externally on unhealthy worker/API/DB, pending lag >2 minutes, any failed
work, >=80% inbox capacity, backup age >24h, growing swap or <384 MiB RAM / <6 GiB
disk. No in-app status can report a dead VPS; external alert delivery must be tested.
The worker reconnects automatically; Docker health alone does not restart a hung
process, so operator response to an unhealthy alert is required.

Rollback **without reverting either database**: stop hosted worker first, close
private UI writes, export a fresh verified VPS app backup and watchlist (preserve
post-cutover state), then restore the previously recorded receiver image and Caddy
configuration via the original Compose project. The original route/capabilities
and all volumes stay. Keep new app DB intact. To return processing to the Mac,
restore the latest VPS app dump to a **new** Mac database, verify it and watchlist,
repoint the Mac private DSN explicitly, then start exactly one old HTTPS-pull worker.
Never resume the stale Mac snapshot silently after VPS writes: that would lose
watchlist/candidate changes. If the new app never accepted writes, original Mac
snapshot can resume after identity/fingerprint confirmation. Cursor/idempotency
replay handles inbox events accumulated during downtime.


## Implementation acceptance

Local unit baseline: 1,048 passed; the final added hosted-role guard has a separate
passing test (1,049 total cases in the final unit inventory). PostgreSQL: **595
passed, zero skips**, including migration upgrade/repeat/downgrade/re-upgrade and
atomic failure rollback. Script checks and final focused security checks pass.
The new tests exercise commit-only wake-ups, rolled-back receipts/cursors,
startup without a notification, source connection termination/reconnection,
duplicate delivery, restricted SQL roles and candidate API authentication.

Complete isolated Compose acceptance: 11 invented events, 101 candidates, one
research result per candidate, worker stopped during intake/restarted afterwards,
secure HTTPS edge/owner logins, actual browser candidate and watchlist save/reload,
Secure/HttpOnly/Strict cookie, unpublished service ports, internal-only networks,
no OOM and full backup/restore table+sequence equality. All market inputs are
synthetic and blocked for real research. Startup was about 62 seconds. The first
sampled workload peaked at approximately API 51.42 MiB, database 50.47 MiB,
receiver 48.92 MiB, worker 34.93 MiB, Caddy 18.82 MiB, web 3.88 MiB (~208.4 MiB
sum of individual sampled peaks). Sampling is not a continuous peak measurement,
and this ARM blocked-input workload does not qualify actual x86_64 research load.

CI now executes the full hosted/browser rehearsal on Linux x86_64 and retains only
sanitized resource results. Exact-commit CI and owner review must pass before
release. Local private evidence is under `backups/stk099-acceptance/`, including
fresh Mac restore manifests; it is deliberately excluded from Git/build context.

Remaining deployment gates: owner review/merge; tested linux/amd64 release;
representative restored-data host load/private access checks; approved encrypted
off-server backup with tested restore/key custody and external alert; final frozen
Mac export and watchlist verification; owner-authorized maintenance cutover; then
an observed genuine Chartink delivery with the Mac powered off. No production
service, database, receiver credential or URL was changed by implementation.

## PR #48 P2 corrections — 12 November 2026

Watchlist export now requires an existing directory and `watchlist.json`. Only
`--allow-empty-watchlist` permits an absent file in an existing directory, with an
explicit `watchlist-export.json` audit record. Existing bytes are copied unchanged;
change/deletion/creation during copying fails before the completion hash manifest.
An empty JSON file is invalid; a valid empty JSON object is preserved verbatim.

The isolated rehearsal supplies a validated ViewConfig and empty grant list,
owned by container UID 10001 (directory 0700, files 0600). Hosted worker view or
grant-file read errors stop consumption with `hosted_research_configuration_invalid`.
The 101 intake cases must reach the actual stored-identity lookup. A separate
transactional container probe uses fabricated historical evidence to verify a
30-bar descriptive result and permission denial under both hosted roles. Its
fixture rows roll back; no external provider/model calls occur. These checks
remain synthetic software acceptance, not representative restored-market load.

API write-path audit:

| Existing routes | Hosted permission / boundary |
|---|---|
| Paper create, admission/batch, observation/fictional-session | INSERT on portfolios, ledger, observations; column UPDATE on portfolio_id only for row locks, existing immutable trigger rejects mutations; no paper sequence exists |
| Paper source recheck | Column UPDATE on source_id permits FOR SHARE; hosted role guard rejects actual source-control changes, including renames; revoked column remains denied |
| Discovery-run enqueue | INSERT on publication_runs; no publication or evidence writes granted |
| Governance registration/trials/evaluation/controls | INSERT on the four explicit experiment tables; USAGE on experiment_events_sequence_seq; immutable histories retained |
| Legacy initialize/analysis/reveal/explanation/scan/replay/experiments | Existing research INSERT/sequence grants and jobs UPDATE retained |
| Candidate retries | Existing UPDATE on candidates and candidate_event_state retained |
| Watchlist/session | Private filesystem and cookie operations; no database grants needed |
| Receiver ingestion | Separate receiver role/database; unchanged |

Audit limitation: optional legacy `analysis(include_financial=true)` still invokes
synthetic evidence seeding and therefore cannot run under the hosted API role;
its evidence/grant write privileges deliberately remain denied. Ordinary legacy
analysis and restored descriptive research retain their existing access. This
fixture-seeding mode is not enabled by hosting and needs a separate scoped design
if required there; it is not repaired by granting the API ingestion privileges.

The candidate worker cannot write research evidence or paper tables. API cannot
write processed paper receipts, shadow references/outcomes, revisions, grants or
restriction fences. The dedicated hosted worker still runs candidate intake only;
queued paper observations and synthetic publication jobs require the existing
separately operated execution worker. This correction grants no worker activation.

Local validation: 1,053 application/worker unit tests and 34 script tests passed.
PR CI supplies disposable PostgreSQL role/route regressions, migrations, Linux
hosted research probe and browser acceptance. Exact-head CI evidence is recorded
in PR #48. No production services, volumes, credentials or webhook URL changed;
all previously listed owner/recovery/rights/cutover/genuine-delivery gates remain.
