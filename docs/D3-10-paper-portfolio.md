# D3-10 — paper portfolio and outcome tracking

STK-037–044/060–063. Builds on merged D3-09 (PR #10, `5121cd3`). Local PostgreSQL, FastAPI, worker and React only. No broker interface, paid data/model call, deployment, real-source activation or strategy promotion.

## Two separate contracts

`fictional-simulation-1.0.0` explicitly authorizes software simulation with the frozen D3-09 fixture universe. It records its own admission, cash ledger and outcomes. **It does not change the original v2 recommendation, its blocked paper admission, synthetic flag or shadow cohort.** The UI labels this MOCK / SHADOW / FICTIONAL SIMULATION / NON-ACTIONABLE. Historical mock model knowledge is not represented as verified forward research.

`paper-1.0.0` creates an empty forward-paper book using actual time. D3-09 MOCK, SHADOW, simulated-availability and unapproved recommendations cannot enter it. Fictional observation inputs are rejected. There are no approved real policy/model/capital/source registrations or qualified forward observation adapters in this baseline, so forward admission remains fail-closed. This is an activation dependency, not permission to grant approvals, synthesize real prices or execute broker orders. The separate software-test contract is never an investment approval.

## Portfolio accounting and admission

Each portfolio freezes its starting virtual capital, reserve fraction, loss limits, issuer/sector/gross/horizon exposure limits, mark age, fees, slippage and entry gap cap. API clients may configure these at creation; the UI starts with explicit **fictional** defaults. They are not ratified real risk settings. Starting capital is the sole external cash contribution; additional deposits, withdrawals, dividends and real corporate-action accounting need qualified adapters and are not inferred.

One PostgreSQL row lock serializes all admissions and observations for a portfolio, across horizons and research arms. Cash is shared; per-horizon views do not invent separate capital. Batch admissions use frozen action tier, quantitative readiness, listing, horizon and recommendation ID as deterministic rank; the whole candidate set shares one lock. Independent owner requests are serialized in committed order. AI scores never rank admissions. Exact retries are idempotent; a recommendation can be tracked once per portfolio. Every attempt, including WATCH, AVOID, INSUFFICIENT_EVIDENCE and capital rejection, is retained. Comparison figures therefore include selection/admission effects and are not paired research experiments.

Admission rechecks current source permissions, fixture policy identity, frozen quantitative reproduction, deterministic eligibility, decision availability, cutoff, expiry, sector, portfolio pause and mark freshness. Forward approval absence always rejects. The largest whole-lot quantity must jointly satisfy cash, costs, per-trade/combined risk, cross-horizon issuer exposure, sector exposure, gross exposure and horizon limits. Effective capital is the minimum of starting ceiling, frozen monthly base and current equity. AI scores never increase this quantity. At execution, opening marks recheck portfolio risk and loss limits before further entry; prior pauses cancel pending entries but preserve known protective exits. Current high/low/close never influence this opening gate.

Reservations include capped pending notional, variable entry fees and worst-case fixed fees for one-share partial entry/exit allocations. Fixed exit fees remain reserved on held positions, including unresolved positions, so even a severe price gap cannot consume cash already promised to another entry. Expiry releases unfilled reservations; fills atomically convert reservation to cash/position changes. Daily/monthly losses, ambiguous paths and data failure latch new-admission pause. There is no automatic unpause or override endpoint.

## Deterministic execution policy

- Long only, whole lots. No shorts, leverage or broker execution.
- Buy-stop entry uses the greater of opening price and trigger, plus configured slippage, subject to the smaller of the frozen quantitative cap and portfolio cap. A gap above that cap does not fill.
- Limit entry uses the lesser of opening price and limit, with adverse slippage capped at the limit.
- Existing stops gapped through at the open fill at that open with adverse slippage; never at a fictitious guaranteed stop price. Opening target gaps use the open less slippage, bounded by the target limit.
- A daily bar touching both stop and target without decisive opening information remains **ambiguous**. An intraday entry followed by a potentially earlier stop/target also remains ambiguous. No invented liquidation, P&L or intrabar ordering resolves it. The position and exit fee reserve remain held, valuation is unavailable, and admissions pause.
- A triggered exit with explicitly limited allocation carries a pending at-open exit to the next observed session. Its opening priority is known; later high/low cannot override it.
- Fixture `entry_capacity` / `exit_capacity` can explicitly limit fills. They represent declared fictional allocations, **not estimates from daily traded volume**. Absent capacity means the documented full-fill fictional assumption, never a real liquidity claim. Unsupported real partial fills cannot be submitted through this contract.
- Entry expiry releases pending quantity. An expiry inside an unsequenced daily candle is unavailable. Time exits use the scheduled session close, with adverse slippage. Calendar sessions come from the original immutable recommendation; missing sessions cannot be silently bypassed.
- Fees are `fixed_fee + filled_notional × fee_bps / 10000` on each fill. Slippage changes fill price and is also reported separately; it is not deducted twice. Decimal arithmetic retains precision without exchange-specific rounding; this is a frozen software-test assumption.
- Missing, late/stale or invalid session data and flagged unsupported corporate actions produce unavailable outcomes. Holdings are retained, not erased as if delisted companies never existed. No splits, dividends or exit values are fabricated.

## Observation clocks, worker and provenance

Authenticated observation submission seals a fictional, chronological OHLC batch with session open/close, availability and observation time. The same listing has one bar per batch across cohorts/horizons. The next session must match the original calendar. The data cannot be before the recommendation cutoff, use future-unavailable observations, rewrite a processed session, or feed a forward-paper book. New admissions wait for any already-sealed batch to settle.

The portfolio has separate economic (`asof`) and knowledge (`available_at`) clocks. Delayed observations advance knowledge time; their resulting cash cannot fund a newly admitted recommendation at an earlier time. Prices are stale based on session close, not a delayed vendor availability stamp. Observation inputs, original decisions and all ledger versions are immutable.

The existing local worker checks the paper inbox before discovery/replay jobs. Processing, ledger insert and completion receipt are one transaction. Concurrent workers and retries produce one event; a crash rolls everything back. There is no fabricated unattended market feed. The UI's **Advance one fictional session** seals one versioned illustrative session; the worker performs tracking automatically. Its flat reference-price path is shared by listing and derives only from frozen reference prices. An authenticated test client can submit explicit fictional OHLC/allocation scenarios through the same inbox.

The append-only ledger stores every cash delta, fill, cost, outcome state, original recommendation reference/hash, horizon/cohort, pinned policy/model versions, source permissions and observation hash. Each event hashes its predecessor. The immutable D3-09 artifact supplies the calendar and original terms, avoiding duplicated calendars in every ledger entry. Updating/deleting portfolios, ledger, observations or processing receipts is rejected by PostgreSQL triggers. Corrections do not overwrite a historic run; use a separately named simulation with a new observation history.

## Evaluation

Cash plus observable marked holdings forms the chronological portfolio equity curve. Starting capital is identified as an external flow. Portfolio return and maximum drawdown come from that curve, not a sum of independent trade returns. Turnover is buy-plus-sell notional divided by the mean recorded-session equity; it is not annualized. Report open and pending exposure, concentration, reserved funds, fees and slippage separately.

Closed-trade win rate, average net return, profit factor and net INR expectancy use **resolved closed trades only**, including losses. Provisional, no-entry, rejected, ambiguous and unavailable counts remain visible. Profit factor is unavailable when there are no realized losses. Per-horizon and per-research-cohort views use the same definitions and show denominators.

Forecast evaluation is separate: original-decision endpoint price return can mature even if no trade entered, and an early trade exit does not mature a one-year forecast. Missing coverage permanently marks that forecast unavailable in this history. Four action labels are not a shared binary price-direction forecast, so a pooled direction hit rate is explicitly unavailable. MAE/MFE cover fully observed held sessions only, excluding intraday entries, exits and ambiguous bars; coverage is reported, not portrayed as complete-trade extrema.

Cash benchmark return is zero. There is no eligible permitted market benchmark in the installed fixture observation contract, so market benchmark/excess return are explicitly unavailable. Uncertainty intervals, annualization and risk-adjusted statistics are also unavailable without qualified independent samples and experiment registration. D3-11 experiment governance is not implemented here.

## Authenticated endpoints and UI

All new routes use the existing owner authentication and same-origin controls:

| Endpoint under `/v1/paper-portfolio` | Purpose |
|---|---|
| `POST /` with `Idempotency-Key` | Freeze portfolio configuration and initial virtual cash |
| `GET /` | List portfolios |
| `GET /{id}` | Cash, reserves, positions, metrics, comparisons, ledger and limitations |
| `POST /{id}/admissions` | Track one immutable recommendation; record acceptance/rejection |
| `POST /{id}/admissions/batch` | Track a candidate set in deterministic frozen quantitative rank order |
| `POST /{id}/observations` | Seal explicit fictional observation data |
| `POST /{id}/fictional-session` | Queue the next declared illustrative session |
| `GET /{id}/outcomes/{recommendation_id}` | Original terms, fills, current outcome and immutable event history |

Trailing slashes in this table are conceptual; the collection path is `/v1/paper-portfolio`. Permission revocation denies portfolio detail/drill-down reads, clears cached UI detail, cancels unfilled entry reservations during tracking, and preserves the audit history. The existing `/api/v1` synthetic replay and `/v1` discovery contracts remain unchanged.

The dashboard adds portfolio creation/selection, capital and exposure, positions, transaction history, original recommendation drill-down, horizon/cohort comparisons and clear limitations. The separate forward-paper book displays activation blocked. Configuration is immutable; the UI exposes starting capital and contract choice, while the API exposes all supported fictional limits.

## Verification

See `backend/tests/test_paper_engine.py`, `backend/tests/integration/test_paper.py`, and `frontend/tests/paper.spec.ts`. Tests cover all horizons/actions, shared cash concurrency, risk rejection, idempotency, immutable ledgers, rollback/retry, source revocation, gaps/ambiguity, partial allocations, fees/slippage, missing/stale sessions, expiry, delayed-data clocks, forecast maturity, authentication and D3-09 compatibility. Migration `0011` is additive and reversible. CI's migration runner rejects empty integration reports and any skipped integration case.

Final validation results are recorded in `SIMPLE-BOARD.md`. Real policy/model/source qualification and restricted production-runtime grants remain existing activation blockers. No deployment or infrastructure change is part of D3-10.
