# Scope and capital risk contract 1.0.0

STK-003 · P1 · v0.1. This contract completes S01's scope and risk semantics alongside the immutable [recommendation](recommendation-contract.md) and [evaluation](evaluation-contract.md) contracts. It authorizes neither investment allocation nor real orders. Numerical examples are fictional, and no live risk profile is approved. The validator demonstrates arithmetic only; application sizing, portfolio reconciliation and execution remain later tickets.

## Scope and horizons

| Capability | Contract support | Implementation status / gate |
|---|---|---|
| Daily swing research | BUY, holding SELL, WAIT, HOLD, insufficient evidence; frozen entry, stop, target, entry expiry, session-based holding limit | First strategy path planned; no replay engine or broker data yet |
| Long-term investment research | Separate allocated bucket, thesis/valuation and scheduled review horizon; holding-specific reduction/exit | Deferred to company/holding research; never inherit swing stops or automatically size an investment using this swing example |
| Intraday | Future separate profile with session end, no-overnight rule, interval quality and realistic costs | Deferred to v0.5; not enabled by a `horizon` label alone |
| Historical and forward paper | Same future analysis/risk code, separate clocks; immutable versioned inputs | Evaluation policies/data rights must be resolved before real experiments; synthetic contracts/UI can proceed |
| IPO research | Separate assessment, no assumed allocation or listing fill | Deferred; subscription/allotment not modeled as a stock BUY |
| Shorts, margin, derivatives, leverage | Unsupported in this contract | Explicitly disabled; SELL never opens a short |
| Real orders | Unsupported | Optional v1.1 gates and concrete owner authorization required; no automatic order submission |

The next approved work must be requested separately. STK-010/STK-011, STK-004 source work and all other tickets remain unstarted by this delivery. A basic synthetic UI may display these states without implying those capabilities exist. STK-002's proposed performance policy remains unresolved for real experiments and is not converted to an approved risk setting here.

## Money buckets and ledger

All money is INR Decimal/NUMERIC; store amounts as decimal strings and timestamps in UTC, display Asia/Kolkata. Use stable event IDs, bucket IDs and account references, not credentials. Every posted event has type, amount, effective time, recorded time, source/reference and immutable revision/correction link. A duplicate ID must not post twice. Pending/failed deposits are not available cash; reconcile before posting. Corrections reverse and replace rather than edit history.

- **Contributions** are optional external cash flows. A suggested monthly amount (including the earlier 50,000 planning figure) is a planning preference, not a standing funding order, obligation or balance. A skipped month posts no deposit, creates no receivable/debt and triggers no catch-up purchase. Record actual settled amount; irregular or zero contributions are valid.
- **Unallocated cash** is not automatically active trading capital. New deposits enter an explicitly chosen bucket; the default bookkeeping route is unallocated. Transfers require a recorded allocation decision. Retain an available-cash reserve and commitments before sizing.
- **Active trading allocation** is a deliberately approved capital ceiling for the swing/intraday research/paper profile. Active equity includes its cash and marked positions. It is distinct from cumulative contributions, account cash, portfolio equity, buying power and long-term investments. A deposit never automatically raises the ceiling.
- **Long-term investments** have their own cash, holdings and review policy. They are excluded from active sizing collateral and active loss-budget denominators. Reallocating cash from long-term to active is an explicit paired transfer, not an assumed liquidation. Cash cannot belong to two buckets at once.

Total equity is unallocated cash + active cash/positions + long-term cash/positions, less liabilities. Bucket transfers are paired debit/credit entries and net to zero for total-portfolio flows and P&L. For a bucket's performance calculation, transfers in/out are that bucket's external flows, so reallocation is not profit or loss. Buy/sell cash movement is internal to the relevant bucket; fees and economic gain/loss affect P&L. Do not book both sale proceeds and profit as independent income. Reserved withdrawals, unsettled sale proceeds and cash reserved by pending BUY orders are unavailable for new sizing until reconciled. A pending SELL does not release cash/exposure/risk before its confirmed fill.

A fictional contribution history of January 50,000, February skipped and March 30,000 produces **80,000 actual contributions**, not 150,000. The planner's suggested amount never enters that sum. These are invented ledger examples, not user balances.

## Configurable policy and versioning

Before enabling a real-data paper risk profile, freeze a profile ID/version, approval state, effective timestamp, currency, horizon, allowed instruments/products, approved active ceiling, reserve, per-trade loss fraction, combined planned-loss fraction, gross/instrument/sector exposure fractions, daily/monthly loss limits, optional portfolio drawdown limit, mark freshness, cost/slippage model, entry price cap, holding limits and pause/resume authority. Fractions lie in [0,1]; required limits are positive. Cross-validate per-trade <= combined loss and instrument <= sector <= gross exposure. Explicitly disabled optional limits carry a reason; missing required inputs mean **insufficient_evidence / sizing unavailable**, never unlimited risk.

Store policy/version and the full as-of capital/exposure/reservation snapshot with every later sizing decision, including proposed integer quantity, binding constraints and rejection reason. Activations and changes are append-only approvals; they never retroactively change an earlier recommendation or evaluation. A lower cap can block new entries immediately; it must not automatically liquidate existing holdings. Raising limits or resuming from a pause requires an explicit new approval. Configurability is not permission to relax limits after losses.

`examples/capital-risk.synthetic.json` is labelled `synthetic_only`, with `live_enabled: false`. The earlier .25% per-trade, .5% combined and 1% monthly-review figures are retained only as **unapproved illustrative proposals**. The other exposure/fee numbers are arithmetic examples, not recommendations. Production activation, real capital amounts and long-term rules remain owner decisions. No order path consumes this fixture.

## Conservative planned sizing for an opening long

Let approved ceiling A, frozen period risk base B and current marked active equity E give effective sizing base `R = max(0, min(A, B, E))`. B is approved at the start of the review period from then-current allocated capital; it cannot be increased by deposits or midperiod reallocation. At a new month, freeze a new approved base and opening equity. Retain prior period loss and pause history; the calendar change alone cannot clear a latched pause. Withdrawals/losses can lower E and hence R; they do not rewrite prior P&L.

For a hypothetical full-fill BUY, let P be the maximum allowed adverse entry fill, S the modeled protective exit fill, v the nonnegative variable round-trip fee per share, f the nonnegative fixed round-trip charge. P/S already incorporate the configured adverse entry/stop slippage; do not deduct slippage again. Require `P > S > 0`, valid tick rounding, fresh marks and a complete stop/cost model. Risk per share is `(P - S) + v`; risk cost for q>0 shares is `L(q) = q × risk_per_share + f`; q=0 creates no trade or fees.

The permitted planned risk is `min(R × per_trade_fraction, R × combined_fraction - existing_planned_risk - pending_planned_risk)`. Existing active risk uses downside from the **current mark** to modeled protective exit, plus remaining exit costs, floored at zero; unrealized gains or negative risk do not offset other positions. Missing/invalid stops or stale marks make combined risk unknown and block new entries. Pending BUY risk uses its allowed adverse entry cap and reserved costs. A breached stop is an unresolved exit condition, not zero risk.

Choose the largest nonnegative integer quantity satisfying **all** constraints:

1. `L(q) <= permitted planned risk`.
2. `q × P + entry fees(q) <= settled active cash - reserve - pending BUY cash - reserved withdrawals`.
3. New notional `q × P` plus current marked exposure and pending BUY notional <= `R × gross_fraction`, separately <= instrument and sector caps. Existing/pending exposure belongs to each applicable cap; do not subtract hypothetical SELLs. Fees affect cash/loss, not position notional. Unsupported currency or missing sector classification blocks sector-dependent sizing.
4. Valid instrument lot size/tick, horizon and risk profile; no current pause, unsupported leverage, new short or unknown required input.

Negative residual budgets yield quantity zero and a rejection reason. Fractional shares are not allowed in this example; later product lot sizes round quantity down. For nonlinear/minimum statutory fees, search/recheck the integer candidate with the actual versioned cost function rather than relying on a linear approximation. At execution, gaps above P or changed capital/exposure invalidate the proposal and require revalidation; do not silently fill a larger notional. A protective stop is not a guaranteed loss cap: gaps, halts and liquidity can exceed L(q), per-trade and portfolio limits. Stress assumptions and a pause rule supplement planned risk; none guarantee bounded actual losses.

The separate synthetic validator computes only these linear fixture constraints. For R=100,000, per-trade budget=250 and combined remainder=500-300=200. At P=100, S=95, v=.20, f=2, risk allows floor((200-2)/5.20)=**38** shares. Spendable cash=2,500 with entry variable fee .10/share and fixed entry fee 1 permits **24**. Instrument remaining notional 10,000 permits 100; sector remaining notional 25,000-23,000=2,000 permits **20**; gross remaining 80,000-70,000=10,000 permits 100. Final **20 shares**, entry cash **2,003**, planned loss **106**. One more share breaches the sector cap. This is not implemented production sizing (STK-032).

## Loss accounting, pauses and exits

For each day/month, freeze starting marked bucket equity E0 and its approved loss-budget base B0. At any observation, `period_pnl = current_equity - E0 - net_external_flows_since_start`. Include realized and unrealized P&L and accrued fees under the same valuation convention. Deposits and withdrawals (including bucket transfers) are flows, not returns. Period loss is `max(0, -period_pnl)`; breach occurs at equality or greater than `B0 × loss_fraction`. Do not use contribution totals as the denominator, reset losses after a deposit, omit underwater open positions, or use current higher deposited equity to dilute the threshold. Unknown/stale equity means no new risk until reconciled.

Daily and monthly limits are checked independently; either breach latches a pause on new or increased active exposure. Optional portfolio drawdown uses the flow-neutral chronological method in STK-002, not the sum of recommendation P&Ls. A pause remains until recorded owner review/resume, even after an equity recovery, contribution or new month. Continuing existing protective exits and genuinely risk-reducing holding sales remains permissible in research/paper modeling; increasing/reopening a position is not an exit. Real orders still require their own later authorization.

Example: monthly E0=B0=100,000, equity after losses=98,800. Loss=1,200 breaches the illustrative 1,000 review threshold. A posted 50,000 deposit raises equity to 148,800 and flows to 50,000: period P&L remains **-1,200**. A later 20,000 withdrawal gives equity 128,800 and net flows 30,000: still **-1,200**, still paused. None of these flows create a return. A subsequent recovery does not silently clear the latched pause.

## Holding sale versus short

SELL / CLOSE_LONG disposes of all available holding quantity; SELL / REDUCE_LONG disposes of less. Available quantity subtracts pending sell reservations and unavailable/pledged quantity. A sale exceeding that amount is rejected, never interpreted as a short. HOLD preserves the holding; WAIT preserves a prospective entry's inactivity. A completed holding sale reports proceeds net of charges; holding profit requires original basis and acquisition costs. STK-001's one-share sale remains a holding exit, not an executed short or a profit claim. A cancelled or uncertain sell does not release its reserved quantity until reconciled.

## Validation and unresolved activation choices

Run `python3 scripts/validate_capital_risk_examples.py`, plus the existing STK-001 and STK-002 validators. Independent expected results cover skipped contributions, risk/cash/exposure bounds, zero quantity/fees, invalid stops, exhausted risk, deposits/withdrawals preserving loss, threshold equality, latched pauses and overselling reserved holdings. Original decisions/outcomes are unchanged. No data provider, model, broker or external account is called.

Before real experiments: approve actual capital allocation and all risk values; select costs/slippage, calendar and data rights; ratify STK-002's evaluation policy; approve long-term rules separately. These activation decisions do not block this contract or a synthetic skeleton/UI. This ticket does not implement STK-010/011 or authorize their start.
