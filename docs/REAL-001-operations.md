# REAL-001 — unattended local research operations

24 October 2026 · STK-014/017/058/059/060/073 · existing D3-03–10 pipeline.
Baseline `619030131b2deb1db400ef9059ad0a4cd430e5cd`, draft PR #12, exact-head CI passed.

**AUTOMATED RESEARCH OPERATIONS: PARTIAL. PROSPECTIVE RECOMMENDATIONS: BLOCKED.**

## Continuity and startup

Phase 10's final worker was deliberately stopped after bounded acceptance. Its earlier overnight disappearance has no recorded process exit reason. macOS power logs confirm sleep/dark-wake intervals that evening; they explain unavailable execution intervals but do not establish the process termination cause. The worker previously depended on a foreground tool session, with no installed supervisor.

The existing Python worker now accepts a private operations directory. A common user/account `flock` spans idle and active ticks and rejects a second worker even if it supplies another state directory. Crash releases the OS lock; existing PostgreSQL leases, checkpoints and per-stock/model receipts continue to govern work. The loop catches runtime/provider failures, persists safe health information and retries calendar acquisition at most hourly. Daily calendar validation and resource/retention preflight precede scheduling. Pauses, sleep or clock gaps are labeled as such; they are not attributed to a specific cause without evidence. Complete exchange sessions plus the existing 30-minute delay remain mandatory. Catch-up never creates a forward recommendation.

`scripts/prepare_pilot_launchd.py` creates an **inactive** user LaunchAgent preview. It uses the existing virtual-environment interpreter, absolute paths, private credential-file references, a 60-second restart throttle and the existing Python worker. It does not install, bootstrap, enable or change power settings. The virtual-environment symlink is deliberately preserved; resolving it to the base interpreter loses dependency isolation. Normal diagnostics use a bounded private ring rather than unbounded launchd stdout.

**Persistent startup is not activated**, as explicitly required by the owner. No overnight unattended interval or launchd-supervised crash recovery is claimed. A user LaunchAgent requires a logged-in session and available PostgreSQL/Ollama/model drive. It does not wake a sleeping Mac or guarantee execution while logged out. The bounded foreground worker is stopped after acceptance; explicit owner authorization is still required to load the reviewed preview.

## Automatic calendar renewal

Actual permitted dated NSE calendar responses extended coverage from **October 30 to November 7**. Sixteen dated calls validated the retained catch-up window and future horizon, including declared closed dates. Refresh occurs daily, before coverage becomes short, or when no successful refresh exists. Any failed date prevents replacement of the planning calendar. The previous verified schedule is retained; stale/unknown coverage blocks source work. A persisted one-hour retry deadline survives restart. The owner grant is reloaded for acquisition, derivation and storage; no weekday/holiday guesses are substituted.

Successful observations are privately archived by content hash; session revisions use existing D3-03 append-only storage. Changing a planning-calendar hash can produce a new D3-04 occurrence hash. Before network/model work, the ingest handler checks for an already complete scan of the same scope, inputs and session cutoff and returns its immutable reference. Thus rollover cannot duplicate financial/model outputs. The latest due actual occurrence was processed this way; it reused the complete October 23 scan. This is genuine scheduler execution and deduplication, **not a newly acquired market session**. Next observed due time is **October 26 at 10:30 UTC / 16:00 IST**.

## Retention and resources

The current owner-local grant expires November 19 and permits a 30-day retention/review window; it does not permit metadata tombstones after required deletion. This operational limit is not represented as a new provider term. The original evidence and grant remain unchanged.

Preflight stops processing for revoked/expired/unknown grants, oldest observed revisions reaching the retention limit, database size at 2 GiB, free disk at or below 2 GiB, or operation-directory size at 64 MiB. It records CPU time, process peak RSS, database size and free disk. These are high-water stops, not filesystem quotas, CPU governors or complete Ollama memory accounting. Existing provider budgets and sequential inference limits remain in force; renewal reservations share the existing account request ledger. The additive migration permits only `pilot_request:` maintenance reservations without a job ID; other audit records retain their job requirement. Downgrade refuses to discard genuine maintenance reservations.

Automatic cleanup is restricted to the worker's own source-free diagnostic ring (four files, approximately 1 MiB total), with rotation recorded. It never traverses or deletes original documents, database rows, backups or unrelated files. Immutable evidence and permitted lineage survive. **Source-content deletion is not implemented or claimed:** deleting original data conflicts with this task's preservation instruction and would require an approved lineage/backup deletion workflow. Until resolved, expiry/age limits stop processing and remain an operations blocker. Current evidence is within the active grant; no real source content was due for cleanup in this run.

## Genuine acceptance, distinct from fixtures

| Check | Observed result |
|---|---|
| Existing baseline | Branch/PR match; Phase 10 exact-head CI success; unrelated main WIP preserved. |
| Automatic renewal | PASS: actual dated provider responses extend coverage to November 7; prior original revisions retained. |
| Scheduled cycle | PASS bounded scheduler execution: due real occurrence reuses its completed genuine scan; no new closed session existed during this Saturday check. |
| Termination/restart | PASS: task-owned process killed, OS lock released, same configuration restarted, saved calendar/scan retained. Manual restart test, not activated launchd recovery. |
| Duplicate worker | PASS: second process rejected with `pilot_worker_already_running` before source work. |
| Missed-session recovery | Existing genuine Phase 10 next-morning catch-up retained; current due-occurrence reuse succeeds. No fabricated clock or new missed-market-session event created. |
| Calendar rollover | PASS forward coverage extension and changed-calendar occurrence deduplication; actual expiry/next-session boundary not yet observed. |
| Missing token | PASS local denial before network. |
| Invalid token | LIMITATION: calendar and historical-price probes returned HTTP 200; upstream authentication rejection was not demonstrated. HTTP 401/403 denial remains covered by existing adapter fixtures. |
| Permission revocation | PASS real local control with a separate copied revoked grant; no provider request, original grant edit or original deletion. Not an actual account revocation. |
| Financial/model duplicates | PASS: 96 financial facts and 48 total retained RAG results unchanged, including earlier phases; no duplicate logical revision sequences. |
| History | PASS original revision/fact/RAG hash checks and grant hash unchanged. New calendar observations append only. |
| Dashboard | PASS genuine health, renewed calendar, next occurrence, current real scan and company research; stopped-worker heartbeat expiry checked separately. |
| Safety | Zero recommendations, references, outcomes, portfolios or ledger entries. Existing 36 abstentions and policy 2.0.0 unapproved. |

The two invalid-token probes are not silently counted as authentication failures. One calendar diagnostic made an additional sixteen calls; the historical-price diagnostic one. Total provider attempts in this milestone: 16 renewal +16 diagnostic calendar +1 diagnostic price =33. No new model inference was needed. Paid cost **₹0**. No email, downloads, cloud deployment, trades or new services.

Local validation: **687 backend/worker tests**, **171 PostgreSQL integration tests, zero skips**, migration lifecycle including atomic rollback, all three contract/evaluation/risk validators, eleven script tests and frontend production build passed. All **six browser workflows passed** against an isolated fictional stack, separately from genuine local acceptance. An initial fixture run used mismatched API/worker code versions and failed two jobs; aligning the isolated fixture versions resolved the rerun. A first integration attempt encountered retained disposable fixture jobs; resetting only the disposable test database resolved it. Exact delivered-commit CI is reported at delivery.

Remaining acceptance: authorized persistent activation; an actual overnight interval and following session; launchd-supervised recovery; actual sleep/wake execution and calendar-expiry boundary; upstream authentication-rejection evidence; approved source-content retention/deletion handling. Resource stops bound new processing but do not replace those checks. **Stop after this operational milestone; do not merge PR #12.**

References: [Apple user-agent lifecycle](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html), [Apple launchd plist specification](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5), [Upstox dated holiday interface](https://upstox.com/developer/api-documentation/get-market-holidays/). Implementation uses the existing dated market-timings adapter and unchanged source grants.
