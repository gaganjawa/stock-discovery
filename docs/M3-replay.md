# M3 — Replay and evaluation evidence

STK-037–040: persisted analysis freezes before outcome access; idempotent run identity retains original generation time; restart reloads the exact content-addressed dataset and frozen analysis. Daily fills, gaps, expiry, cash, coarse liquidity, date-effective synthetic fees/slippage and ambiguity are implemented. Original fixtures untouched. Daily fill representation documented in the 1.1.0 addendum.

STK-041: STK-002 arithmetic is reused, with parity against all original scenario metrics and the 5.6% return/20% drawdown cash-flow example. Coverage/exclusion IDs remain visible; no-entry/ambiguous records are excluded from realized trade denominators. Per-replay marked equity supports return/drawdown. Combined portfolio/exposure/turnover and real benchmark comparison remain incomplete, explicitly undefined.

STK-042: synthetic chronological windows and insufficient-promotion-evidence gate exist. Full sector/regime uncertainty reports and EP-1's 30-complete-month validation remain incomplete; synthetic weekdays are not real market history.

Validation: six hand-calculated daily replay tests, one original-metric parity test, two strategy tests and six PostgreSQL integration cases pass. Migration upgrade/downgrade/re-upgrade and atomic failure rollback pass. No real trading, providers or paid API calls.

Status: STK-037–040 Ready for Release for synthetic scope. STK-041/042 partial; outstanding items above prevent claiming the full v0.2 acceptance scope is complete.

## Validated checkpoint — 11 Oct 2026

Added a separate, predeclared synthetic single-position portfolio evaluator. It reserves capital at the signal, excludes overlapping candidates, revalidates cash/risk, and leaves ambiguous admitted paths undefined. It reports return, drawdown, traded notional and closing-mark exposure (explicitly not calendar-weighted exposure). Mixed dataset/code/strategy cohorts are not pooled. Added grouped horizon/strategy/regime reports, unclassified synthetic-sector disclosure and descriptive Wilson intervals. These are software-validation statistics, not signal confidence or real experiment acceptance.

Four focused portfolio/report/contract-parity tests and two ingestion/service PostgreSQL checks passed at this checkpoint. Completed manifests now support idempotent reuse regardless of requested import page size; partially imported pages still enforce their recorded chunk configuration. Full real-market benchmark and EP-1 acceptance remain blocked. STK-041/042 remain partial for the full planned scope.
