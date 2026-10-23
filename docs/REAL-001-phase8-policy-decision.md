# One decision record: INFY Swing shadow research proposal

22 October 2026 · STK-028/054/058/059/060 · **PROPOSED / NOT APPROVED / NOT ACTIVATED**.

The [D3-05 policy manifest](policies/real-swing-proposed-2.0.0.json) uses the existing contract, ID `REAL-001-SWING-PROPOSED`, version `2.0.0`, status `unconfigured`, approval reference null. It is a new proposal following Phase 6's unset draft, not a production policy. Its effective date is a schema field, not approval. Loading it for readiness display cannot activate it.

## Exact proposed rules and reasons

| Setting | Proposal | Reason and limit |
|---|---|---|
| Listing | Only NSE:INE009A01021 / INFY | This milestone has no universe qualification. |
| Holding / forecast | 3 completed trading sessions each | Small bounded prospective observation window within D3-05's 2–10-session contract; operational choice, not optimized profitability. |
| Entry window | 1 future trading session | Avoid carrying a stale condition across several sessions. No executable order is authorized. |
| Price freshness | At most 1 elapsed day and the latest closed dated session present | Conservative research freshness. A weekend/holiday may block under the elapsed-day cap; no calendar exception is silently invented. |
| Required bars | At least 30 consecutive verified closed sessions, no duplicates/gaps, one observation/adjustment basis | EMA30 warm-up and D3-05's exact session completeness gate. SMA20 uses 20, ATR14 uses 14, prior-20 breakout and volume need 21. |
| Coverage freshness | At most 1 elapsed day | Requires fresh complete actions, material-events and filings coverage under existing D3-05, including for Swing. Parsed annual statements alone do not attest coverage completeness. |
| Price condition | EMA10 > EMA30 and latest close > prior-20 high | Existing D3-05 Swing formula, explicitly proposed for review; historical fixture behavior is not real calibration. |
| Volume / liquidity | Every required bar has positive volume; relative volume20 ≥ 1.5 only after adjustment semantics are verified; instrument eligibility independently true | Existing formula threshold, not a validated liquidity floor. No evidence-backed absolute turnover/spread threshold is available, so liquidity qualification remains missing. |
| Corporate actions | Complete effective-date coverage for the lookback and prospective window; unknown adjustment factors, volume basis or action effects block | Today's adjusted history cannot become raw execution or historical PIT evidence. No action feed completeness is inferred from an empty response. |
| Market/instrument risk | Known eligible instrument and risk_prohibited=false, with evidence; unknown means insufficient | No market-regime threshold or risk approval is invented. Current real risk settings are not implemented/qualified. |
| Missing evidence | INSUFFICIENT_EVIDENCE before directional decisions | Required controls remain fail-closed. Missing long-term valuation alone is not added as a Swing requirement; existing actions/events/filings and risk requirements remain. |
| Entry / invalidation | No executable entry/stop/target while real tick, action and risk settings are unqualified | Legacy geometry is high + one tick, cap ×1.01, stop 2 ATR, target 2R; its hard-coded 0.01 tick is synthetic-only and must not be activated for INFY. Actual instrument tick must be used by a separately validated existing-engine implementation. |
| Source / model | Existing scoped grants; exact fact/citation checks and supported mathematical relations only; unsupported free prose excluded | Phase 7 judge false positives forbid model self-approval. No general semantic or investment-quality qualification. |
| Position / cost | Admission disabled; quantity null; zero positions/fills/orders; ₹0 local inference | Shadow evidence does not authorize paper or broker trading. No slippage, sizing or returns assumption is invented. |

Decision order is existing D3-05: missing required input → INSUFFICIENT_EVIDENCE; otherwise verified adverse input → AVOID; otherwise all technical conditions → BUY; otherwise WATCH. Every result remains NON-ACTIONABLE. The proposal cannot remove the existing `real_swing_instrument_settings_unavailable` gate.

## Evidence, consequences and approval state

The existing engine, schemas and arithmetic have regression coverage. Actual private INFY evidence supports historical financial reporting and descriptive adjusted-price indicators. Corporate-action scope/completeness, volume basis, risk qualification and real execution settings remain unresolved. No empirical profitability, calibrated edge or owner approval exists.

**Approval state: not requested for immediate activation, not granted.** Approving this proposal would express acceptance of the stated research design only. It would not enable publication until source, action, risk, model and existing D3-09 gates independently pass; it would never enable paper admission or broker orders. Activation requires a separately recorded owner approval and a new immutable approved policy version, after those blockers are resolved. There is no useful activation decision to request while those prerequisites remain missing.

## Phase 9 review — 23 October 2026

Version 2.0.0 and its hash, approval state and parameters remain unchanged. Its one-elapsed-day price cap is unsuitable as the sole freshness rule across weekends/holidays. The existing session calendar supports a separate descriptive comparison to the latest verified closed session; the dashboard now presents that comparison and elapsed age separately. Matching a session does not attest full calendar coverage.

D3-05 currently expresses the policy cap in elapsed days. No approved contract parameter for missed-session tolerance exists, and changing that meaning would require a new versioned strategy contract/policy and regression evidence. The engine's gate is **not** silently relaxed. This proposal is not ready for activation; action/volume, risk, real instrument settings and research qualification prerequisites are still missing. No new owner decision or approval request is appropriate yet. No policy was modified or activated during beta testing.
