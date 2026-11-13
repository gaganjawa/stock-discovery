# STK-095 / D3-03 + D3-04 + D3-09: Mac consumer release closure

Status: preparation only; production activation remains NO-GO. This supplements
[the webhook fix](STK-095-webhook-rejection.md), not the STK-099 hosted migration.
No new database migration, image deployment or production service activation is
part of this change. Reuse the completed f8f930d release evidence.

## Confirmed consumer configuration

The existing Mac files are under `~/.config/stock-discovery`: `chartink-worker.env`,
`chartink-pull-secret`, `chartink-scanner.json`, `candidate-worker-db-url` and the
separate owner `production-database-url`. These were discovered after the first
preparation archive, so a supplemental private archive preserves them unchanged.
Never attach this archive or any manifest containing private paths/URLs to a PR.

Read-only verification on 13 November: the restricted credential authenticates as
`stk_candidate_worker` against `stk_real001_private`; required candidate table and
sequence grants are present. It is not superuser or BYPASSRLS. The configured
receiver URL hashes to the existing cursor identity (cursor 0), and its origin
matches the VPS proxy. The pull secret and full scanner configuration match the
archived VPS copies. No URL, secret or cursor was changed. Production remains 0016.

No candidate LaunchAgent is installed and no native worker/API process was found.
The old stopped Docker worker has no Chartink configuration and is not the
candidate launcher. The inspected STK-093 ViewConfig parses, and its referenced
grant/policy files are readable. That does not certify underlying source rights,
NSE identity coverage, price freshness or qualified research; existing research
checks continue to return blocked outcomes where evidence is insufficient.

The worker does not use filesystem watchlists. The last recorded STK-093 UI
launcher explicitly points to `backups/stk093-acceptance/watchlist`; the later
STK-095 acceptance watchlists were separately preserved. With no active UI process,
none is asserted to be the current user-selected production watchlist. Confirm the
UI launch record before changing/restarting the UI; this release does not do so.

## Minimal native supervisor

`scripts/stk095_consumer.py` runs the existing worker with `--candidate-intake
--once` repeatedly. It passes only approved configuration variables, not inherited
provider/LLM/hosted-mode settings. It checks schema 0017, existing cursor identity,
restricted role, required grants, scanner expiry and use-specific approval before
every cycle. It never creates a cursor during preflight or changes any grants.
One canonical private state directory supplies a nonblocking process lock. Existing
transactional worker locks additionally protect destination cursor commits.

Each child gets at most 180 seconds; SIGTERM stops its process group and waits up
to 30 seconds before forced termination. PostgreSQL transaction rollback and the
existing cursor/event deduplication handle interruption. Runtime output is
suppressed; private health records contain only status, times and cursor numbers.
A failed cycle is not a success heartbeat. This is a Mac-dependent bridge, not
Mac-independent hosted acceptance; macOS must remain available.

A mode-0600 manifest contains these keys (absolute paths):
`python`, `repo`, `environment_file`, `database_file`, `view_file`,
`authorization_file`, `state_directory`, `database`, `receiver_id`.
Use the existing restricted credential, frozen reviewed release source and Python
environment. Do not select the owner URL as the runtime database file.

The owner-reviewed authorization JSON binds `scanner_key`, `rights_reference`,
`enabled_until`, `evidence_reference` and `scopes` to actual reviewed evidence.
Required scopes: `receive`, `store`, `derive`, `operational_replay`. The launcher
rejects a pending rights reference and missing/expired/mismatched approval. An
approval file is a deployment record, not a provider license: do not manufacture
one or rename the pending marker to bypass review. Research grants remain separate.

Preparation (does not install/start):
```sh
PYTHONPATH="$RELEASE/shared" "$PYTHON" "$LAUNCHER" check "$MANIFEST"
PYTHONPATH="$RELEASE/shared" "$PYTHON" "$LAUNCHER" prepare-plist "$MANIFEST" \
  --output "$PRIVATE_DIR/inactive-consumer.plist"
```
The prepared plist points to an absolute persistent launcher path. Do not install
from a temporary worktree. Store its source/commit and manifest hashes with the
reviewed release. Never launch a second copy with a different state directory.

Only after owner cutover approval, rights closure and BOTH database migrations:
```sh
# Verify no competing native/Docker/launchd consumer before bootstrap.
install -m 600 "$PRIVATE_DIR/inactive-consumer.plist" \
  "$HOME/Library/LaunchAgents/local.stock-discovery.chartink-consumer.plist"
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/local.stock-discovery.chartink-consumer.plist"
launchctl print "gui/$(id -u)/local.stock-discovery.chartink-consumer"
# Controlled stop; verify launchctl print reports absent before another start.
launchctl bootout "gui/$(id -u)/local.stock-discovery.chartink-consumer"
# Restart only after shutdown verification, with the same manifest/state/cursor.
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/local.stock-discovery.chartink-consumer.plist"
```
Do not overwrite an existing LaunchAgent: if the target already exists, stop and
review its provenance. The install command above is authorized only after checking
that the target is absent. The supervisor is not installed by its preparation CLI.

Release order: final frozen backups → migrate both databases to 0017 → verify
identity/data/ACL/cursor → keep old receiver healthy → start compatible consumer
and verify original cursor → receiver-only image replacement last (`--no-deps`).
Keep original proxy/database containers, configuration, URL and volumes. Use the
pinned receiver/migration/rollback commands in the private f8f930d cutover record;
replace its unresolved Docker consumer template with this native launcher.
Rollback only the receiver image; retain schema 0017 and compatible consumer once
expanded envelopes exist. Never reset cursor or replay synthetic events into live
storage. Stopping a failed new consumer preserves backlog. Do not resume the old
generic worker as a substitute.

## Rights decision: narrowly distinguish the operations

Reviewed 13 November 2026:
- [Official webhook documentation](https://chartink.com/articles/alerts/webhook-support-for-alerts/)
  expressly describes callbacks to the user's own internet-reachable application
  for monitoring/automation. This supports private alert receipt and immediate
  processing; it is not necessary to infer those features from payment alone.
- [Terms](https://chartink.com/articles/terms-of-usage/) limit general website
  content use to temporary personal/noncommercial storage on one device and do
  not expressly resolve persistent copies across VPS, Mac and recovery storage.
- Account invoice confirms premium membership 6 November–6 December 2026; the
  activation email confirms alert features. No account-specific retention or
  recovery approval was found in the inspected correspondence.

Engineering decision, not a legal determination: private webhook receipt is a
documented feature. The precise unresolved scope for THIS implementation is
persistent raw/normalized alert-column storage, its retention duration, private
VPS→Mac replication, encrypted recovery copies, operational replay and derived
research. Record applicable contractual evidence or obtain provider clarification
for those operations. Do not request blanket trading/model rights unnecessarily.
Historical strategy evaluation/replay is distinct from retrying a failed consumer;
redistribution and third-party model transfer are separate and remain disabled.
No orders or model calls are authorized by the webhook documentation.

## Smallest recovery and independent monitoring closure

Use the already selected encrypted restic/B2 design; do not activate the legacy
`operate.py backup` unchanged: it stops the full app and its older fingerprint
covers only research tables. Instead upload the complete, verified two-database
transfer bundle and private files from the existing STK-099 transfer workflow.
The uploaded bundle must include the newly found consumer configuration, original
cluster identities, all-table/sequence manifests, image IDs and recovery commands.
Do not include the restic repository password in that bundle.

Owner actions: approve an existing B2 bucket/account, restricted backup identity,
separate encryption-key custody and retention. No purchase, account creation,
credential generation or upload is performed here. Use the least permissions
restic requires, with independent owner-controlled prune credentials; validate the
chosen backend's actual permissions, not an assumed append-only guarantee.
[restic repository/key guidance](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)
explains password-file configuration and recovery-key requirements.

After authorization, the minimal operator flow is:
```sh
# RESTIC_REPOSITORY_FILE and RESTIC_PASSWORD_FILE point to private existing files.
restic backup --json --tag stk095 "$VERIFIED_FROZEN_BUNDLE"
restic check --read-data
restic restore "$EXACT_SNAPSHOT_ID" --target "$NEW_ISOLATED_RECOVERY_DIR"
# Compare bundle hashes; then restore BOTH databases with explicit expected source
# database/cluster identities and compare all tables/sequences using stk099_transfer.
```
No automatic init, forget, prune or overwrite. A local synthetic encrypted test
passes backup/check/restore and wrong-key rejection, but is NOT off-server recovery.

Independent monitoring must run outside the VPS and outside the Mac consumer's
failure domain: external HTTPS health probe plus missing-heartbeat alarm, routed
to an owner-selected destination. Authenticated collection additionally supplies
high-water, cursor, rejection count, last receipt and last verified backup time.
Never give an external public probe a webhook capability URL. A missing expected
EOD receipt means delivery unverified, never zero market matches. The pure
`scripts/stk095_health.py` emits only diagnostic codes, sends nothing, and rejects
stale/future observations, cursor-ahead, backlog, missing consumer/backup heartbeat
and recent rejections. Owner must approve the collector credentials/destination,
external monitor and test outage/alert receipt. No external monitor is activated.
