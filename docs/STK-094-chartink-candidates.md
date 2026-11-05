# STK-094 — D3-03 ingestion, D3-04 automation, D3-09 research UI

## Delivered boundary

Chartink supplies discovery candidates. Existing Stock Discovery identity, source
rights, immutable market evidence, descriptive analysis, research, prediction,
risk, paper-trading and evaluation engines retain their roles. No new backtest,
indicator, model, ranking or execution engine was introduced.

The owner's corrected acceptance scope does **not** require Premium, an alert,
public hosting or a real provider delivery. Premium has not been purchased. The
receiver is **disabled by default** and is a separate entrypoint from the private
research API. No infrastructure purchase, public deployment, provider price call,
LLM execution, broker order or existing-service reconfiguration occurred.

Starting `origin/main` and branch HEAD were
`a4174fd66a48bdd24919c0c50d077d1721ec2959`. The local `main` ref was older
(`96f829a`). Work uses `feat/stk-094-chartink-candidate-intake`. The seven existing
untracked WIP paths, historical evaluation fixtures and original market database
remain unchanged.

## Provider evidence and uncertainty

Read on 6 November 2026:

- [Chartink webhook documentation](https://chartink.com/articles/alerts/webhook-support-for-alerts/)
  publishes a JSON POST sample with `stocks`, `trigger_prices`, `triggered_at`,
  `scan_name`, `scan_url`, `alert_name`, and `webhook_url`.
- [Alerts guide](https://chartink.com/articles/alerts/alerts-guide/) documents
  unique versus repeated matches.
- [Alerts FAQ](https://chartink.com/articles/alerts/alerts-faq/) describes notifications
  for newly matching stocks. An alert is not evidence of a full daily universe.
- The owner supplied [the intended scanner URL](https://chartink.com/screener/stock-discovery-eod-swing-candidates-v1).
  The page could not be retrieved by the documentation browser. Rules are
  owner-supplied, not independently certified from that page.

The documented sample's trigger time has **no date or offset**. No signature,
custom authorization header, retry schedule, delivery guarantee, payload-date
extension or complete-snapshot flag is assumed. The adapter validates the
published sample shape, but actual account-specific payloads, headers, timing,
redelivery and live behavior remain unobserved. A real sample is an activation
check, not a prerequisite for this implementation's local acceptance.

For time-only alerts, `event_at` is null; the Asia/Kolkata receipt date is an
**unverified session hint**. The original trigger text is retained. Cross-midnight
provider delay cannot be disambiguated. Identical alerts deduplicate within that
receipt day; identical next-day alerts remain distinct, because the provider's
sample cannot distinguish next-day matches from old redelivery. Same-day
repeated symbols never duplicate candidate research. No inferred timestamp is
eligible for historical predictions. Outbound retrieval preserves the receiver's
receipt clock rather than replacing it with Mac recovery time.

## Actual application flow and reuse

1. The optional receiver authenticates a secret URL and validates a pinned scanner
   manifest. A PostgreSQL transaction commits the sanitized immutable event before
   HTTP 202. `webhook_url` is dropped because it may contain the capability secret;
   `payload_hash` hashes canonical sanitized provider fields, not raw HTTP bytes.
2. The existing worker has an opt-in `--candidate-intake` mode. It optionally pulls
   a bounded HTTPS receiver feed, committing received events and its cursor
   together. Redirects are rejected and TLS verification remains enabled.
3. Events materialize scanner/version/session/symbol candidates and immutable
   event-to-candidate links. First/last receipt times are monotonic; historical
   classification is computed from session order, not arrival order. Scanner rule
   content is immutable within a version; credential/authorization renewal does
   not change scanner identity.
4. The worker resolves observed NSE EQ identity revisions through existing source
   grants and original-grant read fences. It expands the company reader's identity
   scope only; it does not expand any source permission. The existing `company()` /
   adjusted-research path supplies independently qualified indicators and blockers.
   No provider or LLM client is called. Missing request budgets are explicit.
5. Current descriptive results and exact revision dependencies persist in immutable
   research-run receipts. Current candidate status points to the latest result.
   Reads recheck grant fences; revocation removes cached identity/indicator content.
   Analysis time is separate from candidate session, and results are never frozen
   predictions or historical point-in-time analysis.
6. The STK-093 **Candidates** tab polls every 15 seconds and offers date selection,
   bounded pages, scanner/version, partial/full fixture labels, new/continuing
   observations, data/research state, evidence readiness, limitations, retry and
   watchlist actions. An unresolved symbol can be saved under a `CHARTINK:` private
   metadata key; this is **not** an invented instrument ID. Notes persist in the
   existing private watchlist store, independent of future scanner appearances.
   Verified identities open the existing company research page. CSV company names
   are labeled Chartink labels rather than verified identity evidence.

No candidate record publishes a recommendation or changes risk/admission gates.
Research priority is evidence readiness, not an actionable trading signal. Where
independent ranking is unavailable, it stays unavailable. Existing financial,
news/event and grounded research history remain available through the existing
company view subject to their original rights and qualification checks.

## Durable state and limits

Migration `0016` adds candidate events, statuses, sessions, matches, research runs,
pull cursors and small receiver control tables. Existing legacy schema consumers
explicitly accept additive schema 0016 as well as 0015; older schemas still fail
closed. No existing market, grant or evaluation record is rewritten.

- Maximum body/envelope 64 KiB, 500 symbols/event, 10-second body timeout.
- Receiver launcher: 20 concurrent connections, no access log, loopback binding.
- Shared authenticated intake/feed budget: 60 requests/minute; bounded invalid-auth
  throttling reuses `LoginLimiter`. Forwarded IPs are not trusted.
- Maximum 10,000 stored events, 50,000 immutable research runs; capacity exhaustion
  fails closed and requires operator action. No silent eviction of accepted events.
  A dedicated disk quota, monitoring and approved archival/retention policy are
  prerequisites for a public installation. Rejection history keeps at most 1,000
  hashes/codes, without attacker bodies.
- Feed: at most 25 events / 2 MiB per retrieval, 15-second network timeout.
- Worker: at most five events and five companies/tick; PostgreSQL advisory locks
  serialize materialization and research. SQL/lock timeouts bound worker work.
  A process crash rolls back its claim. Research retries at most three times,
  with 30-second backoff; failed/blocked jobs have an authenticated explicit retry.
  Failed event processing retains a code and has an authenticated replay action.
- Newest sessions are processed first. A CSV history import may leave older
  descriptive work pending; it never becomes a historical prediction experiment.

A partial result does not certify absence. `continuing_observed` means seen in
the previous **represented** session. `new_observed_vs_previous_results` means
absent from those earlier results, not necessarily absent from the full market
scanner. Only independently verified full snapshots could establish that stronger
claim. The model distinguishes complete snapshots, complete **synthetic fixture**
snapshots, partial results and missing delivery. Public webhooks and CSV recovery
cannot assert completeness. No delivery is never written as a verified zero day.
The `asof_candidates` reader filters immutable receipt clocks at T and explicitly
withholds universe completeness and evaluation eligibility.

## CSV recovery, not production ingestion

The supplied UTF-8/BOM files were read directly from Downloads after the owner
provided their exact paths. They are not committed or uploaded. The historical
file uses `Date` in `%d-%m-%Y`; the daily export has no date and requires explicit
`--session`. Column mapping and date format are configurable. Counts-only is the
CLI default; `--apply-recovery` explicitly stores unverified recovery events.

```sh
PYTHONPATH=shared .venv/bin/python scripts/import_candidate_recovery.py \
  '/path/Backtest Stock Discovery - EOD Swing Candidates v1.csv' \
  --date-format '%d-%m-%Y'

PYTHONPATH=shared .venv/bin/python scripts/import_candidate_recovery.py \
  '/path/Stock Discovery - EOD Swing Candidates v1.csv' \
  --session 2026-11-05 --apply-recovery
```

Set a private `CHARTINK_SCANNER_CONFIG` and, for an applied recovery, the target
`DATABASE_URL_FILE`. The adapter caps files at 10 MiB / 50,000 rows and records file
hash, column mapping and adapter version. Prices in the CSV do not become OHLCV.
Daily manual downloads/uploads are not the production workflow.

## Acceptance evidence

Actual CSV verification and application import:

| Measure | Observed |
|---|---:|
| Historical date-symbol matches (no duplicate rows) | 3,094 |
| Distinct stocks | 457 |
| Represented sessions | 160 |
| Period | 13 March–5 November 2026 |
| 4 November matches | 21 |
| 5 November matches | 35 |
| New versus 4 November represented results | 28 |
| Continuing observed matches | 7 |
| Daily export versus historical 5 November set | Exact match |

Historical file SHA-256:
`8b85f97c72d83db16131d8cf3f5acae93b8f490f6f6e8ff28dada8716cb65e38`.
Daily file SHA-256:
`8d91b5a56f775e3f227c198c3ed91a8a4eee4c51fc6f03b4a3efb309e427bbc8`.

A disposable PostgreSQL container on loopback port 54394 was created without
restarting or reconfiguring existing Colima/Docker/database services. The local
acceptance database is a private copy of the original 2,648 market revisions;
only the copy was migrated. Actual import is 3,094 candidates, including all 35 on
5 November. All 160 historical event replays reused accepted records. Newest-first
then older-session arrival preserves the 28/7 comparison. Browser acceptance uses
actual API responses and actual CSV rows: 35 rows, partial labels, unresolved
ANGELONE watchlist save, durable note after reload, and the existing INFY 44-bar
chart through 4 November.

All 35 actual 5 November candidates currently lack a usable identity in permitted
stored reference evidence. Their precise blocker is
`nse_identity_missing_or_ambiguous`; no ISINs or prices were guessed. Separately,
an authenticated **simulated** INFY webhook was durably acknowledged before the
worker ran, recovered from a new database connection, resolved against actual
stored reference evidence, and produced existing descriptive research on 44 bars.
Replay did not add a research run. This demonstrates the eligible path without
claiming any actual Chartink delivery or real trading performance.

Automated checks include parser/auth/default-disable/size/rate/capacity rejection,
partial alert semantics, synthetic 35/28/7 reconciliation, idempotency, reversed
arrival order, crash rollback, durable recovery, atomic remote cursor validation,
immutable receipts, grant revocation redaction, bounded retries, unresolved
watchlist persistence and T-cutoff exclusion. Existing prediction/evaluation and
research suites remain in place.

Local validation: 1,033 backend/worker tests at the broad regression checkpoint;
26 script tests; 586 PostgreSQL tests with zero skips plus full migration lifecycle;
subsequent focused candidate checks include the final additions. The clean
frontend build and 22 focused browser regressions passed. Exact final-commit CI
is reported on the PR. The original untracked `ImportPreview.tsx` syntax error
requires a clean tracked-source frontend copy for local builds; that WIP was not
edited. An early migration rehearsal used a stale disposable development schema;
a fresh disposable database passed the complete lifecycle. No current product
failure was hidden by changing a source or qualification gate.

Private local evidence is under `backups/stk094-acceptance/` (ignored, not in PR):
CSV counts/hashes, copied-database summary, simulated-event receipt, browser
summary/screenshots and isolated application logs. Public CI uses invented test
fixtures, never the private CSVs or original database.

## Later live activation steps — not performed by STK-094

1. Owner separately authorizes Premium purchase and the public receiver deployment
   within the already approved hosting choice. Confirm Chartink private storage/use
   rights and retention, budgets, backup/restore, disk quota and monitoring first.
2. Provision only a narrow HTTPS receiver/retrieval surface with durable PostgreSQL
   and migration 0016. Keep the research API private and the Mac outbound-only.
   Never tunnel/expose localhost. Use a dedicated least-privilege database role for
   receiver event/control tables; worker/API require their existing market rights
   plus candidate-table privileges. Apply no grants to existing runtime roles
   automatically.
3. Copy `deploy/chartink-scanner.example.json` to private configuration. Confirm
   exact live `scan_name`, `scan_url` slug and `alert_name`; pin rule version/content,
   approved rights reference and a finite authorization expiry. The example is
   deliberately expired. A changed rule definition needs a new version.
4. Generate independent strong webhook and pull secrets into private 0600 files,
   outside Git: `CHARTINK_WEBHOOK_SECRET_FILE` and `CHARTINK_PULL_SECRET_FILE`.
   Set `CHARTINK_SCANNER_CONFIG`. Keep `CHARTINK_RECEIVER_ENABLED` unset/false until
   activation is authorized. Use the provided no-access-log launcher; proxy,
   platform and error logs must also exclude capability URLs and request bodies.
5. After authorization, set `CHARTINK_RECEIVER_ENABLED=true` only for the receiver.
   Configure Chartink to POST to `https://RECEIVER/hooks/chartink/WEBHOOK_SECRET`.
   This is a bearer capability URL, **not** provider signature verification. Rotate
   by updating the secret file and alert URL; revoke immediately by disabling the
   receiver. Never put the separate pull secret in Chartink.
6. Receive and inspect an actual Premium delivery privately: confirm shape, content
   type, scanner identity, timestamp semantics and whether the endpoint is echoed.
   Check actual duplicate, failure and delay behavior with the provider. Until
   observed, do not claim live compatibility or assume Chartink retries lost
   deliveries. If behavior differs, update only the adapter and tests.
7. On the Mac, configure the same approved scanner version, private source view,
   local database and `CHARTINK_PULL_SECRET_FILE`, plus
   `CHARTINK_RECEIVER_URL=https://RECEIVER`. Run the existing worker using
   `PYTHONPATH=shared:worker .venv/bin/python -m worker.main --candidate-intake`.
   Retrieval polls automatically; no daily CSV is needed. Existing market-data
   acquisition remains disabled without a separately approved Upstox budget/grant.
8. Verify receiver-ack durability, Mac downtime recovery, private watchlist
   persistence, expiry/revocation, capacity alerts and backup restore. Record live
   validation separately. No-delivery monitoring must report unknown coverage,
   never an empty complete universe. Receiver-before-ack outages may require
   explicit exceptional recovery because provider retries are not documented here.

## Remaining qualification and next milestone

Public activation is outside the corrected STK-094 Definition of Done. Broader
NSE reference evidence, authorized/qualified OHLCV, original price/action/volume
basis, financial/news/AI qualification, point-in-time Nifty 500 membership,
historical availability and real prediction/paper qualification remain unfinished.
The original product remains prediction, historical experiments, forward paper
trading and outcome evaluation. Current final-candle research cannot simulate an
entry at an earlier same-day close.

The agreed overall planning baseline remains **46%**; area baselines remain
90/93/30/48/32/20 percent. No revised percentages are asserted. Functional evidence
above supports advisor reassessment; candidate software acceptance is not trading
performance, current-market readiness or training-data certification.

After owner review/merge/closure, recommend the smallest next package: one bounded
point-in-time historical candidate cohort with verified membership/evidence at T,
existing strategy versions producing frozen BUY/SELL/HOLD/NO TRADE decisions, and
post-T Upstox-price simulation through existing risk/evaluation engines. Preserve
separate reconstructed and prospective-paper clocks. Do not start it in STK-094.
