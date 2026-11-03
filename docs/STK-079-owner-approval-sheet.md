# STK-079 — Owner approval sheet: cautious starting rules (PROPOSED, NOT APPROVED)

This sheet is one page to sign or change. It reuses the existing proposals: Swing policy
`REAL-001-SWING-PROPOSED` 2.0.0, the capital/risk contract 1.0.0 and the EP-1 promotion
gates in the evaluation contract.

Approving it activates nothing. It allows no paper admission or broker order on its own, and it
makes no data, rights or AI gate pass. Each approved row becomes a new immutable policy version.
Mark each row **A** (approve), **C** (change, with a new value) or **D** (defer).

## 1. Scope and capital

| # | Rule | Proposed starting value | Why | A/C/D |
|---|---|---|---|---|
| 1 | Universe | Only the existing 12-stock NSE pilot, EQ series, active listings | Universe expansion is not qualified | |
| 2 | Liquidity floor | 20-session median traded value ≥ ₹50 crore. Unknown means excluded. | Keeps slippage assumptions credible for large caps | |
| 3 | Real money | None. Forward **paper** only, and no broker orders. | Already recorded; restated for completeness | |
| 4 | Paper starting capital | ₹1,50,000 virtual (about three months at ₹50,000). Skipped months post nothing. | Matches the contribution plan without inventing deposits | |
| 5 | Buckets | Long-term 60%, short-term 25%, swing 15%. Each bucket has its own ceiling. | Conservative tilt to longer horizons | |
| 6 | Cash reserve | 10% of each bucket is never sized | Contract requires an explicit reserve | |

## 2. Risk limits (paper)

| # | Rule | Proposed | A/C/D |
|---|---|---|---|
| 7 | Planned loss per trade (swing, short-term) | 0.25% of the bucket sizing base | |
| 8 | Combined open planned loss | 0.50% of the bucket sizing base | |
| 9 | Single-company exposure | ≤ 10% of total paper equity | |
| 10 | Sector exposure | ≤ 25% of total paper equity. A missing sector blocks sizing. | |
| 11 | Gross exposure | ≤ 90% of total paper equity | |
| 12 | Pause on loss | Daily loss ≥ 1% or monthly loss ≥ 3% pauses new admissions. Resuming needs your explicit approval. | |
| 13 | Drawdown gate | Flow-neutral maximum drawdown ≤ 10% (EP-1) | |
| 14 | Long-term positions | No price stop. A thesis review every quarter and after every results filing. Exit only on a recorded thesis break. | |

## 3. Horizon rules (existing D3-05 formulas; values are starting points, not calibrated)

| # | Horizon | Proposed rule | A/C/D |
|---|---|---|---|
| 15 | Swing (2–10 sessions) | Swing 2.0.0 as written: EMA10 > EMA30 and close > the prior 20-session high; hold 3 sessions; entry window 1 session; stop 2×ATR14; target 2R; real tick size required | |
| 16 | Short-term (1–3 months) | Year-over-year revenue and EPS growth > 0 from registered filings; close > SMA20; margin of safety ≥ 15% against the bear-case annual-EPS scenario; hold ≤ 63 sessions | |
| 17 | Long-term (1–5 years) | Positive operating cash-flow margin in at least 4 of 5 years; net debt / operating cash flow ≤ 2; positive free cash flow; business and governance coverage required; bear/base/bull PE scenarios are display only | |
| 18 | Missing evidence | Always INSUFFICIENT EVIDENCE before any directional decision. Verified adverse evidence leads to AVOID. | |

## 4. Costs and slippage (Indian delivery equity; check against a current contract note)

| # | Item | Proposed model | A/C/D |
|---|---|---|---|
| 19 | Statutory and exchange charges | STT 0.1% on buy and sell. NSE transaction about 0.003%. SEBI ₹10 per crore. Stamp duty 0.015% on buys. GST 18% on brokerage plus transaction charges. | |
| 20 | Brokerage and DP | ₹20 fixed per executed order. ₹20 DP charge per sell. This deliberately assumes the higher of the two brokers. | |
| 21 | Slippage | 10 bps adverse on each fill (large caps). Gaps fill at the open, never at the stop price. | |
| 22 | Stress test | Results must stay positive at 2× fees and 2× slippage (EP-1) | |

## 5. Benchmarks and promotion

| # | Rule | Proposed | A/C/D |
|---|---|---|---|
| 23 | Market benchmark | NIFTY 500 total-return index. Also report an exposure-matched reference and a cash reference. The index needs a permitted data source; until then the comparison is null. | |
| 24 | Pilot-matched benchmark | NIFTY 50 total-return index, because the 12-stock pilot is large-cap | |
| 25 | Promotion | EP-1 unchanged: deterministic gates, then coverage ≥ 95%, then positive net expectancy and return ≥ the references on validation **and** the untouched test, then your review. Never automatic. | |
| 26 | AI arms | Q, Q+RAG and Q+agent stay in shadow until the 50-case independent review passes | |

## 6. Operations

| # | Rule | Proposed | A/C/D |
|---|---|---|---|
| 27 | Schedule | Daily after the NSE close (18:30 IST, trading days only), weekly on Saturday, monthly on the first Saturday | |
| 28 | AI budget | Local Ollama only, ₹0. At most 40 model calls per day. No paid model calls. | |
| 29 | Deployment | Local only on the Mac until Level 2. Hetzner is decided separately. | |

Signature: ____________________ Date: __________

Rows marked D stay unconfigured, and the dependent features stay INSUFFICIENT EVIDENCE.
