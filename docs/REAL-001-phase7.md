# REAL-001 Phase 7 — useful historical financial research

22 October 2026. STK-014/046/048/052/059/060; reuses D3-03/05/06/07/08/09/10.
Continues `feat/stk-014-046-052-060-real-001` from Phase 6 `846f99c` in draft PR #12. Unrelated main-checkout WIP is preserved. No merge, universe expansion or D3-11–13 work.

**Phase 7 historical research acceptance: passed, with narrow model reasoning. REAL-001: PARTIAL.** The genuine report contains non-empty model-selected financial facts and one model-selected directional inference, independently verified against comparable-period calculations. It is not a qualified investment recommendation. Public evidence contains counts, model usage and private-artifact hashes only; provider values, generated claims, local grants and screenshots remain private.

## Zero-claim diagnosis

The three Phase 6 final stored results actually called Ollama and had empty missing/contradiction arrays. Their zero claims were therefore not caused by the missing-evidence short-circuit. Facts and canonical citation IDs were visible in the bounded prompt; no evidence of context truncation was found. The old response contract allowed an empty claims array, the prompt encouraged abstention, and historical reporting shared the investment-assessment envelope. These are observable contract/prompt shortcomings; the model's internal reason cannot be proven.

The opt-in historical mode separates evidence reporting from investment suitability. It recomputes a deterministic catalogue from the immutable retrieved bundle, gives the model a compact latest-period view, and validates each returned claim independently. Invalid claims no longer erase unrelated supported ones. The legacy decision assessment intentionally retains `INSUFFICIENT_EVIDENCE`; non-empty historical claims live in `factual_report`, not in an approved recommendation.

## Genuine execution

Existing privately retained Upstox numerical income-statement, balance-sheet and cash-flow observations supplied 24 consolidated INFY facts across four annual periods. No new issuer PDF/HTML was fetched or represented as accepted. Unknown original publication dates remain unknown; observation and availability clocks and exact revision/locator/fact IDs are preserved. Existing source permissions are rechecked for reading, storage and embeddings. No permission was invented or expanded.

The catalogue contains 44 candidates: the 24 stored facts/calculations and 20 additional deterministic comparisons. Decimal arithmetic validates matching metric, unit, scope and period; growth requires adjacent complete annual periods and a positive base. New comparisons include revenue/profit/operating-cash-flow growth, margin changes and cash-flow ratios. Every calculation preserves its formula and ordered inputs, with full input-fact lineage.

Final actual `historical-factual-1.2.0` results:

| Horizon | Accepted model-selected factual claims | Accepted direction classifications | Rejected claims | Unaccepted prose |
|---|---:|---:|---:|---:|
| Swing | 2 | 1 | 1 | 1 |
| Short-term | 2 | 0 | 2 | 1 |
| Long-term | 2 | 0 | 2 | 1 |

The model selected two comparable growth candidates and classified their direction in the accepted Swing inference. The service separately checked signs, periods and scope, then rendered a canonical sentence. This is narrow structured model inference, not deterministic rendering alone and not general financial reasoning. Short/long-term invalid relation selections were rejected. Incorrect cash-flow factual text failed exact parity in all three runs. Unreviewed positive prose is retained as pending and is not shown as accepted.

## Local models and independent validation

Final generation: installed `qwen2.5-coder:7b`, digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. Three actual calls used 3,312/3,313/3,313 prompt tokens and 1,166/1,165/1,165 output tokens; wall times 42.904/40.617/40.364 seconds. Real retrieval used installed `nomic-embed-text:latest`, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, three calls of 864 prompt tokens, 401/360/345 ms.

A separately executed `qwen2.5-coder:14b` judge was evaluated in earlier trials. It accepted some unsupported prose: **false-positive evidence, not semantic qualification**. It shares a model family and lacks human calibration. An initial 14B generation and an inline review timed out; those failures are retained privately. Current conservative screening rejects unsupported causal, quality, valuation and forward assertions, and mathematical directional entailment is checked independently. No uncalibrated judge can qualify publication. No new model was downloaded; calls ran sequentially with unloading and bounded model/context/output/time/account limits. The explicit optional 10 GB model-file limit allowed the installed 14B trial; the default remains 6 GB. Peak total RAM was not measured.

Four validation layers remain distinct:

1. Exact financial text, values, units, periods and scope against recomputed candidates.
2. Canonical citation membership, exact ordered IDs and source locators from the retrieved immutable bundle.
3. Independent deterministic directional entailment; separate free-prose judge evaluated but unqualified.
4. Investment qualification blocked by `research_only`, missing policies and other existing gates.

## Risks and readiness

Cash-flow components match their reported total, but opening-to-closing cash movement does not; reconciliation items are unavailable. No balancing figure or cause is invented. EPS/per-share units, unambiguous total debt/equity, capex, valuation, timely news/events and risk coverage remain insufficient. Numerical secondary-source observations are not an official filing corpus. Historical observations do not establish PIT execution/replay or future returns.

| Horizon | Minimum missing qualification |
|---|---|
| Swing | Price/action and volume qualification, suitable instrument risk inputs, approved/calibrated strategy and risk policies. Existing adjusted candles support only available descriptive indicators. |
| Short-term | Current period-aligned fundamentals, EPS/share inputs, valuation, catalysts/events and risk coverage, approved policies. |
| Long-term | Reconciled cash flow, debt/equity, valuation, sufficient longitudinal business-quality evidence, approved policies. |

Existing versioned Phase 6 policy proposals remain unactivated with no owner approval. No thresholds, calibration or profitability were invented.

## Actual acceptance A1–A9

| Requirement | Observed result |
|---|---|
| A1 Non-empty supported model output | PASS: two validated model-selected facts per horizon and one independently checked model-selected directional inference in Swing. |
| A2 Verifiable citations | PASS: all accepted facts/relations carry canonical source IDs, revisions and locators from real retrieval. |
| A3 Deterministic comparisons | PASS: exact catalogue recomputation and per-claim parity; unsupported cash-flow text rejected. |
| A4 Missing/conflicting evidence | PASS: cash reconciliation, missing financial fields, unknown filing times and news/risk gaps visible. |
| A5 Unsupported statements rejected | PASS: actual invalid financial claims/relations rejected; earlier judge false positives documented; pending prose not accepted. |
| A6 Actual local inference | PASS: real 7B generation, Nomic embeddings and separately evaluated 14B judge; no mocks counted here. |
| A7 Actual dashboard | PASS: no HTTP stubs; all three horizons checked against persisted results, 27 candles, 24 facts, exact accepted text and labels. Zero page errors; screenshot visually inspected. |
| A8 Horizon limits | PASS: all remain INSUFFICIENT_EVIDENCE; policy/financial/market limitations displayed. |
| A9 Publication/tracking controls | PASS: all three real publication attempts fail `factual_research_not_recommendation`; zero recommendations, shadow references/outcomes, portfolios and ledger entries; pending observation work empty. |

The owner-only `phase7-owner-report.md` contains the actual figures, calculated comparisons, accepted claims and all source references. Raw results, browser evidence and failure diagnostics remain in the existing private verification directory. [Redacted execution metadata](../evidence/real-001/phase7-execution.json) provides reproducible hashes and counts without public redistribution.

## Validation and delivery

- Full backend/worker: **653 passed**, one existing Starlette deprecation warning.
- PostgreSQL integration: **167 passed, zero skips**; upgrade, repeat upgrade, downgrade/re-upgrade and atomic failure rollback passed. No schema migration added.
- Contract, evaluation and capital/risk validators passed; script unittest suite: **10 passed**. Historical evaluation fixtures unchanged.
- Frontend production build passed; **five browser regression workflows passed**. Browser regression and genuine acceptance are separate: fixture workflows test UI behavior; the actual INFY browser run above used real private database records.
- GitHub CI for the Phase 6 baseline was confirmed successful before work. The Phase 7 commit's PR checks are reported separately at delivery; local real-provider/model evidence is not CI evidence.
- Paid cost **₹0**. No provider emails, paid API, new model, external deployment, broker action or merge.

Remaining REAL-001 blockers: semantic/business-quality calibration, approved strategy/risk policies, source-qualified financial/event coverage and unresolved financial discrepancies, corporate-action/PIT execution qualification, qualified publication and then genuine prospective acceptance. Useful historical research is now available; end-to-end recommendation acceptance is not complete. Stop after Phase 7.
