# Stock Discovery — project handoff

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
Planning baseline remains **58%**. Owner monitors CI; do not wait or merge.

Requirements: [SD ARCH 3.0](SD-ARCH-3.0.md); canonical task status in
[SIMPLE-BOARD](SIMPLE-BOARD.md). Historical evidence retains its original scope.

## Objective and horizons

Automatically discover eligible NSE cash equities, validate immutable market and
company evidence, apply deterministic quantitative/risk rules, add grounded bounded
research, and expose evidence-backed decisions with measured paper outcomes.
No picks is a valid outcome. Manual uploads are not the intended daily workflow.

| Horizon | Holding period | Reassessment / emphasis |
|---|---|---|
| Swing | 2–10 trading days | Each completed exchange session; trend, breakout, liquidity, volatility and catalysts |
| Short term | 1–3 calendar months | Weekly; earnings, business changes, valuation and price confirmation |
| Long term | 1–5 calendar years | Monthly; financial quality, durability, governance and thesis evolution |

Material events also trigger reassessment. BUY, WATCH, AVOID and INSUFFICIENT
EVIDENCE are the target research outputs; research ranking does not authorize
portfolio admission or broker orders. The first usable slice is daily swing;
full eligible NSE coverage and all three horizons remain the product objective.

## Architecture and deployed state

React/TypeScript UI → authenticated FastAPI → PostgreSQL and private artifact/
watchlist files. Python workers reuse shared domain analysis, immutable revisions,
calendar/grant checks, durable leases, quotas and retry/recovery contracts. No new
queue service or duplicate acquisition subsystem is needed.

Current production is split: BookMyHost VPS Caddy/receiver and inbox PostgreSQL;
Mac application PostgreSQL, UI/API, one Chartink consumer and one restricted
`stk_price_refresh` worker. Both databases are schema **0017**. The purchased
BookMyHost host supersedes the architecture's historical Hetzner selection for
deployment; do not reopen host selection. See [current STK-099 release prerequisites](STK-099-release-prerequisites.md).
The original [hosting runbook](STK-099-bookmyhost.md) retains historical evidence.

Read-only evidence at **2026-11-16T13:42–13:45Z**: consumer PID **8125**, refresh PID
**8129**, one launch each and exactly one matching refresh process; latest consumer
cycle completed normally. Mac cursor **3**, events **3**, genuine candidates
**0**, revisions **2,648**. No refresh jobs or provider requests in the preceding
24 hours. Preserve webhook URL, scanner identity, secrets, volumes, event history,
immutable revisions and cursor. No production change is authorized by this handoff.

STK-095 real provider Tests passed HTTP 202, durable receipt, deduplicated retry,
consumer cursor advancement and zero candidate/session/research materialization.
Genuine market-alert acceptance remains **pending**. Tests do not count as candidates.
A request reached validation at **16-Nov 11:30:04.603766 UTC** and was rejected with
`invalid_columns_fields`; its original JSON was not retained. Durable raw intake and asynchronous quarantine/replay are
prepared in PR #59, not deployed. No specific column incompatibility can yet be established.
Latest complete stored INFY session is **4-Nov**, stale against 16-Nov; current
OHLCV qualification remains unavailable. Scanner authorization expires 18-Nov
12:11:49 UTC. [Exact evidence and scoped release](STK-095-private-rejections.md).

The live INFY refresh scope uses the existing NSE EQ mapping, grants, restricted
role and account quota ledger. Initial Upstox HTTP 200 returned 30 validated bars
but omitted expected **13 November**; **zero bars ingested**. The one permitted
additional diagnostic returned only 12-Nov for a 12–13-Nov inclusive request,
with cache Age **56,991 seconds**. Upstream incompleteness is observed; cache lag
is an inference, not a proved internal cause. No response stitching or incomplete
current-data admission. Existing readiness retries are 900 seconds, at most three
attempts per job; no genuine candidate means no forced job or diagnostic retry.

## Merged, in review and acceptance evidence

PR #54 merged as **`fbd841aa9948949dfed655e462ea292b9204b007`**; its final
PR head `bf12c5394a678633f8426f3fe06c9040a246fd03` passed
[all four required checks](https://github.com/gaganjawa/stock-discovery/actions/runs/43717712492).
PR #55 continuity and PR #56 CI selection are merged; PR #57 operations prerequisites are merged as `0fe2136`.
The earlier exact-merge CI observations retain their dates in the board/work history;
this task makes no new CI-success claim from a prior PR run. Current application
changes require their own exact-head checks; owner monitors without waiting.

| Delivery | State / evidence |
|---|---|
| PR #48 · STK-099 | Merged `f8f930d`; private hosting overlay, durable same-host bridge and restore tooling. Full cutover not performed. |
| PRs #49–51 · STK-095 | Merged; schema-0017 envelope support, controlled Mac consumer and provider-Test time fix. Provider-Test release accepted; genuine alert pending. |
| PR #52 · STK-094 | Merged `9196e9d`; candidate → stored-price qualification → EMA10/EMA30/prior 20-session high → page-scoped descriptive ranking. |
| PR #53 · STK-014 | Merged `098ba86`; bounded refresh, mapping, quotas, deduplication, interrupted-job recovery and durable re-analysis after complete ingestion. Mock-provider browser acceptance passed; current live ingestion not yet qualified. |
| [PR #54](https://github.com/gaganjawa/stock-discovery/pull/54) · STK-099/STK-014 | Merged `fbd841a`; online snapshot backup and optional hosted refresh integration are on main. Final PR head `bf12c53` passed unit/PostgreSQL/UI/aggregate checks. Full production cutover remains unauthorized. |
| [Issue #47](https://github.com/gaganjawa/stock-discovery/issues/47) · STK-099 | Only open GitHub issue at reconciliation. Its 11-Nov schema-0016 / 6,727-row starting point is historical, not a current production count. Cutover and genuine Mac-off acceptance remain open. |

The **14-Nov isolated VPS rehearsal** restored 70 application tables, 6,737 rows
(including alembic_version), three sequences and the existing watchlist. Actual
authenticated browser, 24 company reads at concurrency four, worker restarts,
fingerprint preservation and a second recovery restore passed. Minimum sampled
available RAM **1,008.6 MiB**, no OOM. Rehearsal containers stopped; live services
unchanged. No provider credentials/egress were used. This validates stored reads
and idle refresh, not active-provider capacity or genuine market acceptance.
[Merged rehearsal evidence](STK-099-restored-rehearsal.md) contains image IDs and
recovery limits; merging the implementation does not establish production cutover.

Private evidence remains outside Git: `backups/stk099-vps-rehearsal-20261114/`
contains `result.json`, `live-status.json` and preservation manifests;
`backups/stk014-activation-20261114/` contains `health.json` and
`session-diagnostic.json`. Do not print credential files. The current
[WORK-HANDOFF](WORK-HANDOFF.md) agrees with this summary. Its historical sections,
[product acceptance](PRODUCT-ACCEPTANCE-HANDOFF.md) and `AI_RESEARCH_PROGRESS.json`
retain dated specialist evidence, not current deployment or PR inventories.

## Overall and component progress

**58% is the owner-specified planning baseline as of 15 November.** It supersedes
the previously reported 57% and historical 46%/49% estimates. No reproducible
weighting/denominator was found; retain 58% as a planning baseline, not a measured
release-readiness, test-success or profitability percentage. Component status below
is evidence-based; merged package count does not measure product completion.

| Component | Completed capability | Pending capability / qualification |
|---|---|---|
| D3-01 contracts; D3-02 source gates | Three horizons, provenance, four actions, permission fences merged | Broader source/account scope is capability-specific; existing approved Upstox scope remains usable |
| D3-03/04 ingestion and scheduling | Immutable revisions, calendars, durable jobs/quotas, Chartink/Test intake, bounded refresh implemented; restricted Mac workers live | Genuine candidate, complete current batch, automatic analysis acceptance; universe beyond INFY |
| D3-05 quantitative policies | Three-horizon engines; descriptive EMA/breakout integration | Qualified current coverage/volume, complete strategy inputs and real policy approval; no invented levels/sizing |
| D3-06 evidence ingestion | Adapters, extraction, immutable evidence/facts and event plumbing; bounded real-source probes recorded | Complete qualified original filings/news, availability clocks and production coverage |
| D3-07/08 research and judge | Retrieval, bounded investigation, deterministic validation, runtime integration and development evaluations | Independent research-quality/holdout calibration (M2); actionable financial research not qualified |
| D3-09 UI/publication | Authenticated workbench, 12 configured listings, comparison, private watchlist, Candidates status and page-scoped ranking; shared refreshed-batch continuity fix tested for review | Genuine candidate → qualified current analysis visibility; full-universe ranking/publication not established |
| D3-10/11 outcomes/governance | Paper/risk arithmetic, replay, immutable history, registered experiments and scorecards implemented/tested | Qualified real forward observations, benchmarks, matured horizon cohorts and policy/promotion gates |
| D3-12 operations | Receiver live, controlled Mac workers; hosting foundation merged; representative VPS rehearsal passed | Off-server recovery/alerts, full cutover and genuine Mac-off acceptance |
| D3-13 release | Stored/descriptive slices and runbooks delivered | Integrated three-horizon live release, measured limits and prospective acceptance incomplete |

## Top three priorities and verified gates

1. **P0 — STK-095 / STK-014 / STK-094:** release durable intake and asynchronous parsing,
   quarantine/replay only verified schema differences, then ordinary alert → durable candidate
   identity/session/symbol count and cursor → eligible complete EOD refresh →
   durable re-analysis → authenticated Candidates API/UI. Provider Tests stay
   excluded. Missing/stale/insufficient evidence stays unranked. No manufactured alert.
2. **P1 — STK-014 / STK-094:** qualify the current complete price batch for genuine
   eligible candidates, then durable re-analysis and authenticated UI. Preserve
   source/calendar/coverage gates and the INFY acquisition bound.
3. **P2 — STK-099 / STK-054 / STK-079–081:** retain existing off-server recovery,
   key custody and external alert provisioning gates; full cutover needs separate
   authorization. Qualify volume and remaining strategy/research inputs; no BUY,
   levels, sizing or profitability claims. Infrastructure work is outside this fix.

Owner decisions: identify existing off-server destination, private credential/key
paths and separate key custodian, plus external alert/host-loss resources;
review/authorize the prepared schema-0018 application/consumer/receiver release; separately authorize
full cutover only after recovery gates.
No new provider-rights review is required for already approved descriptive scope.
Broader M1/M2, real policy/risk and strategy-promotion approvals apply only to their
unqualified capabilities, not as a blanket stop to independent implementation.

## Exact next executable task

**STK-095 / STK-014:** review existing PR #59 and exact-head CI; authorize the
additive 0018 migration and compatible application/consumer release before the
receiver emits raw envelopes. Preserve the existing cursor and singleton workers.
Then verify the next ordinary genuine event through durable receipt, parsing,
qualified refresh, analysis, Candidates and watchlist. Unknown schemas stay
quarantined; use the existing authenticated retry after a verified parser fix.
[Release gates and rollback](STK-095-private-rejections.md). No deployment or
migration is authorized by this handoff. No manufactured market acceptance.

Before any separately approved cutover: persistently stop both Mac workers, verify
singleton release, export fresh application state including cursor and quota ledger,
preserve watchlist bytes, restore to new VPS targets and retain rollback. Never run
Mac/VPS acquisition against divergent quota ledgers. Keep the live receiver intact.

For every PR that materially changes state, update this handoff and SIMPLE-BOARD
in that same PR, retaining dated evidence and test/rehearsal/live distinctions.
Follow [AGENTS.md](../AGENTS.md): existing STK IDs and D3 names, isolated related
changes, owner review/merge, preserved WIP; no new services or automation required.

## Historical delivery checkpoint — 15 November

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

## Historical delivery checkpoint — 16-Nov operations

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

Reconciled **16 November 2026** under **STK-099 / D3-12 Private operational pilot**.
Read [SD ARCH 3.0](SD-ARCH-3.0.md) for requirements and
[SIMPLE-BOARD](SIMPLE-BOARD.md) for canonical task status. This file is restart
context, not another tracker. Historical acceptance records retain their scope.


Previous next task (superseded by STK-095 failure):

**STK-099:** fill the reviewed private operations config once the owner identifies
existing backup and alert resources. Run one encrypted exact-snapshot backup/restore
with `scripts/operate.py backup`, one `alert-test` with observed external delivery,
and `monitor`; enable existing timers only after real verification. No new paid
resource or application cutover. [Evidence and commands](STK-099-release-prerequisites.md).
15 focused synthetic operations tests passed; these do not close live release gates.
VPS read-only check 16-Nov 06:06:20 UTC confirms unchanged receiver image/start time
and the same three live services. Mac counts above remain dated 15-Nov, not remeasured.
Owner monitors this PR's CI; do not wait or merge.

Historical P1/P2 priorities before the confirmed receiver failure:

2. **P1 — STK-099:** finish encrypted off-server restore, key custody and external
   alert/host-loss delivery using existing resources. Restic 0.19.1 is now installed
   separately; online operations mode, private templates and cutover/rollback
   commands are prepared. No destination/credential/key-custody or alert-hook config
   was found; actual remote restore/delivery and timers remain unactivated. Full
   cutover needs separate authorization, including proxy-only ingress interruption
   because existing Caddy has `admin off`. No hardware upgrade is justified.
3. **P2 — STK-014 / STK-054 / STK-079–081:** qualify volume and remaining strategy evidence for usable
   swing signals. Current price-only EMA/breakout review does not establish BUY,
   entry/stop/target, position sizing, strategy superiority or profitability.

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

Reconciled **16 November 2026** under **STK-094 / D3-05 Quant horizon policies + D3-09 UI**.
Read [SD ARCH 3.0](SD-ARCH-3.0.md) for requirements and
[SIMPLE-BOARD](SIMPLE-BOARD.md) for canonical task status. This file is restart
context, not another tracker. Historical acceptance records retain their scope.

Read-only **16-Nov 06:41–06:49 UTC** evidence: VPS schema 0017, three provider-Test
events, zero non-Test events, high-water 3. Mac schema 0017, cursor **3**, events
**3**, candidates **0**, revisions **2,648**, no refresh jobs and zero provider quota
requests in preceding 24h. Consumer PID **8125** and refresh PID **8129** remained
running with one launch each. Latest stored INFY candle session is **4-Nov**; other
11 stored listings end **23-Oct**. This is not complete current OHLCV qualification.
Webhook, secrets, scanner identity, volumes, history and cursor were not modified.

PR #55 continuity, PR #56 CI selection and PR #57 operations prerequisites are
merged; current base is `0fe2136`. The current STK-094 shared-batch research fix is
for review, with 169 focused passing tests and synthetic browser continuity evidence.

2. **P1 — STK-014 / STK-094:** review the shared-batch research fix, then expose
   per-candidate refresh eligibility/out-of-universe reasons using existing contracts.
   Infrastructure work is deferred; missing backup resources do not block this work.
3. **P2 — STK-014 / STK-054 / STK-079–081:** qualify volume and remaining strategy evidence for usable
   swing signals. Current price-only EMA/breakout review does not establish BUY,
   entry/stop/target, position sizing, strategy superiority or profitability.

Owner decisions: review/merge the STK-094 software fix after exact-head checks.
No new authorization is required for its isolated application tests. Existing
infrastructure provisioning/release gates remain in the STK-099 runbook; no
provisioning, alert activation or cutover is part of this application task.

**Exact next executable task — STK-014:** after review/merge of the current
STK-094 fix, expose per-candidate refresh eligibility/out-of-universe reasons using
the existing worker configuration and job contracts. Observe the next ordinary
eligible EOD alert independently; do not manufacture events or expand provider scope.
Volume-qualified swing checks remain subsequent work. Owner monitors this PR's CI;
do not wait, merge, deploy, interrupt live workers or start infrastructure work.

The [continuity acceptance](STK-094-candidate-research-continuity.md) records the
reproduced failure, fix, 169 tests and exact live/synthetic distinction. No complete
current price, volume-qualified swing signal or genuine live UI acceptance is claimed.

## Historical delivery checkpoint — 16 November operations

