# STK-014 / D3-03 + D3-04 — bounded candidate price refresh

After STK-094 PR #52, an opt-in worker now connects recent stored candidates to
existing Upstox price/calendar acquisition and durable re-analysis. No migration,
webhook, consumer launcher, credential, production database or live service changes.

## Execution

Run `python -m worker.candidate_prices --config /private/refresh.json --once`
with the existing acquisition worker's `DATABASE_URL_FILE` and repository Python
paths. Omit `--once` for a 60-second cycle. This command does not install a service.
It needs the existing acquisition/scheduler permissions; the restricted webhook
receiver and candidate-only consumer are not given acquisition privileges.

Configuration uses the existing `MarketConfig` under `market`, plus:

```json
{
  "market": {
    "account_ref": "existing-account-reference",
    "grant_file": "/private/existing-grants.json",
    "token_file": "/private/existing-upstox-token",
    "symbols": ["INFY"],
    "lookback_days": 40,
    "retention_days": 365
  },
  "scanner_keys": ["existing-approved-scanner-key"],
  "candidate_days": 3,
  "max_symbols": 20
}
```

These are configuration examples, not actual credentials or permission evidence.
Set the explicit symbol allowlist to the approved acquisition universe. Each cycle
selects only already observed candidates from the configured scanners and the last
1–7 calendar days, intersects that list with `market.symbols` (at most 100), enqueues
at most `max_symbols` new jobs and executes one. Symbols outside the configured
universe are counted explicitly in `selection.outside_configured_universe`.
Existing identity mapping validates NSE EQ/ISIN/provider keys; unknown or ambiguous
mappings remain retryable readiness failures. No provider Test receipt can create
a candidate or enter this queue. Future-received candidates are excluded.

## Durability and bounds

Jobs use a versioned namespace in the existing D3-04 occurrence/job/audit/outbox
tables, with no schema changes. Duplicate deliveries and multiple scanners matching
the same symbol share one refresh job per configuration/day/closed-session target.
A morning success cannot suppress a refresh after a later verified session closes.
Missed prior-day work is recorded as missed; a later refresh has its actual clock.

The worker reuses the native account singleton and the `REAL-001:<account>` database
session lock. Claims have 15-minute fenced leases and at most three attempts.
Current candidates are queued for the existing stored research worker in the same
transaction as successful job completion. A crash before that commit resets neither
research nor job completion; after lease expiry a restarted worker can recover.
Immutable ingestion pages/revisions remain replay-safe. Historical candidates and
prior research receipts are not rewritten; fresh analysis retains its current clock.

The existing Upstox adapter performs acquisition/derive/store grant checks,
instrument mapping, bounded responses and per-client rate enforcement. The new
worker uses the existing durable account ledger (`pilot_request:`): fewer than 90
requests/minute, 800/30 minutes, 60/job attempt, spaced by at least 0.7 seconds.
Requests are charged before HTTP and survive interruption. The limits also account
for existing pilot reservations. No broker, model or financial-statement calls.

The existing dated calendar ingester is shared through an injectable adapter;
its default behavior is unchanged. A fully validated calendar refresh is reused
within the same configuration/day. Lookback is 40–44 days, within that ingester's
52-date bound. Prices are refreshed as a full coherent configured window, not
patched with invented bars. Missing latest sessions, partial responses or fewer
than 30 bars do not trigger re-analysis. Partial coverage is retained and retried;
third-attempt partial coverage remains explicitly partial. HTTP/authentication,
quota, permission and mapping failures receive sanitized retry/block states.

## Usable product path and remaining step

Observed candidate → configured Upstox universe → verified instrument mapping →
dated calendar and complete price batch → durable pending research → existing
candidate worker → STK-094 ranked price review. The real-browser test traverses
this complete software path with invented provider responses and actual PostgreSQL,
API, authentication and UI. No browser API responses are mocked.

This PR does not activate acquisition in production. After review, the next operational
step is to configure and activate this worker alongside the existing stored-research
consumer for the chosen acquisition universe. Existing adjusted-price volume and
full swing qualification limits remain unchanged; refreshed descriptive price checks
do not authorize BUY, publication or trading. Genuine ordinary-alert acceptance
remains separate from these fictional test cases.

## Validation

- 1,177 unit tests passed, including nine new configuration/error-classification cases.
- 47 affected PostgreSQL/API tests passed, including 12 new refresh cases: duplicates,
  cross-scanner coalescing, stale/partial response recovery, exhausted retries, request
  accounting, interrupted HTTP, interruption before completion commit, current-session
  refresh, missed-day recovery, acquisition scope/mapping and observation-time bounds.
- Real Chromium acceptance passed: refreshed 41-bar fixture → completed stored
  analysis → authenticated candidate API → ranked Candidates UI; volume unavailable.
- Existing base migrations were applied only to the task-owned disposable test DB.
  The first broader scheduler run found that test DB uninitialized; rerunning after
  initialization passed. No production migration or actual provider request occurred.
