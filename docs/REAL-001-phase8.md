# REAL-001 Phase 8 — Swing qualification, prospective signal blocked

22 October 2026 · STK-014/028/046/052/054/058/059/060 · **PARTIAL**.
Baseline `5ee88e2`; existing REAL-001 branch and draft PR #12. No new recommendation framework, universe expansion, merge or D3-11–13 work.

## Repository and CI synchronization

Local HEAD and the remote feature ref both resolved to `5ee88e21d521a1b1af10a17769e4b659acdc2450` before changes; the feature worktree was clean. Unrelated main-checkout WIP remained untouched. GitHub's branch-ref API also returned that SHA, but the PR head, PR commit list and `refs/pull/12/head` still resolved to `846f99c`. No Actions run or check run existed for `5ee88e2`. The PR remained open/draft and its body could be updated, so this is not merely the UI displaying an old check. The exact server-side cause is unconfirmed; no history rewrite, force push, close/reopen or PR recreation was attempted.

The unchanged Phase 7 baseline was retested locally: **653 passed**. This is local baseline validation, not GitHub CI acceptance. Phase 6's green run cannot validate Phase 7 or Phase 8. PR synchronization remains an external delivery blocker; the final pushed SHA/check state is reported at delivery.

## Actual market coverage and safeguards

Permitted Upstox requests refreshed dated NSE sessions and INFY identity/prices using the existing scoped private grant. D3-05 needs 30 complete sessions: EMA30 needs 30, SMA20 needs 20, ATR14 needs 14 and prior-20 breakout/relative-volume calculations need 21. No indicator was added solely for appearance.

A bounded larger refresh yielded **33 actual daily candles** with one coherent observation/adjustment anchor, verified INFY EQ identity, no duplicate bars and no internal gaps against the observed calendar. The endpoint's final window was 2 September–22 October; the last returned candle was **21 October**, while the calendar confirmed **22 October's closed session**. That missing latest bar and an age greater than the proposed one-day cap remain explicit. An earlier narrower refresh had 30 bars but stopped its calendar at yesterday; current-date calendar ingestion is now fixed. It can observe today's session before close, but price ingestion still excludes unclosed sessions. All revised adjusted observations append through existing D3-03 storage.

Existing D3-05 functions calculated actual SMA20, EMA10, EMA30, ATR14, prior-20 high and support. The private report gives their exact values and comparisons. They describe the last available observed window; they are not a current trade signal. A missing session inside that window suppresses indicators; a missing later session preserves historical descriptive values while explicitly failing freshness. Relative volume remains unavailable because provider volume adjustment semantics are not established. No new standalone momentum or volatility engine was added; EMA comparisons and ATR retain their existing meanings.

Corporate-action access under the configured local grant fails **`scope_denied` before network**. Existing scopes do not include `corporate_actions`; no scope was relabelled or approval invented. The official [corporate-actions API](https://upstox.com/developer/api-documentation/get-corporate-actions/) documents ex/effective dates, but endpoint existence is not a grant or a completeness guarantee. Split/bonus effective-date coverage, dividend effects, action factors and volume semantics remain unqualified. Back-adjusted OHLC remains excluded from raw execution inputs and historical PIT acceptance.

## Financial and AI validation

The 24 genuine consolidated numerical facts and four-period Phase 7 report are preserved. A permitted new [key-ratios API](https://upstox.com/developer/api-documentation/get-key-ratios/) request returned seven entries. Its response did not supply the reporting-period, scope and price-as-of metadata needed for an independent join, so **zero new verified financial facts** were added. Ratios were not used to infer EPS, shares, debt/equity or valuation. Cash reconciliation and original publication-time uncertainty remain unresolved. No copyrighted PDF corpus or news body was downloaded.

Saved actual Qwen 7B/Nomic outputs were re-evaluated against immutable genuine PostgreSQL bundles, not replaced by new mock generation. All six accepted factual claims and the one supported Swing direction relation revalidated; all five previously rejected model claims/relations remained rejected. Twelve explicitly constructed adversarial probes across the three bundles rejected wrong-year text, unsupported management causality, valuation and no-risk assertions. These probes are validator tests against real evidence, not additional model responses. No new inference/download was necessary. Prior separate 14B judge false positives remain documented evidence against broad semantic qualification; the judge does not qualify itself.

Historical fact correctness, mathematical interpretive support, strategy approval and investment qualification remain separate. Useful factual research survives, while unaccepted prose cannot support publication.

## Policy and executed assessment

The [single decision record](REAL-001-phase8-policy-decision.md) provides exact proposed thresholds, reasons, consequences and approval state. Its [existing-schema manifest](policies/real-swing-proposed-2.0.0.json) is version `2.0.0`, **unconfigured**, with null approval reference. Proposed holding/forecast are three sessions, entry window one session, price/coverage freshness one day, and at least 30 complete bars. Existing EMA/breakout/relative-volume rules are explicitly proposed for review, not described as empirically profitable. Risk, liquidity, source and model controls remain mandatory. Loading the proposal for display does not activate it.

The real D3-05 Swing execution returned **INSUFFICIENT_EVIDENCE**, with exact engine reasons `policy_not_configured` and `eligibility_or_instrument_risk_unavailable`. Additional readiness blockers are the missing latest session, unqualified action/volume basis, absent verified event/filing completeness and future horizon calendar, and missing real instrument-specific execution settings. D3-05 retains `real_swing_instrument_settings_unavailable`; its synthetic tick/entry geometry is not silently enabled for INFY. No unsupported entry/invalidation price is issued. Missing long-term valuation was not introduced as an extra Swing engine requirement.

The actual D3-09 attempt rejected the latest research with **`factual_research_not_recommendation`**. This is the first encountered gate, not the sole unresolved condition. There are zero real recommendations, D3-10 prospective references/outcomes, portfolios and ledger entries; pending observation work is empty. **B9 did not pass.** No future performance was fabricated.

Short-term still lacks current period-aligned fundamentals/EPS/shares, valuation, catalyst/event and risk coverage. Long-term still lacks reconciled cash flow, debt/equity, valuation and sufficient quality/business coverage. Their historical reports remain available; neither was forced into publication.

## Dashboard and acceptance

The existing Real Research view now shows coverage count and warm-up requirement, latest verified session versus latest candle, missing/unverified sessions, age eligibility, action/volume/PIT limitations, policy version/status/approval and publication state. Historical factual research, research-only assessment, qualified shadow recommendation and paper position are explicitly distinct.

The genuine local browser used no response mocks: 33 candles, 24 financial facts, all three historical research tabs, exact blocked latest-session state and unapproved proposal were checked; zero page errors. The screenshot was visually inspected. Actual values and screenshots are private.

| Acceptance | Result |
|---|---|
| B1 | Investigated; feature/pull-ref mismatch persists and CI is not claimed. |
| B2–B4 | Genuine 33-bar coverage evaluated, safeguards retained, eligible descriptive indicators calculated; latest session missing. |
| B5–B6 | Real claims/citations revalidated; unsupported actual model statements and separate adversarial probes rejected. |
| B7 | Exact versioned Swing proposal prepared, unapproved and unactivated. |
| B8 | Actual engine executed; INSUFFICIENT_EVIDENCE with exact qualification reasons. |
| B9 | **BLOCKED, not passed:** no qualified publication/prospective reference. |
| B10 | No recommendation, position, fill or outcome fabricated. |
| B11 | Genuine dashboard acceptance passed. |
| B12 | Existing rights, safety, separation and ₹0 constraints retained. |

## Validation and delivery

Full backend/worker: **658 passed**. PostgreSQL integration: **168 passed, zero skips**. Migration upgrade/repeat/downgrade/re-upgrade/atomic rollback passed; no schema change. Contract/evaluation/risk validators and ten script tests passed. Frontend production build passed. All five browser fixture workflows passed after resetting the isolated fixture database; an initial source-inspection failure from retained test state is recorded in private logs. These fixture results are separate from genuine acceptance. One existing Starlette deprecation warning remains.

[Redacted execution metadata](../evidence/real-001/phase8-execution.json) retains counts, statuses and hashes. The private `phase8-owner-report.md` contains actual indicators, financial context, cutoff, source lineage and assessment detail, with private JSON evidence. Local successful tests are not GitHub CI success. No paid API, provider email, download, external deployment, broker action, merge or new framework. **REAL-001 remains PARTIAL; stop after Phase 8.**
