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

M2 hybrid development: PR24 merged (`e7523bb`), exact CI passed. [Hybrid evaluation](STK-052-hybrid-financial-selection.md) recovered coder positive cells 2/2 with contract validity 4/4; model negative abstention remains 0/2, VL extraction 0/2. Application rejects unsupported selections. Independent human review packet prepared, labels null. M2 PARTIAL; no advance to combined recommendations/replay. Original results preserved.

M2: PR25 merged (`2607e09`) after exact-commit CI/review. [Explicit abstention experiments](STK-052-financial-abstention.md) improve coding-model negatives 0/2 → 2/2 but regress positives 2/2 → 1/2 in both v3/v4. All failures and prior runs preserved; no further VL inference. Independent reviewer/holdout absent: M2 gate BLOCKED. Reviewer worksheet prepared; combined recommendations/replay remain gated.

M2: PR26 merged (`54b27de`), all required checks passed including 429 PostgreSQL cases and lifecycle. [Exact selection](STK-052-exact-financial-selection.md) replaces unnecessary model choice for unambiguous row/period/scope: 2/2 positives, 2/2 deterministic abstentions, zero inference. Human source review and unseen 50-case quality gate remain BLOCKED; 50 blank allocation slots contain no labels/evaluation evidence. No milestone promotion.

Latest owner instruction supersedes the earlier pause on M3–M7 implementation:
independent **non-actionable product development** may proceed while M2 external
review is blocked. Acceptance dependencies are unchanged. PR27 merged at `ceacc432`
after exact `c1d8bf3` CI/review (431 PostgreSQL tests, zero skips, migration lifecycle).
The [combined company research increment](STK-052-054-combined-research.md) connects
existing technical and factual research to the company API/UI, and exposes explicit
financial-evidence gaps in existing synthetic freeze/reveal. It does not accept M2,
promote recommendations, or claim combined historical performance. The external
review worksheet is finalized; no unseen cases, labels or threshold approval exist.

PR28 merged at `db61f7c` after exact `d63f784` unit/postgres/ui/checks passed,
including 442 PostgreSQL tests and migration lifecycle. Fresh review found no P1/P2.
The next [STK-037/043/059 vertical slice](STK-037-043-historical-evidence.md) freezes
full fictional financial/technical evidence in existing immutable replay manifests,
renders the known-at-cutoff evidence, and reveals the separate technical baseline
outcome. AI attachment requires explicit contemporary completion evidence; none is
invented for today's cached runs. Combined paired metrics remain unavailable and
M1/M2 acceptance stays blocked. This advances product development, not promotion.

PR29 merged at `466de933` after exact `acd827d` checks passed (461 PostgreSQL cases,
zero skips, lifecycle and 12 browser tests). The original `de28d4c` browser failure
was reproduced as HTTP429 on the sixth same-peer login; test-session isolation fixed
it while retaining UI login/security coverage and all production throttles.
The [STK-043/059 saved-replay dashboard](STK-043-059-saved-replay-dashboard.md) adds
bounded history discovery, exact reopening, side-by-side evidence, a cutoff chart
marker and existing-worker financial batches. Paired AI metrics stay unavailable.

PR30 merged under protected main at `7f87b1c` after exact `bcb51e6` unit/postgres/
ui/checks succeeded. Fresh source review found no P1/P2 in saved authorization,
stable pages, immutable reopening, idempotent batches or future separation.

The next bounded [STK-058/059 dashboard increment](STK-058-059-product-acceptance.md)
exposes **existing** frozen ranking components and compares up to four fictional
companies within one batch/horizon/research arm. It does not add a score or engine.
The same record audits existing strategy/replay acceptance against original tickets
and separates synthetic end-to-end coverage from genuine data requirements. The
[M1 checklist](AI_RESEARCH_DATA_ACCEPTANCE.md) now names exact missing rights,
retention, sources, timestamps and raw price/volume semantics. Independent M2
review and the unseen 50-case holdout stay BLOCKED, with prior artifacts unchanged.
No additional four-example model run or infrastructure experiment is justified.

PR31 merged under protected main at `6d6a2c8` after exact `a0ee567` CI attempt 2
produced unit/postgres/ui/**checks** success. The initial completed constituent
jobs lacked the required aggregate; no protection bypass was used. Fresh review
found no P1/P2 in ranking, scopes, permission checks, leakage or immutability.

M3 now integrates the existing evaluator/portfolio/split contracts into a
[read-only performance screen](STK-041-042-performance-evaluation.md): explicit
observations/denominators, descriptive risk ratios, costed fictional benchmark,
purged partition outcomes and stable evidence identity. Missing data remains
unavailable. Registered untouched walk-forward, genuine benchmark/strategy
acceptance and independently qualified AI pairs are not fabricated. Existing
D3-11 and Experiment governance remain the preregistered path.

PR32 merged under protected main at `f172a28` after exact `02af305` CI passed:
790 unit, 482 PostgreSQL (zero skips), lifecycle and 13 browser workflows. Fresh
review reproduced/fixed a P2: late-disclosed in-window actions must be checked at
the recorded outcome knowledge cutoff, not merely the observation end. The original
`eb6dca1` was superseded; it is not the final accepted commit.

STK-041/042 now adds [registered fold reporting](STK-041-042-registered-folds.md) to
the existing governance API/Scorecard. It reads sealed versioned trials and pinned
ledger outcomes with current source authorization, no holdout reservation/evaluation,
strict phase/configuration separation and no compounding of separate portfolios.
Failed, pending, missing and immature evidence stays visible. The
[remaining product acceptance handoff](PRODUCT-ACCEPTANCE-HANDOFF.md) audits actual
workflow boundaries and gives the minimal M1/M2 owner/reviewer inputs. It identifies
the remaining Discovery-to-history identity link without fabricating shared data.

PR33 merged under protected main at `8d336486` after exact `74d7b15` unit,
PostgreSQL, UI and aggregate success. Fresh correctness review found no confirmed
P1/P2 in frozen lineage, source restrictions, phase isolation, overlap aggregation
or read-only reporting; four focused aggregation tests passed again.

STK-043/059 now connects [Discovery to its actual saved records](STK-043-059-discovery-history.md):
immutable publication history, explicitly revealed pinned portfolio outcomes and
existing trial registration links into Scorecard. No legacy dataset mapping, new
evaluation or inference is implied. Missing and revoked relationships stay unavailable.
After this software increment, the existing M1/M2 handoff, genuine evaluation and
supervised operational acceptance remain the identified gates; no unrelated
infrastructure or repeated model experiment is scheduled.

PR34 merged under protected main at `63e2cfcc` after exact `27b0ffc` unit,
PostgreSQL, UI and aggregate success and independent source review. The final
bounded synthetic product audit found no demonstrated missing software capability
requiring another feature. Exact CI confirms 794 unit, 516 PostgreSQL (zero skips),
migration lifecycle and 14 browser workflows. No new P1/P2 correction was needed.

Primary focus returns to M1 under existing STK-004/005/007/014: reconcile the saved
private Upstox scope with raw Swing requirements; obtain one permitted raw INFY
price/volume/action packet and original disclosures with truthful availability
and retention evidence. The [handoff](PRODUCT-ACCEPTANCE-HANDOFF.md) distinguishes
existing file-level permission, public-source candidates and unverified policy.
New source activation is not authorized. M2 independent review/50-case holdout,
genuine strategy/benchmark/forward, operational and trading gates remain blocked.

2 November M1 decision checkpoint: the five pending PR34 closure documents were
committed at `860e06b`; production code and frozen evaluations are unchanged. The
[provider decision table and unsent inquiries](PRODUCT-ACCEPTANCE-HANDOFF.md#owner-decision-table--cost-and-proposed-combination)
now distinguish free data access, full-product tariffs and unquoted API access.
Preferred clarification: existing Upstox scope + official NSE raw EOD + SEC originals;
TrueData historical-only API is conditional on a quote and resolution of published
simulation restrictions. No complete genuine INFY packet or retention compliance is
accepted. Next: owner/provider decisions and lawful evidence, then only demonstrated
ingestion/qualification gaps. No additional synthetic features are scheduled.
