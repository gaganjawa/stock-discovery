# STK-094 / D3-05 Quant horizon policies + D3-09 UI — candidate research continuity

16 November 2026. Base main `0fe21361b590992dd9c96f346fb10ff1891566e7`
(PR #57 merged). This change is application code for owner review, not a deployment.

## Confirmed defect and fix

After two successful rolling candidate-price refreshes, Candidates selected the
latest complete ingestion stream. Opening the same company's research, or reading
it through the watchlist/workbench, instead selected all latest logical candle
revisions. The retained first day from the older window was mixed with the new
window. The existing coherent-batch validator correctly rejected that mixture,
leaving the company view unavailable despite completed candidate analysis.

The new PostgreSQL regression reproduced that exact mismatch before the fix:
Candidate `status=completed`; company `adjusted_research.status=UNAVAILABLE`.
The shared current company reader now selects the completed candidate refresh
receipt before the existing stream/page, listing, calendar, coverage and grant
checks. Candidate research reuses this same reader. The synthetic regression now
returns the same batch identity and 41-bar window in Candidates, company detail
and watchlist. The older revision remains stored; no series is stitched or deleted.

Historical cutoffs and publication-input reads retain their previous selection.
Receipts after the evaluation clock are excluded. Missing/wrong-scope streams and
partial refreshes that supersede earlier revisions fail closed; no fallback makes
an incomplete old batch rankable. Grant revocation hides evidence across all views.
Relative volume remains unavailable because adjusted volume basis is unqualified.
No BUY, trade levels, position sizing or global-ranking claim is introduced.

## Actual live evidence — read-only

- **16-Nov 06:42:22 UTC, VPS:** schema 0017; three events, all provider Tests;
  non-Test events **0**, feed high-water **3**.
- **16-Nov 06:41–06:49 UTC, Mac:** schema 0017; three provider-Test events;
  candidates **0**, refresh jobs **0**, total revisions **2,648**, consumer cursor
  **3**, provider quota requests in preceding 24h **0**. Consumer PID **8125** and
  refresh PID **8129** were running with one launch each.
- Latest stored INFY candle session is **4-Nov 2026**, not current. Its 506 candle
  revisions include retained versions; this is not 506 distinct sessions or a
  qualified coherent batch. The other 11 stored listings end at **23-Oct**.
  Volume fields exist, but that does not verify their raw/adjusted basis.
- No new provider request, candidate/event write, cursor change, production schema
  migration, webhook change or worker/UI restart. Genuine alert → current qualified
  prices → analysis → authenticated UI acceptance remains **pending**. No live UI
  acceptance is claimed; the browser evidence below uses only disposable fixtures.

The prior missing-13-Nov Upstox diagnostic remains historical evidence. This task
made no further diagnostic call and does not infer the provider's current response.

## Focused synthetic acceptance

**169 tests passed:** four new continuity/negative PostgreSQL cases and 165 affected
unit/integration regressions covering candidate review, refresh, adjusted research,
freshness, workbench and read fences. The four new cases passed in 11.20s including
actual Chromium acceptance; the affected suite passed in 58.23s. Existing dependency
deprecation warnings do not affect results.

The new isolated acceptance uses invented Upstox responses through the actual
adapter, immutable ingestion, durable jobs and research. It verifies authenticated
API access, two complete rolling refreshes, shared batch identity, retained revisions,
no acquisition during reads, old-clock/historical/publication behavior, partial or
invalid batch rejection, grant revocation and watchlist review metadata.

Actual browser: sign in → Candidates → price-refresh completion → page-scoped rank
→ Open INFY research → 41-bar current window → save to watchlist → readable EMA
comparison → mark observations reviewed. The synthetic calendar and price values
are test fixtures, not genuine Chartink acceptance or market evidence.

Existing webhook/provider-Test and refresh deduplication/recovery implementations
are reused. No new migration, service, acquisition architecture, infrastructure
work or CI workflow change. Owner monitors exact-head PR CI; do not wait or merge.

## Next product step

After review/merge, expose per-candidate refresh eligibility and reasons for symbols
outside the configured acquisition universe (STK-014), using the existing config and
job contracts. Current live scope remains INFY; no scope expansion is assumed.
Observe the next ordinary eligible alert independently. Qualified volume/basis and
remaining strategy inputs are still needed for volume-confirmed swing signals.
