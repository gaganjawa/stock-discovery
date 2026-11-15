# STK-099 / D3-03 + D3-04 + D3-09 + D3-12 — restored VPS rehearsal

This slice reconciles schema 0017 hosting with the merged STK-014 price worker.
It adds an opt-in `compose.refresh.yaml`, separate acquisition-role grants and
credential preparation (`stk099_prepare.py --price-refresh`). The existing worker,
Upstox adapter, grants, quotas, leases and immutable ingestion remain unchanged.
Only the acquisition service gets an egress network and provider secret; the API
and candidate consumer retain their internal networks and restricted roles.

The candidate and acquisition worker ceilings are 128 MiB each, retaining the
existing combined 256 MiB budget and 1,376 MiB total service ceilings. Treat these
as tested bounds only for the recorded load, not proof of full-market capacity.
The optional refresh heartbeat reports completion of a processing cycle; job
failures remain explicit in PostgreSQL. A failed cycle does not advance health.
Its 960-second age bound permits a fenced acquisition attempt; inspect job errors
and quota usage separately from container liveness.

## Consistent online backup

The existing `stk099_transfer.py backup --online` exports one read-only PostgreSQL
snapshot for pg_dump and all table fingerprints. Ordinary row updates can continue.
Sequence state is not MVCC: any observed allocation or schema change causes failure
without a completed manifest. Exporter lifetime spans the dump and verification.
Restore still verifies source identity, schema, checksum, every table and sequence,
and requires a new target. It never cleans or drops an existing database.

This closes an observed rehearsal failure: the live inbox rate counter changed
while the old quiescent backup compared before/after rows. No webhook stop was
needed. An isolated regression kept updating a counter during export, then restored
the exact snapshot. The quiescent backup path and final cutover write-freeze
requirements remain available and unchanged.

## Representative rehearsal

`stk099_representative.py` uses verified application/inbox dumps and the existing
watchlist bundle in a new Compose project, with its own PostgreSQL volume and
loopback-only TLS. Source cluster IDs must be supplied independently. A restored
inbox initially has a distinct name for transfer safety; after fingerprint checks,
only the new rehearsal cluster renames its empty bootstrap database and restored
copy to satisfy the existing hosted identity fence. Production names/volumes never
enter a rename operation. Failed projects remain stopped for inspection.

The rehearsal deliberately omits live provider credentials and removes acquisition
egress. It verifies restored private API reads, concurrent company reads, browser
watchlist/Candidates access, consumer/refresh restart, table/sequence preservation,
watchlist hashes and a second recovery restore. It samples host headroom/swap and
container resources, rejects <384 MiB available RAM or >=256 MiB swap use, and
checks that preexisting live container identities, images and start times survive.
Browser acceptance runs through an SSH loopback tunnel, without mocked API data.
This is representative stored-data acceptance, not genuine candidate acceptance or
provider-load certification.

Inputs are a private directory containing `app.dump`, `app.manifest.json`,
`inbox.dump`, `inbox.manifest.json`, `bundle/`, `scanner.json` and `prior-url`.
Set API_IMAGE/WORKER_IMAGE/WEB_IMAGE to reviewed images and CODE_VERSION explicitly.
Set STK099_REQUIRE_BROWSER=1 to require the external browser marker. Never use
production DSNs or provider tokens in the rehearsal directory.

## Live STK-014 session diagnosis — 14 November IST

Main merge `098ba86ad8d386ed887d769239ec21cdb424cddd` passed all required CI jobs.
The single additional diagnostic requested INFY NSE EQ (INE009A01021), daily bars,
from 2026-11-12 through 2026-11-13 using the existing historical V3 endpoint.
At 2026-11-13T19:21:38Z it returned HTTP 200 with only the raw 12-Nov midnight IST
label. The Date header was 19:21:39 GMT and Age was 56,991 seconds. Stored observed
NSE calendar evidence marks 13-Nov 03:45–10:00 UTC as an open session; no instrument
suspension is present in the existing active EQ mapping.

[Upstox documents to_date as inclusive](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/).
The date is absent before adapter validation, including in the two-day request.
This establishes an incomplete upstream response; its old cache age supports lag,
but the provider's internal cache/update cause is not established. No ingestion
or range-boundary defect is demonstrated. No intraday data was fetched or stitched.

The existing unavailable state is missing_sessions=[2026-11-13], partial coverage,
no current rank and no re-analysis trigger. For a genuine eligible candidate, the
worker retries readiness after 900 seconds, at most three attempts per job; exhausted
coverage stays partial. It refreshes a coherent window and uses the durable quota
ledger. No new production candidate or job is manufactured to force a retry.

## Observed acceptance — 14 November IST

The BookMyHost x86_64 rehearsal restored 70 application tables, 6,737 rows (including
alembic_version), three sequences and the schema-0017 inbox. All source fingerprints,
sequence values and watchlist bytes matched. The actual browser saw the one saved
watchlist entry and 12 workbench rows; Candidates remained empty. Twenty-four company
reads at concurrency four, both worker restarts and a second recovery restore passed.
No provider credential/egress or simulated genuine candidate was used. All rehearsal
containers were stopped; the three original live services retained their IDs, images
and start times and remained running. No production cutover occurred.

Rehearsal image IDs (local AMD64 images, not published registry digests):

- API: `sha256:e4979c6f99cb501eb2eaedb1a1b69b861de8f4c26fabd492c8dcdff13b0103ea`
- Worker: `sha256:de4fa48de8937924c930fe6d9751b7adc78027677cc369459d2e5c9f0e31d2fb`
- Web: `sha256:2a3194d92e6f7dbfc690447d2a55016c35635877c3d58f0b60ed781f3cc8f913`

Read-only production recheck at 2026-11-15T13:01Z: consumer PID 8125 and refresh
PID 8129 remained running with one launch each; exactly one refresh process was
present. Consumer completion age was five seconds. Schema 0017, cursor 3, three
events, zero candidates and 2,648 revisions were unchanged. There were no refresh
jobs and zero quota requests in the preceding minute, 30 minutes or 24 hours.

Minimum sampled host available RAM: 1,008.6 MiB. Maximum swap use: 3.1 MiB. Maximum
sampled service usage: API 99.2 MiB, PostgreSQL 64.5 MiB, receiver 49.2 MiB, refresh
38.4 MiB, candidate worker 35.3 MiB, Caddy 13.9 MiB and web 2.3 MiB. No OOM occurred.
These samples support the tested stored-read/idle-refresh load; active provider-load
and genuine candidate throughput remain unverified. No host upgrade is demonstrated
necessary by this measurement.

Rehearsal-only startup failures were corrected: archive directory modes prevented
non-root imports; a noncanonical inbox name triggered the intended hosted identity
fence. The source packaging and isolated rename sequence were corrected; neither
required weakening production checks. The browser's initial five-second wait was
too short for restored workbench loading; its bounded wait is now 60 seconds.

The historical saved-scan endpoint returns 403 in the restored stack. A read-only
comparison confirmed the same denial on the Mac and absent legacy universe lineage.
That restriction was preserved, not bypassed; current workbench, watchlist and
Candidates reads passed. Missing current price evidence remains unranked.

Validation: 10 candidate refresh unit tests, 10 transfer/preparation/bundle/resource
unit tests, an actual concurrent-counter PostgreSQL snapshot/restore regression,
UI build and the actual VPS/browser/recovery run. The PostgreSQL regression is also
wired into CI. The main merge's four jobs passed; this focused PR needs its own CI.

## Remaining release conditions and next command

No restic executable or Stock Discovery systemd backup/monitor unit was found on the
VPS. Encrypted off-server restore, key custody and external alert delivery are still
unverified; the completed recovery test is an isolated same-host restore. Do not
represent it as off-server disaster recovery. Full production cutover requires its
separate release authorization and a fresh final export/watchlist check.

Before authorized cutover, stop and persistently disable BOTH Mac consumer and price
refresh launch agents, verify their singleton locks released, and export the current
application DB including cursor and quota ledger. Keep the existing receiver running.
Restore into verified new VPS targets and retain rollback snapshots. Prepare the
separate role with `python scripts/stk099_prepare.py --price-refresh PRIVATE_DIR`,
apply the reviewed grants only to the application DB, and remap the existing token,
grants and one-symbol config into the refresh service's private mounts. Do not run
Mac and VPS acquisition against separate quota ledgers at the same time.

Use the existing hosting overlay plus `deploy/bookmyhost/compose.refresh.yaml` and
explicit `--profile price-refresh`; activate only reviewed services with `--no-deps`
after dependency checks. A rollback must carry forward the latest VPS DB/watchlist
and quota history before reenabling the Mac. Receiver URL, secrets, volumes and
schema remain unchanged. Genuine Chartink → qualified price → analysis/UI acceptance
and volume-qualified signals remain separate, pending evidence.
