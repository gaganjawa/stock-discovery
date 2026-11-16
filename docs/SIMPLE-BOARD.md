# Stock Discovery — SD ARCH 3.0 board

## Current — STK-014 / STK-094 · D3-03 + D3-09 candidate qualification

16-Nov: STK-095 hybrid release `2c39f61e` is active on Mac + VPS, both databases
at **0018**. Read-only evidence after activation: cursor/high-water **3/3**, three
provider Tests, zero raw receipts, failed/quarantined events, candidates or refresh
jobs. Genuine acceptance remains **PENDING**; authorization expires 18-Nov
12:11:49 UTC. No alert/provider requests or production writes in this change.

Qualification visibility reuses identity/grant fences, refresh jobs, stored research,
EMA/breakout checks and page-scoped ranking. Both candidate views expose research
eligibility, refresh history, blockers and price-session limitations. Cached analysis
is labeled separately from a current stored-price review; neither certifies a BUY.
A prior refresh job does not certify current private acquisition scope, credentials
or quota; absent jobs remain explicitly unverified. Empty and quarantined inbox
states do not imply scanner zero matches.

Focused unit, disposable PostgreSQL and browser acceptance covers synthetic INFY,
unmapped identity, revoked permission, stale/incomplete prices, duplicates,
provider-Test exclusion and Candidates/company/watchlist continuity. Production is
unchanged by this PR. Next: review this change, then observe the next genuine alert
and trace its retained receipt. Current worker admission and volume-qualified
signals remain separate gates. Planning baseline stays **58%**; owner monitors CI.

## Historical — pre-release PR #59 preparation

Current delivery — **STK-095 / STK-014 · D3-03 Revision storage and ingestion**
(16 November), continuing **PR #59** on main with **PR #58 merged** (`0daf5eb`).
Authenticated, rate/size-bounded webhook intake now durably stores a private,
credential-redacted raw receipt before HTTP 202. The existing consumer advances
its cursor after local durability, then parses asynchronously. Unknown schemas
are quarantined with diagnostics and authenticated replay; downstream validation,
source grants, quotas and candidate deduplication remain strict.
Additive **0018** stores parsed envelopes/diagnostics alongside immutable receipts;
no production migration or deployment has occurred. Synthetic PostgreSQL and real
browser acceptance covers raw intake → eligible refresh → research → ranked
Candidates → watchlist. This is **not genuine market acceptance**.
[Implementation and release gates](STK-095-private-rejections.md).
Optional capture failures remain visible in authenticated diagnostics and do not
fail database/receiver health; best-effort retention cleanup still runs.
Planning baseline remains **58%**. Owner monitors CI; do not wait or merge.

## CURRENT — 16 November 2026 · STK-095 / D3-03

Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md); this is the canonical task board.
[PROJECT-HANDOFF](PROJECT-HANDOFF.md) records persistent component context.
Overall **58%** is a planning baseline, not a measured acceptance percentage.

| Component | Current state | Remaining gate |
|---|---|---|
| STK-095 | Receiver/Mac consumer live; provider Tests passed; a candidate-format request was rejected at column validation on 16-Nov. Durable raw intake, worker quarantine/replay and schema 0018 prepared in PR #59, not deployed. | Approve additive migration/compatible consumer and receiver release; verify genuine candidate acceptance. |
| STK-094 / STK-014 | PR #52/#53 merged; restricted INFY refresh singleton; EMA/breakout and page-scoped Candidates ranking implemented. | Current complete price batch and genuine candidate → analysis → UI. PR #58 stored-price coherence fix is merged. |
| STK-099 | PR #57 merged as `0fe2136`; prior representative restore/resource/recovery evidence retained. | Off-server restore/key custody, external alerts, separate cutover approval and genuine Mac-off acceptance; issue #47 remains open. |
| D3-13 | Continuity and CI selection merged. | Integrated three-horizon live release and prospective qualification remain incomplete. |

**Actual production evidence, 16-Nov 13:42–13:45 UTC:** schema **0017** on both
sides, remote high-water/Mac cursor **3**, accepted events **3**, all provider Tests;
genuine candidates **0**, refresh jobs **0**, revisions **2,648**. Consumer PID 8125,
refresh PID 8129, one launch each; consumer cycles completed. Latest accepted event
13-Nov 16:16:04.537076 UTC. Receiver/proxy/database unchanged and healthy.
`invalid_columns_fields` is the confirmed receiver failure; zero matches, no alert
generation or consumer failure cannot be inferred. Latest complete stored INFY
session **4-Nov** is stale; no current OHLCV qualification. Scanner authorization
expires **18-Nov 12:11:49 UTC**; existing approval window must cover the next alert.

| Priority | Tickets | Next outcome |
|---|---|---|
| **P0** | STK-095 | Review PR #59, approve schema 0018 and compatible worker/receiver/API/UI release; verify next genuine delivery, quarantine/replay if needed, then candidate acceptance. |
| **P1** | STK-014 / STK-094 | Genuine eligible candidate → complete EOD refresh → durable analysis → authenticated UI; missing/stale/insufficient data stays unranked. |
| **P2** | STK-099 / STK-054 / STK-079–081 | Existing off-server/alert provisioning gates remain; volume/strategy/research qualification remains. No infrastructure work in this fix. |

**Verified blocker:** original rejected JSON is unavailable; no evidence supports a
specific column alias, omitted-field relaxation or successful genuine delivery.
**Exact next task:** review PR #59 and exact-head CI, authorize additive 0018 and
the compatible application/consumer then receiver release. Use the
[release sequence](STK-095-private-rejections.md), then verify the next ordinary alert. Preserve secrets/URL, event history, cursor
and singleton workers; only the approved additive schema change is permitted. No test alert, provider call or full cutover.

## HISTORICAL — superseded 16-Nov operations checkpoint

Current delivery — **STK-099 / D3-12 Private operational pilot** (16 November).
Main includes PR #56 at `5a78b6846cd88d89e68abf8864b8fe707c50b8b6`.
Release prerequisites now include opt-in non-interrupting full-schema backup/recovery,
receiver/hosted monitoring, an alert-delivery drill, and current cutover/rollback
commands. **15 focused synthetic operations tests pass**; no VPS/browser rehearsal
repeated. Restic 0.19.1 is installed separately on the VPS; no timers or application
release were activated. The live receiver image/start time remains unchanged.
**Off-server restore and external alert delivery remain unverified:** the inspected
configuration has no destination/credentials/key-custody or alert hook. Owner input
is required for those existing resources, then one actual restore and observed alert.
[Exact evidence, prerequisites and executable sequence](STK-099-release-prerequisites.md).
Planning baseline remains **58%**. No cutover authorization; owner monitors PR CI.

## HISTORICAL — 16 November 2026 · STK-099 / D3-12 Private operational pilot

Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md). [SIMPLE-BOARD](SIMPLE-BOARD.md)
is the canonical task board; [PROJECT-HANDOFF](PROJECT-HANDOFF.md) provides product
and component context; [WORK-HANDOFF](WORK-HANDOFF.md) records execution continuity.
Update board and project handoff together on material state changes.
**58% remains the owner-specified planning baseline**, not measured live readiness.

| Component | Actual current state | Remaining gate |
|---|---|---|
| STK-095 | VPS receiver/inbox/proxy and native Mac consumer; schema 0017; real provider-Test acceptance passed. | Ordinary genuine alert; no manufactured candidates. |
| STK-094 / STK-014 | PR #52/#53 merged; native bounded INFY refresh; stored-price EMA/breakout and page-scoped ranking implemented. | Complete current qualified price batch and genuine candidate → analysis → UI. |
| STK-099 | PR #48/#54 merged; 14-Nov representative VPS restore/resource/recovery evidence retained. Current operations tooling and cutover/rollback checklist prepared for review. | Off-server restore/key custody, external alert/host-loss test, separate release authorization, genuine Mac-off acceptance. [Issue #47](https://github.com/gaganjawa/stock-discovery/issues/47) remains open. |
| D3-13 | PR #55 continuity and #56 CI selection merged. | Integrated three-horizon live release, real research/policy/forward-evidence gates remain capability-specific. |

**Live VPS, 16-Nov 06:06:20 UTC:** receiver/proxy/database still running; receiver
and database healthy, receiver image and start time unchanged. Restic 0.19.1 was
installed at a separate versioned tools path. No application service restart,
migration, cursor update, volume change, provider request or cutover occurred.
**Last Mac evidence remains 15-Nov 13:01 UTC:** schema 0017, cursor **3**, events
**3**, genuine candidates **0**, revisions **2,648**, consumer PID 8125 and refresh
PID 8129, one launch each/one refresh process, no refresh jobs or quota requests in
preceding 24h. Those counts were not remeasured in this operations task.

Initial Upstox HTTP 200 gave 30 validated bars but omitted expected 13-Nov; **zero
ingested**. The one authorized diagnostic also omitted it. Upstream incompleteness
is observed; cache lag remains an inference. Existing retries: 900 seconds, at most
three per eligible job. Missing/stale/insufficient evidence stays unranked.

**Reused acceptance:** 14-Nov isolated VPS restore preserved 70 tables / 6,737 rows /
three sequences and watchlist bytes; browser, 24 company reads at concurrency four,
worker restart and second recovery passed. Minimum available RAM 1,008.6 MiB,
no OOM. This was stored-data/idle-refresh rehearsal, not off-server recovery or
live acquisition. No repeat VPS/browser rehearsal. Current 15 operations tests use
synthetic transports/databases; they do not prove external delivery or remote restore.

| Priority | Tickets | Next outcome |
|---|---|---|
| **P0** | STK-014 / STK-094 / STK-095 | Next ordinary EOD alert → identity/session/symbols → durable candidate/cursor → complete eligible refresh → re-analysis → authenticated Candidates UI. Provider Tests excluded. |
| **P1** | STK-099 | Supply existing backup destination/private credentials, independent key custody and alert/host-loss resource; perform one encrypted off-server restore and actual alert delivery, then request separate cutover authorization. |
| **P2** | STK-014 / STK-054 / STK-079–081 | Qualify volume and remaining strategy/research inputs for daily usable swing and all three horizons; no invented BUY, levels, sizing or performance. |

**Verified blockers / release gates:** no backup repository/credentials/custodial-key
configuration or alert hook found in inspected locations; no Stock Discovery timers
or root cron entries. Restic executable availability is now resolved. Off-server
restore, key custody, external alert/host-loss delivery, active-provider capacity and
genuine Mac-off evidence remain unverified. Existing Caddy uses `admin off`; proxy
replacement needs a separately authorized brief ingress window. No host upgrade is
justified by the retained rehearsal. No new paid resources or provider-rights review.

**Exact next executable task:** owner identifies existing off-server and alert
resources/private paths (never secret values); fill reviewed private operations
config and run `python3 scripts/operate.py backup`, `alert-test`, and `monitor`.
Record exact snapshot/restored fingerprints and actual delivery ID/time; enable
existing timers only afterward. Full cutover remains **NOT READY / unauthorized**.
The [current release checklist and rollback commands](STK-099-release-prerequisites.md)
supersede historical 0016 migration/receiver upgrade steps. Preserve schema 0017,
credentials, webhook, original cursor identity, volumes and fresh rollback state.
PR checks and owner review are pending; do not wait for CI, merge or cut over.

## HISTORICAL — superseded 15-Nov current checkpoint

Current delivery — **STK-081 / D3-13 CI efficiency** (15 November): PR #55 is
merged as main `549cf2b02a287647635e5dee5f176f5855545625`. Change-based selection
and a fail-closed stable `checks` gate are implemented for review; workflow/runtime/
security/infrastructure changes still select full affected suites. Documentation
replay selects only fast validation. [Measured baseline and validation](STK-081-selective-ci.md)
separate 8m52s prior hosted documentation CI from 0.0445s local selection/docs logic;
new hosted timings are pending. No production change; planning baseline **58%**.
Immediate delivery task: owner review/new-head CI, with owner monitoring and no wait.
The next product task remains STK-099 off-server recovery preparation; P0 genuine
candidate acceptance and existing release gates remain unchanged.

## CURRENT — 15 November 2026 · STK-099 / D3-03 + D3-04 + D3-09 + D3-12

Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md). This is the canonical task board;
[current work handoff](WORK-HANDOFF.md) records the next executable task.
[PROJECT-HANDOFF](PROJECT-HANDOFF.md) supplies persistent product/component context.
Update this board and PROJECT-HANDOFF in the same PR when project state materially
changes, retaining dated evidence and test/rehearsal/live distinctions.
**Overall planning baseline: 58%, owner-specified on 15 November.** This supersedes
the prior reported 57% and historical 46%/49% estimates; it is not a measured
release-acceptance percentage, test pass rate or investment-performance claim.

| Component | Current delivery / deployment | Remaining acceptance |
|---|---|---|
| D3-01–11 foundations | Merged software, including PR #12; quantitative policies, research, publication, paper outcomes and governance have scoped software evidence. | Qualified real evidence, research calibration and forward/policy gates remain capability-specific. |
| STK-095 Chartink | PRs #49–51 merged; real provider-Test acceptance passed. BookMyHost receiver and Mac consumer live; both production databases schema 0017. | Ordinary genuine-alert acceptance pending; provider Tests never materialize candidates/research. |
| STK-094 / STK-014 candidates and prices | PR #52 stored-price review and PR #53 bounded refresh/re-analysis merged; one restricted INFY refresh worker active on Mac. | Complete current Upstox batch and genuine candidate → analysis → UI acceptance pending; no volume-qualified BUY/sizing claim. |
| STK-099 hosting | PR #48 and PR #54 merged; online snapshot backup and scoped hosted refresh are on main. Actual isolated VPS restore/browser/restart/recovery passed. | No full production cutover. [Issue #47](https://github.com/gaganjawa/stock-discovery/issues/47) remains open. |
| D3-13 release | Descriptive research slices delivered; continuity/runbook work in progress. | Integrated three-horizon live release and genuine prospective outcomes incomplete. |

**Actual deployment, last verified 15-Nov 13:01 UTC:** VPS runs the receiver,
inbox PostgreSQL and proxy. Application database/UI/API and consumer/refresh remain
Mac-dependent. Consumer PID 8125, refresh PID 8129, one launch each and exactly one
refresh process; Mac schema **0017**, cursor **3**, events **3**, genuine candidates
**0**, revisions **2,648**. No refresh jobs or quota requests in the preceding
24 hours. No production changes were made for this documentation update.

Initial Upstox response contained 30 validated bars but lacked the expected 13-Nov
session; **zero bars ingested**. The one permitted diagnostic also omitted 13-Nov.
Upstream incompleteness is confirmed; cache lag is an inference. Existing readiness
retry is 900 seconds, at most three attempts per eligible job. No forced candidates,
extra speculative provider requests, response stitching or incomplete current data.

**Previous merge evidence:** PR #54 merged as `fbd841aa9948949dfed655e462ea292b9204b007`.
All four required checks passed at its final head `bf12c53`
([run](https://github.com/gaganjawa/stock-discovery/actions/runs/43717712492)).
Exact-merge main CI was still running at reconciliation
([run](https://github.com/gaganjawa/stock-discovery/actions/runs/43718688001)); this
is separate from the passed PR checks. PR #55 is merged with all four final checks passed;
this CI change needs new exact-head CI; owner monitors it without waiting or automatic merge.
Prior local 21 focused
tests and 14-Nov VPS evidence remain valid within their recorded scope. The rehearsal
preserved 70 tables / 6,737 rows / three sequences and watchlist bytes, with minimum
sampled available RAM 1,008.6 MiB and no OOM. It was isolated stored-data/idle-refresh
acceptance, not live acquisition, genuine alerts or off-server disaster recovery.

| Priority | Existing tickets | Next outcome |
|---|---|---|
| **P0** | STK-014 / STK-094 / STK-095 | Observe the next ordinary genuine EOD alert; verify event/session/symbols, durable candidate/cursor, eligible complete price ingestion, re-analysis and authenticated Candidates UI. |
| **P1** | STK-099 | Verify encrypted off-server recovery, key custody and external alerts with the merged tooling, then seek separate full-cutover authorization. |
| **P2** | STK-014 / STK-054 / STK-079–081 | Qualify volume/remaining strategy inputs and advance the full three-horizon release with explicit research/policy/forward-evidence gates. |

Release gates: encrypted off-server restore/key custody and external alert delivery
remain unverified; no restic executable or Stock Discovery backup/monitor units were
found on the VPS during preflight. Active-provider load and genuine Mac-off acceptance
remain unverified. Same-host restore does not satisfy those gates. Before any approved
cutover, stop both Mac workers persistently, preserve fresh DB/watchlist/cursor/quota
state, restore to new VPS targets and retain rollback. Preserve the live receiver.

**Next executable task — STK-099:** inspect existing private backup/alert
configuration and prepare an isolated off-server restore using the merged tooling.
Record any missing destination/key-custodian input for the owner. This CI change remains
for owner review and exact-head CI; do not wait, merge or infer cutover approval.
Do not expose secrets, send alerts or make paid requests without authorization.
[Rehearsal evidence and release procedure](STK-099-restored-rehearsal.md).

## HISTORICAL — prior board snapshots and evidence

The original summaries, package table and dated records below are retained verbatim.
Their old PR states, absent grants, hosting choice and activation instructions are
historical; the CURRENT summary above governs present state. No prior test evidence
is relabelled as live production acceptance.

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

D3-03 validation: 243 tests passed in the isolated delivery snapshot, including 40 new cases and 32 total database integration cases; 7 script tests passed. Migration upgrade, repeat upgrade, downgrade, re-upgrade and atomic failure rollback passed on 16 October 2026. PostgreSQL validation uses a disposable container, not the application database. No API key or paid service is used.

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

2 November — STK-004/014 [bounded official-source probes](PRODUCT-ACCEPTANCE-HANDOFF.md#actual-official-source-probes--2-november-2026):
NSE initializes but session continuity fails; no market-tool result. Upstox live
descriptive samples pass and stay adjusted. SEC reuse permission is published,
but direct API/original requests return 403. Fresh 173 focused fixture tests pass.
No production change justified; datasets/grants/fences/gates unchanged. Resolve
technical access and missing qualifying inputs, not blanket permission letters.

2 November — STK-004/014 [Breeze read-only feasibility](STK-004-014-breeze-evaluation.md):
published free backtesting, official public master INFTEC/INFY/ISIN mapping and
40 offline contract cases verified (246 focused regressions passed). No configured
account/session or actual daily sample; no SDK/MCP install, source activation,
dataset mutation or trading capability. M1 remains BLOCKED.

3 November IST — STK-004/014 [authenticated Breeze follow-up](STK-004-014-breeze-evaluation.md#authenticated-sdk-follow-up--3-november-2026-ist):
official SDK authentication and 41 actual INFY daily candles succeeded with three
bounded GETs; no duplicate labels/basic OHLCV failures, values discarded. Fresh
300 focused fixture tests passed separately. Private manual-session preflight,
GET-only transport, isolated SDK logging and durable local request budget added.
No source/grant activation or database access; raw/volume/action/calendar,
disclosure/time and retention requirements still block M1. M2/strategy/
operational/publication/admission/trading gates unchanged. PR35 remains draft.

3 November IST — STK-004/014 official-source qualification: `bda66eb` passed all
four exact CI jobs. Actual labels match all 41 regular NSE calendar sessions;
official SDK documents unadjusted history. Against actual NSE MCP EOD data,
closes match 41/41, but open 6/41, high 8/41, low 12/41 and volume 0/41.
[Full criterion matrix and source receipts](STK-004-014-breeze-evaluation.md#official-source-qualification-follow-up--3-november-2026-ist)
keep M1 BLOCKED on these discrepancies, rights/retention, complete disclosures,
settings and original clocks. No production behavior, grants or datasets changed.

3 November IST — STK-004/014 [three-source triangulation](STK-004-014-breeze-evaluation.md#original-eod--mcp--breeze-triangulation--3-november-2026-ist):
three original NSE Final INFY/EQ rows match MCP on all 15 OHLCV fields; Breeze
matches closes only (12 other mismatches), with nonconstant volume ratios.
Source classified UNQUALIFIED for M1; closing-only remains a provisional research
candidate. Auction/sampling alone is not a proved explanation. No production
change or stored source dataset. Exact `26ed321` CI passed all four jobs; PR35
stays draft/unmerged, with new documentation CI required separately.

3 November IST — STK-014/074/079 [takeover audit and real-data recovery](STK-079-takeover-audit.md):
root cause of the INFY 403 reproduced (retained 0013 schema lacks 0015 read fences).
Unmigrated databases now report "Database migration required" instead of a source denial,
with a Level 1/2/3 readiness banner. Read-only owner audit and copy-only migration rehearsal
scripts were added, plus an owner-gated multi-stream rule (`approved_v1`, off by default).
The rule combines only individually verified rolling streams that overlap and agree, and fails
closed on any conflict. Validated on invented rows only. The original database is unchanged, no
provider call was made, and M1 remains BLOCKED pending the owner rehearsal and approvals.

3 November IST — STK-079 pilot coverage: `/v1/real-research/coverage` and a panel show each
configured pilot company as readable, unavailable or denied, with plain reasons. These are
descriptive only and never actionable. The migration state no longer discloses the schema
version. One-page [owner approval sheet](STK-079-owner-approval-sheet.md), PROPOSED and not approved.

3 November IST — STK-079 corporate actions and unattended refresh tooling:
- Optional `corporate_actions` ingestion from the documented Upstox endpoint (append-only, grant-scoped, weekly per pilot stock). Only dividend cash is stored as arithmetic; split, bonus and rights ratios fail closed as `unsupported`. The company page lists observed ex-dates.
- `scripts/activate_pilot_launchd.py` activates the reviewed LaunchAgent only with the owner approval phrase and only at schema 0015.
- Default settings keep existing schedule hashes.
- Tested on fabricated payloads only. No provider call was made.

3 November IST — STK-079 owner usability:
- `scripts/owner_rehearsal.sh` and [Mac steps](STK-079-mac-steps.md) give a copy-paste rehearsal: one command produces three sanitized files. It was tested on a simulated 0013 database.
- Charts mark dividend and bonus/split ex-dates. These are labels only and never adjust prices.
- The pilot coverage panel adds a daily note covering refreshed, behind and not-readable stocks.
- The approval sheet is now versioned rules (`/v1/real-research/rules`). Private decisions and gate evidence are kept outside Git; approved rules stay inactive until every gate passes.

4 November — **STK-082 / D3-13 scoped descriptive release**: opt-in
`one_trailing_session_v1` permits one missing trailing verified session only after
single-batch provenance, authorization and boundary checks. Strict remains default;
readiness stays delayed, never current. Read-only INFY verification returns 43
historical chart points through November 3 against the November 4 closed session;
original evidence is unchanged. No provider/AI calls, policy activation, grant
changes, trading or admission. [Behavior, validation and remaining blockers](STK-082-delayed-descriptive.md).
M1 and full D3-13 acceptance remain blocked; owner PR review required.

4 November — **STK-083 / D3-04 + D3-09**: unified guarded INFY daily insight reuses
existing prices, indicators, facts and factual verifier; the actual stored batch
renders 43 bars, six descriptive indicators and 24 reported facts. AI/levels/news
qualification remains unavailable. New stored-only mode reuses D3-04 jobs and
launchd with a separate INFY label; tested offline, not activated. Provider/model
requests: zero; original evidence and 12-stock config preserved. M1/M2, ranking,
real OOS and trading/admission remain blocked. [Reuse, operation and acceptance](STK-083-automated-infy-research.md).

5 November — **STK-086 / D3-04 + D3-09**: stored-only INFY lifecycle/readiness
gate reuses original grants, revision provenance and scheduler fences; private
deployment manifests bind merged code and configuration. Finite calendar and
grant/retention expiry fail closed, with private health and existing receipts.
Read-only real preflight retains 43 delayed bars and unchanged evidence; inactive
current-main configuration awaits this correction's review/merge. Session rows
cannot establish new closed-date coverage: renewal remains explicitly blocked.
No provider/model calls, real database mutations or launchd activation.
[Operating notes and limits](STK-086-calendar-lifecycle.md).

5 November — **STK-093 / D3-09 real research workbench**: discovery/search/filters,
2–4 company comparison and authenticated private watchlist with notes/review dates
implemented. Real local browser acceptance: 12 configured, INFY 44 bars through
4 November, other 11 explicitly unavailable; note survives reload and company
navigation works. Saved scan names/ranks remain unavailable under existing lineage
gates. No source calls or market-evidence changes; STK-092 remains deferred.
[Delivery, private persistence and acceptance](STK-093-research-workbench.md).
Pending owner PR review; no current-market or actionable release claim.

6 November — **STK-094 / D3-03 + D3-04 + D3-09**: disabled-by-default Chartink
receiver, PostgreSQL candidate inbox/replay/recovery, existing stored-only research
integration and Candidates workbench implemented. Actual CSVs verified/imported:
3,094 matches / 457 stocks / 160 represented sessions; 5 November 35 candidates,
28 new versus previous results and seven continuing. All 35 lack usable stored
identity evidence; simulated INFY intake reuses verified identity and existing
44-bar descriptive analysis. Browser candidate/watchlist/legacy INFY acceptance
passed. Premium is not purchased; public deployment and real delivery validation
belong to a later activation milestone, not this ticket's corrected local DoD.
No provider/model calls, original-data mutation, trading or percentage revision;
overall planning baseline stays 46%. [Implementation, evidence and activation steps](STK-094-chartink-candidates.md).
Pending owner PR review; do not merge or start the next milestone.

11 November — **STK-095 / D3-03 + D3-04 + D3-09**: enriched CSV recovery and
synthetic-only versioned webhook enrichment implemented; real enriched webhook
shape remains unverified. Local acceptance: 1,047 unit / 26 script / 589 PostgreSQL
checks, migration lifecycle and real browser 35/28/7, watchlist, enrichment and
historical-clock INFY passed. Current-date INFY correctly blocks stale data,
identically to STK-094. PR/exact-head CI pending; hosting and webhook activation
remain disabled. Accepted overall baseline **49%**, no new percentage asserted.
[Evidence and deployment proposal](STK-095-chartink-integration.md).

11 November — **STK-096 / D3-03 standalone maintenance**: add slow-test and
per-phase timing diagnostics to disposable PostgreSQL migration validation; not
a new product milestone, with no test, migration, isolation, production-code or CI changes.

11 November — **STK-097 / D3-03 + D3-04 + D3-09**: separate disabled-by-default
receiver Compose stack, HTTPS route isolation, durable inbox, restricted role
grants, internal DB health and authenticated cursor-lag monitoring prepared.
Synthetic real HTTPS receiver → worker → separate PostgreSQL → browser/watchlist
acceptance passed locally; real enriched provider JSON and public activation remain
unverified. Full exact-head CI/owner review pending. No paid deployment or original
data mutation. [Operations and acceptance](STK-097-webhook-readiness.md).


11 November — **STK-099 / D3-03 + D3-04 + D3-09 + D3-12**: BookMyHost full-app
Compose overlay, private HTTPS, restricted same-host PostgreSQL notification bridge,
durable cursor recovery and verified non-overwriting migration tooling implemented.
595 PostgreSQL checks/zero skips and isolated full-stack/browser acceptance passed;
Mac schema-0016 restore preserved all 6,728 current rows, 70 tables and three sequences.
Read-only VPS preflight passes static budget; x86_64 representative load, encrypted
off-server recovery/alerts, owner review/cutover and genuine Mac-off delivery remain
gates. Production unchanged; no readiness percentage or real-research activation.
[Architecture, measurements and exact cutover/rollback](STK-099-bookmyhost.md).

12 November — **STK-099 / D3-03 + D3-04 + D3-09 + D3-12**, PR #48 review fixes:
watchlist export fails closed with audited empty opt-in; hosted rehearsal checks
readable configuration and actual evidence/permission paths; API paper operations
and audited queue/governance writes receive specific grants with mutation guards.
1,053 local unit checks pass; exact-head PostgreSQL/hosted/browser CI evidence is
recorded in PR #48. Production remains unchanged; release gates remain open.
13 November — **STK-095 / D3-03 + D3-04 + D3-09**, customized webhook rejection:
owner-supplied provider Test webhook verifies the 14-column row-array shape.
Versioned strict adapter, isolated test receipts (zero candidate/research/session
writes), opt-in private shape diagnostics and HTTP/DB/feed regressions prepared
in PR #49, separate from STK-099. Genuine alert compatibility/deployment remain
unverified; compatible consumers must precede receiver rollout. No production
change. [Evidence and gated deployment/rollback](STK-095-webhook-rejection.md).

13 November — **STK-095 / D3-03 + D3-04 + D3-09**, PR #49 P2 follow-up:
separate bounded transport/storage capacities and guard all enrichment decimal
arithmetic. Added batch/capacity and private durable rejection regressions.
No production changes; exact-commit CI evidence is tracked on PR #49.

13 November — **STK-095 / D3-03 + D3-04 + D3-09**, PR #49 migration follow-up:
add schema 0017 for bounded 1 MiB JSONB envelopes; Python checks identical PostgreSQL
size semantics. Both receiver inbox and private import database require migration
before activation. Preservation, exact boundaries and failed downgrade regressions
added; replay pages stay within the worker response cap. No production changes.

13 November — **STK-095 / D3-03 + D3-04 + D3-09**, PR #49 schema audit:
classified all 20 PostgreSQL failures; corrected explicit API/worker compatibility,
current-head assertions and historical fixture ancestry. Unknown schema versions
remain blocked; receiver least-privilege expanded-event regressions added.
Exact-head CI acceptance is tracked on PR #49; production remains untouched.

STK-095 / D3-03 + D3-04 + D3-09 consumer release preparation (13 November): located
and read-only verified the existing restricted Mac consumer credentials, original
receiver/cursor identity (0), scanner and pull-secret parity. Added an inactive
native supervisor with fail-closed rights/schema/grant checks, sanitized heartbeat,
singleton and bounded shutdown; no production activation. Launcher/monitor tests
and isolated PostgreSQL replay/recovery pass. A local synthetic restic encrypted
restore passes; independent off-server recovery/alert receipt is NOT established.
[Consumer cutover and scoped rights decision](STK-095-consumer-release.md): private
webhook callbacks are documented; durable retention/replication/recovery scope,
owner authorization, external recovery/monitoring and production cutover remain
gates. Existing review-pending rights and schema 0016 remain unchanged.

STK-095 PR #50 review follow-up: bounded preflight SQL, stop-during-preflight,
explicit cycle-timeout failure and inherited child singleton lock close confirmed
supervisor failure paths. Added abrupt-parent-death and timeout regressions.
Provider evidence checklist and external recovery/monitoring deployment worksheet
are documented; UI/watchlist selection is outside webhook-only release gates.
No production actions or provider approval were inferred.

13 November — **STK-095 / D3-03 + D3-04 + D3-09**, release acceptance follow-up:
the owner's new provider Test capture uses `7:43 pm`; the adapter incorrectly
pinned the first capture's `11:45 am`. Validate the documented clock grammar
while preserving exact placeholders, scanner checks, URL redaction and zero
candidate/research materialization. Local validation: 1,160 application/worker,
37 script and 14 PostgreSQL/HTTPS checks pass, including two-database replay and
cursor continuity. Exact-head CI and production Test acceptance remain pending;
provider Test data never establishes genuine-alert or real-market readiness.

13 November — **STK-094 / D3-03 + D3-05 + D3-09**, stored candidate swing review:
connect existing identity/Upstox descriptive-price validation to current price-check
ranking within a bounded UI page. Missing/stale/delayed inputs stay unranked;
volume and complete strategy signals remain unavailable. 1,168 unit, 12 disposable
PostgreSQL/API and two browser checks plus frontend build pass. Production read-only
check: three provider Tests, cursor/high-water 3, no genuine alert yet. STK-095 Test
acceptance remains passed; no production changes. Owner review/CI pending.
[Slice, limits and next price-refresh integration](STK-094-candidate-swing-review.md).

13 November — **STK-014 / D3-03 + D3-04**, after owner merged STK-094 PR #52:
bounded candidate price refresh reuses Upstox mapping/acquisition, grants, request
ledger and dated calendars. Durable jobs coalesce duplicate symbols, recover after
interruptions and atomically queue stored re-analysis after complete ingestion.
1,177 unit, 47 affected PostgreSQL/API tests and a real refresh-to-ranked-UI browser
flow pass using invented provider responses. No production activation or migration;
ordinary genuine-alert acceptance remains pending. PR #53 review reproduced and fixed
second-day batch ambiguity without changing immutable history. Latest validation:
1,177 unit and 80 affected PostgreSQL/API tests plus actual browser acceptance pass.
Candidates now expose refresh state, retry/failure details and timestamps. Owner merge
approval and new-head CI remain required before production activation.
[Implementation, operation and recovery evidence](STK-014-candidate-price-refresh.md).

14 November — **STK-099 / STK-014 · D3-03 + D3-04 + D3-09 + D3-12**:
merged main CI passed. One authorized Upstox diagnostic confirmed upstream missing
13-Nov data (HTTP 200, raw 12-Nov only, aged cache); no current-data admission.
A new x86_64 VPS project restored 70 tables / 6,737 rows / three sequences and the
existing watchlist, passed private browser and 24 concurrent-load reads, worker
restarts and recovery restore. Minimum sampled headroom 1,008.6 MiB; no OOM.
Online snapshot backup and opt-in scoped hosted refresh are implemented for review.
Live services/cursor 3/schema 0017 preserved; no genuine candidates or full cutover.
[Evidence, limitations and release conditions](STK-099-restored-rehearsal.md).

## Retained PR #58 reconciliation evidence

Current delivery — **STK-094 / D3-05 Quant horizon policies + D3-09 UI** (16 November).
PR #57 is merged at main `0fe21361b590992dd9c96f346fb10ff1891566e7`.
A confirmed rolling-price integration defect is fixed for review: Candidates, open
company research and the watchlist now select the same complete refreshed batch.
Historical/publication reads, source grants, immutable revisions and fail-closed
qualification are preserved. **169 focused tests passed**, including actual Chromium
with isolated synthetic provider/DB fixtures. No live application deployment.
[Defect, tests and dated live evidence](STK-094-candidate-research-continuity.md).
Read-only 16-Nov evidence: VPS non-Test events **0**; Mac candidates **0**, cursor
**3**, revisions **2,648**; latest stored INFY session **4-Nov**, no current qualified
batch. Genuine end-to-end acceptance remains pending. Planning baseline **58%**.

## CURRENT — 16 November 2026 · STK-094 / D3-05 + D3-09 Candidate research

Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md). [SIMPLE-BOARD](SIMPLE-BOARD.md)
is the canonical task board; [PROJECT-HANDOFF](PROJECT-HANDOFF.md) provides product
and component context; [WORK-HANDOFF](WORK-HANDOFF.md) records execution continuity.
Update board and project handoff together on material state changes.
**58% remains the owner-specified planning baseline**, not measured live readiness.

| Component | Actual current state | Remaining gate |
|---|---|---|
| STK-095 | VPS receiver/inbox/proxy and native Mac consumer; schema 0017; real provider-Test acceptance passed. | Ordinary genuine alert; no manufactured candidates. |
| STK-094 / STK-014 | PR #52/#53 merged; native bounded INFY refresh; stored-price EMA/breakout and page-scoped ranking implemented. Shared current-batch reader fix prepared for review; synthetic candidate → research → watchlist acceptance passed. | Complete current qualified price batch and genuine candidate → analysis → UI. |
| STK-099 | PR #48/#54 merged; 14-Nov representative VPS restore/resource/recovery evidence retained. PR #57 operations tooling/checklist merged; no activation. Infrastructure work deferred by current owner direction. | Off-server restore/key custody, external alert/host-loss test, separate release authorization, genuine Mac-off acceptance. [Issue #47](https://github.com/gaganjawa/stock-discovery/issues/47) remains open. |
| D3-13 | PR #55 continuity and #56 CI selection merged. | Integrated three-horizon live release, real research/policy/forward-evidence gates remain capability-specific. |

**Live VPS, 16-Nov 06:06:20 UTC:** receiver/proxy/database still running; receiver
and database healthy, receiver image and start time unchanged. Restic 0.19.1 was
installed at a separate versioned tools path. No application service restart,
migration, cursor update, volume change, provider request or cutover occurred.
**Current application evidence, 16-Nov 06:41–06:49 UTC:** both DBs schema 0017;
VPS three provider-Test events, zero non-Test events and high-water **3**; Mac cursor
**3**, events **3**, candidates **0**, revisions **2,648**, refresh jobs **0** and
zero provider quota requests in preceding 24h. Consumer PID 8125 and refresh PID
8129 remained running with one launch each. Latest stored INFY price session is
**4-Nov**; other 11 stored listings end **23-Oct**. No complete current OHLCV batch
or live candidate/UI acceptance is claimed. No production writes or restarts.

Initial Upstox HTTP 200 gave 30 validated bars but omitted expected 13-Nov; **zero
ingested**. The one authorized diagnostic also omitted it. Upstream incompleteness
is observed; cache lag remains an inference. Existing retries: 900 seconds, at most
three per eligible job. Missing/stale/insufficient evidence stays unranked.

**Reused acceptance:** 14-Nov isolated VPS restore preserved 70 tables / 6,737 rows /
three sequences and watchlist bytes; browser, 24 company reads at concurrency four,
worker restart and second recovery passed. Minimum available RAM 1,008.6 MiB,
no OOM. This was stored-data/idle-refresh rehearsal, not off-server recovery or
live acquisition. No repeat VPS/browser rehearsal. The prior 15 operations tests used
synthetic transports/databases; they do not prove external delivery or remote restore.

| Priority | Tickets | Next outcome |
|---|---|---|
| **P0** | STK-014 / STK-094 / STK-095 | Next ordinary EOD alert → identity/session/symbols → durable candidate/cursor → complete eligible refresh → re-analysis → authenticated Candidates UI. Provider Tests excluded. |
| **P1** | STK-014 / STK-094 | Review shared-batch research fix, then expose per-candidate refresh eligibility and out-of-universe reasons; preserve bounded approved acquisition scope. |
| **P2** | STK-014 / STK-054 / STK-079–081 | Qualify volume and remaining strategy/research inputs for daily usable swing and all three horizons; no invented BUY, levels, sizing or performance. |

**Application acceptance gaps:** no genuine alert yet, no current complete stored
INFY price batch, adjusted volume basis remains unqualified. Existing acquisition
scope is INFY. No additional owner authorization was needed for this software fix.
Infrastructure gates remain recorded in [STK-099](STK-099-release-prerequisites.md)
but are outside this task and do not block independent application implementation.

**Current synthetic validation:** four new PostgreSQL/API/negative cases including
real Chromium candidate → open research → save/review watchlist passed; 165 affected
unit/integration regressions passed. These do not establish genuine market acceptance.

**Exact next executable task — STK-014:** after review/merge of the current
STK-094 fix, expose per-candidate refresh eligibility/out-of-universe reasons using
the existing worker configuration and job contracts. Observe the next ordinary
eligible EOD alert independently; do not manufacture events or expand provider scope.
Volume-qualified swing checks remain subsequent work. Owner monitors this PR's CI;
do not wait, merge, deploy, interrupt live workers or start infrastructure work.

## HISTORICAL — prior 16-Nov operations delivery

