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
or run a second PostgreSQL server on this small host. No schema migration beyond
0016 is needed. Existing API, frontend and worker images supply the application.

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

## Exact operator sequence (after review/approval)

Do not execute production-mutating steps until the owner approves host staging,
resource/load results, encrypted off-server recovery and the cutover window.
Use the reviewed commit, not a moving branch. Values below use observed paths;
`RELEASE` and image digests must be the exact reviewed build. No command removes
volumes or changes the existing webhook URL.

### 1. Read-only preflight and immutable image preparation

From the Mac repository:

```sh
SSH_KEY="$HOME/.ssh/stock-discovery-vps"
ssh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -i "$SSH_KEY" root@160.22.109.189 python3 - < scripts/stk099_preflight.py
```

Build/test linux/amd64 images on a capable builder/CI, using existing Dockerfiles,
then deliver reviewed image archives or immutable registry digests to the VPS.
For a native Linux x86_64 builder, after checking out the reviewed commit in a clean
checkout (never the Mac WIP tree):

```sh
RELEASE=REVIEWED_COMMIT_SHA
test "$(git rev-parse HEAD)" = "$RELEASE"
docker build --platform linux/amd64 -t stock-discovery-api:$RELEASE -f backend/Dockerfile .
docker build --platform linux/amd64 -t stock-discovery-worker:$RELEASE -f worker/Dockerfile .
docker build --platform linux/amd64 -t stock-discovery-web:$RELEASE frontend
docker tag stock-discovery-api:$RELEASE stk099-api:acceptance
docker tag stock-discovery-worker:$RELEASE stk099-worker:acceptance
docker tag stock-discovery-web:$RELEASE stk099-web:acceptance
STK099_STACK_BROWSER=1 PYTHONPATH=backend:shared:worker \
  python3 scripts/stk099_rehearsal.py /tmp/stk099-release-test --context ''
docker save stock-discovery-api:$RELEASE stock-discovery-worker:$RELEASE \
  stock-discovery-web:$RELEASE | gzip > stk099-images.tar.gz
sha256sum stk099-images.tar.gz > stk099-images.tar.gz.sha256
git archive --format=tar.gz -o stk099-source.tar.gz "$RELEASE"
```

Transfer the archives/checksum by SCP. On the VPS verify `sha256sum -c`, load via
`docker load -i stk099-images.tar.gz`, extract source to the new release path, and
record each `docker image inspect --format '{{.Id}} {{.Architecture}}'` result.
Compose also accepts immutable local `sha256:<image-id>` references when no image
registry is used. Do not silently use an ARM build on this x86_64 host.
Do not build the frontend on the running 2 GiB VPS. The local rehearsal uses
`stk099-api:acceptance`, `stk099-worker:acceptance`, `stk099-web:acceptance`; those
ARM development tags are not production artifacts. CI's Linux image build and
rehearsal must pass on the PR commit before a release is selected.

### 2. Freeze Mac writes and export database plus private files

Stop the actual Mac candidate process and private UI writes using their recorded
launcher/PID; do not stop the database or kill unrelated Python processes. Stop
any configured stored-only scheduler that writes to this DB. Keep the receiver
running: its inbox safely accumulates real deliveries. Confirm pg_stat_activity
has no other writers and retain the unchanged Mac DB for rollback.

```sh
umask 077
python3 scripts/stk099_transfer.py backup --context colima \
  --container stock-discovery-database-1 --owner stock_discovery \
  --database stk_real001_private --expected-cluster 7695120939741798433 \
  --dump backups/stk099-cutover.dump
# VIEW is the exact existing REAL_RESEARCH_VIEW_CONFIG path, not an example.
.venv/bin/python scripts/stk099_bundle.py --view "$VIEW" \
  --watchlist "$WATCHLIST" --destination backups/stk099-private-bundle
```

Use the configured watchlist directory (default `backups/private-watchlist`).
Inspect the bundle's file-hash manifest, listing_ids, policy flags and original
file provenance privately. No provider keys belong in the bundle. Create a fresh
backup filename for each attempt; scripts deliberately refuse overwrites.
Transfer over SSH/SCP into a **new** root-only release directory:

```sh
RELEASE=REVIEWED_COMMIT_SHA
ssh -i "$SSH_KEY" root@160.22.109.189 "install -d -m 700 /var/lib/stock-discovery/releases/$RELEASE"
scp -i "$SSH_KEY" backups/stk099-cutover.dump backups/stk099-cutover.manifest.json \
  root@160.22.109.189:/var/lib/stock-discovery/releases/$RELEASE/
scp -i "$SSH_KEY" -r backups/stk099-private-bundle \
  root@160.22.109.189:/var/lib/stock-discovery/releases/$RELEASE/
```

Deliver reviewed source separately under `/opt/stock-discovery/releases/$RELEASE`
without replacing the running receiver checkout. Verify Git SHA and image digests.
Verify every bundled SHA-256 on the VPS before ownership changes.

### 3. New credentials, rehearsal restore and recovery

On the VPS, using the reviewed source directory:

```sh
cd /opt/stock-discovery/releases/$RELEASE
python3 scripts/stk099_prepare.py /etc/stock-discovery/stk099
# Review this private SQL locally; it creates NEW roles, never alters existing ones.
docker exec -i stock-discovery-chartink-database-1 \
  psql -X -U chartink_owner -d postgres -v ON_ERROR_STOP=1 \
  < /etc/stock-discovery/stk099/bootstrap.sql
python3 scripts/stk099_transfer.py restore \
  --container stock-discovery-chartink-database-1 --owner chartink_owner \
  --database stk099_rehearsal --restore-owner stk_app_owner \
  --dump /var/lib/stock-discovery/releases/$RELEASE/stk099-cutover.dump
```

The restore tool verifies all tables/sequences, and cannot overwrite chartink_inbox
or an existing target. This adds a database to the existing volume; it does not
recreate that volume. Do not run migrations against either production database.
Keep credentials in root-only parent directories. For container readability,
`chown 10001:10001` only the new app_url/worker_url/source_url/owner_access files
and the new private/watchlist directories; files 0600, directories 0700. The root
proxy can read root-owned `ui_auth` 0600. Existing receiver secret ownership stays
unchanged. Do not recursively chmod `/etc/stock-discovery`.

Generate an edge password interactively with the pinned Caddy image:

```sh
docker run --rm -it caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d \
  caddy hash-password
```

Store only the line `owner <generated-bcrypt-hash>` in `/etc/stock-discovery/stk099/ui_auth`; keep the password and generated
owner_access in the owner's password manager. Never paste plaintext into commands,
Git, PRs or logs. `bootstrap.sql` contains credentials and remains private.

Before final cutover, back up both the receiver and new app snapshot plus watchlist
and config with the existing encrypted off-server backup design. No paid account
or key custody is selected by this change. If no approved encrypted repository/key
and external alert destination exist, **cutover stays blocked**. Verify a restore
from that off-server copy, not merely the local dump; record the manifest hash,
recovery duration, backup age and location of the separately held decryption key.

### 4. Host staging/load gate and final restore

First run the synthetic rehearsal on an approved staging machine/VPS window with
its own project/volumes and loopback port, using linux/amd64 images. Never send its
payload to the production capability. On a 2 GiB VPS do not run a second complete
stack concurrently unless measured headroom supports it. Prefer same-sized
isolated staging or a reviewed maintenance window; static idle memory alone is
not permission to overload the receiver. Use SSH forwarding for private staging.
The reusable command is:

```sh
STK099_STACK_BROWSER=1 PYTHONPATH=backend:shared:worker \
  python3 scripts/stk099_rehearsal.py /private/stk099-new-rehearsal --context ''
```

Python dependencies and Playwright must be installed on that test runner. It leaves
stopped volumes and sanitized results. Require no OOM/restarts under representative
load, <75% of each container limit, >384 MiB host available RAM, stable swap, no
missed/duplicate events, verified TLS/private auth and restore. Repeat with the
real restored copy for read-only history/UI plus stored-only analysis, not invented
market rows; confirm source permissions and mapped file paths. No LLM test here.

When approved, refresh final Mac snapshot and bundle under the same frozen-write
procedure if anything changed since rehearsal. Restore to the **new final** DB:

```sh
python3 scripts/stk099_transfer.py restore \
  --container stock-discovery-chartink-database-1 --owner chartink_owner \
  --database stk_real001_private --restore-owner stk_app_owner \
  --dump /var/lib/stock-discovery/releases/$RELEASE/stk099-cutover.dump
docker exec -i stock-discovery-chartink-database-1 psql -X -U chartink_owner \
  -d stk_real001_private -v ON_ERROR_STOP=1 < deploy/bookmyhost/grants.sql
docker exec -i stock-discovery-chartink-database-1 psql -X -U chartink_owner \
  -d chartink_inbox -v ON_ERROR_STOP=1 < deploy/bookmyhost/source-grants.sql
python3 scripts/stk099_transfer.py verify \
  --container stock-discovery-chartink-database-1 --owner chartink_owner \
  --database stk_real001_private \
  --dump /var/lib/stock-discovery/releases/$RELEASE/stk099-cutover.dump
```

### 5. Reviewed Compose environment and cutover

Create a private `/etc/stock-discovery/stk099/compose.env` with these non-secret
values (replace image references with tested immutable digests):

```dotenv
RECEIVER_DOMAIN=160-22-109-189.sslip.io
CHARTINK_RECEIVER_ENABLED=true
CHARTINK_SECRETS_DIR=/etc/stock-discovery/chartink
STK099_SECRETS_DIR=/etc/stock-discovery/stk099
STK099_CONFIG_DIR=/opt/stock-discovery/releases/REVIEWED_COMMIT_SHA/deploy/bookmyhost
STK099_PRIVATE_DIR=/var/lib/stock-discovery/releases/REVIEWED_COMMIT_SHA/stk099-private-bundle/private
STK099_WATCHLIST_DIR=/var/lib/stock-discovery/releases/REVIEWED_COMMIT_SHA/stk099-private-bundle/watchlist
CHARTINK_RECEIVER_URL=https://160-22-109-189.sslip.io
CODE_VERSION=REVIEWED_COMMIT_SHA
API_IMAGE=reviewed-api@sha256:REVIEWED_DIGEST
WORKER_IMAGE=reviewed-worker@sha256:REVIEWED_DIGEST
WEB_IMAGE=reviewed-web@sha256:REVIEWED_DIGEST
```

The receiver URL must match the Mac's exact string (including a trailing slash if
present); verify the restored candidate_receivers receiver_id equals its SHA-256
via the existing `candidate_store.digest`, not a new ad-hoc hash format.
Use the **existing base Compose path** to preserve volume identity; the overlay
only adds services/config and resource tuning. Confirm rendered volumes equal the
observed three production names before applying anything.

```sh
dc() {
  docker compose --env-file /etc/stock-discovery/stk099/compose.env \
    -p stock-discovery-chartink \
    -f /opt/stock-discovery/deploy/chartink/compose.yaml \
    -f /opt/stock-discovery/releases/$RELEASE/deploy/bookmyhost/compose.yaml \
    --profile receiver "$@"
}
dc config --quiet
# Save the old receiver image ID, Compose/config hashes and container inspect
# privately for rollback before the following maintenance-window step.
dc up -d --no-build --wait database receiver api worker web proxy
```

This briefly restarts PostgreSQL for tuning and the receiver/proxy for new code;
Chartink delivery during downtime has no guaranteed retry. Choose a quiet window,
record the gap, and inspect alert history. Do not change the alert URL/email.
No command above invokes the setup/migrate profile or drops a volume.

From another device verify TLS, edge login, owner login, historical research,
watchlist, candidates, blocked reasons and no public health/docs/API/DB access.
Stop the Mac completely. Observe a **genuine** Chartink delivery, durable inbox
commit, application cursor advance, one candidate/research result and UI display.
If no genuine delivery arrives, report this gate pending; never substitute a
synthetic delivery. Test worker restart using the same committed genuine rows.

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

The candidate worker cannot write research evidence or paper tables. API cannot
write processed paper receipts, shadow references/outcomes, revisions, grants or
restriction fences. The dedicated hosted worker still runs candidate intake only;
queued paper observations and synthetic publication jobs require the existing
separately operated execution worker. This correction grants no worker activation.

Local validation: 1,053 application/worker unit tests passed, plus script tests.
PR CI supplies disposable PostgreSQL role/route regressions, migrations, Linux
hosted research probe and browser acceptance. Exact-head CI evidence is recorded
in PR #48. No production services, volumes, credentials or webhook URL changed;
all previously listed owner/recovery/rights/cutover/genuine-delivery gates remain.
