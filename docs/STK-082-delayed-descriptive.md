# STK-082 — D3-13 one-session delayed descriptive research

4 November 2026. Scoped release improvement, not D3-13 completion or investment readiness.

## Explicit policy

The existing private `ViewConfig` accepts:

```json
{"descriptive_freshness_policy": "one_trailing_session_v1"}
```

Add this field to the existing view configuration to opt in. Omission selects
`strict`, preserving the requirement that the latest completed session is present.
This PR does not edit private runtime configuration, grants, retention, stored
prices, pages or historical evaluation fixtures. Reverting the setting to `strict`
restores strict descriptive freshness without any data migration.

The exception applies only to descriptive observed history: exactly one trailing
verified completed session is absent, every earlier session in the selected window
matches its actual opening/closing boundaries, at least 30 bars exist, and all
bars reconstruct one complete, hash-verified ingestion batch. Interior gaps,
duplicates, competing calendar boundaries, unknown sessions, incomplete pages,
missing provenance and multiple adjustment vintages still block. Existing guarded
reads validate current and original authorization, retention, dependencies and
revocation fences. Historical-cutoff requests remain unsupported; acquisition and
availability clocks are unchanged.

`adjusted_research.freshness` and `market_readiness.descriptive_freshness` expose
policy, latest available price session, latest verified closed session, trailing
missing-session count, status and reason. An accepted delay is
`delayed_one_session`, never `current`; `latest_session_present` stays false.
The coverage API also exposes descriptive freshness without changing its
`refresh.current` calculation. The company UI places the dated delay notice above
the historical chart and explicitly excludes current-day intraday candles.

SMA20, EMA10, EMA30, ATR14, breakout20 and support20 remain descriptive. Relative
volume remains unavailable. Publication, actionable recommendations, execution
backtests, historical point-in-time qualification and paper admission stay blocked.
No historical/intraday combination or new adjustment-consistency claim is made.

## Actual INFY read verification

Read-only guarded evaluation of `stk_real001_private`, schema `0015`, on 4 November:
strict policy returned `UNAVAILABLE`; the in-memory opt-in returned
`AVAILABLE_DESCRIPTIVE_ONLY` with **43 chart points through 3 November**, latest
closed session **4 November**, and **one trailing missing session**. Stored page
hashes reconstruct one observation batch. INFY revision/payload fingerprints
matched before and after; no original evidence changed. Six price indicators are
available; relative volume is null. Private verification metadata and a rendered
chart screenshot remain outside Git; no provider prices or private grants are
committed. No provider request or AI inference was performed.

This validates the existing batch under this policy at that evaluation time. It
is not permanent freshness approval: a second subsequently completed missing
session blocks the chart again. Runtime policy activation is a separate config
choice; existing private configuration was left unchanged.

## Validation

- 87 focused domain/API tests pass, including zero/one/two-session lag, interior
  gaps with more than 30 bars, missing/incomplete receipts, mixed vintages,
  malformed boundaries, insufficient warmup, absent policy, serialization
  contradictions and immutable non-actionable flags.
- 978 backend/worker regression tests pass (unrelated untracked import-preview
  WIP excluded).
- 65 relevant PostgreSQL tests pass on disposable migrated databases, including
  11 new delayed-read/authorization cases. Missing, expired, revoked and fenced
  grants and excessive requested retention deny reads; revision payloads remain
  unchanged. No migration was applied to the original database.
- Tracked frontend plus STK-082 builds in an isolated temporary tree. Building
  the mixed working directory encounters the pre-existing untracked
  `frontend/src/ImportPreview.tsx` syntax error; that WIP is preserved.
- 17 desktop/mobile Playwright checks pass (16 committed regressions and one
  private actual-data rendering check). They cover delayed/current/unavailable display,
  chart/indicator removal on denial, existing recovery/coverage UI, and a private
  actual-INFY rendering check. Browser launch uses normal interactive approval
  because macOS sandbox restrictions prevent Chromium startup.

## Remaining limits

Level 1: opt-in runtime configuration is not changed by this PR. The dataset is
explicitly delayed, calendar completeness is not attested merely by session rows,
and other stocks/batches need their own rights, coverage and provenance checks.
No acquisition or automatic refresh has been enabled.

M1 remains blocked on original raw prices or a qualified point-in-time adjustment
path, verified volume and complete corporate-action coverage, complete original
filings/material events with authoritative availability, applicable retention/use
rights, financial reconciliation/valuation fields and instrument eligibility/risk.
Research policy and semantic financial qualification remain unapproved. See
[the M1 acceptance checkpoint](AI_RESEARCH_DATA_ACCEPTANCE.md). This descriptive
exception closes none of those source or investment-qualification gates.

## Final review — response compatibility and calendar wording

The notice says “Latest verified closed session in stored calendar” because the
stored session list does not attest authoritative exchange-calendar completeness.
Date formatting, the one-session warning and descriptive restrictions are unchanged.

Repository call-site inspection found no application deserialization of persisted
`AdjustedResearch` payloads. The only production constructor is `describe()` in
`shared/stock_discovery_analysis/adjusted_research.py`, which supplies `freshness`
for every newly generated result. `real_views._company()` calls it on each read
and serializes the result with `model_dump(mode="json")`. The API status/coverage
readers in `backend/app/real_research.py` consume those newly generated dictionaries.
All `AdjustedResearch.model_validate` / `model_validate_json` calls occur in
`backend/tests/test_adjusted_research.py` and `test_descriptive_freshness.py`,
where they validate new responses or intentionally contradictory test payloads.

Persistence consumers were also inspected: `worker/worker/real_pilot.py` saves
selected readiness/indicator fields in scan receipts, not an `AdjustedResearch`
object; publication code in `real_publication.py` rebuilds company inputs and
persists recommendation artifacts under separate contracts. Neither path reads
old adjusted response dictionaries through this model. Repository searches for
`AdjustedResearch`, `adjusted_research` and `adjusted-research-v1` found no other
persisted model consumer. This conclusion is scoped to current repository code,
not hypothetical external clients.

The model is therefore generated-response-only in current application use. Keep
`adjusted-research-v1`, required `freshness`, and every invariant unchanged; no
compatibility default, new version or database migration is needed.
