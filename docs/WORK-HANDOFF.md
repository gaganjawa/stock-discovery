# Stock Discovery — work checkpoint

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

## CURRENT — 15 November 2026 · STK-099 / D3-12 Private operational pilot

Use [SD ARCH 3.0](SD-ARCH-3.0.md) for requirements and
[SIMPLE-BOARD](SIMPLE-BOARD.md) as the canonical task board;
[PROJECT-HANDOFF](PROJECT-HANDOFF.md) is the persistent product/component context.
**Overall planning
baseline is 58%, specified by the owner on 15 November**, superseding the reported
57%; it is not a calculated release-readiness or profitability metric.

**Previous merge evidence:** PR #54 merged as
`fbd841aa9948949dfed655e462ea292b9204b007`. All four required checks passed at its
final head `bf12c5394a678633f8426f3fe06c9040a246fd03`
([PR CI](https://github.com/gaganjawa/stock-discovery/actions/runs/43717712492)).
The [exact-merge main run](https://github.com/gaganjawa/stock-discovery/actions/runs/43718688001)
was still running at reconciliation; do not infer its result from PR checks.
PR #53 bounded refresh, PR #52 candidate analysis, PRs #49–51 provider-Test fixes
and PR #48 hosting foundation are also merged. [Issue #47](https://github.com/gaganjawa/stock-discovery/issues/47)
remains open; its schema-0016 / 6,727-row starting point is historical.
[PR #55](https://github.com/gaganjawa/stock-discovery/pull/55) is merged with all four
final checks passed; the current CI optimization requires owner review/new-head CI. Owner monitors CI; do not wait, merge or cut over.

**Production, last verified 15-Nov 13:01 UTC:** BookMyHost VPS receiver/proxy/inbox
and Mac application DB/UI/API remain split. Both databases schema **0017**;
consumer PID **8125**, refresh PID **8129**, one launch each and exactly one refresh
process. Mac cursor **3**, events **3**, genuine candidates **0**, revisions **2,648**;
no refresh jobs or provider requests in the preceding 24 hours. Existing restricted
`stk_price_refresh` worker is active for INFY. No restart/deployment/provider call
was performed for this documentation follow-up.

Real provider-Test acceptance **passed** (202, durable receipt, deduplicated retry,
cursor advancement, no candidate/session/research writes). Ordinary genuine-alert
acceptance is **pending**. Initial Upstox HTTP 200 returned 30 validated bars but
missed expected 13-Nov; **zero ingested**. One authorized narrow diagnostic also
omitted that date. Cache age supports lag but does not prove the provider's internal
cause. Keep incomplete/stale evidence unranked; reuse 900-second readiness retries,
maximum three attempts per eligible job. No manufactured candidates or extra probes.

**Completed rehearsal, not production cutover:** 14-Nov isolated x86_64 VPS restore
preserved 70 tables, 6,737 rows, three sequences and existing watchlist. Actual private
browser, 24 company reads at concurrency four, worker restarts and second recovery
restore passed. Minimum sampled available RAM 1,008.6 MiB; no OOM. Rehearsal stopped;
live services unchanged. Prior 21 focused tests remain recorded; none rerun here.
See [exact evidence and limits](STK-099-restored-rehearsal.md). No repeat VPS rehearsal.

| Priority | Tickets | Required next outcome |
|---|---|---|
| **P0** | STK-014 / STK-094 / STK-095 | Genuine EOD alert → original identity/session/symbols → durable candidate/cursor → complete qualified refresh → re-analysis → authenticated ranked Candidates UI. Provider Tests excluded; ranking remains page-scoped. |
| **P1** | STK-099 | Encrypted off-server restore, key custody and external alerts using merged PR #54 tooling; separately authorized Mac-independent cutover and genuine Mac-off acceptance. |
| **P2** | STK-014 / STK-054 / STK-079–081 | Volume-qualified swing inputs, remaining real research/policy gates and complete three-horizon release; no invented BUY, levels, sizing or performance. |

**Verified release gates / owner decisions:** off-server restore/key custody and
external alert delivery are unverified (no restic executable or Stock Discovery
backup/monitor units found during VPS preflight). Existing same-host recovery and
idle-worker load do not establish those gates or active-acquisition capacity.
Confirm missing private destination/custodian inputs if needed; use existing tools.
PR #54 is merged; full cutover still needs separate owner authorization. Preserve webhook
URL, secrets, scanner identity, schema, volumes, cursor and immutable history; no
new migration or full deployment is implied. Do not reopen approved provider scope.

**Exact next executable task — STK-099:** inspect existing private backup/alert
configuration read-only and prepare the existing restore tooling against an isolated
off-server recovery target. Record missing destination/key-custodian decisions without
exposing secrets, making paid requests or sending alert messages. This CI change remains for
owner review/new exact-head CI; owner monitors it without waiting or automatic merge.
After a separately authorized cutover decision, persistently stop both Mac workers,
verify singleton release, transfer fresh DB/watchlist/cursor/quota state to new VPS
targets and preserve rollback before activation. Never acquire concurrently against
divergent Mac/VPS quota ledgers. Keep the existing receiver running.

## HISTORICAL — preserved execution checkpoints

The dated records below describe their original milestones. Their earlier waits,
PR states and activation restrictions do not override the CURRENT summary or newer
owner authorization. Prior test evidence remains unchanged and scoped as originally
recorded.

## D3-08 — STK-052/070/071/072 · 17 October 2026

Verified PR #7 merge `d7f3381` against origin/main. [Bounded research and semantic judge](D3-08-bounded-research.md) reuse D3-07 retrieval/contracts/budget reservations, enforce four database-read-only tools and a 120-second default deadline, and persist immutable validation/judge reports. The 54-case paired mock evaluation has provisional synthetic labels, not human calibration or evidence of agent superiority. All outputs remain shadow/non-actionable. No paid call, source activation, deployment or broker action. Preserve unrelated WIP. Owner authorized the connected GitHub account for this PR with Codex commits. Deliver on the ticket branch and stop; D3-09 requires owner confirmation.

## D3-07 — STK-052/053/074 · 17 October 2026

Verified D3-06 merge `5be2cac` against origin/main. [Hybrid RAG](D3-07-hybrid-rag.md) adds rights-filtered structured/PostgreSQL lexical/local semantic retrieval, deterministic ranking/calculations, strict fixed research validation, abstention and durable all-component budgets. Research stays shadow/non-actionable; no paid model or real source is activated. Existing synthetic workflows and unrelated WIP remain intact. Owner authorized the connected GitHub account for this PR, with commits attributed to Codex. Deliver the STK-052/053/074 branch for review; stop after D3-07. D3-08, publication integration and existing runtime grant blockers remain later dependencies.

## D3-06 — STK-046–051 · 17 October 2026

Verified PR #5 merge `ad1da0b` against origin/main. [Evidence ingestion foundation](D3-06-evidence-ingestion.md) adds bounded automatic mock feeds, immutable content/chunks/facts/claims, source permissions and point-in-time retrieval, revisions/quarantine and D3-04 event dispatch. Existing synthetic workflows and unrelated WIP are preserved. No real provider, paid API, RAG/agent, deployment or broker operation. Real format/provider activation and the prior restricted-runtime grants remain explicit blockers. Owner authorized the connected GitHub account for this PR, with commits attributed to Codex. Deliver on the STK-046–051 branch and stop after D3-06.

## D3-05 — STK-028–032/054/058/076 · 17 October 2026

Owner explicitly authorized D3-05 after PR #4 merged at `08812db`. [Quantitative policies](D3-05-quant-policies.md) implement three deterministic engines, immutable configuration manifests, as-of evidence/financial calculations, valuation sensitivity, calendar endpoints and research/admission separation. Legacy swing remains unchanged. All shipped settings are fictional; real-market acceptance is not complete. No runtime grant change, paid API, RAG/agent, broker action or deployment. Preserve unrelated WIP. Deliver on the ticket branch for owner review and stop after D3-05; D3-06 requires confirmation.

## D3-04 — STK-017/058/060/073 · 16 October 2026

PR #3 merged at `e5bc9ea`; the owner authorized D3-04. [Scheduler delivery](D3-04-scheduling.md) adds durable calendar occurrences, dependency jobs, fenced atomic results, event hooks, frozen-universe counters and an opt-in fictional unattended worker. Runtime-role access remains blocked by automatic approval review; `deploy/roles.py` and database grants are unchanged. No owner key, paid service or deployment is used. Unrelated WIP and historical evaluation fixtures remain preserved. Open a ticket-branch PR; wait for owner review/merge and confirmation before D3-05. Earlier entries describe historical checkpoints.

## D3-03 — STK-014/015/019–024 · 15 October 2026

After PR #2 merged, the owner authorized D3-03. [Delivery details](D3-03-revision-ingestion.md): additive discovery schema, rights-checked paged adapter boundary, immutable source revisions and snapshots, quarantine, raw/adjusted separation and recovery tests. Real sources remain disabled. The supplied OpenAI key is not read, committed or used. Application database and unrelated WIP are unchanged. Deliver as a ticket-branch PR; wait for owner merge and confirmation before D3-04. Older status entries below are historical.

## D3-02 — STK-004/005/006/007 · 15 October 2026

Owner authorized D3-02 after the board PR merged. The ticket branch contains a [source feasibility review](D3-02-source-feasibility.md), use-specific rights gate, strict schemas, fictional fixtures and 52 denial/cleanup tests. Real permissions, quotes, coverage samples and regions remain explicit activation blockers. No live provider or paid AI was activated. Deliver through a review PR; wait for owner merge and confirmation before D3-03. Unrelated WIP and historical fixtures are preserved. Earlier “D3-02 unstarted” statements below describe prior checkpoints.

## Owner review workflow — 15 October 2026

Use ticket-named branches and PRs for all new work. Never push directly to main or merge PRs. The owner reviews, merges and confirms before the next package starts. See [repository rules](../AGENTS.md) and the [SD ARCH 3.0 board](SIMPLE-BOARD.md). D3-01 was already on main before this instruction; it is not being rewritten. D3-02 remains unstarted and awaits authorization. Older workflow/scope notes below are historical.

## Current scope — 15 October 2026

[SD ARCH 3.0](SD-ARCH-3.0.md) is the authoritative design specification. The subsequent owner instruction authorized repository integration and **D3-01 only**. [D3-01 contract amendment](contracts/v2/README.md) is implemented: strict v2 recommendations, all three horizon profiles, policy/outcome schemas, research/admission separation, synthetic fixtures and deterministic compatibility tests. D3-02 through D3-13 remain unstarted. No real data source, paid AI, hosting or broker action is activated.

Validation: 141 application/worker tests passed in the isolated delivery snapshot (including 83 D3-01 cases); 11 database cases skipped without a test database; 7 script tests passed. All six historical fixtures match their original hashes. Schema regeneration, whitespace checks and the isolated delivery frontend build pass. The working tree additionally contains three passing unrelated WIP tests; that WIP is excluded from the commit. Existing unrelated application and untracked work are preserved and excluded from this delivery. Full automatic discovery, RAG/agents/judge, operational paper tracking and deployment remain later packages. See the contract document for precise scope and limitations.


**Current progress view: [Lightweight board](SIMPLE-BOARD.md).** Owner requested Markdown tracking on 14 October 2026 to avoid hosted-board overhead. Use this file for routine overall/feature status; hosted-board synchronization is no longer a prerequisite for local status reporting. Existing historical sync-pending notes below remain historical.

## Active scope reset — 14 October 2026

Owner explicitly selected local daily-swing MVP software first, with hosting and broader v1.0 enhancements deferred. Finish this consolidated batch rather than stopping after each small ticket. Added optional LLM explanations (disabled by default, no paid calls), preserved local .env with blank key fields, and local startup helper. See [MVP handoff](DAILY-SWING-MVP.md). Implementation `a9a3eb7` passed full CI (58 application, 11 database, 7 script tests, build/browser). Local stack is running and API/UI/database/worker/login checks pass. Local synthetic MVP software acceptance is complete; live LLM access remains untested without an owner key. Earlier repeated wait-for-go milestones are historical; pause only after the current consolidated handoff.

## STK-042 audit reproducibility — 14 October 2026

Frozen split policy and content-based audit identity added; duplicate IDs rejected and unknown split policies unavailable. Implementation `32c4416` passed full CI: 55 application tests, 11 database cases, build and browser acceptance. Trial ledger/untouched-test controls remain open. Pause after status.

## STK-042 chronological audit — 14 October 2026

Synthetic split assignments and conservative label-window exclusions are implemented and visible. Implementation `1fa5ca0` passed full CI: 53 application tests, 11 database cases, build and browser acceptance. This is an assignment audit, not training or EP-1 acceptance; STK-042 stays partial. Pause after status.

## STK-042 validation visibility — 14 October 2026

Grouped validation results, sample sizes, descriptive intervals and limitations now appear in the scorecard. Implementation `c9d3ecf` passed full CI: 51 application tests, 11 database cases, build and browser acceptance. STK-042 remains partial for real-history and chronological/overlap-aware acceptance. See [STK-042](STK-042.md). Pause after status.

## STK-041 scorecard visibility — 14 October 2026

Counts, traded notional, closing-mark exposure and admission/exclusion details are now visible with definitions and unavailable states. Implementation `d7ab84f` passed build and full CI: 51 application tests, 11 database cases and browser acceptance. STK-041 remains partial. Pause after status.

## STK-041 scorecard selection — 14 October 2026

Version-group selection implemented using frozen dataset/code/strategy/configuration. 51 local tests/build passed; implementation `bc57f40` passed full CI including browser acceptance and 11 database cases. STK-041 remains partial for real benchmarks/full portfolio acceptance. See [STK-041](STK-041.md). Pause after the status report.

## STK-044 versioned reruns — 14 October 2026

New jobs pin code/strategy/configuration versions; upgrade reruns preserve prior results and mismatching workers reject pinned jobs. 50 local tests passed; implementation `1544f45` passed full CI including 10 database cases and browser acceptance. No external deployment. Pause after the result.

## STK-044 continuation — 14 October 2026

Job inspection and failure-inclusive audit export implemented; 50 local application tests and frontend build pass. Implementation `ae607b2` passed full CI including the nine-job batch/export browser workflow and database failure checks. See [STK-044](STK-044.md). Hosted sync pending for STK-033/043/044; pause after status.

## STK-043 continuation — 13 October 2026

Owner authorized another bounded task. Replay now exposes its supported strategy version and rejects unsupported versions. 49 local tests/build passed; implementation `83f8fa8` passed full CI including browser acceptance and database migrations. See [STK-043](STK-043.md). Pause after status report. Hosted board synchronization remains pending for STK-033/043.

## STK-033 continuation — 13 October 2026

Owner authorized the next bounded task with minimal usage. STK-033 now displays frozen rule results and complete version provenance; see [acceptance notes](STK-033.md). Implementation `039c492` passed full CI including browser acceptance and migrations. Hosted board synchronization remains pending; local status is Ready for Release for synthetic scope only. Stop after reporting this task and wait for the owner's next go. Foundation external gates remain unchanged.

## Latest continuation — foundation work complete to external gates

Owner approved Hetzner CX23/Linux/Compose and encrypted restic/B2; do not reopen hosting alternatives. STK-008 is Done. STK-009/016/017/018 remain PARTIAL (Backlog + Blocked), with secure private configuration, runtime privileges, worker/monitoring controls, encrypted local recovery and rollback verification delivered. See [current STK-018 acceptance](STK-018.md#current-foundation-acceptance--supersedes-historical-configuration-findings-below) for exact tests, commits and remaining gates. Native AMD64 CI evidence is retained in docs/licenses/linux-amd64-6e3886d.json.gz; no blanket licence clearance.

Hosted board updates for these five tickets were saved and verified after reload. No purchases, B2 connection, external deployment or accepted release tag. Earlier unresolved-provider and configuration-gap descriptions below are historical. Unrelated .idea/, main.py and root pyproject.toml remain untouched.

**Owner instruction: wait for explicit go after the current foundation status report.** Do not start another milestone or provision services automatically. Required before provisioning: region, final checkout price, backup-key custody and explicit authorization. Remaining deployment gates include native/host licences, actual private HTTPS/firewall, B2 disaster recovery and external alert/dead-man acceptance.

Local preview: from this repository, use the existing ignored local .env owner key and run `COOKIE_SECURE=false APP_ORIGIN=http://127.0.0.1:5173 docker-compose up --build -d`, then open http://127.0.0.1:5173. Never carry the HTTP override to private hosting. Isolated verification containers are stopped after testing; their explicitly named test volume is retained, not substituted for preview data.


## Hosted tracking synchronized — 12 Oct 2026

39 tickets synchronized and their saved fields verified after reload; 51 unrelated tickets unchanged. See the [local Kanban synchronization record](stock-platform-kanban-plan.md#hosted-board-synchronization--12-oct-2026). Existing Done and synthetic Ready for Release statuses retained. Partial work uses Backlog + Blocked (not Done); no tickets remain In Progress or Review/Test. STK-004–008 remains outstanding, STK-008 not started. No deployment/tag or application changes. Historical notes below about the hosted board being untouched are superseded by this synchronization.

Current release decision: **PARTIAL**. [STK-009 software audit](STK-009.md) records dependency inventory, corrected browser notices and remaining native/platform licence evidence gaps. See [STK-018 acceptance, release notes and recovery/rollback runbook](STK-018.md). Local synthetic preview verification passes; private deployment and formal release gates remain open.

## Verification update — 12 Oct 2026

- Replay root cause: global table margins/borders reached Lightweight Charts internal table. With an unconstrained autoSize host this formed a resize feedback loop: measured chart height grew 48px per two frames, moving the reveal button continuously. No animations or DOM replacement were observed during measurement. Fixed a 340px chart host and scoped table styles to application tables; added geometry assertions without changing timeouts or forcing clicks. Replay fix: `17e4300`.
- Focused headed Replay test passed (1.9s); full E2E suite passed (one workflow, 1.7s), and passed again after runtime changes. Production frontend build passed.
- Python regression: 42 passed; 7 PostgreSQL cases passed separately. Migration upgrade/repeat upgrade/downgrade/re-upgrade and intentional atomic failure rollback passed. Original contract, evaluation and capital/risk fixtures and two smoke-script tests passed.
- Full Compose source rebuild passed; migration exited 0, database healthy, API/UI/worker smoke passed. Running worker completed a queued synthetic scan for three instruments. API and worker run as UID/GID 10001; worker now receives CODE_VERSION.
- Authentication now rejects non-ASCII invalid credentials with 401 rather than raising a server error. Tests cover expiry, tampering, key rotation, fail-closed configuration and cookie origin protection. Local access key is ignored, owner-only (0600), and absent from tracked files.
- Backup was restored into a new disposable database with matching hashes for every research table; disposable restore database removed and services restarted. The verification dump is a temporary local artifact, not an operational backup policy.
- GitHub CI passed for `067860fd16b3ee26d207e4bd67d47935a448d4d4`: [verified run](https://github.com/gaganjawa/stock-discovery/actions/runs/38176118150). The old WIP baseline `002ddf0` had failed CI.

Remaining release limits: synthetic-only scope; real source rights/imports, full corporate actions, market benchmark/EP-1 acceptance and full notice audit remain unresolved. Before external deployment, configure HTTPS/secure cookies, strong database credentials and a separate least-privilege runtime database role (Compose currently shares the bootstrap owner), login abuse controls, and encrypted off-host backups with retention/restore procedures. Nginx retains its standard root master/non-root worker model. No release tag, external deployment, live feed, broker orders or Kanban changes were made. These verification results do not imply full release readiness.

The earlier checkpoint below is historical; the checks above supersede its pending local-verification notes.

Paused at the owner's request to commit completed work separately from work in progress. No v0.2 release tag or external deployment was created.

## Completed and validated implementation

- M1: availability-aware clocks/adapters, immutable decisions/outcomes, point-in-time identities/universe, synthetic raw daily history, PostgreSQL ingestion, dataset manifests and quality/chronological gates. STK-014, 015, 019, 021–024 are Ready for Release for synthetic scope. STK-020 remains partial: known-action price normalization and conservative exclusions exist; full action execution and real exchange imports do not.
- M2: deterministic SMA/EMA/ATR, relative volume and prior-window breakout; frozen EMA/volume/breakout BUY/WAIT/INSUFFICIENT_EVIDENCE strategy; entry/stop/target/expiry and Decimal cash/risk/exposure sizing. STK-028–032 implemented for synthetic scope; private release acceptance pending.
- M3: persisted freeze/reveal, daily fills/gaps/expiry, date-effective fictional fees/slippage, ambiguity and missing-data handling, unchanged STK-002 metric parity. STK-037–040 implemented for synthetic scope. STK-041/042 have core metrics, a predeclared single-position portfolio and grouped descriptive reports, but full market/benchmark/EP-1 acceptance remains partial.
- Completed-work checkpoint: `62a9860` (portfolio/report tests and PostgreSQL ingestion/service tests pass).

## Separate WIP snapshot

Authenticated owner sessions and API routes; persistent leased/retried jobs; daily synthetic scans, replay jobs, sample batches and audit export; API-backed React Dashboard/Research/Replay/Scorecard; Lightweight Charts attribution; Portfolio/IPO future placeholders; Compose migration service; browser test/CI wiring; backup/restore verification script; source-rights register.

These changes are committed as WIP, not completed tickets. Main remaining checks: browser acceptance; final rebuilt-stack smoke test; executing backup/restore; runtime privilege/security review; final CI; release documentation/rollback acceptance. API/UI and worker files changed after the first local image build, so the running stack may lag the saved source until rebuilt. The test browser download was cancelled at this checkpoint; rerun installation before browser tests.

## Verification recorded

- Latest full local Python run: 40 passed, 7 database cases skipped in that unit-only invocation.
- Separate database migration run: 7 integration cases passed; upgrade, repeat upgrade, downgrade, re-upgrade and intentional atomic failure rollback passed.
- Additional checkpoint: 4 portfolio/report/metric parity tests plus 2 PostgreSQL ingestion/service tests passed.
- React production build passes. Dependency install audit reported 0 vulnerabilities; this is not a complete security audit.
- Last confirmed green GitHub CI: `0603132` (replay milestone). New checkpoint CI must be checked after push.
- Local Compose build/start succeeded, bound to loopback. Browser workflow and backup/restore have not been executed successfully. No public deployment, real provider, broker order or paid service activated.

## Resume / local preview

Repository: `/Users/gaganjawa/Documents/Code/stock-discovery`.

An owner-only `.env` was generated locally with a random owner access key; it is ignored by Git and Docker build context. Read the key locally to sign in; never commit or send it. Local HTTP uses `COOKIE_SECURE=false` and `APP_ORIGIN=http://127.0.0.1:5173`; external deployment requires HTTPS and secure cookies.

```sh
docker-compose up --build -d
# Open http://127.0.0.1:5173 and sign in with the local AUTH_TOKEN.
# Dashboard: Load synthetic history; Replay: choose instrument/date,
# Freeze recommendation, then Reveal future prices and outcome.
cd frontend
npx playwright install chromium
npm run test:e2e
```

Before release, set CODE_VERSION to the tested commit, rebuild, rerun migrations/smoke/browser tests and verify backup into a disposable database. The current backup script does not encrypt off-host copies. No hosting/backup provider or source subscription has been selected.

## Copy-ready Kanban update

STK-014/015/019/021–024/028–032/037–040: synthetic implementation validated; Ready for Release, not Done. STK-020/041/042: partial with documented limits. STK-016–018/033/043–045: WIP/release verification pending. STK-004–008: source/account/hosting permissions or decisions unresolved; real integrations disabled. STK-009: chart attribution included; full notice audit pending. Original completed tickets remain unchanged. Hosted Kanban was not modified.

Unrelated `.idea/`, `main.py`, and root `pyproject.toml` were preserved and excluded from these commits.
