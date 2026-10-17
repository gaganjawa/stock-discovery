# D3-07 — Hybrid RAG

Tickets: **STK-052/053/074**. Baseline: D3-06 merge `5be2cac` (PR #6).
Source of truth: [SD ARCH 3.0](SD-ARCH-3.0.md), sections 10.1–10.4.

## Delivered behavior

- Structured retrieval reads D3-06 validated financial facts with explicit metric, period, reporting scope, units, original source locators and derived-fact lineage. `calculate_ratio` uses an isolated Decimal context and produces a hashed calculation record with input references; incompatible inputs fail and missing/zero denominators remain unavailable.
- PostgreSQL full-text search uses an English GIN index. Issuer, listing, document category, mode and exact as-of revision eligibility are applied before search. Current source and identity permissions are checked before content access and rechecked before storing or returning results. Publication/availability/fetch rules remain those of D3-03/06. Latest eligible corrections replace older revisions; stale documents are reported and excluded.
- Provider-neutral local embeddings use Decimal cosine similarity. The supplied frozen synonym-vector mock is a test adapter, **not a qualified financial semantic model**. No model download, API key or paid call occurs. Embed permission is required before source text reaches the adapter and checked again before use. Denial produces an explicit `lexical_only` result and reason.
- Version 1 reciprocal-rank fusion records configuration hashes, raw lexical/cosine scores, component ranks and final scores. Stable ID tie-breaking and primary-source preference make retrieval repeatable. Syndicated text collapses before ranking; individual source attribution and exact excerpts remain available. Conflicting compatible financial facts are retained and block research completion.
- A fixed-RAG provider protocol accepts one fixed bundle and a strict response schema. Citation membership, exact quote support, issuer/horizon, financial values/units/periods/scope and missing/contradictory evidence are checked. Financial claims use canonical factual wording to prevent unsupported prose being attached to a valid number. Inferences are labelled and **not semantically validated**. No tools, agent loop, judge or automatic repair is implemented.
- Missing mandatory evidence and contradictions produce `INSUFFICIENT_EVIDENCE` without calling the research provider. Other valid output remains **shadow/non-actionable WATCH**, with the proposed action retained separately. Paper admission is always blocked. Nothing promotes an existing quant decision or changes synthetic MVP behavior.

## Bounds, persistence and accounting

`RetrievalPolicy` caps source documents (default 30, hard 100), evidence chunks (hard 20) and serialized bytes (default 64 KB). Exceeding input/bundle caps fails closed; chunk truncation is recorded. `allocate_candidates` provides the per-horizon maximum of 10, a configurable event reserve, and explicit omitted candidates. Publication/scheduler integration of this allocation remains a later-package responsibility; single-candidate APIs do not imply full-market research coverage.

`run_research` requires a dedicated idle autocommit connection. It commits an account-locked, idempotent reservation **before retrieval/embedding/research**. The reservation covers conservative UTF-8 byte upper bounds for embedding, prompts and output, and Decimal cost ceilings across run/day/month windows (UTC). Work is rejected before calls if configured bounds cannot fit. All installed adapters are local and zero-cost; accounting reports actual cost zero. Full reservations remain charged against limits, including failures and ambiguous crashes: no automatic release or blind retry. This is deliberately conservative, not a provider billing reconciliation system.

Linux/macOS main-thread workers enforce wall-time interruption with a scoped POSIX timer; late results are also rejected. Other execution contexts fail closed. Installed adapters are trusted code and must not suppress timeout exceptions. The timer is restored after each call. Paid/remote providers are rejected before reservation; adding one requires separate rights, deadline, tokenizer, rate and billing qualification.

Migration **0008** adds the FTS index and immutable bundle, reservation and result manifests. Query, selected evidence, component scores, coverage, omitted requirements, model/prompt/ranking hashes and accounting are persisted. No embeddings are persisted. Retry cache reuse is restricted to the same run identity, model/prompt/configuration, unchanged eligible document set and current rights (including embed rights). A failed or unresolved reservation cannot trigger a second model call. Cache access is through the gated API, not unrestricted direct table reads.

`coverage` measures configured category/metric/text requirements, **not complete news-feed coverage or investment confidence**. Source count counts providers, not syndicated confirmations. Missing adverse-news coverage never becomes “no adverse news.” The mock corpus does not establish semantic quality on real filings.

## Entry points

Modules under `shared/stock_discovery_analysis`:

- `rag_contracts`: strict query, policy, bundle, claim, assessment and budget schemas (`model_json_schema()`).
- `rag_retrieval`: `retrieve`, `calculate_ratio`, `allocate_candidates`, `Embeddings`, `MockEmbeddings`.
- `rag_research`: `run_research`, `ResearchProvider`, `MockResearchProvider`, deterministic validation and budget reservation.

Call `run_research` with a validated `Query`, `RetrievalPolicy`, D3-06 `Access`, an explicit `Budget`, local adapters and a stable scheduler/job-derived `run_id`. Evidence comes from automatic D3-06 ingestion; no manual upload workflow is introduced. The application worker/UI defaults are unchanged.

## Validation and remaining dependencies

Golden cases cover lexical matches, synonym-only semantic matches and no matches, all horizons, stable rankings, precise citations, period/unit/scope traps, source coverage, cutoff/revision isolation, rights denial/revocation, duplicate evidence, missing/conflicting evidence, prompt injection, byte/time bounds, cache identity, crashes/retries, concurrent budget reservations and Decimal cost accounting. Migration lifecycle and regression results are recorded in the [board](SIMPLE-BOARD.md).

Real-source permissions, provider/model qualification and the existing restricted-runtime database-grant blocker remain unresolved. No runtime grants or application database were changed. These tests establish mocked software acceptance only. D3-08 semantic validation/calibrated judge is required before actionable AI; D3-09 owns operational publication/UI integration. Deployment and paid services remain unauthorized. Stop after this PR; do not begin D3-08 without owner confirmation.

Validation on 17 October 2026: 423 application/worker tests (57 new; 105 database cases), 7 script tests, migration lifecycle, historical examples and whitespace checks passed on the isolated delivery snapshot. One existing Starlette/AnyIO deprecation warning remains.
