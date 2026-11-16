# STK-095 · D3-03 Revision storage and ingestion — private rejection evidence

## Confirmed production failure

Read-only inspection on **16 November 2026, 13:42–13:45 UTC** found one retained
`invalid_columns_fields` rejection at **11:30:04.603766 UTC / 17:00:04.603766 IST**.
This code follows authentication, scanner identity, symbol/price and time checks,
and column-array length validation. It means a row is not an object or its key set
differs from the exact `chartink-columns-v1` contract. It does **not** identify the
missing/extra keys or prove a genuine provider sender. Diagnostics were disabled,
receiver/proxy logging was disabled, and the database retained only a body hash,
reason and timestamp. The rejected original JSON cannot be reconstructed.

Both databases were schema **0017**. Remote high-water and Mac cursor **3**;
three accepted events were provider Tests, genuine accepted events/candidates and
refresh jobs **zero**. Latest accepted receipt: 13-Nov **16:16:04.537076 UTC**.
Scanner: `Stock Discovery - EOD Swing Candidates v1`, slug
`stock-discovery-eod-swing-candidates-v1`, version 1. Scanner authorization expires
**18-Nov 12:11:49 UTC**; check the existing approval window before the next delivery.
No scanner change is included here. Consumer PID 8125, refresh PID 8129, one launch
each; latest consumer cycle completed normally. Existing INFY data remains stale:
latest complete stored session **4-Nov**, not current complete OHLCV acceptance.

## Implemented capture and boundaries

Opt-in receiver-local archive, independent of PostgreSQL/schema/cursor:

- Private directory owned by runtime UID/GID **10001:10001**, mode **0700**;
  archive, lock and temporary file **0600**. Unsafe ownership, symlinks and hardlinks
  fail closed for capture. No HTTP endpoint returns the archive.
- At most **20 records**, **128 KiB per record**, **1 MiB archive**, **24 hours**.
  Atomic replacement can temporarily use an additional 1 MiB. Existing 30-second
  container health checks prune expiry and interrupted temporary writes; age cleanup
  resumes at the first health check after downtime. No new service/timer.
- Redacted decoded JSON, UTC timestamp, reason, SHA-256/body length and per-row
  missing/extra column names plus JSON value types. Column report covers at most
  200 rows and explicitly marks truncation. Oversize records retain bounded summary
  metadata and `capture_omitted=record_size_limit`, not an apparently complete payload.
- Redact `webhook_url`, credential-named values, configured webhook/pull/database
  secrets (including secret files), URLs, Bearer/Basic credentials, credential
  assignments and token-shaped strings. Unknown field **values** are redacted;
  unknown names/types remain private after redaction. Redaction takes precedence
  over exact names. Known market/scanner fields remain available for comparison.
- Invalid JSON/duplicate-key bodies retain metadata only; unparseable raw bytes
  cannot be reliably redacted. Unauthenticated, oversized and other transport
  rejections are not buffered outside the existing 64 KiB request limit.
- Authenticated health still returns only the existing whitelisted structure
  summary plus time/availability. Capture failure leaves the request rejected and
  makes internal `/healthz` return **503 Private rejection capture unavailable**.
  No payload, exception text or secret is emitted to public logs.

The production column adapter is **unchanged**: no genuine payload was retained to
justify accepting an alternate key set. Capture resolves the verified diagnostic
gap; it does not establish that the next genuine request will be accepted.

## Focused validation

Isolated synthetic fixtures exercise exact missing/extra fields/types, nested
redaction and secret-file tokens, no HTTP disclosure, malformed JSON, concurrent
writers, retention count/bytes/expiry, crash cleanup, unsafe file paths, and capture
failure. PostgreSQL integration exercises rejected requests with zero event/
candidate/cursor creation, durable accepted original/columns envelopes, replay,
provider-Test zero materialization and consumer delivery. These are regression
checks, not genuine market acceptance. Focused unit and PostgreSQL delivery checks
passed on 16-Nov; the storage/capacity capture additions passed the affected
PostgreSQL rerun. Compose overlay validation and Markdown/link checks passed.
Exact-head CI belongs to the PR; the owner monitors without an agent wait.

## Minimal release preparation — do not execute without release approval

Only the receiver image and its private capture mount change. Keep the existing
project, base Compose, release overlay, env/secrets, URL, proxy, database volume,
scanner, Mac consumer and refresh worker. No migration, UI restart or full app release.
Require merged reviewed commit and its passing exact-head CI. Build/package that
commit's `backend/Dockerfile` for the VPS architecture using the existing release
process; record commit, image ID/digest and transferred image verification. No image
has been built, transferred or deployed by this documentation change.

Observed rollback receiver image:
`sha256:f9e0103a16bc01a03faed376921960d70646ada9423fc280ddec88ff82111b4c`.
Preserve it locally on the VPS; verify it still exists before replacing anything.
Existing project is `stock-discovery-chartink`; base and current release files:

- `/opt/stock-discovery/deploy/chartink/compose.yaml`
- `/var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml`

After authorization, copy the reviewed `compose.rejections.yaml` to a private
release directory, set `STK095_OVERLAY` to its absolute path, set
`CHARTINK_REJECTION_DIR` to an approved dedicated persistent directory and
`CHARTINK_REJECTION_IMAGE` to the verified new immutable image. These are required
release inputs, not invented existing paths. Retain the exact existing private
Compose environment (`CHARTINK_SECRETS_DIR`, receiver domain and enabled flag);
never print it or use unredacted `docker compose config` in logs.

```sh
# Run as the existing VPS release operator, after approval and image verification.
test -n "$CHARTINK_REJECTION_DIR"
test -n "$CHARTINK_REJECTION_IMAGE"
test -f "$STK095_OVERLAY"
# Stop if this path already exists with unexpected contents/owner/mode.
# For a new dedicated directory only:
install -d -m 0700 -o 10001 -g 10001 "$CHARTINK_REJECTION_DIR"
export CHARTINK_REJECTION_DIR CHARTINK_REJECTION_IMAGE

docker compose -p stock-discovery-chartink \
  -f /opt/stock-discovery/deploy/chartink/compose.yaml \
  -f /var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml \
  -f "$STK095_OVERLAY" config --quiet

docker compose -p stock-discovery-chartink \
  -f /opt/stock-discovery/deploy/chartink/compose.yaml \
  -f /var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml \
  -f "$STK095_OVERLAY" up -d --no-deps --no-build --pull never receiver
```

Before and after: record receiver image/health, proxy/database container IDs and
start times, schema version, event counts/high-water and Mac cursor. Confirm 0700/
0600 capture ownership, diagnostics availability and unchanged secret-file mounts.
Do not print URL/capability or archive values. Do not send a manufactured alert.
The ordinary next rejected delivery can be inspected privately via SSH: compare
`column_contract` with `chartink_columns.COLUMNS`, retaining only sanitized exact
field/type findings in a regression fixture. Fix only that observed difference.

Rollback uses the **original** Compose inputs without the capture overlay:

```sh
docker compose -p stock-discovery-chartink \
  -f /opt/stock-discovery/deploy/chartink/compose.yaml \
  -f /var/backups/stock-discovery/stk095-hotfix-20261113/receiver-release.yaml \
  up -d --no-deps --no-build --pull never receiver
```

Verify old image and health and unchanged event/cursor state. Capture bind data is
not in a database volume and must not enter Git, artifacts or public logs. If the
new receiver is rolled back/stopped, its age-pruning health hook stops too: the
release operator must remove expired capture archive/temp files within the private
directory or run the reviewed pruner offline under UID 10001. Never prune inbox,
secret files or application volumes.

Genuine acceptance requires the ordinary provider delivery, exact scanner/event
identity, HTTP 202/durable receipt, deduplicated real retry if observed, consumer
cursor advancement, matching symbols/candidates, refresh eligibility and qualified
analysis/API/UI evidence. If no retry occurs, report retry acceptance separately as
pending. Provider Tests remain excluded. **Live ingestion fix/acceptance is pending**.
