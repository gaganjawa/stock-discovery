# STK-041/042 — Observation-supported performance view

1 November 2026 · D3-10/11 reuse, M3 engineering increment. Real strategy and M3
acceptance remain **PARTIAL**, not approved by this report.

## User workflow

Open **Scorecard**, select one evaluation version group, then inspect **Strategy
performance evaluation**. The existing single-slot portfolio, immutable decisions,
outcomes and split audit supply the report. Choose a fictional benchmark from that
group's pinned dataset. Refresh preserves that choice; changing group clears it.
Permission denial clears old results. The authenticated endpoint remains
`GET /api/v1/scorecard`, with optional `cohort` and `benchmark_instrument` parameters.
Reads are no-store and perform no provider/model calls, trial access, persistence,
publication, admission or trading.

Displayed fields include strategy/configuration, dataset, evaluation window,
decision/trade/missing counts, net full-capital return, flow-neutral drawdown,
resolved-trade win rate/expectancy/profit factor, exposure definition, descriptive
risk ratios, reference costs/coverage, split results, zero-pair limits and a stable
content-hashed report ID. Decision IDs and outcome-content hashes pin the view.
New outcome revisions produce a new report; original records are never rewritten.

## Arithmetic and availability

- `evaluation.portfolio`, `portfolio.replay_portfolio`, `evaluation.summarize` and
  `splits.split_report` remain the authority for capital, chronology, fill-derived
  P&L, drawdown, overlapping-slot exclusions and split membership. Closed trades
  are distinct from forecasts, no entries, ambiguities and missing observations.
  Profit factor uses positive/negative realized BUY P&L with proven entry, aligned
  with the resolved-trade denominator; no losses means unavailable, not infinity.
- Risk ratios require a complete close-to-close session series. Only known idle
  cash is carried between marks; missing position marks block ratios. Initial
  partial-session return is excluded from ratios, but not from total return or
  drawdown. Unqualified external-flow timing blocks session ratios. Zero cash
  yield and downside target are explicit fictional assumptions. Sharpe is mean
  excess return / sample standard deviation (n−1); Sortino is mean excess return /
  all-session target semideviation. At least two intervals are required for the
  shared sample estimator. Missing rates/observations, zero variance or no downside
  return the applicable unavailable reason. Ratios are **not annualized** and do
  not assume independent samples, establish significance or approve a strategy.
- `SYN-buy-hold-net-v1` is an exploratory reference using only the same immutable
  **synthetic** dataset and window. It buys at the next session open plus the
  existing adverse slippage and exits at the final close less slippage. Whole-share
  cash sizing includes the existing fixed/per-share fee schedule; both sides'
  costs are charged. Idle cash remains in the full-capital denominator. Existing
  1%-of-daily-volume validation can make a full-capital reference unavailable;
  there is no retrospective resizing to obtain a result. Unsupported corporate
  actions, eligibility changes, missing/late observations, immature outcome clocks
  and expired costs also block it. Availability is checked at the recorded outcome
  **knowledge cutoff**, separately from the historical observation window.
- Benchmark identity, policy/cost versions, raw basis, currency, source references,
  dataset/calendar hashes and clocks are reported. No real index/proxy prices,
  licence, dividend adjustment, costs or benchmark approval are invented. The
  default is **not selected / unavailable**. Strategy-minus-reference is a
  descriptive net-return difference, not causal alpha or exposure-matched return.
  The ordinary demo may correctly fail reference liquidity. The positive API test
  uses an explicitly separate high-volume synthetic dataset; originals are intact.

## Walk-forward and AI boundaries

The new table evaluates only IDs retained by the **existing** outcome-independent
60/20/20 session split audit, including its five-session gap, horizon purging,
configuration checks and exclusions. Each partition gets its own existing
cash-constrained portfolio calculation. This table is not renamed walk-forward,
an untouched holdout, EP-1's complete-month history or an independent experiment.

Use the existing D3-11 authenticated registry/trials and **Experiment governance**
screen for preregistration, fixed strategy/model/policy hashes, chronological
windows, label-overlap purge/embargo, train-only preprocessing, validation trial
budget, irreversible holdout reservation, forward registration and immutable
evaluation. Those controls are not duplicated or bypassed here. No fitted model,
optimization, new stopping criterion, threshold approval or holdout access is
introduced. Registered walk-forward fold evidence is absent from this scorecard
and explicitly unavailable; displaying the synthetic split does not satisfy it.

Combined/unknown strategy configurations cannot receive technical performance from
this view. Independently qualified historical AI pairs are absent: eligible pairs
remain **zero**, AI performance **null**, comparison **unavailable**. Existing
technical-only outcomes never become financial-research or AI accuracy results.

## Validation and remaining work

Focused tests independently check risk formulas and mathematical edge cases,
hand-calculated costed reference P&L, knowledge clocks, missing/late prices,
liquidity/action rejection, idle-cash/missing-mark behavior, immutable inputs,
denominators, combined abstention and deterministic report identity. PostgreSQL/API
tests cover auth/no-store, actual pinned source reads, valid reference, missing
outcomes, denied rereads and absence of inference/ledger changes. The existing
Replay browser workflow exercises the new view, benchmark selection, unchanged
split/scorecard results and restricted-result clearing. Exact execution totals,+final-review corrections and CI are recorded in the checkpoint/PR.

Full real M3 acceptance still requires qualified point-in-time strategy/benchmark
observations, verified costs/action coverage, a predeclared experiment/fold plan,
permitted benchmark and EP-1 decisions, appropriate mature samples and forward
evidence. M1 qualification and M2 independent review/50-case holdout remain blocked.
Only missing report presentation/arithmetic is added; no new evaluator framework,
schema, frozen experiment, real recommendation or activation is introduced.
