# Bounded discovery and product acceptance — STK-058/059

1 November 2026. This is a repository/software audit, not real-market acceptance.
Original requirements: `reference/stock-platform-kanban-plan.md` S11/S13–15/S20,
`SD-ARCH-3.0.md` §§9, 12, 15 and the existing evaluation/risk contracts.

## Missing dashboard capability delivered

The existing **Dashboard → Three-horizon discovery** already scans five fictional
companies in three horizons and compares Q/Q+R/Q+A for one company. Reuse its
immutable batches, worker, sorting and authenticated evidence readers.

The screen now exposes frozen research priority and its existing quantitative/AI
components. The fixture policy orders action tier, binary quantitative score, then
stable listing ID; AI contributes zero. This is neither a probability nor expected
return, calibrated financial research or evidence of an AI advantage. No score,
policy, frozen experiment or admission rule is changed.

The technical-condition filter selects loaded candidates whose frozen quantitative
BUY gates passed, without changing their original rank or implying that missing
research/rights gates passed. Counts refer only to loaded rows, never the full NSE.

Select two to four companies and choose **Compare selected companies**. The existing
`GET /v1/recommendations/{id}/comparisons` accepts up to three repeated `compare_to`
IDs. It reuses current permission checks, rejects duplicate/missing IDs and mixed
batch/mode/horizon/cutoff/arm, and returns deterministic frozen metrics, evidence
gaps, conflicts and blocked admission. Requests without `compare_to` retain the
existing same-company research-mode comparison. Cross-company comparison is
explicitly synthetic-only; it does not add an observed-data ranking endpoint.

Comparison requests do not run a model, create decisions or reveal outcomes. Reads
are no-store; denied reads clear the comparison and old detail/source content.
Filters/refresh reset selections, and pending reads are cancelled on scope changes
or navigation. At most 100 listings can accumulate in the screen; comparisons are
bounded to four. Subsequent pages remain pinned to the original immutable batch.
P3: authorization per record can be costly at larger volumes. No 100-listing or
full-NSE load acceptance is claimed from five fixtures.

## Quantitative and historical acceptance audit

| Original requirement | Existing implementation and regression evidence | Result / remaining acceptance |
|---|---|---|
| STK-028–032: aligned indicators, deterministic strategy and risk arithmetic | `indicators.py`, `strategy.py`, `risk.py`, `quant_policies.py`; `test_indicators.py`, `test_strategy.py`, `test_quant_policies.py`, `test_swing_qualification.py`; original capital/risk contract validator | Implemented for declared synthetic/qualified-input contracts. EMA uses SMA seed, ATR Wilder smoothing, breakout/relative volume exclude the current session. Legacy geometry/configuration remains frozen. No empirical strategy edge or real policy approval. |
| STK-014/079: genuine inputs before real swing calculation | `swing_research.py`, `swing_qualification.py`, `read_fences.py`; `test_swing_research.py`, qualification and read-fence suites | Trusted stored revisions, original acquisition/current grants, complete coverage and raw basis required. Real sizing additionally constrains cap below target on the supplied tick grid. No qualified NSE dataset supplied. See the explicit M1 checklist. |
| STK-037/043: cutoff-only decisions frozen before reveal | `service.py`, `dataset.py`, `historical_research.py`; `test_historical_research.py`, `test_saved_research.py`, Replay and saved-research browser tests | Software complete: immutable run IDs, original generation time, as-of source clocks, financial snapshot and exact reopening. Actual archived financial availability, contemporary AI completion and genuinely frozen historical research remain unavailable. Today's cached reports cannot fill those gaps. |
| STK-038/039: entry, expiry, gaps, liquidity, fees/slippage and uncertainty | `replay.py`, `paper_engine.py`, daily-replay addendum; `test_replay.py`, `test_paper_engine.py`, original evaluation validator | Deterministic fictional daily fills/cost schedule and separate paper engine exist. Ambiguous paths never gain scalar profit; unsupported action windows are rejected. Actual dated statutory/broker costs, permitted corporate-action outcomes and liquid execution evidence remain unaccepted. Do not replace frozen legacy assumptions. |
| STK-040/041: all outcomes and honest denominators/portfolios | `evaluation.py`, `portfolio.py`, `paper_reporting.py`, `governance_metrics.py`; evaluation/portfolio/paper/governance suites | Forecasts and resolved trades have separate denominators; missing, no-entry and ambiguity remain visible. Synthetic single-slot portfolio differs from multi-position D3-10 ledger. No pooled independent-trade curve. Missing marks/benchmark produce unavailable; genuine comparable benchmark and performance acceptance absent. |
| STK-042/076–078: chronological leakage/holdout/promotion controls | `splits.py`, `governance_contracts.py`, `governance.py`; split/governance/store suites | Fixed synthetic split audit and stronger D3-11 purge/embargo, immutable trials, one-way holdout reservation and forward preregistration already exist. A synthetic split audit is not an untouched real test. EP-1 proposals remain unratified; no new numeric thresholds or promotion. |
| STK-044/058/059: bounded scans, failure-inclusive batches and usable comparisons | Existing publication jobs, saved replay API/UI and this small dashboard increment; publication, saved-history, comparison API and browser suites | Software vertical slice, five fictional listings only. No full eligible NSE load, operational overnight acceptance or actionable researched recommendations. |

This audit identifies acceptance work, not a justification to rebuild completed
engines. Existing `D3-05-quant-policies.md`, `M3-replay.md`, D3-10/11 records and
contracts remain authoritative; earlier checkpoints are historical, not new results.

## End-to-end acceptance split

| Can finish with existing synthetic evidence | Requires genuine evidence or an independent owner/reviewer |
|---|---|
| Authenticated scan → immutable ranked batch → bounded company/mode comparison → citations, missing/conflicting records → denied reread | Exact provider/account/grant-version permission and verified retention/deletion obligations for **every** contributing input |
| Historical selection → frozen technical/financial context → restart/reopen → explicit future reveal → separate baseline outcome | Permitted raw prices/volume semantics, closed exchange sessions, point-in-time instrument/action/filing/event coverage and archives |
| Gap/ambiguous/no-entry/expiry arithmetic; synthetic fee and risk boundaries; duplicate batches and failure accounting | Real dated cost/benchmark observations, point-in-time eligible universe and corporate-action/delisting execution coverage |
| Future-document/late AI exclusion, revision revocation, immutable freeze, zero-pair unavailable comparison | Contemporary financial/AI availability, original revisions and qualified matched decisions; technical-only outcomes cannot measure AI performance |
| Current mandatory CI, API/browser desktop/mobile workflows and migration compatibility | M2 independent source review and **50 unseen human-labelled cases**, approved/frozen evaluation protocol, then measured quality; developer labels are not independent ground truth |

## Smallest remaining path (existing tickets only)

1. **STK-058/059:** deliver this transparent bounded comparison via review/CI;
   retain non-actionable synthetic labels. No new infrastructure dependency.
2. **STK-014/004–007/046/049:** owner/provider decisions and one INFY qualification
   packet meeting every row in `AI_RESEARCH_DATA_ACCEPTANCE.md`. Implement only a
   demonstrated adapter/semantics gap after the permitted source is identified.
3. **STK-052/053:** independent reviewer completes the existing worksheet and
   supplies unseen holdout material/labels; owner approves the proposed protocol
   before use. No further four-example inference or fabricated reviewer.
4. **STK-037–044/076–078:** replay only eligible archived inputs, pin real costs
   and benchmark, preregister comparison before revealing future observations.
   Existing freeze/reveal/evaluator and D3-11 controls are the starting point.
5. **STK-054/059/060:** supervised one-instrument API/UI acceptance and operational
   evidence; separate policy/publication/admission approval remains required.

M1 remains BLOCKED, M2 quality acceptance BLOCKED, REAL-001 operational acceptance
PARTIAL. Publication, paper admission and trading remain blocked. Engineering
checks cannot substitute for these approvals or for financial-performance evidence.

## Validation for this increment

`test_discovery_comparison.py` covers persisted ranking parity and stable pages,
2/4-item order-independent read-only comparisons, auth, duplicates, unknown IDs,
request bounds, incompatible horizons/arms/batches, legacy mode comparison and
revoked rereads. The existing discovery browser workflow now exercises the four
selection slots, ranking explanation, company comparison, scope reset and denied
comparison clearing without adding another mock-model run. Execution totals and
exact CI are recorded in the durable checkpoint/PR, not inferred from this design.
