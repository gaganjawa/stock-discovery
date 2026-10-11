# M3 — Replay and evaluation evidence

STK-037–040: persisted analysis freezes before outcome access; idempotent run identity retains original generation time; restart reloads the exact content-addressed dataset and frozen analysis. Daily fills, gaps, expiry, cash, coarse liquidity, date-effective synthetic fees/slippage and ambiguity are implemented. Original fixtures untouched. Daily fill representation documented in the 1.1.0 addendum.

STK-041: STK-002 arithmetic is reused, with parity against all original scenario metrics and the 5.6% return/20% drawdown cash-flow example. Coverage/exclusion IDs remain visible; no-entry/ambiguous records are excluded from realized trade denominators. Per-replay marked equity supports return/drawdown. Combined portfolio/exposure/turnover and real benchmark comparison remain incomplete, explicitly undefined.

STK-042: synthetic chronological windows and insufficient-promotion-evidence gate exist. Full sector/regime uncertainty reports and EP-1's 30-complete-month validation remain incomplete; synthetic weekdays are not real market history.

Validation: six hand-calculated daily replay tests, one original-metric parity test, two strategy tests and six PostgreSQL integration cases pass. Migration upgrade/downgrade/re-upgrade and atomic failure rollback pass. No real trading, providers or paid API calls.

Status: STK-037–040 Ready for Release for synthetic scope. STK-041/042 partial; outstanding items above prevent claiming the full v0.2 acceptance scope is complete.
