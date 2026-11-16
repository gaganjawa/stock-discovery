# STK-095 / STK-014 · D3-03 — durable intake and asynchronous parsing

## Evidence and current implementation

On 16-Nov at **11:30:04.603766 UTC / 17:00:04.603766 IST**, production rejected a
request with `invalid_columns_fields`. It reached authentication/scanner/row-count
validation, but the original JSON was not retained. Exact genuine field differences
remain unknown. Last read-only production evidence (13:42–13:45 UTC): both databases
schema **0017**, remote high-water/Mac cursor **3**, three accepted provider Tests,
zero genuine candidates/refresh jobs, 2,648 price revisions. Latest complete stored
INFY session **4-Nov** is stale. Scanner approval expires **18-Nov 12:11:49 UTC**.
No production changes or provider requests were made in this PR.

PR #59 now supersedes its initial capture-only implementation:

- Authenticate, rate-limit, enforce existing JSON transport and **64 KiB** request
  bound, save immutable `chartink-raw-v1` in existing `candidate_events`, then return
  **202 / delivery_kind=unclassified**. The receipt means durable intake, not a
  validated candidate or classified provider Test. Capacity/database failures never
  acknowledge success. Existing inbox count/size bounds and deduplication apply.
- Preserve raw JSON text/unknown fields for replay, original body SHA-256/length,
  receipt time and scanner snapshot. Redact credential properties (including nested
  values/escaped names), webhook URL, URLs, Bearer/Basic strings and configured
  capabilities. Redaction intentionally prevents byte-for-byte reconstruction;
  malformed syntax is retained in redacted form with its original syntax error.
  Syntax checking at intake serves privacy only; it never validates known columns.
- Pull the receipt to the existing Mac database and commit it with the existing
  cursor. The existing worker parses under its approved scanner configuration.
  Unknown schema/invalid identity/values/expired authorization are quarantined in
  existing failed-event state, with bounded reason/time/field/type diagnostics.
  A poison receipt does not block following valid events. No new queue or worker.
- **0018**, an additive migration, adds bounded `parsed_envelope` and `diagnostics`
  columns to event state. Immutable raw events stay unchanged. Validated result and
  candidate materialization commit together; interruption rolls the claim back.
  Existing legacy envelopes remain supported. Replay uses the existing authenticated
  event retry; no cursor reset. Completed deliveries cannot be replay-reset.
- Candidates reads the stored validated result. UI displays quarantine diagnostics
  and queues replay without claiming candidate creation or enabled acquisition.
  Existing source grants, price jobs, quotas, calendars, research and watchlist remain
  authoritative. Provider Tests classify asynchronously and create no candidates.
- Initial PR #59's optional 0600 private archive remains bounded diagnostic support
  for **storage rejection**, not the durable replay source. Its existing 20-record,
  128 KiB-record/1 MiB-archive, 24-hour limits remain. Normal raw receipts live in the
  private database, never a public log or Candidates API response. Feed access uses
  the existing separate pull credential. Do not enable payload/access logging.

## Focused evidence (all synthetic, no market/provider calls)

Passed targeted PostgreSQL checks cover durable unknown schemas, exact column
quarantine, later-valid-event isolation, duplicate receipts, legacy-to-raw candidate
deduplication, interruption/restart, cursor preservation, parser-upgrade replay,
provider-Test exclusion and immutable migration history. The 0018 downgrade guard
refuses to discard retained parsed/quarantine evidence. Schema-version compatibility
checks were updated only where needed by the migration and existing transfer tool.

The actual local browser passed authenticated raw webhook → candidate → bounded
mock Upstox acquisition through the real adapter/calendar/grant/quota contracts →
immutable price revisions → analysis → ranked Candidates → opened company research
→ saved/reviewed watchlist. Current views share the same coherent price batch.
Volume remains unavailable, page rank is not global rank, and no BUY is invented.
Focused UI tests cover quarantine diagnostics and replay; frontend build passed.
These results do not certify a genuine Chartink event or current live Upstox coverage.

## Required release sequence — approval pending, do not execute yet

This is now a compatible **application/consumer plus receiver** release, not the
superseded receiver-only capture rollout. No VPS application cutover is involved.

1. Owner reviews PR #59 and its exact-head CI, then authorizes deployment and the
   justified additive **0018** production migrations. Build reviewed merged artifacts,
   record actual digests and preserve current image/code/config rollback references.
2. Use existing state-preserving backup procedures; preserve both original database
   identities, event/history/price revisions, scanner, secrets, watchlist and cursor.
   Apply 0018 with the migration owner under a short bounded lock timeout. No table
   recreation, destructive migration, role replacement or cursor mutation.
3. Install compatible application/API/UI and Mac consumer code using the existing
   controlled singleton stop/restart procedure. No second active consumer. Existing
   restricted table grants cover additive columns. Consumer preflight requires 0018;
   refresh supports 0017/0018 and retains its configured account/grants/quotas/scope.
4. Only then replace the VPS receiver using project `stock-discovery-chartink`,
   existing `/opt/stock-discovery/deploy/chartink/compose.yaml` and current approved
   release overlay, with **`up -d --no-deps --no-build --pull never receiver`**.
   Preserve URL/credentials, proxy, database volumes and scanner. The optional private
   capture overlay requires a dedicated UID/GID 10001, 0700 directory; files are 0600.
5. Record actual images, schema versions, singleton health, raw/parsed/quarantined
   counts, remote high-water and local cursor before/after. Receiver health reports
   raw receipts as unclassified; classification belongs to asynchronous local state.

Rollback must preserve schema 0018, raw receipts and parsed evidence. Restore the
previous receiver image (last observed
`sha256:f9e0103a16bc01a03faed376921960d70646ada9423fc280ddec88ff82111b4c`)
using the original Compose inputs and `--no-deps`. Keep a compatible consumer to
drain already-retained raw receipts; rolling back to a consumer that cannot read
raw envelopes can stall it, and must never be disguised by resetting the cursor.
Do not downgrade 0018 after parse/quarantine evidence exists. Stop the affected
consumer if necessary, preserve its cursor and fix forward. No rollback is licensed
to delete new events or restore an older database over them.

## Exact remaining production acceptance

After separately approved release, observe an ordinary genuine Chartink delivery:
HTTP 202/durable raw identity → cursor commits local copy → strict parse or explicit
quarantine → original symbol count/candidates → eligible refresh → complete current
qualified EOD batch → durable analysis → authenticated Candidates and watchlist.
If quarantined, use the private retained payload to establish the actual difference,
add its sanitized regression, deploy only the verified parser fix and replay the
same receipt. Verify deduplicated retry if an actual retry occurs; otherwise report
that live observation pending. Do not manufacture an alert or backdate candidates.
Existing live price incompleteness may still keep indicators unavailable/unranked.
**No genuine market acceptance or production activation is claimed.**
