# STK-095 — D3-03/04/09 enriched discovery integration

Status: implementation in progress; PostgreSQL and real-browser acceptance blocked
on 11 November 2026 by missing Colima Docker socket. Inspection outside the sandbox
failed identically. No service was restarted. No database identity/schema could be
verified; no migration success is claimed. The original private database was not
accessed. Local validation logs are in ignored `backups/stk095-acceptance/`.

## Contract boundary

Basic documented Chartink payloads retain the STK-094 contract. The isolated
`synthetic_enrichment_v1` extension is accepted only for a synthetic scanner.
It is an invented test transport, not a confirmed production webhook format.
CSV recovery recognizes the supplied result-column names, rejects conflicting
Symbol/symbol values and conflicting duplicate rows, and retains optional values,
field states and aliases in immutable event envelopes. Unknown ATR period remains
unverified and cannot supply ATR14 metrics. CSV is exceptional recovery, not the
production workflow. Source grants and independent market research remain separate.

## Deployment proposal — approval required, nothing activated

Retain the approved Hetzner CX23 / Linux / Compose / restic / B2 selection.
Use the existing host if already provisioned with sufficient capacity (incremental
compute cost zero); otherwise provision one approved CX23. Do not expose the
research API or PostgreSQL. Only HTTPS receiver and authenticated feed routes are
public. The Mac makes outbound HTTPS pulls using the existing worker cursor.

Planning allowance: **EUR 8/month for compute and public networking**, plus taxes,
domain renewal and backup storage. This is a budget estimate, not a verified quote:
Hetzner's indexed June 2026 price adjustment lists EUR 5.49/month for CX23, but its
page returned 404 on direct retrieval on 11 November. Verify stock, region, IPv4,
tax and checkout price before owner approval; do not silently substitute a host.
Source: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
B2 currently lists USD 6.95/TB/month and first 10 GB free. A conservative 20 GB
backup allowance is USD 0.14/month before free allowance, tax and excess egress.
Source checked 11 November: https://www.backblaze.com/cloud-storage/pricing

Persist the inbox in PostgreSQL on a dedicated durable volume. Apply schema 0016
only to the approved receiver database. Restrict database roles to required
candidate tables; do not copy private research evidence to the receiver. Use TLS
with automatic certificate renewal and a firewall. Store independent webhook and
pull secrets in mode-0600 files; keep capability URLs, bodies and authorization
headers out of proxy/application/error logs. Receiver remains disabled by default.

Back up PostgreSQL using consistent dumps encrypted with restic to a restricted
B2 bucket; retain the encryption key separately and rehearse restoration before
activation. Monitor disk space, inbox capacity, failed events, oldest pending event,
Mac cursor lag, TLS expiry and backup age. Alert on missing delivery as unknown
coverage. Do not assume Chartink retries failed deliveries. The receiver must
acknowledge only after durable commit; capacity errors require operator action.

## Owner activation procedure after software acceptance and hosting approval

1. Provision the approved narrow receiver, database, DNS and TLS; rehearse backup
   restore and outbound recovery. Pin the actual scanner identity/rule version and
   finite rights approval. Configure separate secret files and local pull settings.
2. Open the existing Chartink scanner and Modify Alert. Preserve conditions,
   universe, frequency and existing email notifications. Enable webhook delivery.
3. Configure **Payload Columns separately from Result Columns**. Select stock name,
   symbol, close, percentage change, volume, marketcapname, sector, industry,
   EMA10, ema30, sma50, rsi14, AVG_VOLUME20 and PREV20_HIGH. Select avg_true_range
   only after recording its configured period. Verify available field naming/type
   controls in the actual account; no enriched JSON shape is assumed here.
4. After authorized receiver activation, enter the private capability URL
   `https://<receiver>/hooks/chartink/<webhook-secret>` and save. Never share it in
   diagnostics or put the pull secret into Chartink.
5. Observe the first delivery privately. Compare sanitized structure, field types,
   column alignment, trigger-time/date semantics and partial-match behavior with
   the adapter. Unknown enriched formats must fail safely; update only the versioned
   adapter after examining real evidence. Do not claim live support from fixtures.
6. Verify durable acknowledgement, stored payload and receipt clock, outbound Mac
   ingestion, deduplication, candidate values and source labels in the dashboard.
   Confirm missing indicators stay missing and independent research blockers remain.

Chartink references:
https://chartink.com/articles/alerts/webhook-support-for-alerts/
https://chartink.com/articles/alerts/alerts-guide/

## Remaining delivery gates

Complete disposable database identity/schema verification, full migration and
integration suite, actual 35-row recovery and 28/7 reconciliation, real browser
checks including persisted watchlist and INFY research, full diff review, then
commit/push/PR and CI for the exact final SHA. No acceptance is inferred from the
prior interrupted migration run. Overall accepted planning baseline stays 49%.

## Resumed acceptance — 11 November 2026

Supersedes the earlier Docker-access blocker above. The existing STK-095 database
was verified as `stk013_test`, PostgreSQL 16.15, schema 0016. Full validator exit
status was 0: **589 integration tests passed, zero skipped**, with upgrade, repeat
upgrade, downgrade, re-upgrade and intentional-failure rollback passing. The nine
focused candidate PostgreSQL tests also passed, including enriched CSV reconnect,
replay and API output. Logs are retained under `backups/stk095-acceptance/`.

The stopped STK-094 acceptance volume was mounted read-only and copied into a new
`stk095-browser-copy` volume. Only the new `stk095-browser-db` container was started
for browser work. Its acceptance database has schema 0016, 2,648 market revisions,
35 candidates on November 5 and 21 on November 4. Original/private databases and
preserved evidence were not changed.

Real Playwright browser checks against the application and copied PostgreSQL
passed the original 35 rows, 28 new / seven continuing observations, partial/CSV
labels, and watchlist note persistence after reload. A separately labeled synthetic
row passed indicator display, relative volume 2, RSI14 60, missing ATR14, synthetic
label and stored AVG_VOLUME20 provenance checks. Browser evidence is private and
ignored. The original CSV files remain inaccessible under macOS permissions.

The old INFY 44-candle chart assertion failed. The actual backend reports
`recent_sessions_not_ingested` and `session_coverage_unavailable`, with an empty
price series and `descriptive_validation_failed`. No permissions, freshness gates
or provider acquisition were changed to bypass this result. Positive INFY chart
regression and final delivery remain pending; no PR/CI completion is claimed.

## INFY verdict — identical baseline behavior

Baseline `cd3e1a6` and STK-095 were evaluated against the same isolated database,
configuration, grants and two fixed test clocks. Their summarized outputs compare
byte-for-byte equal (`infy-baseline.json` and `infy-current-code.json` in private
acceptance evidence). At 2026-11-06T00:00:00Z both return 44 candles with
`AVAILABLE_DESCRIPTIVE_ONLY`, one trailing missing session and latest price session
November 4. At 2026-11-11T00:00:00Z both return zero candles, `UNAVAILABLE`, four
trailing missing sessions, `recent_sessions_not_ingested` and
`session_coverage_unavailable`. The previous chart failure was an outdated test
expectation, not a regression. Production clocks, grants and freshness remain
unchanged. A separate isolated fixed-clock server reproduced the original browser
acceptance successfully: 35 candidates, 28/7 comparison, persistent watchlist and
INFY 44-candle chart. Current-date enrichment browser acceptance also passed.

Local totals: 1,047 unit tests, 26 script tests, 589 integration tests (zero skips),
nine focused PostgreSQL candidate tests, frontend build and the real-browser
scenarios above. Tests use no provider/model calls. Exact final-commit CI must be
checked on the PR before owner review/merge. Public activation remains pending.
