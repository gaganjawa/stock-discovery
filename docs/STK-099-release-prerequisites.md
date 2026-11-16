# STK-099 / D3-12 Private operational pilot — release prerequisites

## 17-Nov STK-099 / D3-12 — full VPS release preparation: NO-GO

Base includes merged PR #61 (`2c8f286`). Existing hybrid production is schema
0018 on both databases. Operations backup/receiver monitoring now require 0018;
older and unknown schemas fail closed. No production deployment in this PR.

Read-only VPS observation: 1,967 MiB RAM total, 1,396 MiB available, 4 MiB swap
used; 13 GiB disk free. Receiver/proxy/database used 49.47/15.29/33.86 MiB.
Reuse the representative 14-Nov restore/browser/recovery evidence, not another
rehearsal. Its minimum available RAM was 1,008.6 MiB. The 2 GB host is not proven
insufficient; active acquisition load remains unmeasured. Enforce existing
384 MiB headroom, <256 MiB swap and 6 GiB disk gates. If exceeded, stop and request
4 GiB RAM / 2 vCPU; no upgrade or forced deployment is authorized here.

Required gates remain open: no operations.env or Stock Discovery timers found;
/etc/stock-discovery contains only the existing Chartink configuration files.
No encrypted off-server restore or independently delivered external failure alert
has been verified. Existing private destination/repository ID, credential-file
paths, independent encryption-key custody, external alert hook/delivery destination
and external dead-host monitor must be supplied. Do not invent or provision them.

Next executable sequence: configure the existing operations templates privately;
run the existing `operate.py backup`, `alert-test`, and `monitor` procedure below;
record exact restored snapshot, table/sequence/watchlist equality and external
alert receipt. Then pin latest-main AMD64 application/worker/frontend artifacts,
prepare existing hosted/refresh Compose inputs and preserve both database identities,
scanner, grants, webhook and cursor using the existing transfer runbook. Capture a
fresh final recovery point. Request explicit cutover approval before stopping Mac
writers, restoring the application on VPS or switching proxy routes. Start exactly
one VPS consumer/refresh pair only after Mac writers are stopped. Verify authenticated
Candidates/company/watchlist, recovery and actual Mac-off HTTPS operation.

Rollback retains 0018 and all newly received evidence. Stop affected VPS workers,
keep inbox receipt available, and transfer current application data into a new Mac
recovery database with verified fingerprints before resuming one compatible Mac
worker pair. Never reset cursor or restore old backups over new receipts.
Genuine Chartink acceptance and full VPS Mac-off acceptance remain PENDING.
See [existing cutover commands](STK-099-bookmyhost.md) and
[representative evidence](STK-099-restored-rehearsal.md).

## Historical prerequisite evidence (schema 0017)

Current evidence: **16 November 2026**. **Cutover: NOT READY / not authorized.**
Use this sequence for the current schema-0017 deployment. The migration and receiver
upgrade sequence in the original BookMyHost runbook is historical. This increment
prepares operations; it does not deploy the application or repeat the VPS/browser
rehearsal. Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md).

## Verified state and gates

| Gate | Actual evidence / remaining work |
|---|---|
| Main implementation | PR #53/#54/#55/#56 merged; base `5a78b6846cd88d89e68abf8864b8fe707c50b8b6`. This operations change needs its own PR checks and owner review. |
| Representative restore/resource/recovery | Reuse [14-Nov evidence](STK-099-restored-rehearsal.md): 70 tables, 6,737 rows, three sequences, watchlist, authenticated browser and recovery passed; minimum available RAM 1,008.6 MiB. No repeat rehearsal. Idle refresh is not active-provider load. |
| Live VPS preservation | Read-only check **2026-11-16T06:06:20Z**: exactly receiver/proxy/database running; receiver and DB healthy. Receiver image `sha256:f9e0103a16bc01a03faed376921960d70646ada9423fc280ddec88ff82111b4c`, start `2026-11-13T16:11:51.672976128Z`, unchanged. No production service restart, migration, cursor mutation or provider request. |
| Backup tool | Restic 0.19.1 installed separately at `/opt/stock-discovery-tools/restic-0.19.1/restic`; official release archive checksum matched `f415415624dcc452f2a02b8c33641791a8c6d6d3b65bbb3543fcf9a25151585c`. Binary SHA256 `20d4142678d0d95ec11a4759def1b73fd9190abc9ca19e4b62d067c0b387e639`. LICENSE and installation receipt retained alongside it. Checksum verification is not signature verification. |
| Encrypted off-server restore | **NOT VERIFIED.** No initialized destination, repository credentials/password file or separate-key-custody evidence found in inspected project/VPS configuration. No remote backup request made. |
| External alert and host-loss detection | **NOT VERIFIED.** No operations.env, alert executable/destination or Stock Discovery timers found; root crontab empty. No alert sent. A host-local monitor alone cannot detect total host loss. |
| Current application evidence | Last Mac observation remains **15-Nov 13:01 UTC**: schema 0017, cursor 3, three provider-Test events, zero genuine candidates, 2,648 revisions, one consumer/one refresh worker. This task did not refresh those counts. Genuine candidate/current-price/Mac-off acceptance remains pending. |

Inspection was limited to project backup/config metadata, `/etc/stock-discovery`,
Stock Discovery systemd units/timers, root crontab and standard restic/rclone/AWS/mail
configuration locations. No credentials were printed. No rclone/AWS/mail resource
files were present in those VPS locations. This does not assert that the owner has
no external account elsewhere.

**Required owner input:** identify an existing off-server repository/destination
and its private credential-file paths, its independently held encryption key and
custodian, and an existing external alert destination plus delivery credentials/hook
path. Identify an existing external heartbeat/dead-host monitor too. Provide resource
names/paths, not secret values. No paid service creation or new account is assumed.
Then configure and verify one exact-snapshot restore and one observed alert delivery.
Full production cutover still needs separate release authorization after these gates.

## Prepared operations, not activated

The existing `scripts/operate.py` now has an opt-in `STK099_TRANSFER_CONFIG` path
that reuses `stk099_transfer.backup_online` and its full-table/sequence restore
verification. It does not stop writers, migrate, delete databases, or prune snapshots.
Concurrent sequence allocation fails closed and retains the failed stage for review;
choose a fresh stage only after inspecting it, never repeatedly force a busy backup.
Recovery creates new named databases on an independently identified recovery cluster;
those copies remain for inspection. This is distinct from running the full app/VPS
rehearsal again.

The old default backup path stops api/worker and verifies only research tables.
**Do not use that legacy path on this release.** Receiver/hosted modes require the
online config and fail if it is absent. Receiver monitoring checks only the services
and schema actually present. Hosted monitoring additionally checks the refresh
service and scheduling queue; it rejects a receiver-only backup receipt.

Private templates: [environment](../deploy/bookmyhost/operations.env.example) and
[backup config](../deploy/bookmyhost/backup.example.json). They intentionally contain
unresolved values and false confirmations; they are not an activated configuration.
The repository must be remote, its exact ID checked against the reviewed config,
and encryption-key custody confirmed separately. Restic encrypts its repositories;
see the [official setup](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)
and [restore documentation](https://restic.readthedocs.io/en/stable/050_restore.html).
Do not initialize a repository, choose a destination or incur charges implicitly.
Use the existing budget and append-only backup identity where supported; retention
remains an explicit offline owner operation. Do not grant the VPS pruning authority.

Before configuring timers:

1. Install the reviewed scripts into a persistent release directory, not a temporary
   worktree. Copy templates only to absent private paths, mode 0600; never overwrite
   existing secrets. Fill them privately. Set exact code version and Compose command.
2. Record the actual off-host repository ID and independently obtained source/recovery
   cluster IDs. Pre-provision only required restore roles on an isolated recovery
   cluster. Do not execute downloaded role SQL automatically. Never point recovery at
   the live database container/cluster. Review disk/RAM before starting recovery.
3. Prepare a private recovery bundle containing current configuration, private view
   dependencies/watchlist, role/grant definitions, credentials and TLS recovery
   material, image digests and configuration hashes. Preserve bytes/permissions;
   freeze watchlist changes while capturing it. Do not include the restic encryption
   password or its independent custodial copy. Record the bundle SHA256 in backup.json.
   The cycle also exports fresh DB dumps/manifests and role SQL. The bundle hash is
   verified after download; its contents still need operator inventory review.
4. Current `scope=receiver` covers only the inbox plus reviewed bundle. After the
   fresh application restore, `scope=hosted` must include **both** `chartink_inbox`
   and `stk_real001_private`; a receiver receipt is not full-application recovery.
5. Configure the existing alert hook to consume allowlisted JSON on stdin and return
   nonzero on transport failure. Verify the destination is external. Do not log
   credentials, URLs with capabilities or provider payloads. Configure the external
   dead-host monitor with the existing resource's own supported interface.

Run once with the reviewed private environment. Shell and systemd environment-file
quoting must agree; use simple quoted assignments without shell expansion. Do not
turn on shell tracing. These commands remain pending the missing configuration:

```sh
set -eu
umask 077
: "${STK_OPS_RELEASE:?persistent reviewed checkout}"
set -a
. /etc/stock-discovery/operations.env
set +a
cd "$STK_OPS_RELEASE"
python3 scripts/operate.py backup
python3 scripts/operate.py alert-test
python3 scripts/operate.py monitor
```

The backup receipt is written only after downloading/decrypting the **exact** new
snapshot with `--no-cache`, matching every staged file, and restoring/verifying all
schema-0017 table/sequence fingerprints. Save snapshot ID, source/target clusters,
new recovery DB names, elapsed restore time, and watchlist/config hash evidence.
Measure RPO ≤24h and attended RTO ≤8h; do not infer these from unit tests.
The alert receipt deliberately says `external_delivery_verified=false`: record the
actual provider delivery ID/time and recipient observation separately. Test the
external dead-host alarm using its supported test function, without stopping the VPS.

Only after both real checks pass, install the **existing** backup/monitor service
and timer files from `deploy/systemd`; use drop-ins for `WorkingDirectory` and
absolute `ExecStart` pointing to the reviewed persistent operations checkout.
Validate with `systemd-analyze verify`, then:

```sh
systemctl daemon-reload
systemctl enable --now stock-discovery-backup.timer stock-discovery-monitor.timer
systemctl list-timers stock-discovery-backup.timer stock-discovery-monitor.timer
```

Never start the legacy backup unit without the online config. The backup unit has a
2-hour ceiling; the serialized monitor skips during backup. External dead-host
monitoring must remain independent. Retained recovery DBs and failed stages need
operator review and disk monitoring; no automatic destructive cleanup is introduced.

## Full cutover checklist — execute only after separate release authorization

- [ ] Off-server exact-snapshot recovery, independent key custody, actual external
      alert and dead-host test recorded; existing budget confirmed.
- [ ] Final approved commit and exact-head CI passed; immutable AMD64 API/worker/web
      registry digests recorded. Prior rehearsal image IDs are not release pins.
- [ ] Private API/UI auth, source identity (including exact receiver URL), unchanged
      scanner/secrets, restricted refresh role, current token/grants/calendar/quota,
      INFY scope and mounts validated. No paid or diagnostic provider call implied.
- [ ] Existing source/destination cluster identities verified independently; schema
      0017 in both source DBs; current counts/cursor/leases/quota and watchlist hashes
      saved. No migration, database tuning or volume recreation.
- [ ] Maintenance window includes UI write freeze and proxy-only replacement: the
      reviewed Caddyfiles have `admin off`, so a hot reload is unavailable. Owner must
      authorize the brief ingress interruption; do not claim uninterrupted cutover.
      Receiver process/inbox remain running, but provider retry cannot be assumed.
- [ ] Preserve original Compose/env/Caddy files, TLS volume, launchd plists, native
      private config and binaries; record their hashes and rollback locations.

Commands below are an operator sequence, **not executed by this PR**. Require all
paths from the actual private release record; never substitute rehearsal data.
On the Mac, persistently stop both existing workers and verify their child processes
and locks are gone before exporting or starting either VPS worker:

```sh
set -eu
STK_GUI="gui/$(id -u)"
for label in local.stock-discovery.chartink-consumer local.stock-discovery.candidate-price-refresh; do
  launchctl disable "$STK_GUI/$label"
  launchctl bootout "$STK_GUI/$label"
  if launchctl print "$STK_GUI/$label" >/dev/null 2>&1; then exit 1; fi
done
: "${STK_MAC_DB_CONTAINER:?verified existing Mac database container}"
: "${STK_MAC_DB_OWNER:?verified existing database owner}"
: "${STK_FROZEN_DIR:?new private export directory}"
: "${STK_VIEW:?current private view file}" "${STK_WATCHLIST:?current watchlist directory}"
# Freeze UI/API and all other application writers using their recorded launch method.
# Verify no matching worker/child remains and no active DB writers, then export.
python scripts/stk099_transfer.py backup --context colima \
  --container "$STK_MAC_DB_CONTAINER" --owner "$STK_MAC_DB_OWNER" \
  --database stk_real001_private --expected-cluster 7695120939741798433 \
  --dump "$STK_FROZEN_DIR/app.dump"
python scripts/stk099_bundle.py --view "$STK_VIEW" --watchlist "$STK_WATCHLIST" \
  --destination "$STK_FROZEN_DIR/bundle"
```

Transfer dumps/manifests/bundle securely to a new private VPS directory; verify all
hashes. Provision reviewed existing-role credentials/grants, including
`stk_price_refresh`, without rotating secrets or changing the live inbox. All
required roles must exist before restore. The target app DB must be absent; if it
exists, stop and investigate rather than overwrite it. On the VPS:

```sh
set -eu
umask 077
: "${STK_RELEASE:?reviewed persistent checkout}" "${STK_ENV:?private release env}"
: "${STK_EXPORT:?verified transferred export directory}"
cd "$STK_RELEASE"
STK_DB=stock-discovery-chartink-database-1
python3 scripts/stk099_transfer.py backup --online --container "$STK_DB" \
  --owner chartink_owner --database chartink_inbox --expected-cluster 7706856885194760225 \
  --dump "$STK_EXPORT/inbox.dump"
python3 scripts/stk099_transfer.py restore --container "$STK_DB" \
  --owner chartink_owner --database stk_real001_private --restore-owner stk_app_owner \
  --dump "$STK_EXPORT/app.dump" --expected-source-database stk_real001_private \
  --expected-source-cluster 7695120939741798433
```

Verify table/sequence fingerprints (the restore command does this), current app
cursor/quota/event state and watchlist bytes. Move operations to `scope=hosted` with
both sources at the VPS cluster and refreshed bundle/hash. Run the encrypted backup
cycle and require **both** isolated restores before worker activation. Keep Mac
workers disabled throughout. Retain the original native DB and files unchanged.

Use the same project, existing base and receiver pin; explicit service selection
prevents applying overlay database/receiver changes. Check Compose privately with
`config --quiet`; never print expanded secrets. Preserve actual base env values.

```sh
dc() {
  docker compose --env-file "$STK_ENV" -p stock-discovery-chartink \
    -f /opt/stock-discovery/deploy/chartink/compose.yaml \
    -f "$STK_RELEASE/deploy/bookmyhost/compose.yaml" \
    -f "$STK_RELEASE/deploy/bookmyhost/compose.refresh.yaml" \
    -f /var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml \
    --profile receiver --profile price-refresh "$@"
}
dc config --quiet
dc up -d --no-deps --no-build --wait api web
# Verify internal authenticated reads and frozen-state preservation first.
dc up -d --no-deps --no-build --wait worker
# Verify one consumer and durable progress against the retained source identity.
dc up -d --no-deps --no-build --wait price-refresh
# Verify one refresh worker, shared transferred quota ledger and health.
# Only in the explicitly authorized ingress window, with rollback config ready:
dc up -d --no-deps --no-build --wait proxy
```

No `up` without service names, `migrate`, `down`, `down -v`, or receiver/database
recreation. Validate private UI authentication and original webhook routing, health,
restart counters, resources and current backup/monitor receipts. End the write freeze
only after checks pass. Observe genuine Chartink candidate → eligible complete price
batch → durable analysis → authenticated Candidates UI independently. Do not send a
manufactured market alert or label synthetic rehearsal as Mac-off acceptance.

## Rollback commands and preservation

First stop hosted acquisition and consumption, then application writes; the receiver
and inbox stay running. Persistently disable any external scheduler that could
restart these services. Preserve the latest state, even if acceptance failed:

```sh
dc stop price-refresh worker api web
: "${STK_ROLLBACK_EXPORT:?new private rollback directory}"
python3 scripts/stk099_transfer.py backup --container "$STK_DB" \
  --owner chartink_owner --database stk_real001_private --expected-cluster 7706856885194760225 \
  --dump "$STK_ROLLBACK_EXPORT/app.dump"
# Copy the current VPS private view/watchlist with stk099_bundle.py, as above.
# Transfer and verify this NEW state on the Mac; never resume its stale pre-cutover DB.
```

If the VPS cannot provide its latest state, stop: recover the newest verified
snapshot, quantify any gap and obtain an owner recovery decision. Never reset cursor
or quota ledger. On the Mac restore to a **new** DB (the example names must be absent),
verify fingerprints, then retain the old DB under an archive name and assign the
canonical name to the verified recovered copy. No source DB is dropped:

```sh
: "${STK_MAC_APP_OWNER:?original Mac application database owner; required roles pre-provisioned}"
python scripts/stk099_transfer.py restore --context colima \
  --container "$STK_MAC_DB_CONTAINER" --owner "$STK_MAC_DB_OWNER" \
  --database stk_real001_vps_return --restore-owner "$STK_MAC_APP_OWNER" \
  --dump "$STK_ROLLBACK_EXPORT/app.dump" --expected-source-database stk_real001_private \
  --expected-source-cluster 7706856885194760225
# All Mac app clients/workers must still be stopped; assert no connections first.
docker --context colima exec "$STK_MAC_DB_CONTAINER" psql -X \
  -U "$STK_MAC_DB_OWNER" -d postgres -v ON_ERROR_STOP=1 \
  -c 'ALTER DATABASE stk_real001_private RENAME TO stk_real001_before_vps' \
  -c 'ALTER DATABASE stk_real001_vps_return RENAME TO stk_real001_private'
```

If either rename fails, stop and inspect; do not bootstrap any worker until the
canonical DB is the verified VPS return. Preserve original watchlist files before
installing the latest verified bytes and compatible private configuration. Retain
unchanged credentials and exact receiver URL/cursor identity. Run the existing
native manifest/preflight checks before reenabling the original launch agents:

```sh
for label in local.stock-discovery.chartink-consumer local.stock-discovery.candidate-price-refresh; do
  launchctl enable "$STK_GUI/$label"
  launchctl bootstrap "$STK_GUI" "$HOME/Library/LaunchAgents/$label.plist"
  launchctl print "$STK_GUI/$label"
done
```

Verify only one consumer and one refresh worker, latest cursor/quota continuity and
native app health. Restore the original receiver-only proxy config, using the
recorded original env and the two original Compose files in the authorized ingress window:

```sh
: "${STK_ORIGINAL_ENV:?preserved original receiver env file}"
docker compose --env-file "$STK_ORIGINAL_ENV" -p stock-discovery-chartink \
  -f /opt/stock-discovery/deploy/chartink/compose.yaml \
  -f /var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml \
  --profile receiver up -d --no-deps --no-build --wait proxy
```

Preserve
TLS volumes, receiver image, endpoint and secrets; no database or receiver rollback
is required. Reconcile receipts arriving during the transition, without assuming
provider redelivery. Full cutover, interruption/recovery execution and genuine
Mac-off acceptance remain unperformed.

## Focused validation

15 synthetic operations tests passed (three retained legacy tests plus 12 focused
new cases): no service stop, source/recovery separation, repository/key/bundle
identity, corruption/failure preservation, scope checking, receiver/hosted monitoring
and alert-hook failure semantics. No VPS/browser rehearsal repeated. These tests
are neither a real off-server restore nor external alert delivery.
