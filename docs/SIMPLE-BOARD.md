# Stock Discovery — SD ARCH 3.0 board

Updated: **24 October 2026** · Baseline: [SD ARCH 3.0](SD-ARCH-3.0.md)
REAL-001 local operations: PARTIAL; prospective recommendations BLOCKED. Calendar renews automatically, actual coverage extended through November 7; duplicate worker/restart/history and health controls verified. Inactive launchd preview prepared; persistent activation and genuine overnight acceptance pending. No new financial/model outputs or recommendations. [Operational acceptance](REAL-001-operations.md). Draft PR #12 remains unmerged; stop at this milestone.

**Overall:** architecture integrated; D3-01 contracts implemented at `6b88cf6`. D3-02 rights/feasibility is merged (PR #2), with activation controlled by source-specific grants. D3-03 revision storage/ingestion is merged (PR #3). D3-04 scheduling/coverage is merged (PR #4); its restricted-runtime permission blocker remains. D3-05 quantitative policies are merged (PR #5). D3-06 evidence ingestion is merged (PR #6). D3-07 hybrid RAG is merged (PR #7). D3-08 bounded research and semantic judge and PR #9 CI fix are merged; human calibration remains unapproved. D3-09 publication and UI are merged (PR #10). D3-10 paper portfolio and outcomes are merged (PR #11, `a0846b5`). REAL-001 remains PARTIAL: actual prices and financial facts were retrieved and three final local model runs now supply non-empty verified historical claims; financial reasoning is not semantically qualified and real policies are not approved. No publication or prospective reference exists. D3-11 experiment governance is merged (PR #13); D3-12/13 remain unstarted. This is a package count, not a percentage of effort or application readiness. The existing synthetic MVP works; real-market discovery and actionable AI research remain blocked.

## Delivery workflow

- Use existing STK ticket IDs and the architecture's D3 package names in branches, commits and PR titles. D3 labels are delivery packages, not new tracker IDs.
- Work on a ticket-named branch. Push that branch and provide a PR for owner review. Never push directly to `main` or merge a PR.
- Wait for the owner to review, merge and confirm before starting the next package. REAL-001 was authorized after D3-10 merged; it reuses D3-02 through D3-10. D3-11 was separately authorized and is now merged (PR #13). This work only reconciles REAL-001 with main; no live activation.
- Keep one implementation package in progress. Preserve unrelated tracked/untracked WIP; stage only the current ticket's files.

## Package and feature status

| Package / ticket names | Done | Remaining | Status / dependency |
|---|---|---|---|
| **D3-01 Contract amendment** · STK-001/002/003 | Strict v2 recommendations, three horizon profiles, four actions, research/admission separation, policy/outcome contracts, fixtures, compatibility tests | Runtime adoption belongs to later packages | Implemented · `6b88cf6` |
| **D3-02 Rights and source feasibility** · STK-004/005/006/007 | [Source matrix and rights gate](D3-02-source-feasibility.md), strict grant contracts and T03 denial tests | Written account-specific permissions/quotes, coverage samples and territorial approval before activation | Merged · PR #2; real-source activation blocked |
| **D3-03 Revision storage and ingestion** · STK-014/015/019–024 | [Revision storage and paged ingestion](D3-03-revision-ingestion.md), immutable as-of snapshots, quarantine, action metadata/adjustment, additive migration and recovery tests | Real provider adapters and activation blocked by source rights; document extraction, scheduling and execution outcomes remain later packages | Merged · PR #3; fictional adapter acceptance |
| **D3-04 Scheduling and coverage** · STK-017/058/060/073 | [Durable scheduler](D3-04-scheduling.md), calendar occurrences, catch-up, fenced dependencies/outbox, event hooks and reconciled coverage; unattended fictional pipeline | Restricted-runtime grant approval/test; real handlers and UI/outcomes belong to later packages | Merged · PR #4; runtime activation blocked |
| **D3-05 Quant horizon policies** · STK-028–032/054/058/076 | [Three quantitative engines](D3-05-quant-policies.md), immutable registrations, as-of financial features, valuation scenarios, calendar endpoints and separated admission; legacy swing preserved | Approved real policy settings, real source/evidence integration and sector-specific formulas; publication/admission are later packages | Merged · PR #5; synthetic acceptance only |
| **D3-06 Evidence ingestion** · STK-046–051 | [Automatic evidence foundation](D3-06-evidence-ingestion.md): mock filing/news adapters, immutable blobs/revisions/chunks/facts, rights gates, corrections, coverage and eligible event dispatch | Approved real sources/adapters and PDF/HTML/OCR qualification; RAG remains D3-07 | Merged · PR #6; mocked acceptance only |
| **D3-07 Hybrid RAG** · STK-052/053/074 | [Hybrid retrieval and fixed research](D3-07-hybrid-rag.md): structured facts, PostgreSQL FTS, local/mock vectors, RRF ranking, citations, abstention and durable budgets | Real model/source qualification, runtime grants, D3-08 semantic gates and D3-09 publication integration | Merged · PR #7; local/mock acceptance only |
| **D3-08 Bounded agent and judge** · STK-052/070/071/072 | [Bounded investigation and separate judge](D3-08-bounded-research.md): read-only tools, deterministic gates, immutable traces, shared budgets and 54-case paired mock evaluation | Human-reviewed holdout/calibration, independent model/source qualification and runtime grants; all output stays shadow | Merged · PR #8; local/mock acceptance only |
| **D3-09 Policy publication and UI** · STK-033/054/058/059 | [Immutable three-horizon publication and dashboard](D3-09-publication-ui.md), distinct modes, four-action gates, current permission checks, comparisons, coverage and queued execution | Real-policy/source activation, calibrated models, restricted-runtime grants; portfolio admission belongs to D3-10 | Merged · PR #10; local/mock acceptance |
| **D3-10 Paper portfolio and outcomes** · STK-037–044/060–063 | [Paper portfolios and immutable outcomes](D3-10-paper-portfolio.md): shared reservations, risk/cost controls, deterministic fictional execution, outcome tracking and authenticated dashboard | Qualified forward source/model/policy approvals and observation/corporate-action adapters; no real activation | Merged · PR #11 (`a0846b5`); local fictional simulation |
| **D3-11 Experiment governance** · STK-041/042/044/069/072/076–078 | Immutable registry/trials, paired/end-to-end Q/Q+R/Q+A, leakage/holdout controls, pinned outcomes, blocked promotion and Scorecard view | Genuine prospective qualification remains external; see D3-11 acceptance | Merged · PR #13; local software acceptance |
| **D3-12 Private operational pilot** · STK-009/016/017/018/073–075 | Hetzner CX23/Compose/restic/B2 selection approved | Authorized provisioning, security, budgets, monitoring and off-host restore | Deferred · D3-02/04/09/10 + explicit deployment approval |
| **D3-13 Three-horizon release** · STK-079/080/081 | Release criteria specified | Integrated acceptance, coverage evidence, known limits and operational runbook | Not started · D3-11/12 |

## Verification and boundaries

D3-01: **141 application/worker tests passed**, including **83 new contract cases**; 7 script tests, schema consistency, whitespace checks and isolated frontend build passed. Eleven database cases were skipped locally without a test database. All six historical fixture files retain their original hashes. [D3-01 CI run](https://github.com/gaganjawa/stock-discovery/actions/runs/38758750057) completed successfully, including the database and browser workflow checks.

Existing optional LLM explanations summarize synthetic decisions. They are not the planned pre-decision RAG, bounded agent or LLM judge. No paid AI or real-source capability has been activated.

Purchases, paid APIs, deployment and broker orders are outside current authorization. Hosting selection remains fixed; region, final pricing and backup-key custody must be confirmed before provisioning. Optional IPO, intraday, broker reads and predictive ML are not prerequisites for the core three-horizon release.

[Contract details](contracts/v2/README.md) · [Handoff](WORK-HANDOFF.md) · [Historical board](archive/BOARD-before-sd-arch-3.md). Historical synthetic milestones remain valid within their original scope; they do not mark new architecture packages complete.

D3-02 validation: the isolated delivery snapshot passes 193 application/worker tests (52 new rights cases) and 7 script tests; 11 database cases skip locally without a test database. Schema consistency, whitespace and documentation-link checks pass. All real-source grants remain absent; no paid call or provider activation occurred. Existing app WIP is preserved. This delivery does not claim STK-004–007 real-use approvals are complete.

D3-03 validation: 243 tests passed in the isolated delivery snapshot, including 39 new cases and 32 total database integration cases; 7 script tests passed. Migration upgrade, repeat upgrade, downgrade, re-upgrade and atomic failure rollback passed on 16 October 2026. PostgreSQL validation uses a disposable container, not the application database. No API key or paid service is used.

D3-04 validation: the isolated delivery snapshot passes **279 application/worker tests**, including **36 new scheduler cases**, plus **7 script tests** and the frontend build. All **48 database integration tests** and migration upgrade/repeat/downgrade/re-upgrade/failure rollback pass; generated-schema consistency, legacy contract examples and whitespace checks pass. Runtime database grants are unchanged: automatic approval review blocked the proposed permission expansion. See the [scheduler handoff](D3-04-scheduling.md) before activating the restricted runtime worker. No key, paid API or deployment is used.

D3-05 validation: **326 application/worker tests passed** in the isolated delivery snapshot, including **47 new quantitative-policy tests** and all **48 database integration cases**; **7 script tests** passed. Generated policy/schema/result fixtures reproduce exactly; whitespace checks pass. Legacy strategy and historical evaluation fixtures are unchanged. No approved real policy, source activation, admission grant, AI call or deployment is included.

D3-06 validation: **366 application/worker tests passed** in the isolated delivery snapshot, including **40 new evidence cases** and all **72 database integration cases**; **7 script tests** passed. Migration upgrade/repeat/downgrade/re-upgrade/failure rollback and generated schema/fixture consistency pass. Historical fixtures and legacy strategy remain unchanged. Automatic mock ingestion needs no upload; real providers and PDF/HTML/OCR extraction remain unactivated/unsupported. No paid API, RAG/agent or deployment was used.

D3-07 validation: **423 application/worker tests passed** in the isolated delivery snapshot, including **57 new RAG cases** and all **105 database integration cases**; **7 script tests** passed. Migration upgrade/repeat/downgrade/re-upgrade/failure rollback, historical contract examples and whitespace checks pass. Source fixtures and legacy strategy are unchanged. Local/mock embeddings and a mock research provider only; output stays shadow/non-actionable. No paid API, real provider, D3-08 agent/judge, deployment or broker action was used.

D3-08 validation: **465 application/worker tests passed** in the isolated delivery snapshot, including **42 new agent/judge cases** and all **116 database integration cases**; **7 script tests** passed. Migration upgrade/repeat/downgrade/re-upgrade/failure rollback, legacy contract examples, dataset/hash consistency and whitespace checks passed. The 54-case paired evaluation uses provisional synthetic labels and local mocks only; it is not human calibration or evidence of agent superiority. Historical fixtures and unrelated WIP remain unchanged. All research stays shadow/non-actionable; no paid AI, real-source activation, deployment or broker transaction occurred.

D3-08 CI follow-up · STK-052/070/071/072: fixed workflow ordering on baseline `12077b4`. The full suite previously ran before the disposable database existed or `STK_TEST_DATABASE_URL` was set; D3-06/07 module skip markers concealed that missing setup, while D3-08's imported fixture executed without those module markers. CI now provisions PostgreSQL and runs migration/integration acceptance before the full regression, with the test URL available throughout. Integration acceptance rejects empty reports and skipped tests. Local verification: **116 integration tests, zero skipped; 465 application/worker tests passed; 10 script tests passed**, plus migration lifecycle and contract checks. No AI behavior, historical fixtures or D3-09 scope changed.

D3-09 validation (18 October 2026): **493 application/worker tests passed**, including **28 new policy/integration cases and all 129 database integration tests with zero skips**; **10 script tests passed**. Migration upgrade/repeat/downgrade/re-upgrade/atomic rollback, historical contract examples, production UI build, and both new discovery and existing synthetic browser workflows passed locally. The five-listing fictional universe runs all three horizons and all three research modes, with strict v2 provenance and current permission checks. Unrelated WIP and historical fixtures are preserved. Local/mock shadow acceptance only; no real source, paid API, broker execution or D3-10 work was activated.

D3-10 validation (18 October 2026): **546 application/worker tests passed**, including **53 new cases and all 160 database integration tests with zero skips**; **10 script tests passed**. Migration upgrade/repeat/downgrade/re-upgrade/atomic rollback, legacy contract examples, production UI build and local Compose smoke checks passed. Browser acceptance covers discovery, the new fictional paper portfolio and the existing replay/scorecard workflow. Reservations and outcome receipts serialize in PostgreSQL; ledger/input/history mutations are rejected. Historical decisions and unrelated WIP are preserved. D3-09 MOCK/SHADOW recommendations remain blocked from approved forward paper; fictional software outcomes use a separate contract. Real source/model/policy qualification, benchmark/corporate-action adapters and restricted-runtime grants remain activation dependencies. No D3-11, paid service, deployment or broker execution is included.

## REAL-001 — STK-004–007/014/015/046/048/052/059/060

**Current: Phase 8 PARTIAL (22 October).** Genuine descriptive indicators, explicit coverage/freshness and unapproved policy display pass local acceptance. B9 publication/prospective acceptance is blocked. [Execution](REAL-001-phase8.md). Earlier phases remain history; D3-11–13 are untouched.

**PARTIAL, not real-market readiness.** [Acceptance](REAL-001-acceptance.md) · [Provider matrix](REAL-001-provider-matrix.md) · [Runbook](REAL-001-runbook.md). Upstox access verified for INFY: identity, 11 actual daily candles, calendar, financial responses and 10 news items (availability/count metadata only retained). Native qwen2.5-coder:7b and nomic-embed-text ran; financial qualification remains unapproved. New opt-in price adapter uses existing grants, revision ingestion and scheduler; downstream real research stages block. Existing UI has an authenticated blocked REAL RESEARCH mode. No actual filing, real recommendation or forward outcome has been persisted. Remaining owner/source action is use-specific permission evidence; credentials have been supplied and secured. No paid API, deployment, model download or broker order. D3-11/12/13 remain unstarted.

Phase 2 (19 October): **PARTIAL**, continuing PR #12. Added configured official
document acquisition/extraction to D3-06, native-provider D3-07/08 orchestration,
rights-aware company/analysis readers, D3-05 input mapping and existing UI panels.
601 tests and 163 PostgreSQL cases pass with zero skips. Actual SEC filing fetch
returned 403; Upstox use evidence remains unknown. No actual filing, new model
run, real recommendation or prospective outcome accepted. Publication/tracking
still require implementation. [Phase 2 record](REAL-001-phase2.md).

Phase 3 (20 October): **PARTIAL**, same draft PR #12. Conditional D3-09 real
publication and D3-10 immutable shadow references/observation receipts are wired
to rights-aware dashboard history; no portfolio admission or fabricated returns.
606 tests, 164 PostgreSQL cases (zero skips), migration lifecycle, five browser
workflows and production build passed. **No actual INFY filing, grounded research,
publication or outcome**: unresolved provider rights, observed coverage/policies
and model qualification. T9/Ollama inventory passed the final recheck. [Phase 3/A1–A14](REAL-001-phase3.md).
D3-11/12/13 remain unstarted.

Phase 4 (20 October): **PARTIAL / permission stop condition reached**. New provider replies establish private Upstox market-data storage/research/replay rights. Financial/news corpus rights and price-adjustment semantics remain blockers. No actual filing, RAG, publication or outcome; no infrastructure added. [Operation matrix and unsent owner drafts](REAL-001-phase4.md). D3-11/12/13 untouched.

D3-11 validation (24 October 2026): **590 unique backend/worker tests exercised** across the regression/integration suites and final targeted additions (**194 database integration cases, zero skips**), plus **10 script tests** and **4 browser workflows**. Migration upgrade/repeat/downgrade/re-upgrade/atomic rollback, contract validators and frontend production build passed. [Acceptance record](D3-11-ACCEPTANCE.md) separates actual PostgreSQL/browser execution from fictional market/model evidence. Exact-commit GitHub CI is reported on the separate draft PR. No changes depend on or modify PR #12; no live operations, strategy approval, D3-12 or merge.

STK-074 read-side follow-up: manual company/evidence/research reads now have transactional original-grant fences; legacy scans without original universe linkage fail closed. CI mandatory gates are split without duplicate PostgreSQL execution. [Design and measured CI baseline](STK-074-read-fences-ci.md). Uncommitted, pending independent review; REAL-001 operations remain PARTIAL and publication/admission/trading remain BLOCKED.

31 October 2026 — **STK-079 / D3-13 single-instrument research slice:** implementation
merged via PR #19 at `f409bca`; required exact-commit CI passed for `c9d8df1`.
[Stored-evidence swing integration](STK-079-real-swing-integration.md) connects
STK-014 qualification, STK-074 read fences, existing indicators/strategy and
hypothetical sizing to the authenticated company API. Synthetic acceptance only;
no genuine NSE instrument qualified or provider activated. Full D3-13 release and
REAL-001 operational acceptance remain incomplete. Publication, paper admission
and trading remain BLOCKED.

Owner-authorized AI roadmap: [implementation plan](AI_RESEARCH_IMPLEMENTATION_PLAN.md)
and [durable checkpoint](AI_RESEARCH_PROGRESS.json). M0 closes this slice before
the real-data, grounded AI, synthesis, historical replay and UI milestones.

STK-054 / M6 first research screen: connects the existing company view to stored
swing qualification, indicators, hypothetical levels/sizing and explicit gaps.
Production build and two synthetic desktop/mobile browser regressions passed.
No source acquisition or inference is triggered by opening the screen. Full AI
synthesis, discovery ranking and historical replay UI remain incomplete.
M1 real-data acceptance remains blocked; see [exact evidence gaps](AI_RESEARCH_DATA_ACCEPTANCE.md).

31 October — STK-054 first swing research screen merged via PR #20 (`9078493`)
with all required checks passed. Full M6 remains partial. STK-052 / M2 now adds
model-selected exact source excerpts to the existing factual report; attributed
quotations stay separate from verified numbers and event truth. 712 unit tests,
25 fixed-RAG PostgreSQL cases, 37 affected database cases and 2 browser cases
passed. Full database run: 415 passed / 1 existing expiry-lock timeout; isolated
three-case rerun passed. Required PR CI/lifecycle pending; no real quality acceptance.

PR #21 merged (`831feb0`): exact-passage alias-citation fix, 417 PostgreSQL tests
and migration lifecycle passed in required CI. Earlier local lock-timeout cause
remains unresolved; deterministic timeout denial/rollback is covered. M2 next
slice adds opt-in structured financial proposals verified against deterministic
filing facts and exact source rows; 729 unit and 64 affected database cases passed.
Human review packet prepared, labels unverified; actual local model unavailable.
No general financial accuracy, genuine instrument or historical return acceptance.

PR #22 merged (`f05d329`), 419 PostgreSQL cases and lifecycle passed in protected CI.
M2 runtime increment: optional offline llama.cpp provider and lexical retrieval;
736 unit, 30 PostgreSQL and 89 focused cases passed. Existing SSD qwen2.5-coder:7b
ran twice on synthetic rows: first 0 accepted / 3 rejected; after a prompt-only
clarification, 2 financial rows accepted / 1 extra candidate rejected. Both runs
retained; no verifier relaxation, genuine filing, held-out or human quality acceptance.
Ten developer labels remain human-unverified; independent holdout registration empty.

STK-052 / M2: PR23 merged (`103f5ff`), all required exact-commit checks passed,
421 PostgreSQL cases, zero skips and lifecycle checks. Representative public SEC
table-span development benchmark now records actual local coding versus general
instruction model calls: **0/2 supported cells extracted per model**; original
failed run and separate diagnostic preserved. No model-superiority claim.
740 unit and 10 isolated affected PostgreSQL tests passed locally. M2 quality
NOT PASSED; independent human holdout UNAVAILABLE. Current 200000-unit daily
reservation cap exhausted, USD0 API cost. See [results and boundaries](STK-052-financial-span-evaluation.md).
Original-file/PIT/source qualification and human review remain blocked;
M3–M7 must wait for M2 acceptance. Publication/admission/trading remain BLOCKED.

M2 hybrid development: PR24 merged (`e7523bb`), exact CI passed. [Hybrid evaluation](STK-052-hybrid-financial-selection.md) recovered coder positive cells 2/2 with contract validity 4/4; model negative abstention remains 0/2, VL extraction 0/2. Application rejects unsupported selections. Independent human review packet prepared, labels null. M2 PARTIAL; no advance to combined recommendations/replay. Original results preserved.

M2: PR25 merged (`2607e09`) after exact-commit CI/review. [Explicit abstention experiments](STK-052-financial-abstention.md) improve coding-model negatives 0/2 → 2/2 but regress positives 2/2 → 1/2 in both v3/v4. All failures and prior runs preserved; no further VL inference. Independent reviewer/holdout absent: M2 gate BLOCKED. Reviewer worksheet prepared; combined recommendations/replay remain gated.

M2: PR26 merged (`54b27de`), all required checks passed including 429 PostgreSQL cases and lifecycle. [Exact selection](STK-052-exact-financial-selection.md) replaces unnecessary model choice for unambiguous row/period/scope: 2/2 positives, 2/2 deterministic abstentions, zero inference. Human source review and unseen 50-case quality gate remain BLOCKED; 50 blank allocation slots contain no labels/evaluation evidence. No milestone promotion.

PR27 merged (`ceacc432`) after required exact-commit checks and focused review,
including 431 PostgreSQL cases with zero skips and migration lifecycle. Per the latest
owner instruction, independent non-actionable product work may continue despite M2's
external gate. STK-052/054 now integrates [combined company research](STK-052-054-combined-research.md)
and frozen synthetic replay context into the existing API/UI. Human financial quality,
real qualification, combined historical evaluation and actionable promotion stay BLOCKED.

1 November — PR28 merged (`db61f7c`) after exact `d63f784` CI and fresh focused review.
STK-037/043/059 [full historical evidence replay](STK-037-043-historical-evidence.md)
now connects optional fictional statements/facts, pinned provenance, combined
abstention and subsequent technical baseline outcomes to the existing Replay UI.
Independent research quality, real data and valid combined/AI performance remain
BLOCKED; original evaluation artifacts and policy thresholds are unchanged.

PR29 merged (`466de933`), exact `acd827d` checks passed: 461 PostgreSQL, lifecycle
and 12 browser workflows. HTTP429 browser setup contention was reproduced/fixed
without changing authentication or rate limits. STK-043/059 now integrates
[saved historical research](STK-043-059-saved-replay-dashboard.md), source-authorized
reopening and fictional multi-date/instrument batches into Dashboard and Replay.
Coverage counts remain separate from eligible pairs (zero); AI performance unavailable.

1 November — PR30 merged (`7f87b1c`), exact `bcb51e6` unit/postgres/ui/checks
successful under verified protection. STK-058/059 [bounded discovery acceptance](STK-058-059-product-acceptance.md)
exposes existing frozen priority components, a technical-condition filter and
two-to-four-company comparison within one fictional batch/horizon/research arm.
Original strategy/evaluator acceptance is audited and the explicit M1 qualification
checklist names missing permissions, clocks, coverage and price/volume semantics.
Local validation/delivery state is in the durable checkpoint. Independent review
and exact-commit CI are required; genuine NSE qualification, M2 independent
human/50-case quality acceptance and operational acceptance are not advanced.
Next priority is M3's remaining observation-supported benchmark/risk-adjusted and
walk-forward acceptance, reusing the existing D3-10/11 evaluators and controls.

1 November — PR31 merged (`6d6a2c8`) after exact `a0ee567` required checks and
fresh review; the missing aggregate was resolved by an exact-commit CI rerun.
STK-041/042 [performance evaluation](STK-041-042-performance-evaluation.md) extends
the existing Scorecard with descriptive risk, costed synthetic reference, honest
coverage/denominators and purged partition outcomes. Registered walk-forward and
AI-pair results remain unavailable where evidence is absent. No threshold or
acceptance approval; M1/M2 and REAL-001 operational blockers are unchanged.
Delivery and actual validation totals are recorded in the durable checkpoint.

2 November — PR32 merged (`f172a28`) after corrected exact `02af305` checks passed
(790 unit, 482 PostgreSQL, lifecycle, 13 browser). The reproduced benchmark
knowledge-cutoff defect is fixed; original evaluation artifacts remain intact.
STK-041/042 [registered fold reporting](STK-041-042-registered-folds.md) connects
existing sealed trials/outcomes to Scorecard, with immutable references, source
fences, separate phases, honest counts and unavailable pooled-return/benchmark/AI
results. Independent review and exact-commit CI remain required for this increment.
[Product acceptance handoff](PRODUCT-ACCEPTANCE-HANDOFF.md) records remaining software
gaps and the minimum external M1/M2 inputs. Genuine acceptance/activation stays blocked.

2 November — PR33 merged (`8d336486`) under protected main after exact `74d7b15`
unit/PostgreSQL/UI/aggregate success and fresh correctness review, with no confirmed
P1/P2. STK-043/059 [Discovery navigation](STK-043-059-discovery-history.md) links
existing frozen publications, recorded/pinned outcomes and explicit registry
references. Unrelated fixture identities and missing histories remain distinct;
reads never create inference, outcomes or admissions. Review/CI delivery state and
fresh acceptance counts are in the checkpoint. M1/M2, genuine forward/benchmark,
policy, operational, publication and trading approvals remain blocked.

2 November — PR34 merged (`63e2cfcc`) after exact `27b0ffc` protected checks and
independent review: 794 unit, 516 PostgreSQL/zero skips, lifecycle, 14 browsers.
The [final synthetic workflow audit and M1 handoff](PRODUCT-ACCEPTANCE-HANDOFF.md)
found no demonstrated new software gap. Primary focus: STK-004/005/007/014 INFY
source qualification. Saved private grant metadata was found; action/news scopes,
raw-price semantics, original filings/clocks and retention remain unresolved.
No provider activated, private payload copied, model run, holdout consumed or real
recommendation approved. M1/M2, genuine evaluation and operational gates remain blocked.

2 November — STK-004/014 M1 provider decision handoff prepared, documentation only.
[Comparison, owner sequence and three unsent inquiries](PRODUCT-ACCEPTANCE-HANDOFF.md#owner-decision-table--cost-and-proposed-combination)
separate NSE free access/full-product tariffs from TrueData's unquoted API and
simulation restrictions. Saved Upstox scope is preserved; `historical_replay` is
not locally authorized. No new source/grant, dataset change or synthetic feature.
Next action is owner/provider clarification; M1 remains BLOCKED.
