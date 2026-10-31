# AI research implementation plan

Owner-authorized roadmap, 31 October 2026. Existing architecture and ticket IDs remain authoritative. No real-money execution.

## Current checkpoint

M0 merged via PR #19 at `f409bca866bb906121438b45f18a0876cbae72bf`, with all required CI successful for `c9d8df1`. Focused review found no substantiated additional P1/P2 findings. The corrected three P2 areas retain typed filing classification, strict real BUY geometry and authorized historical/current identity dependencies. Previous executed results: 705 backend/worker, 414 PostgreSQL (zero skips), 56 STK-079 database/API, 114 focused, 13 script tests; migrations and three contract validators passed. These overlapping results were not rerun for delivery.

Main protection was enabled with explicit owner approval: GitHub Actions `checks`, strict up-to-date branch, PR merges, administrator enforcement, no force pushes/deletions. CI and merge evidence must be recorded after execution.

## Fixed milestones

### M0 — Close STK-079
Review corrected stored-evidence swing integration, deliver PR, required CI and verified merge.
Status: complete; PR #19 merged and main ancestry verified.

### M1 — Establish real research data
One authorized NSE instrument with traceable prices/documents and point-in-time availability.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M2 — AI company research
Cited structured company research with independent deterministic claim verification and preregistered quality evaluation.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M3 — Quantitative strategy evaluation
Deterministic baseline and hypothesis-driven improvements evaluated without tuning frozen holdouts.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M4 — Combined research recommendation
Versioned synthesis of verified AI and technical findings with deterministic risk vetoes.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M5 — Historical replay and ground truth
Freeze as-of research, reveal subsequent outcomes and compare baselines with leakage controls.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M6 — User-facing dashboard
Research, bounded discovery and historical replay usable through existing React application.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

### M7 — Product acceptance
Separate synthetic software evidence, real-data acceptance and measured research quality.
Status: pending; reuse completed infrastructure before filling demonstrated gaps.

## Safety and external blockers

Source grants do not establish provider policy. Missing rights, retention/deletion support, raw-price semantics, current instrument settings or complete filing/event coverage remain insufficient evidence. No synthetic fixture establishes real qualification or profitability. Human-reviewed reference labels, predefined thresholds and untouched holdouts are required for research-quality acceptance. Publication, paper admission and live trading stay blocked.

## Continuation

Read `AI_RESEARCH_PROGRESS.json`, actual Git state and PR checks first. Record files, actual tests, commit/PR/merge, blockers and exact next step at each milestone. Do not repeat expensive completed tests without a new reason.

## Current independent work while M0 CI runs

M1 source inspection is recorded in `AI_RESEARCH_DATA_ACCEPTANCE.md`; actual data acceptance remains blocked, not complete. Existing RAG, financial candidate verification, agent and replay engines must be reused for M2–M5. Existing Phase 7 local model evidence is narrow factual/directional reasoning; it is not general financial qualification. Human-reviewed labels and a fixed evaluation policy are still needed before research-quality holdout evaluation.

The first M6 screen is implemented locally using the STK-079 authenticated swing endpoint. Production build and two synthetic desktop/mobile browser cases passed. It clears old results on cutoff changes, refresh, navigation and denied reads. It neither acquires market data nor invokes inference itself. Full AI synthesis, discovery ranking and historical freeze/reveal UI are not completed by this screen. Its delivery must use a separate branch/PR after M0.

## Delivered checkpoint and next increment

PR #20 merged at `907849399be33a0a6d178212b64b151de62320e9` with required checks passing. The first M6 screen is delivered; the full milestone remains partial. M2's next bounded increment uses existing fixed-RAG to select and independently match exact source excerpts, alongside verified financial facts. It does not establish event truth, news completeness or semantic quality. See `STK-052-source-excerpts.md` for validation, including the failed full-suite lock timeout and unchanged isolated rerun. Exact-commit CI/lifecycle remain required before merge.

## PR21 review and M2 structured extraction

PR21 merged at `831feb0` after a reproduced alias-citation P2 was corrected in `8b429cd`; required CI passed including all 417 PostgreSQL cases and lifecycle checks. The original `386ff5e` run was cancelled by the correction push, not a successful pinned run. Historical local lock-timeout cause remains unresolved; a deterministic timeout/rollback probe now passes.

The next increment wires structured model proposals from source passages into the existing factual worker, independent stored-fact/passage/unit/period/entity/conflict checks and company report. It supports a narrow explicit row grammar and does not qualify arbitrary filings. A ten-case synthetic development review packet is prepared with null human labels; proposed thresholds and denominators are fixed before holdout use. No actual model ran because local Ollama/T9 are unavailable. Real research quality remains partial and unmeasured.

## PR22 delivered; actual development inference and optional runtimes

PR22 merged at `f05d329` after exact-commit checks passed (419 PostgreSQL cases, zero skips; migration lifecycle passed). Configurable runtime selection now supports Ollama or explicitly installed/hash-pinned offline llama.cpp; lexical retrieval removes the embedding-runtime requirement. Native CLI operational acceptance is still pending.

The external SSD became available and two actual qwen2.5-coder:7b calls ran against invented normalized disclosure rows. First output was fully rejected; a scoped prompt clarification (new hash, unchanged verifier) produced two accepted financial rows and one rejected invented candidate. All attempts and usage are retained. These are development observations only. Ten provisional developer-labelled cases and an empty independent holdout registration do not establish human quality acceptance. Runtime was temporary and stopped; no genuine NSE source was activated.

## PR23 merged; representative-source M2 benchmark

PR23 merged at `103f5ff` after exact-commit CI passed (421 PostgreSQL cases, zero skips, migration lifecycle). The next [table-span development increment](STK-052-financial-span-evaluation.md) used actual local inference on a disclosed public SEC Infosys excerpt, plus explicitly synthetic conflict mutation. Coding and general-instruction candidates each extracted **0/2** supported cells in the original run; a two-call serialization diagnostic did not recover extraction. Failed outputs, model/prompt versions and all denominators are retained. API cost USD 0; 200000 reserved units exhausted without reset/refund.

M2 development readiness **NOT PASSED**, independent human quality acceptance **UNAVAILABLE**. This is neither genuine NSE qualification nor held-out acceptance. The original ten cases and empty human holdout registration remain unchanged. Next: source-column extraction/structured-output diagnosis on development evidence and independent human reference review. Do not advance M3–M7 before the M2 acceptance gate. No publication, paper admission or trading.
