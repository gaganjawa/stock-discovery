# REAL-001 — real integration acceptance record

**Current — Phase 7, 22 October: useful historical research accepted; REAL-001 PARTIAL.** [Phase 7 A1–A9 and execution](REAL-001-phase7.md). Genuine local 7B/Nomic runs yielded two validated financial claims per horizon and one verified model-selected directional comparison in Swing. Actual dashboard acceptance passed. Free-prose semantic qualification, approved policies and recommendation publication remain blocked; no prospective record or position exists. Earlier phase records below are historical.

**Historical Phase 6, 21 October: PARTIAL.** [Grounded research and publication readiness](REAL-001-phase6.md). Genuine Upstox observations remain privately stored: 27 explicitly adjusted candles, three numerical financial snapshots and 24 facts. Three final local Ollama horizon runs passed deterministic validation but emitted no claims and abstained; semantic qualification and approved real policies remain absent, so no publication or prospective reference exists. The phase records below preserve earlier acceptance and its then-current blockers.
Phase 5 final checks: 617 backend/worker tests and 164 PostgreSQL tests (zero skips) passed; actual fact-only Ollama parity passed, broader research failed citation validation; all three actual publication attempts remain blocked by `real_policies_required`. See [Phase 5 evidence](REAL-001-phase5.md).

**Phase 4 update (20 October):** [Permission findings and stop condition](REAL-001-phase4.md). New Upstox developer-community evidence confirms private market-data storage, research/ML and replay, superseding the earlier blanket rights blocker. Financial/news corpus rights remain unresolved; private market-data research outputs and evaluation fit the confirmed research scope. Historical candles are back-adjusted, conflicting with the current raw-data representation. No financial document or actual research was processed; no infrastructure was added. REAL-001 remains PARTIAL.

**20 October 2026 · PARTIAL · not end-to-end acceptance.**

**Phase 3 update:** [Detailed acceptance and blockers](REAL-001-phase3.md). Conditional real D3-09 publication, immutable shadow references/observation receipts and dashboard history are implemented. Actual INFY A1–A14 acceptance remains blocked; no genuine filing/facts, grounded research, real publication or outcome was produced. Local validation: 606 tests, 164 PostgreSQL integration cases (zero skips), five browser workflows, migration checks and build passed. The historical records below remain Phase 1/2 evidence.
**Phase 2 update:** See [Phase 2 progress](REAL-001-phase2.md) for the newer conditional filing/RAG/company-view implementation and its separate validation. The record below preserves Phase 1 actual execution. Phase 2 validation: 601 tests, 163 PostgreSQL cases (zero skips), five browser workflows and frontend build passed. Overall acceptance is still PARTIAL.

Baseline: D3-10 merged PR #11, `a0846b5`. Existing unrelated WIP preserved.
Tickets: STK-004–007/014/015/046/048/052/059/060; reuses D3-02/03/04/06/07/08/09/10.
No D3-11, D3-12 or D3-13 work is included.

## Actual execution, distinct from contract tests

| Requirement | Actual result |
|---|---|
| Resolve actual NSE security | **Passed API probe:** Upstox JSON master resolved INFOSYS LIMITED, INFY, ISIN INE009A01021, instrument key NSE_EQ\|INE009A01021. |
| Retrieve actual daily OHLCV | **Passed read-only access probe:** 11 daily records, 1–16 October 2026. Source values were not persisted. No full history/completeness/adjustment qualification is claimed. |
| Calendar | Actual market-timings GET for 16 October returned one NSE session. Full dated calendar ingestion remains unwired. |
| Financial information | Actual consolidated annual income-statement, balance-sheet and cash-flow API responses returned success with crore units. Only availability metadata retained; no financial facts stored. |
| Genuine filing ingestion | **Not passed.** No approved real HTML/PDF filing has passed D3-06 extraction/storage. One SEC companyfacts request returned HTTP 403; access controls were respected. |
| Events/news | News GET returned 10 items. No text retained, event classification or event-triggered reassessment demonstrated. No official announcements feed integrated. |
| Quant on actual stock | **Not demonstrated.** Existing three engines are preserved. Actual prices have not been admitted to their frozen research inputs. |
| Genuine local inference | **Passed bounded protocol smoke:** qwen2.5-coder:7b, 217 input / 106 output tokens, 11,643 ms adapter wall time. Exact source-quote and citation parity plus abstention checked. **Financial qualification remains unqualified.** |
| Genuine local embeddings | **Passed:** nomic-embed-text:latest, 25 input tokens, 768 dimensions, 875 ms wall time. No semantic retrieval quality claim. |
| Actual RAG citations | Local model copied a verified excerpt/citation from the Infosys 2025 SEC 20-F. It was supplied to the smoke request, **not automatically ingested or retrieved by hybrid RAG**. End-to-end RAG acceptance remains blocked. |
| Dashboard | Existing frontend extended with authenticated REAL RESEARCH and all three horizon tabs. Shows explicit blocked states, no invented chart, company metrics, entry/exit terms or recommendations. Synthetic demo and existing forward-paper controls remain separate. |
| True publication clock | No real research published. Existing synthetic publication unchanged; no backdated prediction created. |
| Prospective tracking | **Not connected for real observations.** D3-10 gates unchanged. No research-only output admitted as a paper position. |
| Eligible later outcome | **None exists.** No future-performance or maturity claim; no synthetic outcome presented as real. |

Machine-readable evidence, including actual fetch timestamps and endpoint URLs:

- [Market access probe](../evidence/real-001/upstox-access.json): 03:33:09–03:33:10 UTC / 09:03:09–09:03:10 IST.
- [Financial/news access probe](../evidence/real-001/upstox-financial-access.json): 03:34:23–03:34:25 UTC / 09:04:23–09:04:25 IST.
- [Ollama execution](../evidence/real-001/ollama-smoke.json): started 03:25:38 UTC / 08:55:38 IST.

Generation digest: `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`.
Embedding digest: `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.
Installed inventory also contained qwen2.5-coder:14b and qwen3-coder:30b; neither
was executed. llama3.1:8b was **not** in the actual installed inventory. Native
Ollama 0.32.11 used the owner's mounted T9 model folder. No model was downloaded.
The adapter caps model bytes, context, request/output size and deadlines and
unloads after calls. Peak combined system memory was not measured; comfortable
concurrent resource qualification is not claimed.

## Implemented slice

- Read-only Upstox instrument/daily-price adapter using documented endpoints,
  exact NSE EQ resolution, bounded payloads, safe errors, conservative process
  quotas, decimal validation, observed clocks and approved-calendar enforcement.
- Optional incremental price ingestion through the existing D3-02 grant and
  D3-03 revision/page/checkpoint storage. Seven-day correction overlap; unchanged
  inputs reuse their first observation, revised content appends. Configurable
  1–100 symbols; this is **not** liquidity screening or 100-company acceptance.
- D3-04 opt-in price-stage handler. Missing rights/credentials block; downstream
  snapshot/research/event stages explicitly block on unqualified policy. No
  recurring real schedule was activated or asserted successful.
- Local Ollama implementations of the existing research, embedding, agent and
  judge protocols. Model digest pinned before/after requests; no cloud fallback,
  model pulls or qualification promotion. Existing validators retain authority.
- Bounded, exact-table HTML extraction into D3-06 `StructuredReport`, with original
  locators, units, period/scope configuration and explicit unknown values. Ambiguous
  or merged tables fail. Tests use fabricated HTML; no real parser qualification.
  PDF/OCR remains unsupported, not a successful empty extraction.
- Authenticated real-readiness API and explicit blocked-state React view.

## Validation

- Full backend/worker regression: **585 passed**, PostgreSQL enabled, zero skips.
- Migration validator: **162 PostgreSQL cases passed**, zero skips; upgrade,
  repeat upgrade, downgrade, re-upgrade and atomic failure rollback passed.
- New adapter/parser tests: permission denial before network, exact identity,
  invalid/missing sessions, provider errors, revision preservation, grant revocation,
  incremental database storage, synthetic schedule rejection, Ollama digest drift,
  truncation, malformed vectors, context bounds and API auth/mode isolation.
- Script tests: **10 passed**; three historical contract/example validators passed.
- Frontend production build: passed.
- Browser workflows: **4 passed** (35.4 seconds): discovery, paper portfolio,
  real-mode isolation/authentication and replay/scorecard. The first launch lacked
  the matching browser; its downloaded runtime was unpacked and all checks rerun.
- A later regression rerun reused browser-seeded records and failed isolation
  assertions. A separate database name was rejected by the validator safety guard.
  The task-owned disposable `stk013_test` was then recreated with test services
  stopped; final regression and migration results above use that clean database.
- Existing D3-10 admission, portfolio, observation and outcome regressions passed.
- No new database schema is required for this slice. No historical fixture changed.

## Costs, secrets and remaining work

Service/subscription/model-download cost: **₹0**. Existing Mac, native Ollama,
Colima and a disposable local PostgreSQL container were used. A free PostgreSQL
image and browser test runtime were downloaded. No cloud deployment or broker order.

The owner initially placed the Analytics Token in the main checkout's `.env.example`.
It was moved to an owner-only file outside all Git checkouts and the example value
was cleared; the token was absent from both HEAD and Git's index. No secret is in
these records, commits, output or PR. Only that requested credential setting was
changed in the main checkout; unrelated WIP remains untouched.

See [provider matrix](REAL-001-provider-matrix.md) for source permissions and the
minimum remaining owner action. Permissions alone do not finish this feature:
calendar/action/financial-document/news adapters still need integrated acceptance,
real inputs must reach all three existing quant/research paths, real immutable
publication must use its true clock, and real shadow forecasts must connect to
subsequent observations without weakening D3-10. Qualification, 50–100-company
coverage and complete unattended operation remain outstanding.

**Overall REAL-001 remains PARTIAL.** This slice is suitable for review as an
unactivated integration slice, not as a working actual-stock research application.
