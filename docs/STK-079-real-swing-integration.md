# STK-079 — Single-instrument research-only swing integration

Base: `8d7f5bb` (main after PRs #17 and #18). D3-13/STK-079 limited vertical
slice; no claim that the full three-horizon release or REAL-001 operations pass.

## Smallest integration path and reused tickets

STK-014 supplies `SwingInputs`/`qualify`; STK-004–007 rights/data contracts and
D3-03/06 supply immutable revisions, original grants and document storage.
STK-074 supplies the transaction-scoped read fence. STK-028/D3-05 already provides
SMA, EMA, ATR, prior-window breakout/support and the EMA/volume/breakout baseline.
STK-054 research presentation and STK-058 discovery infrastructure are reused,
not reimplemented or expanded into a scanner. STK-003 sizing bounds risk, cash
and instrument/sector/gross exposure. STK-079 adapts these pieces for one listing.

The existing synthetic strategy now shares its condition and price geometry
helpers with this path; its one-paise synthetic behavior is regression tested.
Real research instead requires the actual stored tick grid and lot size.
`quant_policies.assess` and `real_swing_instrument_settings_unavailable` are
unchanged. No unapproved real publication policy is activated.

## Trust and evidence boundary

`ViewConfig.swing` optionally pins one listing and one **already stored** coverage
review document by immutable revision ID and content hash. The configuration also
requires an explicit operator review/approval reference, policy version, price-age
limit and complete hypothetical risk scenario. The API cannot supply or override
any of these. Protect the server configuration as strictly as source grant files.
Changing the pin is an operator review decision, not automatic source discovery.

The review is a typed `swing-coverage-1` JSON body in a `text/plain` evidence
document with the explicit immutable `coverage_review` category. It must be
ingested through normal authorized D3-06 ingestion;
this service does not insert it. Ordinary documents and free-text claims cannot
become authoritative simply by appearing in retrieval. Only the explicitly pinned
review is parsed. Its publisher/acquisition identity is resolved from storage and
its original/current grants must authorize each attested scope, not just filings.

`CoverageReview` contains:

- Full immutable revision hashes for the bounded single-listing input set, including
  instruments, eligible membership, candles, sessions, actions and filings/news.
- Separate complete/from/through/fresh-until evidence for prices, calendar,
  corporate actions, instrument metadata, filings and material events.
- Provider-policy review references and retention/deletion support decisions keyed
  to the entire original grant hash; no renewal or different account substitution.
- Verified volume basis, action-free window and instrument risk prohibition state.

These are external evidence-backed attestations, **not inferred truths**. The
operator must verify them and the exact document before pinning it. No real
review, provider permission, default risk policy or approved settings ship here.
Unknown retention/deletion capability must stay unknown/false. This mechanism
does not implement deletion or make an unsupported obligation compliant.

All market values, tick/lot settings, status and membership eligibility come from
the pinned database rows. Original grant, account, upstream version, stored ID
and acquisition time are resolved from immutable tables. Current eligible revisions
are compared with the review: a newly observed correction, action, filing, event
or candle missing from the review requires a refresh. No caller-supplied candle or
grant assertions enter `SwingInputs`. Bound: 600 pinned input revisions.

## Execution and API

Use the existing authenticated route:

`GET /v1/real-research/companies/{listing}?analysis=swing&cutoff_at=<UTC timestamp>`

The default `analysis=company` retains the prior response. An omitted cutoff uses
the current clock; coverage must extend through that cutoff. For a reviewed closed
session use its exact supported analysis cutoff. The result also must pass current
rights and freshness checks; an old cutoff is not an expiry bypass.

Flow: load review and market rows inside `guarded_read` → close original grant and
instrument dependencies → acquire all fence locks → independently validate original
acquisition/current use → build `SwingInputs` → `qualify` → indicators/strategy →
tick-grid levels → existing Decimal sizing → floor quantity to whole lots → recheck
rights/freshness → return. Locks survive until the protected transaction finishes.

No server result cache is introduced. Every repeated request re-reads and checks
all dependencies. Swing responses use `Cache-Control: no-store`. On a denied read,
return only `INSUFFICIENT_EVIDENCE` with a sanitized reason and no revision IDs,
values, grants or paths. Missing configuration is explicit insufficiency; the
existing missing overall real-source configuration/authentication responses remain.

Results carry analysis cutoff, freshness, revisions, STK-014 diagnostics, input hash,
strategy/policy versions and deterministic analysis ID. BUY is a technical research
classification only. WAIT means unmet technical conditions or zero hypothetical
capacity. Missing inputs mean INSUFFICIENT_EVIDENCE. Levels/sizing are null on
unqualified inputs and on technical WAIT; zero-capacity WAIT may expose qualified
geometry with zero hypothetical quantity. Actual account balances are never read.

Raw prices only: provider-adjusted bars and legacy Upstox `raw` labels remain
unqualified. No price/volume conversion, inferred calendar sessions, default
tick/lot, corporate-action adjustment or synthetic fallback. Windows containing
known corporate actions fail closed. A coverage review cannot replace the
required stored filing document. Stored default, restatement, auditor-change or
regulatory claims block research readiness even when a review asserts risk is
clear; unverified adverse claims require resolution too.

All coverage-review documents, including nested older reviews, are excluded from
the substantive-filing requirement but remain authorized provenance dependencies.
Only stored annual reports, quarterly reports or announcements with filing type,
issuer-primary authority and an explicitly trusted primary source satisfy that
requirement. Unclassified/ambiguous documents fail closed. No title, filename or
free-text classification is used. The added category is backward-compatible with
existing document payloads; legacy secondary review documents cannot become filings.

Instrument settings use the latest observed and effective instrument revision at
the cutoff; equal-effective corrections use the source's immutable sequence.
Independent provider identities or conflicting equally eligible revisions remain
ambiguous. `InstrumentData` supports `effective_at`, not effective-to intervals;
none are invented. Future-effective records cannot supply current settings. All
historical and future pinned revisions retain original-grant/fence checks, including
the historical identity parents of prices and documents.

Real BUY geometry must be positive, finite, tick-aligned and satisfy
`stop < entry <= entry_cap < target`. Invalid geometry returns
`INSUFFICIENT_EVIDENCE` with no levels or hypothetical position. This slice rejects
an invalid cap instead of silently changing frozen synthetic formulas or clipping
it. Valid sizing still uses the permitted cap, adverse stop slippage, entry/exit
fees and whole-lot rounding; planned loss and cash are recomputed at that quantity.

## Safety and remaining dependencies

Every result has `research_only=true`, `actionable=false`,
`publication_authorized=false`, `paper_admission_authorized=false`, and
`trading_authorized=false`. There are no recommendation, portfolio, budget, queue,
model or provider writes/calls. BUY levels are hypothetical geometry, not order
instructions, execution authorization or a profitability claim.

Before a genuine NSE result: establish source rights and supported retention/
deletion obligations; acquire verified raw prices/volume and complete calendars,
action/filing/event coverage; verify current metadata/eligibility/risk restrictions;
ingest and independently approve the exact coverage review; configure explicit
hypothetical risk assumptions. Upstox access alone supplies none of these approvals.

General reader/cache, backup/restore/deletion enforcement, new providers, full
signal UI, full-universe discovery, prospective publication and paper/live trading
remain outside this slice. The reviewed configuration is a trusted operator input;
this is not a provider-policy verifier or automated review authoring framework.

## Validation

Tests use invented `NSE:TEST` observed-mode contract fixtures in disposable
PostgreSQL. They are not actual NSE observations or provider acceptance evidence.

Initial implementation validation (before the three P2 corrections), 31 October 2026:

- Full backend/worker suite excluding integration: **687 passed**.
- Full PostgreSQL suite and migration validator: **397 passed, zero skipped**;
  upgrade/repeat/downgrade/re-upgrade and atomic-failure rollback passed.
- Final adverse-event contradiction guard added one additional database case.
  Final affected PostgreSQL rerun: **87 passed**, including all **40 STK-079**
  cases plus read-fence/evidence-ingestion regressions. This overlaps the full
  run; do not add these totals. The full suite preceded that narrow correction.
- New arithmetic/contract tests: **15 passed** (included in the full unit run).
- Final focused qualification, strategy, rights, API and security rerun:
  **204 passed**; these overlap the full unit run.
- Three existing contract validators and **13 script tests passed**.
- Frontend production build passed; no UI source changes or browser run required.
- Syntax/whitespace checks cover tracked and newly added files. No frozen
  evaluation artifacts regenerated; no actual database modified.

Commands: `pytest backend/tests worker/tests --ignore=backend/tests/integration -q`;
`scripts/validate_migrations.py` against the task-owned disposable database;
`pytest backend/tests/integration/test_swing_research.py backend/tests/integration/test_read_fences.py backend/tests/integration/test_evidence_ingestion.py -q`;
the three `scripts/validate_*_examples.py` validators;
`unittest discover -s scripts -p 'test_*.py'`; `npm run build`.

The first fixture runs exposed mismatched document attribution and noncanonical
Decimal strings; fixtures were corrected without relaxing ingestion contracts.
Colima stopped during the interrupted session; the existing profile and only the
task-owned test container were restarted. Known Starlette/AnyIO and fork warnings
remain non-blocking. No live provider, model, broker or production credentials used.

Abbreviated **actual TestClient API response from synthetic fixtures only**:

```json
{
  "instrument_id": "NSE:TEST",
  "analysis_cutoff_at": "2026-10-31T07:52:44Z",
  "status": "BUY",
  "reasons": ["technical_conditions_met"],
  "research_only": true,
  "actionable": false,
  "levels": {"entry": "133.05", "stop": "126.75", "target": "145.65", "entry_cap": "134.40"},
  "hypothetical_sizing": {
    "quantity": 30, "planned_loss": "239.00", "entry_cash": "4036.00",
    "stop_fill_assumption": "126.70", "scenario_only": true
  }
}
```

Independent review remains required before commit. P3 follow-up: bounded but
per-revision dependency/rights queries are not yet a latency/capacity acceptance.
No genuine instrument is qualified by these tests or by this sample.

## P2 correction validation — 31 October 2026

The three new PostgreSQL reproductions failed before correction: nested reviews
without a filing returned BUY; the low-volatility case allowed a cap of 1011.75
above its 1002.40 target; historical/current identity revisions prevented BUY.
The same three tests passed after correction. Formula identity is now
`stored-swing-research-2`; frozen strategy formulas remain unchanged.

- Expanded STK-079 PostgreSQL/API suite: **56 passed**. Includes substantive
  document classification and its own grant restriction, nested reviews,
  future/ambiguous/missing identities, cap above/equal/one tick below target,
  off-grid cap, fees/slippage and all existing read-fence/API cases.
- Focused swing/qualification/strategy unit suite: **114 passed**.
- Full PostgreSQL suite: **414 passed, zero failures/skips**; migration upgrade,
  repeat upgrade, downgrade/re-upgrade and atomic failure rollback passed.
- After that full run, the historical-parent test was strengthened to revoke
  only the old identity's separate-account grant while current settings remain
  authorized: **1 passed, 55 deselected**. No production code changed afterward.
- The first full unit run found the checked-in document schema lacked the new
  enum value (**704 passed, 1 failed**). The schema was corrected; all **16**
  evidence extraction/schema tests then passed. Final full backend/worker rerun:
  **705 passed, zero failures/skips**.
- Three contract validators and **13 script tests passed**. These validate
  existing frozen examples without regenerating them.

These totals overlap; they are synthetic regression evidence, not operational or
provider acceptance. No real provider calls, paid inference, publication,
paper admission, trading or changes to actual evidence databases occurred.
