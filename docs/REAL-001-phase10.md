# REAL-001 Phase 10 — automated private research pilot

24 October 2026 · STK-014/017/028/046/052/054/058/059/060/073 · D3-03–10 reuse.

**AUTOMATED PRIVATE RESEARCH PILOT: PARTIAL.**
**PROSPECTIVE SWING RECOMMENDATIONS: BLOCKED.**
**FULL THREE-HORIZON GO-LIVE: NOT ACCEPTED.**

## Implemented behavior

The existing D3-04 worker resolves a frozen 12-member watchlist, ingests actual prices through D3-03, independently validates financial endpoints into D3-06, executes existing D3-05 assessments for all horizons, prioritizes supported research and runs bounded local D3-07 factual RAG. Durable D3-04 receipts preserve each stock, research intent, result and scan. No new scheduler, publication framework, tables or services were introduced. Existing D3-08 semantic qualification remains mandatory for broader interpretation; the pilot uses its supported factual RAG path and does not activate the judge.

The authenticated homepage opens real research and shows membership, saved scan time, coverage, per-stock errors, horizon priorities, local AI status and cited financial findings. Selecting a company opens its existing detailed research. Synthetic workflows remain explicitly accessible at `/#dashboard`. Refresh and permission denial clear cached scan data; every scan read rechecks current source scopes.

## Genuine watchlist and evidence

The universe is explicitly **LIMITED RESEARCH WATCHLIST**, not a liquidity screen or full NSE scan. Membership is the existing continuity anchor plus the first eleven valid ascending symbols from the actual provider BOD NSE/EQ master. Frozen private evidence records its hash, source time, identity, selection rule, duplicate/invalid exclusions and bounded-out symbols. Current EQ presence supports identity; it does not qualify instrument risk, spreads, volume adjustment or liquidity. Each fetch rechecks the frozen ISIN, preventing silent symbol substitution.

Actual final counts, cutoffs and operational measurements are in [redacted execution metadata](../evidence/real-001/phase10-execution.json). Member identities, values, financial facts, endpoint errors and source revisions remain in the private owner report and acceptance JSON. All twelve real instruments were resolved. The October 23 evening scan had 396 bars through October 22; the October 24 restart obtained the newly available October 23 bars. Earlier immutable observations were retained, not overwritten. Availability lag is observed; the exact provider release time is unknown.

There are 96 validated numerical financial facts across eleven companies; one company has no accepted financial facts. These are permitted secondary annual consolidated numerical snapshots, not original issuer PDF filings. Financial endpoints fail independently on missing fields, unsupported schemas or exact accounting reconciliation. One diagnostic found a 0.01-crore tax residual; its cause is unconfirmed and no tolerance was relaxed. Partial cash-flow/balance-sheet evidence remains usable without pretending that rejected income statements were accepted.

## Quantitative and local AI acceptance

Every company runs all three existing quantitative engines. All 36 assessments remain **INSUFFICIENT_EVIDENCE**, including missing approved policy and eligibility/risk inputs. Supported adjusted-price SMA/EMA, ATR and breakout features are descriptive only. Swing research ranking requires a complete current price window and ranks EMA10/EMA30 spread. Short-term priority uses the minimum of comparable same-period revenue and earnings growth; long-term uses revenue and operating-cash-flow growth. Ties use ISIN. Missing inputs receive no score or rank. Historical growth ranking is not current investment suitability or a BUY signal.

The genuine scheduled pipeline executed installed `qwen2.5-coder:7b` with `nomic-embed-text:latest`. Two new genuine reports each accepted two claims, rejected two unsupported claims/relations and accepted no interpretive relationship. The evening financial candidate and next-morning Swing candidate were different; each had its own real execution. Citation validation was rerun against the immutable genuine bundle. Subsequent equivalent attempts reused the result instead of repeating inference. The 14B judge was not run or approved. Research is sequential, at most one candidate per configured occurrence in this acceptance; ambiguous committed intent prevents automatic duplicate inference after a crash.

## Scheduling and recovery: exact limits

The observed exchange calendar drives existing after-close occurrences, with a 30-minute readiness delay, 15-minute retries and a maximum of three attempts. A shared durable request ledger, account lock and lease checks bound calls across per-stock clients and restarts. The configured calendar covers only through October 30; renewing it and keeping the local worker running remain operator responsibilities.

Actual acceptance includes a late-start scheduled occurrence on October 23, a genuinely timer-triggered second attempt and next-morning restart/catch-up. These are not evidence of a clean future-session unattended launch. The first development attempt failed before provider work because a reconstructed connection string omitted its password; using the existing private runtime setting fixed it. Earlier attempts also encountered lease expiry during large wall-clock gaps. The cause of those gaps is unconfirmed. Added lease checks prevent expired workers from continuing requests. Failed job history remains visible.

The worker was absent at the October 24 inspection; the overnight retry did not run until restart. Original revision/fact/RAG row hashes and source-grant hash survived. Duplicate ticks did not add logical revisions, model results or publications. Missed event windows and the unavailable permitted event feed are explicit. The bounded acceptance worker is stopped after validation, not installed as an unattended operating service. API/dashboard remain local. No OS auto-start, host-sleep reliability, automatic calendar renewal or private-data retention cleanup has been qualified.

Final recovery completed at **04:36:09 UTC / 10:06:09 IST, October 24**: **408 bars (34 per company), 12 current / 0 stale / 0 failed price scans**, 96 facts and all 36 investment assessments insufficient. Financial endpoint failures remain visible despite current prices. Final scan: 69.00 seconds, 46 requests, 369,278,976-byte worker peak RSS. The durable ledger records 194 scheduled requests including interrupted attempts; preparation used 61 and the targeted diagnostic one, **256 total**. End-to-end local research durations were 53.70 and 30.07 seconds; model-only latency and total Ollama peak RAM were not separately measured. Final queue depth is zero. Completion was about 18h36 after the scheduled session close, reflecting provider lag and the stopped worker, not a qualified daily freshness SLA.

## C1–C16 genuine acceptance

| Criterion | Result and scope |
|---|---|
| C1 | PASS limited watchlist identity/provenance; liquidity qualification absent. |
| C2 | PASS twelve actual NSE EQ instruments resolved. |
| C3 | PASS genuine daily prices and accepted financial snapshots persisted. |
| C4 | PASS per-stock current session/gaps evaluated; evening stale state and next-day catch-up retained. |
| C5 | PASS all three engines for twelve companies; all abstain as investment assessments. |
| C6 | PASS deterministic research priorities; missing inputs are not ranked as weak performance. |
| C7 | PASS actual installed 7B/Nomic execution for a supported historical financial candidate. |
| C8 | PASS four accepted claims across two reports revalidated against actual immutable evidence; rejections retained. |
| C9 | PASS genuine authenticated twelve-stock browser workflow, selection, research, refresh and logout; no HTTP mocks. |
| C10 | PASS actual per-endpoint failures isolated; other stocks and valid endpoints persist. |
| C11 | PASS duplicate occurrence/ticks preserve receipts and logical revision uniqueness; zero publications, not a claim of qualified publication deduplication. |
| C12 | PASS bounded actual restart/catch-up and immutable history; unattended continuity remains PARTIAL. |
| C13 | PASS current grants unchanged and request budgets enforced. No restricted corporate-action acquisition. |
| C14 | PASS zero recommendations, references, outcomes, portfolios and ledger entries. |
| C15 | NOT APPLICABLE / BLOCKED: qualification never passed; no shadow reference created. |
| C16 | PASS genuine API/frontend/worker restart, saved research visible, prior row hashes unchanged. |

## Source, policy and go-live blockers

Existing private numerical-data permission evidence remains unchanged. [Official instrument documentation](https://upstox.com/developer/api-documentation/instruments/) supports master interpretation. [Corporate-action documentation](https://upstox.com/developer/api-documentation/get-corporate-actions/) defines fields, not permission or complete coverage. The [official clarification thread](https://community.upstox.com/t/clarification-on-upstox-historical-candle-v3-private-research-data-retention-and-corporate-actions/18014) provided an acknowledgment, not affirmative coverage/rights evidence in the recorded investigation. Corporate-action scope remains blocked before network. No approval was invented.

Split/bonus-adjusted candles retain their existing classification. Raw execution, historical PIT performance, volume adjustment, complete action dates/factors and dividend effects remain unqualified. Current earnings/events, original publication times, sector-specific statement coverage, valuation and instrument risk are incomplete. [Policy 2.0.0 review](REAL-001-phase8-policy-decision.md) remains unchanged, unapproved and unactivated. Levels 1–2 factual/quantitative research do not satisfy Levels 3–4 publication/admission. No entry/exit prices, positions, orders, returns or future outcomes were fabricated.

## Validation and delivery boundaries

Full backend/worker suite: **679 passed**. PostgreSQL integration: **170 passed, zero skips**. Migration upgrade/repeat/downgrade/re-upgrade/atomic failure rollback passed. Three contract/evaluation/risk validators, ten script tests and frontend production build passed. Six browser fixture workflows passed; genuine browser acceptance above is separate. Fourteen final targeted tests passed after the scan reader changes. One existing Starlette deprecation warning remains.

The full suite passed on a freshly migrated disposable test database. A preceding repeat on a retained database exposed stale experiment jobs; resetting only that disposable database resolved the environment collision. A fixture browser attempt reached the legitimate login limit; the added render-only test now uses fixture bearer authentication without changing authentication controls.

Exact Phase 10 commit CI is reported at delivery, not inferred from baseline Phase 9 CI. No provider payloads, keys, private values or research prose are included in public evidence. Unrelated main-checkout WIP is preserved. Draft PR #12 stays unmerged. ₹0 paid services, no downloads/cloud AI/deployment/provider messages. **Stop after Phase 10; REAL-001 remains PARTIAL.**
