# Stock Discovery — project handoff

Reconciled **15 November 2026** under **STK-081 / D3-13 Three-horizon release**.
Read [SD ARCH 3.0](SD-ARCH-3.0.md) for requirements and
[SIMPLE-BOARD](SIMPLE-BOARD.md) for canonical task status. This file is restart
context, not another tracker. Historical acceptance records retain their scope.

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
deployment; do not reopen host selection. See [STK-099](STK-099-bookmyhost.md).

Read-only evidence at **2026-11-15T13:01Z**: consumer PID **8125**, refresh PID
**8129**, one launch each and exactly one matching refresh process; latest consumer
completion five seconds old. Mac cursor **3**, events **3**, genuine candidates
**0**, revisions **2,648**. No refresh jobs or provider requests in the preceding
24 hours. Preserve webhook URL, scanner identity, secrets, volumes, event history,
immutable revisions and cursor. No production change is authorized by this handoff.

STK-095 real provider Tests passed HTTP 202, durable receipt, deduplicated retry,
consumer cursor advancement and zero candidate/session/research materialization.
Genuine market-alert acceptance remains **pending**. Tests do not count as candidates.

The live INFY refresh scope uses the existing NSE EQ mapping, grants, restricted
role and account quota ledger. Initial Upstox HTTP 200 returned 30 validated bars
but omitted expected **13 November**; **zero bars ingested**. The one permitted
additional diagnostic returned only 12-Nov for a 12–13-Nov inclusive request,
with cache Age **56,991 seconds**. Upstream incompleteness is observed; cache lag
is an inference, not a proved internal cause. No response stitching or incomplete
current-data admission. Existing readiness retries are 900 seconds, at most three
attempts per job; no genuine candidate means no forced job or diagnostic retry.

## Merged, in review and acceptance evidence

Main is **`fbd841aa9948949dfed655e462ea292b9204b007`**, merged PR #54.
Its final PR head `bf12c5394a678633f8426f3fe06c9040a246fd03` passed
[all four required checks](https://github.com/gaganjawa/stock-discovery/actions/runs/43717712492).
The [exact-merge main run](https://github.com/gaganjawa/stock-discovery/actions/runs/43718688001)
was still running at reconciliation; no result is inferred from the PR run.
PR #55 rebases this continuity update onto merged #54 and needs its own new-head CI;
owner monitors checks without waiting or automatic merge. PR #12/#35 are merged.

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
| D3-09 UI/publication | Authenticated workbench, 12 configured listings, comparison, private watchlist, Candidates status and page-scoped ranking | Genuine candidate → qualified current analysis visibility; full-universe ranking/publication not established |
| D3-10/11 outcomes/governance | Paper/risk arithmetic, replay, immutable history, registered experiments and scorecards implemented/tested | Qualified real forward observations, benchmarks, matured horizon cohorts and policy/promotion gates |
| D3-12 operations | Receiver live, controlled Mac workers; hosting foundation merged; representative VPS rehearsal passed | Off-server recovery/alerts, full cutover and genuine Mac-off acceptance |
| D3-13 release | Stored/descriptive slices and runbooks delivered | Integrated three-horizon live release, measured limits and prospective acceptance incomplete |

## Top three priorities and verified gates

1. **P0 — STK-014 / STK-094 / STK-095:** next ordinary EOD alert → durable candidate
   identity/session/symbol count and cursor → eligible complete EOD refresh →
   durable re-analysis → authenticated Candidates API/UI. Provider Tests stay
   excluded. Missing/stale/insufficient evidence stays unranked. No manufactured alert.
2. **P1 — STK-099:** use merged PR #54 tooling to verify encrypted off-server restore,
   key custody and external alerts using existing tooling. No restic executable or
   Stock Discovery backup/monitor units were found on the VPS; same-host recovery
   does not establish off-server disaster recovery. Full cutover needs separate
   owner release authorization. No hardware upgrade is justified by the tested load.
3. **P2 — STK-014 / STK-054 / STK-079–081:** qualify volume and remaining strategy evidence for usable
   swing signals. Current price-only EMA/breakout review does not establish BUY,
   entry/stop/target, position sizing, strategy superiority or profitability.

Owner decisions: review/merge PR #55 when its new-head checks pass; confirm the
existing backup destination/key custodian and alert destination if absent from
private configuration; separately authorize full cutover after recovery gates.
No new provider-rights review is required for already approved descriptive scope.
Broader M1/M2, real policy/risk and strategy-promotion approvals apply only to their
unqualified capabilities, not as a blanket stop to independent implementation.

## Exact next executable task

**STK-099:** inspect existing private backup/alert configuration read-only and
prepare the merged restore tooling against an isolated off-server recovery target.
Record missing destination/key-custodian inputs before any paid operation; do not
expose secrets or send alert messages. PR #55 awaits owner review/new exact-head CI;
owner monitors it without polling/waiting or automatic merge. No full production
cutover is authorized by the PR #54 merge or this reconciliation.

Before any separately approved cutover: persistently stop both Mac workers, verify
singleton release, export fresh application state including cursor and quota ledger,
preserve watchlist bytes, restore to new VPS targets and retain rollback. Never run
Mac/VPS acquisition against divergent quota ledgers. Keep the live receiver intact.

For every PR that materially changes state, update this handoff and SIMPLE-BOARD
in that same PR, retaining dated evidence and test/rehearsal/live distinctions.
Follow [AGENTS.md](../AGENTS.md): existing STK IDs and D3 names, isolated related
changes, owner review/merge, preserved WIP; no new services or automation required.
