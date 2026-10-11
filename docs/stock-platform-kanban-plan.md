# Personal stock platform — Kanban delivery plan

Planning baseline: 9 October 2026, Asia/Kolkata. Project key: STK.

**10 epics · 30 stories · 90 tasks.** This is a portable Jira-style backlog, not an existing Jira project. No application work, integrations, purchases or deployments are marked complete. Proposed work and estimates below are planning decisions; externally verified prices and restrictions are identified separately.

## 1. Scope and simple architecture

Build a private, single-owner Indian equity research platform: stock discovery, important news, technical analysis, full company research, IPO assessment, flexible portfolio tracking, historical evaluation and forward paper evaluation. Cover swing, long-term and intraday in successive versions. Upstox and Zerodha account integration is included; real-order execution is optional and last.

React + TypeScript + TradingView Lightweight Charts → FastAPI → PostgreSQL. One dedicated scheduled Python worker runs ingestion, indicators, scans and evaluations. Shared Python analysis code runs with historical or live data adapters and clocks. Use Pandas/NumPy and validated TA-Lib/custom indicator functions; a bounded LLM handles grounded research, while scikit-learn/optional LightGBM handles predictive experiments. Use pytest plus DeepEval for appropriate checks. Deploy with Docker Compose on one private host, with encrypted off-host backups.

No Redis, Kubernetes, microservice fleet, dedicated vector database or LLM training is required initially. PostgreSQL search is sufficient to start; add infrastructure only after measuring a concrete limitation. Technical signals are calculated from numerical candles and volume, not inferred only from chart screenshots.

## Ticket priority policy

Current release: **v0.1**. Priority is independent of status, effort and dependencies.

| Priority | Use | Initial assignment |
|---|---|---|
| P0 — Critical | Active security, data-loss or production incidents | None; do not use for routine planned work |
| P1 — High | Current-release requirements and immediate prerequisites | v0.1 tickets |
| P2 — Medium | Core capabilities in later planned releases | v0.2 through v1.0 tickets |
| P3 — Low | Optional enhancements | Optional v1.1 broker execution |

Review priorities when pulling a task or completing a release. Dependencies still determine which tickets are Ready. Priority does not change time estimates or imply a deadline.

## 2. How we use the board

**Backlog → Ready → In Progress → Review/Test → Ready for Release → Done.** A blocked flag records reason, dependency, owner and next action. WIP limit: one task In Progress and one in Review/Test. Pull work, finish it and update evidence before pulling another task.

- Each story has an epic, release, dependencies, acceptance criteria and three task IDs. Story dependencies are prerequisites for completion; mock-based development can start earlier when clearly labelled.
- First Ready tasks: **STK-001** (recommendation contract), **STK-004** (broker/data rights), **STK-007** (document sourcing). Recommended first pull: **STK-001**. All other tasks start Backlog; no work is Done.
- Default owner is unassigned until pulled. You own product/risk choices, accounts, purchases and concrete order approvals. Implementation/review ownership is assigned when work starts.
- Ready means scope, inputs and expected output are clear and required access is available. Done means acceptance evidence exists, relevant checks pass, code/docs are committed, secrets are excluded and status is updated. Feature tasks wait in Ready for Release until their private release is verified. Research/licensing tasks finish when their evidence/decision is recorded, even if the outcome is to disable a feature.
- Every task row has a mutable checkbox: unchecked means incomplete. Record status, assignee, actual effort, blocker and evidence/commit in a note under that row when picked. Add defect IDs STK-B001 onward without renumbering existing work.
- Every release uses a version tag, migration check, backup, private deployment, smoke check and rollback target. “Live” means privately hosted software; it does not mean real-money orders.
- A source-rights gate applies to the affected feature, not to synthetic development. An unresolved historical-news licence must not block a price-only replay release or be silently treated as permission.

## 3. Releases and realistic timing

Effort estimates are uncertain planning ranges for one experienced developer with AI assistance. They include implementation and ordinary verification, exclude vendor/legal waiting time, and assume limited initial universe and simple UI. Days mean focused engineering days, not calendar promises. Re-estimate after the first five completed tasks.

| Version | Usable result | Stories | Incremental effort estimate | Release gate |
|---|---|---|---|---|
| v0.1 | Private skeleton, contracts and sourcing decisions | S01–S06 | 5–8 days | Auth, synthetic demonstration, restore/rollback; costs recorded |
| v0.2 | First useful historical replay and scorecard | S07–S08, S10–S11, S13–S15 | 10–15 days | Permitted daily history; no future access; hand-checked outcomes |
| v0.3 | Live watchlist, technical comparisons, both broker account reads, portfolio and paper tracking | S09, S12, S20–S21 | 8–12 days | Permitted paper data; freshness/reconnect handling; no real orders |
| v0.4 | News, financial/company and IPO research with LLM evaluation | S16–S19, S24 | 12–18 days | Cited evidence, as-of documents, groundedness tests and archive limits |
| v0.5 | Intraday replay and paper workflows | S22 | 5–8 days | Interval coverage, cost/latency sensitivity and session rules |
| v0.6 | Learned-model challenger experiment | S23 | 5–8 days | Untouched chronological test; explicit promote/reject decision |
| v1.0 | Stable personal research software and maintenance workflow | S25–S27 | 5–8 days | Recovery, budgets, lifecycle controls and end-to-end acceptance |
| v1.1 optional | Human-approved broker orders | S28–S30 | 8–12 days + external waiting | Current broker obligations, lifecycle tests and separately authorised real-order validation |

**First useful version: approximately 15–23 focused days. Research v1.0: approximately 50–77 focused days.** At 10 hours/week, using six focused hours per engineering day, this is roughly 9–14 weeks to v0.2 and 30–46 weeks to v1.0. Full-time implementation is roughly 3–5 weeks and 10–16 weeks respectively. These estimates are not promises; sourcing delays or poor historical coverage can extend them. Forward validation additionally needs elapsed market time and adequate samples; it cannot be compressed by coding faster. We can use early releases while later stories remain in Backlog.

## 4. Third-party integration and sourcing register

These are distinct roles, not interchangeable APIs. Public pages are not automatically supported APIs or permission to archive/train models. First use one approved price provider; avoid paying for duplicate feeds until there is a demonstrated need.

| ID / party | Purpose and access route | When / stories | Price evidence and sourcing action |
|---|---|---|---|
| INT-01 Upstox | Candidate primary historical/live prices; account holdings/positions; optional orders through documented broker APIs | S02, S08–S09, S28–S30 | Advertised API access ₹0 [R1]. Verify account conditions, intervals/history, quotas, retention, replay/paper and ML/LLM rights. No assumption that free access grants every use. |
| INT-02 Zerodha / Kite Connect | Account reads; optional alternate price feed and later orders | S02, S09, S28–S30 | Personal APIs free but exclude market/history data; Connect ₹500/app/month [R2]. Terms restrict mock-trading uses and permanent copies [R3]; obtain use-specific clarity/permission before those workflows. |
| INT-03 NSE / NSE Data & Analytics | Instruments, calendar, corporate actions, filings; possible licensed historical/live data | S02, S07–S08, S16 | Direct data licence/approved vendor if required; price quote unresolved. Contract governs use and redistribution [R4]. Do not purchase a second feed simply because NSE is a source. |
| INT-04 BSE | BSE identities, announcements, results, corporate actions and IPO information; possible data products | S02, S07, S16, S19 | Official corporate/data-product routes [R5]. Verify supported delivery, archival and derived-use rights; commercial-feed costs unknown. Deduplicate dual-listed-company filings. |
| INT-05 SEBI | IPO offer documents and current regulatory circulars; not a stock-price or buy/sell API | S02–S03, S16, S19, S28 | Official public-issue and legal documents [R6–R7]. No assumed API subscription fee; validate retrieval/use route. Document availability is not approval of an IPO investment. |
| INT-06 Company investor-relations sites | Annual reports, presentations, earnings material and disclosed customers/concentration | S03, S16, S18 | Start with permitted imports and source links. Availability varies; retain terms, document version and publication time. Undisclosed clients stay unknown. |
| INT-07 News publisher / licensed aggregator | Timely material company/sector/macro news beyond filings | S03, S17 | Provider not selected. Compare Indian coverage, timestamps, archives and AI rights. Paid historical archives require separate quote; not assumed included in ₹3,000. |
| INT-08 LLM API provider | Structured extraction, grounded research and evaluation judge | S03, S18, S24 | Provider/model selected by small quality/cost trial. Meter token charges; verify retention and permitted source-data transfer. No LLM-provider subscription is purchased by this plan. |
| INT-09 TradingView Lightweight Charts | Chart rendering library; does not supply price data | S03, S11, S15 | Apache-2.0 software with required attribution/notice and link [R8]; no commercial chart-feed subscription assumed. |
| INT-10 Hosting, backup and optional domain providers | Private UI/API/worker/database, encrypted backup and HTTPS endpoint | S03, S06, S25 | Select current quotes within allocation below; static egress IP may add cost for later execution. Prefer region compatible with provider terms. |
| INT-11 Optional historical-data vendor | Fill rights/coverage gaps for candles, delisted stocks, filings or news | S02–S03, S08, S16–S17 | Only source if broker/official routes cannot meet requirements; validate exchange authorisation and exact end-user rights. Quote and sample-quality test required. |

For every provider, record: product/version, official documentation/terms URL, reviewed date, account owner, data fields and coverage, latency, authentication, quotas, storage/retention, private-cloud location, replay/paper rights, ML training, external-LLM transfer, redistribution, attribution, deletion on termination, setup/monthly/usage price, taxes and renewal. Implementation may proceed with fixtures while an access decision is pending. No vendor outreach is sent automatically.

## 5. Licences, costs and procurement

Verified advertised broker prices are above. The following amounts are **planning allocations, not vendor quotations**. They aim to keep routine personal use inside the tentative ₹3,000 monthly budget.

| Item | Monthly allocation | Notes |
|---|---:|---|
| Host for app, worker and PostgreSQL | ₹1,000 | Validate capacity with limited universe; includes no managed-database assumption |
| LLM analysis and judge usage | ₹900 | Hard cap, bounded scans, caching where permitted; actual cost is workload/model dependent |
| Encrypted off-host backup | ₹150 | Verify retention and storage volume |
| Optional domain, amortised | ₹100 | Can omit initially; annual payment is a separate cash outlay |
| Upstox API | ₹0 advertised | Rights/conditions still require review |
| Reserve for tax, FX, data or unexpected usage | ₹850 | Optional ₹500 Kite Connect subscription draws from this reserve, leaving ₹350 |
| **Target total** | **₹3,000** | Freeze purchases if actual quotes cannot fit; reduce scope or revise budget explicitly |

An annual steady-state allowance at that cap is ₹36,000. Trading capital, brokerage/statutory trading charges, account fees, developer labour, professional legal advice and separately licensed historical/news archives are excluded. Setup/procurement costs remain **TBD**, not ₹0: record quoted amount before approval. ₹50,000 monthly investment contributions are a separate, optional ledger input and do not finance software automatically.

Software licensing work is an inventory/notice audit, not a plan to buy a generic “trading software licence.” Data usage agreements, paid service subscriptions and regulatory obligations are separate checks. For personal-only scope, record a scoped assessment rather than asserting that a SEBI registration is required or that no rules apply. Reassess before providing recommendations to others, public distribution, charging users or automated order execution. Upstox currently documents order-related static-IP/algo requirements [R9]; recheck both brokers immediately before v1.1.

Procurement workflow: define intended uses → compare documented terms/quotes → test permitted sample data → record chosen provider and total cost → obtain owner purchase/account consent → configure credentials privately → test limits and expiry → record renewal. No paid historical archive, commercial feed or regulatory registration has been sourced or purchased yet; these are explicit tracked tasks.

## 6. Epic map

| Epic | Outcome | Stories |
|---|---|---|
| E01 | Contracts, data rights, licences and budget | S01–S03 |
| E02 | Simple application foundation and private deployment | S04–S06 |
| E03 | Historical/live data and broker account adapters | S07–S09 |
| E04 | Technical indicators and versioned strategies | S10–S12 |
| E05 | Historical replay, outcome truth and scorecard | S13–S15 |
| E06 | Primary documents, news, company and IPO research | S16–S19 |
| E07 | Discovery, portfolio and all-horizon paper workflows | S20–S22 |
| E08 | Predictive experiments, LLM evaluation and diagnosis | S23–S24 |
| E09 | Reliability, change control and stable release | S25–S27 |
| E10 | Optional owner-approved real orders | S28–S30 |

## 7. Stories and tasks

Each task below has a concrete output. Acceptance applies to the parent story. Dependencies list story IDs; task IDs are permanent. Size individual tasks when pulled: aim for half a day to two days; split any larger item without changing its original ID. Release estimates above include these tasks and ordinary review. Optional v1.1 work has lower priority than all research releases.

### S01 — Recommendation and evaluation contract

Epic: E01 · Target: v0.1 · Status: Done · Owner: Codex · Depends on: -

**Acceptance:** A frozen example defines information cutoff, horizon, entry, stop, targets, expiry and separate forecast/trade outcomes.

- [x] **STK-001** — Define recommendation schema and work through 6 Aug 2025 using illustrative data; include buy/sell/wait and insufficient evidence. **[Done]** · Priority: P1 — High
  - Owner: Codex. Done 10 Oct 2026. Contract and 9 synthetic scenarios validated; implementation commit `6417dba` pushed and verified. Hosted board version 3 published successfully. Blocker: none. Actual effort: not time-tracked (observed resumed work window approximately 10 minutes). Evidence: [STK-001 record](STK-001.md).
- [x] **STK-002** — Define accuracy denominators, net expectancy, drawdown, benchmarks and promotion criteria before testing. **[Done]** · Priority: P1 — High
  - Owner: Codex. Done 10 Oct 2026. Both validators and diff review passed; implementation commit `1143d4a` pushed and remote verified. Hosted board Done save confirmed. Blocker: none. Actual effort: not time-tracked. EP-1 remains proposed policy. Evidence: [STK-002 record](STK-002.md).
- [x] **STK-003** — Record scope and configurable capital/risk rules; distinguish exit of a holding from short selling and allow skipped contributions. **[Done]** · Priority: P1 — High
  - Owner: Codex. Done 10 Oct 2026. All three validators pass; implementation commit `d15c00a` pushed and remote verified; hosted board Done save confirmed. No live risk profile approved. Blocker: none. Actual effort: not time-tracked. Next ticket requires user confirmation. Evidence: [STK-003 record](STK-003.md).

### S02 — Market data rights and broker feasibility

Epic: E01 · Target: v0.1 · Status: Backlog · Owner: Unassigned · Depends on: -

**Acceptance:** Every proposed data use is marked permitted, prohibited or unresolved; unresolved uses cannot enter enabled features.

- [ ] **STK-004** — Review Upstox and Zerodha terms for history, retention, private hosting, replay, paper evaluation, ML and external LLM processing; prepare questions for owner to send. **[Ready]** · Priority: P1 — High
- [ ] **STK-005** — Compare NSE/BSE direct products and authorised vendors for missing data; record coverage, use rights and written quotes. **[Backlog]** · Priority: P1 — High
- [ ] **STK-006** — Review exact private-use and future execution scope against current broker/exchange/SEBI requirements; record approvals or specialist advice needed. **[Backlog]** · Priority: P1 — High

### S03 — Document licences and budget

Epic: E01 · Target: v0.1 · Status: Backlog · Owner: Unassigned · Depends on: -

**Acceptance:** Source and software registers identify terms, costs, restrictions and unresolved decisions; no unapproved purchases.

- [ ] **STK-007** — Assess permitted NSE/BSE/SEBI, issuer IR and news retrieval, archival and summarisation routes; distinguish manual imports from supported feeds. **[Ready]** · Priority: P1 — High
- [ ] **STK-008** — Compare hosting, model API and backup quotes against ₹3,000 monthly budget including tax/FX and one-off charges. **[Backlog]** · Priority: P1 — High
- [ ] **STK-009** — Audit pinned software licences, retain notices and add required TradingView attribution; create renewal and terms-review register. **[Backlog]** · Priority: P1 — High

### S04 — Application skeleton

Epic: E02 · Target: v0.1 · Status: In Progress · Owner: Codex · Depends on: S01

**Acceptance:** UI, API, worker and database run locally with synthetic data and reproducible builds.

- [x] **STK-010** — Create one repository with React/TypeScript UI, FastAPI API, Python worker, shared analysis package and migrations. **[Done]** · Priority: P1 — High
  - Owner: Codex. Done 10 Oct 2026. Synthetic API/worker tests, a local HTTP smoke test, frontend production build, Compose structure and prior contract validators passed. Implementation commit `f522cbd` was pushed and verified on `origin/main`. Docker Compose could not run on this host because the installed Docker CLI lacks the Compose subcommand. Hosted board update to Done is pending because its browser tab became unavailable. Evidence: [STK-010 record](STK-010.md).
- [x] **STK-011** — Build navigation for Dashboard, Research, Replay, Portfolio and IPO with explicit empty/demo states. **[Done]** · Priority: P1 — High
  - Owner: Codex. Completed 10 Oct 2026; build and browser navigation checks passed. Commit `714bad8` pushed and verified. Hosted board Done update pending fresh sign-in. Evidence: [STK-011](STK-011.md).
- [x] **STK-012** — Configure CI, relevant smoke tests, pinned dependencies and secret-free environment templates. **[Done]** · Priority: P1 — High

  - Owner: Codex. Completion recorded 11 Oct 2026. Pushed commit `e355843` passed full CI, including Compose runtime smoke tests. Hosted board update delegated to the user. Evidence: [STK-012 record](STK-012.md).

### S05 — Shared data contracts

Epic: E02 · Target: v0.1 · Status: Backlog · Owner: Unassigned · Depends on: S04

**Acceptance:** The same engine can use a historical or live clock; decisions preserve source and version information.

- [x] **STK-013** — Create PostgreSQL schema for instruments, candles, documents, facts, decisions, runs, holdings and contribution ledger. **[Done]** · Priority: P1 — High
  - Owner: Codex. Completed 11 Oct 2026. Implementation `539f055` pushed; PostgreSQL constraints, unchanged fixture round trips, upgrade/downgrade/re-upgrade and failed-migration rollback passed in CI. Hosted board update delegated to the user. Evidence: [STK-013](STK-013.md).
- [ ] **STK-014** — Define market-data, document and account adapters with explicit availability timestamps and historical/live clock interfaces. **[Ready for Release]** · Priority: P1 — High
- [ ] **STK-015** — Make decisions immutable; store source, dataset, code, strategy, prompt and model versions, with linked corrections. **[Ready for Release]** · Priority: P1 — High
  - Owner: Codex; 11 Oct 2026. Evidence: [STK-015](STK-015.md). PostgreSQL integration and migration lifecycle passed; release pending.

  - STK-014 evidence: [implementation and validation](STK-014.md). Owner: Codex; 11 Oct 2026. Private-release verification pending.

### S06 — First private deployment

Epic: E02 · Target: v0.1 · Status: Backlog · Owner: Unassigned · Depends on: S03,S05

**Acceptance:** Authenticated HTTPS deployment, backup restore and rollback work; unlicensed inputs and order execution are disabled.

- [ ] **STK-016** — Deploy Docker Compose on one private host; protect UI/API, isolate database and keep credentials server-side. **[Backlog]** · Priority: P1 — High
- [ ] **STK-017** — Configure a single dedicated scheduled worker with job locks, retries, health status, redacted logs and backups. **[Backlog]** · Priority: P1 — High
- [ ] **STK-018** — Tag and release v0.1 with synthetic data; verify authentication, restore and rollback and record release notes. **[Backlog]** · Priority: P1 — High

### S07 — Instrument identity and universe

Epic: E03 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S02,S05

**Acceptance:** Security mappings and historical universe limits are explicit; symbol changes do not join unrelated securities.

- [ ] **STK-019** — Map ISIN, NSE symbol/series, BSE code and broker instrument IDs with effective dates. **[Ready for Release]** · Priority: P2 — Medium
  - Owner: Codex; 11 Oct 2026. Evidence: [STK-019](STK-019.md). Two identity tests pass; synthetic scope only.
- [ ] **STK-020** — Import exchange calendars and corporate actions; preserve raw prices and version price-adjustment conventions. **[Backlog]** · Priority: P2 — Medium
  - Partial synthetic implementation: [STK-020](STK-020.md). Real imports and full action execution remain outstanding.
- [ ] **STK-021** — Build as-of universe selection including delisted/suspended instruments where available; document survivorship and coverage limits. **[Ready for Release]** · Priority: P2 — Medium
  - Owner: Codex; 11 Oct 2026. Evidence: [STK-021](STK-021.md). Synthetic universe only.

### S08 — Historical candles and quality

Epic: E03 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S07

**Acceptance:** A permitted, reproducible daily dataset passes quality checks; bad data blocks recommendations.

- [ ] **STK-022** — Implement resumable, rate-limited historical import with idempotent writes and provenance. **[Ready for Release]** · Priority: P2 — Medium
  - Evidence: [STK-022](STK-022.md). Synthetic ingestion verified; real provider access blocked.
- [ ] **STK-023** — Validate timestamps, OHLC, volume, duplicates, gaps and split/dividend treatment against independently checked samples. **[Ready for Release]** · Priority: P2 — Medium
  - Evidence: [STK-023](STK-023.md). Synthetic quality gates verified; independent real samples unavailable.
- [ ] **STK-024** — Freeze dataset manifest and chronological development/test windows; record missing periods and permitted retention. **[Backlog]** · Priority: P2 — Medium

### S09 — Read-only Upstox and Zerodha

Epic: E03 · Target: v0.3 · Status: Backlog · Owner: Unassigned · Depends on: S08

**Acceptance:** Both account adapters work; feed selection, freshness and authentication failures are visible.

- [ ] **STK-025** — Implement authorised Upstox account reads and approved price feed with token lifecycle, quotas and reconnect handling. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-026** — Implement Zerodha holdings/positions reads; enable market data only with appropriate plan and use-specific rights. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-027** — Add stale-data suppression and explicit provider selection; reconcile IDs and never silently change feed semantics. **[Backlog]** · Priority: P2 — Medium

### S10 — Core numerical indicators

Epic: E04 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S08

**Acceptance:** Values match reference fixtures and only use closed, available candles with sufficient warm-up.

- [ ] **STK-028** — Implement SMA/EMA, crossovers, relative volume and liquidity features. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-029** — Implement ATR, prior-window support/resistance and breakout levels without future bars. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-030** — Verify indicator fixtures, missing data and adjustment conventions; expose calculated values for inspection. **[Backlog]** · Priority: P2 — Medium

### S11 — First swing strategy

Epic: E04 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S01,S10

**Acceptance:** A deterministic strategy emits entry/stop/target/expiry or wait with traceable rules.

- [ ] **STK-031** — Implement a frozen EMA plus relative-volume plus breakout baseline and explicit timing/exit rules. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-032** — Implement sizing using chosen active capital, cash, stop distance and exposure constraints; flag gaps and rounding. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-033** — Build recommendation card showing triggered rules, chart, invalidation and version; no invented confidence probability. **[Backlog]** · Priority: P2 — Medium

### S12 — Ichimoku and additional strategies

Epic: E04 · Target: v0.3 · Status: Backlog · Owner: Unassigned · Depends on: S10,S14

**Acceptance:** Additional indicators are correctly aligned and evaluated independently; more indicators do not automatically increase a score.

- [ ] **STK-034** — Implement Ichimoku and test leading/lagging plotting against the time at which each feature is knowable. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-035** — Add RSI/MACD, Bollinger, OBV, session VWAP and a small defined candlestick-pattern set with reference tests; split into subtasks when pulled. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-036** — Compare predeclared strategies and feature ablations against the EMA baseline on held-out periods; retain all experiment trials. **[Backlog]** · Priority: P2 — Medium

### S13 — Historical replay and fills

Epic: E05 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S11

**Acceptance:** Analysis sees only then-available information, freezes its recommendation and follows original execution rules.

- [ ] **STK-037** — Implement replay clock/event loop with future-read guards, closed-bar signals and earliest realistic entry timing. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-038** — Simulate entry, expiry, exits, cash, liquidity limits and gaps; flag bars where stop/target order is unknowable. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-039** — Add date-effective brokerage, statutory charges and slippage assumptions; verify profit, loss, no-entry and ambiguous cases manually. **[Backlog]** · Priority: P2 — Medium

### S14 — Accuracy and performance scorecard

Epic: E05 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S13

**Acceptance:** All recommendations remain visible; forecast accuracy and trade performance have explicit separate denominators.

- [ ] **STK-040** — Implement directional and target-before-stop labels with open, expired, no-entry, invalid-data and ambiguous states. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-041** — Calculate counts, accuracy, net expectancy, drawdown, turnover, exposure and suitable buy-and-hold/no-trade baselines. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-042** — Add chronological validation with overlap-aware gaps and reports by horizon, sector, regime and sample size; report uncertainty. **[Backlog]** · Priority: P2 — Medium

### S15 — Historical replay screen

Epic: E05 · Target: v0.2 · Status: Backlog · Owner: Unassigned · Depends on: S14

**Acceptance:** A user selects a past date, sees the frozen suggestion, then reveals subsequent prices and outcomes.

- [ ] **STK-043** — Build stock/date/strategy selector and before/after chart with future candles hidden until reveal. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-044** — Add batch experiments, failure drill-down and permitted result export with reproducible run IDs. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-045** — Release v0.2 using a covered past-date example; demonstrate anti-leakage checks and disclose unavailable historical news/universe data. **[Backlog]** · Priority: P2 — Medium

### S16 — Primary company and IPO documents

Epic: E06 · Target: v0.4 · Status: Backlog · Owner: Unassigned · Depends on: S03,S07

**Acceptance:** Every document/fact has source, publication time, retrieval time and version; restatements never replace history silently.

- [ ] **STK-046** — Implement permitted NSE/BSE filing routes or manual imports; deduplicate cross-exchange filings and revisions. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-047** — Implement SEBI offer-document and issuer IR imports for DRHP/RHP, annual reports and presentations. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-048** — Extract financial facts with units, fiscal periods, consolidated/standalone scope and page citations; reconcile and flag inconsistent numbers. **[Backlog]** · Priority: P2 — Medium

### S17 — Decision-relevant news

Epic: E06 · Target: v0.4 · Status: Backlog · Owner: Unassigned · Depends on: S16

**Acceptance:** News is source-linked, deduplicated and mapped to stocks/sectors; historical coverage and rumours are labelled.

- [ ] **STK-049** — Integrate permitted filing/news feeds and retain only allowed text or metadata. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-050** — Classify earnings, orders, management, regulatory and macro catalysts; separate event, publication and first-available timestamps. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-051** — Build focused news feed with materiality reasons; enforce as-of retrieval and prohibit current news in historical replay. **[Backlog]** · Priority: P2 — Medium

### S18 — Grounded company research agent

Epic: E06 · Target: v0.4 · Status: Backlog · Owner: Unassigned · Depends on: S11,S17

**Acceptance:** A report covers business, disclosed clients, financials, valuation, peers and risks with evidence; unknowns stay unknown.

- [ ] **STK-052** — Build bounded date-filtered retrieval/tools, structured LLM outputs and token limits; Python computes financial/technical numbers. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-053** — Build research template for revenue, profit, EBITDA definition, cash flow, debt, customer concentration, governance and valuation. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-054** — Combine versioned quantitative evidence and research into buy/sell/wait judgement with horizon, thesis, invalidation and citations; distinguish valuation from trading target. **[Backlog]** · Priority: P2 — Medium

### S19 — IPO assessment

Epic: E06 · Target: v0.4 · Status: Backlog · Owner: Unassigned · Depends on: S18

**Acceptance:** Listing and long-term assessments are separate and refer to the applicable offer-document version.

- [ ] **STK-055** — Build IPO calendar and verified price-band, proceeds/OFS, dilution, dates and document facts. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-056** — Implement financial quality, customer concentration, peer valuation and risk assessment with apply/watch/avoid/insufficient-data conclusions. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-057** — Build IPO screen and later outcome tracking; separate allotment assumptions and exclude unreliable grey-market premium from core rules. **[Backlog]** · Priority: P2 — Medium

### S20 — Discovery and forward paper evaluation

Epic: E07 · Target: v0.3 · Status: Backlog · Owner: Unassigned · Depends on: S09,S11,S15

**Acceptance:** Scans produce immutable ranked suggestions and track outcomes with the same engine as replay and permitted data.

- [ ] **STK-058** — Build bounded-universe scanner, liquidity filters and transparent ranking grouped by horizon. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-059** — Build watchlist/dashboard and deduplicated in-app alerts with timestamps, entry/exit points and reason for change. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-060** — Enable scheduled forward paper tracking and release v0.3; verify simulated mode and data-outage behaviour. **[Backlog]** · Priority: P2 — Medium

### S21 — Portfolio and flexible contributions

Epic: E07 · Target: v0.3 · Status: Backlog · Owner: Unassigned · Depends on: S09,S11,S14

**Acceptance:** Cash contributions are separate from returns and skipped months do not create fictitious funds.

- [ ] **STK-061** — Implement holdings reconciliation and cash ledger for deposits, withdrawals, trades and corporate actions. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-062** — Build realised/unrealised P&L, concentration and concurrent-risk views using selected active capital. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-063** — Add holding-specific exit/thesis reviews and manual import fallback; real trades always remain owner actions at this stage. **[Backlog]** · Priority: P2 — Medium

### S22 — Intraday research

Epic: E07 · Target: v0.5 · Status: Backlog · Owner: Unassigned · Depends on: S12,S20,S21

**Acceptance:** Intraday claims use suitable interval data, realistic latency and costs, with visible missing-data limits.

- [ ] **STK-064** — Add approved intraday subscriptions and session-aware closed-candle aggregation with reconnect/backfill. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-065** — Implement intraday VWAP/volume setup, entry/exit cutoffs and spread/slippage/overnight constraints. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-066** — Release intraday replay/forward-paper comparison; test live/replay parity, latency and cost sensitivity. **[Backlog]** · Priority: P2 — Medium

### S23 — Predictive model experiment

Epic: E08 · Target: v0.6 · Status: Backlog · Owner: Unassigned · Depends on: S12,S14,S20

**Acceptance:** A simple learned model competes with fixed rules on later untouched data; losing candidates remain experimental.

- [ ] **STK-067** — Build labelled as-of feature dataset with target horizons/barriers, train-only preprocessing and overlap separation. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-068** — Train a simple scikit-learn baseline and optional LightGBM candidate with bounded tuning and calibration checks. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-069** — Evaluate untouched periods and forward shadow results; version splits/features/models and promote only against precommitted gates. **[Backlog]** · Priority: P2 — Medium

### S24 — LLM evaluation and failure diagnosis

Epic: E08 · Target: v0.4 · Status: Backlog · Owner: Unassigned · Depends on: S14,S18

**Acceptance:** LLM judges check reasoning quality; actual prices determine outcomes; judge errors and hindsight contamination are recognised.

- [ ] **STK-070** — Create human-reviewed cases for unsupported claims, wrong units, stale evidence, contradictions and source-document prompt injection. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-071** — Use DeepEval/judge checks for factual support, citations, retrieval and tool use; calibrate against human reviews and meter cost. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-072** — Classify bad data, leakage, weak signals, regime changes, unrealistic fills and unsupported narratives; compare component ablations where valid. **[Backlog]** · Priority: P2 — Medium

### S25 — Reliability and spending controls

Epic: E09 · Target: v1.0 · Status: Backlog · Owner: Unassigned · Depends on: S06,S20,S24

**Acceptance:** Failures and costs are visible; optional AI work stops before exceeding configured limits.

- [ ] **STK-073** — Build health dashboard for feed lag, job errors, data coverage, provider quotas, analysis latency and actionable alerts. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-074** — Enforce per-run/day/month AI budgets, permitted caching and retention with required audit preservation. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-075** — Exercise backup restore, outage recovery, migration rollback, token expiry and credential revocation. **[Backlog]** · Priority: P2 — Medium

### S26 — Strategy lifecycle

Epic: E09 · Target: v1.0 · Status: Backlog · Owner: Unassigned · Depends on: S22,S23,S24

**Acceptance:** Experiment/shadow/active/retired states and versioned promotion evidence make changes reversible.

- [ ] **STK-076** — Create strategy/model registry with immutable feature, threshold, prompt and model versions. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-077** — Add sample-aware data, forecast and net-performance degradation monitoring with documented pause rules. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-078** — Implement champion/challenger comparison, relevant regression runs, manual promotion and rollback; final test sets stay untouched. **[Backlog]** · Priority: P2 — Medium

### S27 — Stable personal research release

Epic: E09 · Target: v1.0 · Status: Backlog · Owner: Unassigned · Depends on: S19,S21,S25,S26

**Acceptance:** All agreed research workflows are usable; failed trading hypotheses remain visibly experimental.

- [ ] **STK-079** — Run end-to-end acceptance for gain, loss, wait, no-entry, corporate action, missing evidence, IPO revision and broker disconnection. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-080** — Review source rights, software notices, private access, recovery evidence and projected monthly spending. **[Backlog]** · Priority: P2 — Medium
- [ ] **STK-081** — Release v1.0 with runbook, known limitations and measured results; software readiness is not a profitability claim. **[Backlog]** · Priority: P2 — Medium

### S28 — Optional execution eligibility

Epic: E10 · Target: v1.1 · Status: Backlog · Owner: Unassigned · Depends on: S02,S27

**Acceptance:** Exact current broker/exchange obligations and owner limits are satisfied before order capability is enabled.

- [ ] **STK-082** — Recheck Upstox/Zerodha API-order requirements, static IP, order types/rates, identifiers and necessary approvals. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-083** — Prepare broker onboarding and static-IP/credential separation; record costs and owner actions without submitting applications or purchases. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-084** — Freeze allowed broker/products/capital limits and approval flow; retain disabled feature until prerequisites and owner decision are complete. **[Backlog]** · Priority: P3 — Low

### S29 — Human-approved order workflow

Epic: E10 · Target: v1.1 · Status: Backlog · Owner: Unassigned · Depends on: S28

**Acceptance:** Each order has an exact owner-confirmed preview, idempotency protection and reconciled lifecycle.

- [ ] **STK-085** — Build preview with symbol, side, quantity, type, price constraints, charges, funds and risk; reject stale requests. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-086** — Implement submission/state machine for rejection, partial fills, cancellation and uncertain timeouts; never blindly retry. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-087** — Add kill switch, credential revocation and execution audit trail; research tools have no direct order access. **[Backlog]** · Priority: P3 — Low

### S30 — Optional execution validation

Epic: E10 · Target: v1.1 · Status: Backlog · Owner: Unassigned · Depends on: S29

**Acceptance:** Mock/test-route failure cases pass; actual live validation requires explicit approval of the concrete order.

- [ ] **STK-088** — Test lifecycle using broker-supported sandbox where available or deterministic mocks, including duplicates and restarts. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-089** — After explicit order authorisation only, perform limited live validation and reconcile actual charges/fills; otherwise mark this task blocked. **[Backlog]** · Priority: P3 — Low
- [ ] **STK-090** — Release optional execution with measured evidence and runbook; keep execution off by default until enabled by owner. **[Backlog]** · Priority: P3 — Low

## 8. Why recommendations may fail, and where we address it

| Failure after a few months | Prevention/detection in this backlog |
|---|---|
| Missing/stale/misadjusted prices; symbol mix-ups | S07–S09 quality manifests and stale-data suppression |
| Future information or revised accounts enter old tests | S05 availability contract; S13 future-read guards; S16 versioned filings |
| Surviving-stock universe makes history look better | S07 as-of universe and explicit coverage limits |
| LLM already knows historical events | S24 disclosure and forward evaluation; never treat an old-date prompt as proof of a clean historical test |
| News archive incomplete or publication timestamps wrong | S03 rights/coverage sourcing and S17 first-available timestamps |
| Overfitting, random time splits or repeated tuning on test data | S14/S23 chronological splits, overlap gaps and untouched final tests; S26 trial registry |
| Correct direction but unfilled entry or unprofitable trade | S13 fill/cost simulation and S14 separate forecast/trading metrics |
| More indicators create redundant confidence | S12 strategy/feature ablations rather than an indicator vote count |
| Market regime changes or live engine differs from replay | Shared engine S05; forward comparison S20/S22; monitoring S26 |
| Hallucinated clients, financials or causal explanations | S16 fact validation, S18 citations/unknown states, S24 reviewed evaluations |
| High judge score mistaken for trading edge | S24 judges reasoning only; S14 prices score outcomes; S23 promotion evidence |
| Capital/exposure errors or deposits counted as profit | S11 sizing and S21 reconciled cash/contribution ledger |

## 9. First work session

Pull **STK-001**. Deliver a short recommendation contract and one completely worked example with fictional numbers: what is known at the cutoff, suggested action, entry condition, stop/target, expiry, and exactly how later prices determine each outcome. Review that concrete result, then pull STK-004 to establish the permitted data route. This fixes the evaluation goal before implementation and avoids changing the architecture repeatedly.

Next ready sequence: STK-002 → STK-003; source work STK-004 → STK-005 → STK-006 and STK-007 → STK-008 → STK-009. Once S01 is complete, S04 can begin using synthetic fixtures while source questions are resolved. Reorder based on actual blockers, retaining the one-task WIP limit.

## 10. Official source register

Reviewed 9 October 2026. Recheck prices and terms before activation. Official pages establish the cited product/terms; they do not by themselves grant the particular rights this project needs.

- R1 — Upstox API product/pricing: https://upstox.com/trading-api/
- R2 — Zerodha Personal/Connect pricing: https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/what-are-the-charges-for-kite-apis
- R3 — Kite API terms, especially API use and content restrictions: https://kite.trade/terms/
- R4 — NSE data usage/sharing policy: https://www.nseindia.com/static/market-data/nse-data-policy
- R5 — BSE corporate announcements and data products: https://www.bseindia.com/corporates and https://www.bseindia.com/marketdata-products
- R6 — SEBI public-issue filings and corporate-filing source directory: https://www.sebi.gov.in/filings/public-issues.html and https://www.sebi.gov.in/curation/corporate_filings.html
- R7 — SEBI Research Analysts master circular, 6 February 2026, for scoped regulatory review: https://www.sebi.gov.in/legal/master-circulars/feb-2026/master-circular-for-research-analysts_99571.html
- R8 — Lightweight Charts licence and attribution: https://github.com/tradingview/lightweight-charts#license
- R9 — Upstox algo/static-IP announcement: https://upstox.com/developer/api-documentation/announcements/algo-trading-circular/

## 11. Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-09 | Planning baseline 1 | Created 10 epics, 30 stories and 90 tasks; added provider sourcing, rights gates, budget and private release sequence. No implementation marked complete. |

| 2026-10-09 | Priority revision | Added explicit P0–P3 policy and priorities to all 90 tasks. Preserved status, dependencies and estimates. |
