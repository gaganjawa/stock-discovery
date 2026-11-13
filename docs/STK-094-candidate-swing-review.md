# STK-094 / D3-03 + D3-05 + D3-09 — stored candidate swing review

The Candidates workbench now connects materialized Chartink candidates to a fresh
stored-price review. `GET /v1/real-research/candidates/swing-review` resolves each
symbol through the existing stored NSE identity adapter, reuses `real_views.company`
and verified Upstox adjusted-history indicators, and returns explicit price checks.
No webhook, consumer, schema, acquisition configuration or production state changes.

## First integration slice

Candidate → verified stored NSE EQ identity → permitted observed price batch and
calendar → existing EMA10/EMA30 and prior 20-session high → ranked UI price review.
The existing research adapter also supplies financial/event/history availability
and publication limitations. Cached worker research is not used to determine rank:
each request rechecks current data, grants and fences at one evaluation clock.

Enable **Review stored swing prices** in Candidates. At most 20 candidates from the
selected session/page are reviewed per request; the same symbol/ID pagination is
retained. Ranking is explicitly **within that page**, never across the complete
session, scanner universe or watchlist. Current eligible rows sort by the count of
two conditions: EMA10 > EMA30, close > prior 20-session high. Ties share a dense rank;
symbol and candidate ID provide deterministic display order. These are descriptive
checks from the existing EMA/breakout baseline, not performance estimates.

Unresolved identity, missing/insufficient history, stale data and delayed sessions
are unranked with reasons. Existing provenance, calendar, warmup and adjusted-price
validation remain authoritative. The one-session descriptive allowance does not
silently become current ranking eligibility. No Chartink snapshot value supplies
an independent price indicator. Relative volume remains null because the current
Upstox adjusted-history contract does not verify its volume basis. Even two met
price checks cannot produce a full swing strategy signal, BUY, levels or sizing.

The route is authenticated, no-store and bounded to 20 rows; it performs no provider
or model calls and no candidate research, cursor or price writes. Existing inbox,
retry and watchlist flows remain available. Inputs may be historical candidates,
but analysis is explicitly current; no backdated prediction is created.

## Verified evidence and next slice

13 November 2026, 16:19:28 UTC: read-only production observation found three durable
provider Tests, zero genuine candidate deliveries, zero candidate sessions/rows,
Mac cursor 3 matching remote high-water 3, and healthy receiver/consumer. No new
rejection appeared. Provider-Test acceptance remains passed. No alert was triggered
for this implementation. Genuine-alert identity, symbol count, materialization and
API/UI acceptance await the next ordinary provider alert; this PR does not claim
that event occurred or install a future monitoring service.

After owner review/merge, the next implementation slice is a bounded candidate
price-refresh queue: resolve candidate symbols to stored Upstox instrument keys,
reuse `worker.real_market.ingest_prices` and calendar ingestion for an authorized
coherent history batch, then rerun this review. Missing identity and acquisition
budget/configuration must be explicit job states. No broad source-rights review is
required by this slice; existing use-specific grants remain enforced. Production
activation and provider calls are not part of this PR. Complete swing picks still
need technically qualified volume and the existing swing qualification/policy
inputs; an owner assertion cannot substitute for missing market data semantics.

## Validation

- 1,168 backend/worker unit tests passed (including eight new review tests).
- 12 disposable PostgreSQL/API cases passed: three new stored candidate/price
  review cases plus nine existing intake/replay/research regressions.
- Two Playwright candidate UI cases passed, including review toggle, rank,
  unavailable volume and stale-data display. Browser API responses are fixtures;
  actual stored-price computation and route behavior are covered by PostgreSQL tests.
- Frontend TypeScript/production build and diff whitespace checks passed.

All test market values are invented. Tests use a separate disposable PostgreSQL
container and isolated UI port, never production databases or the active UI.
