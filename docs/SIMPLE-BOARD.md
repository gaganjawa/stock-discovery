# Stock Discovery — lightweight progress board

Updated: **14 October 2026** · Verified implementation checkpoint: **a9a3eb7**

## Current finish target: local daily-swing MVP

Owner selected **daily-swing MVP first**, with hosting deferred. [Software scope, startup and API-key setup](DAILY-SWING-MVP.md). Core synthetic workflows are implemented; optional AI explanation and a local launcher have been added. **Local synthetic MVP software acceptance is complete.** The app is running at http://127.0.0.1:5173; live-market data and hosted release remain deferred. The 81-ticket roadmap below is longer-term scope, not the current finish target.

LLM is optional: blank `OPENAI_API_KEY` is in `.env`; set `LLM_ENABLED=true` after adding a key. Calculations and trading signals remain deterministic. Without a key, explanations use frozen rule text.

## Overall

**A tested synthetic research MVP works end to end. A private deployed product and the full v1.0 roadmap are not complete.**

Working flow: fictional history → rule-based recommendation → historical replay → outcomes and scorecard → batch experiments → audit export. Version selection and chronological audit reports are available.

| Through v1.0: 81 tickets | Count | Meaning |
|---|---:|---|
| Done | 8 | Accepted ticket scope, including hosting selection—not provisioning |
| Implemented; awaiting release | 19 | Tested synthetic scope; not real-data or private-release acceptance |
| Partial | 8 | Useful implementation exists; material acceptance gaps remain |
| Other open work | 46 | 2 marked Ready and 44 Backlog; preparation may exist, but acceptance is not complete |

**27/81 tickets are done or implemented for synthetic use. This is not 33% of effort or production readiness:** ticket sizes differ, and the remaining integrations/release work is substantial. Optional v1.1 real-money execution (9 tickets) is excluded.

Latest verified implementation CI: **58 application tests, 11 database cases, 7 script tests, production build and browser workflow passed**. [Evidence](https://github.com/gaganjawa/stock-discovery/actions/runs/38612490959). These tests validate software, not trading profitability.

## Feature-by-feature

| Feature / tickets | Work completed | Work remaining | Status |
|---|---|---|---|
| Contracts and risk rules · 001–003 | Recommendation format, separate forecast/trade metrics, capital and sizing rules | Later features must preserve these contracts | Done |
| Hosting choice · 008 | Hetzner CX23, Linux, Docker Compose; encrypted restic to Backblaze B2 approved | Region, final checkout price, backup-key custody and separate provisioning authorization | Decision done; server not deployed |
| App foundation · 010–015 | UI/API/worker/database, navigation, migrations, CI, adapters, immutable versioned decisions | Formal private release; adapters are not live provider connections | Built for synthetic use |
| Data/source rights · 004–007 | Preliminary review records and questions | Use-specific permissions, coverage, quotes and applicable review for market/document/news inputs | Open |
| Software licence audit · 009 | Dependency inventory, notices, chart attribution and AMD64 evidence | Native source/notice closure and installed target-host inventory | Partial |
| Private access and hosting · 016 | Private Compose, secret files, non-root services, database privileges, throttling and HTTPS guards | Authorized server deployment and actual HTTPS/firewall/reboot acceptance | Partial |
| Operations and recovery · 017–018 | Persistent jobs, retries/locks, health checks, logs, monitoring setup, encrypted local recovery and rollback checks | B2 setup, off-host recovery, external alert delivery, hosted acceptance and release authorization | Partial |
| Historical data foundation · 019–024 | Synthetic instrument identity/universe, resumable ingestion, quality gates, manifests, calendars and limited split handling | Permitted real history; full corporate-action/import coverage and independent real samples | Mostly built for synthetic use; 020 partial |
| Core indicators and swing strategy · 028–033 | EMA/SMA, relative volume, ATR, breakout, deterministic BUY/WAIT/insufficient evidence, sizing, rule/provenance card | Real-history and private-release acceptance | Built for synthetic use |
| Replay and outcomes · 037–040, 043 | Cutoff-only data, freeze/reveal, entry/expiry/exits, synthetic costs, ambiguous-bar handling, strategy/date/stock controls | Real-market cost/data validation and private release | Built for synthetic use |
| Batch experiments and export · 044 | Nine-job sample batch, failure inspection, complete audit export, version-pinned reruns, preservation of old results | Release acceptance; legacy unpinned jobs retain old behavior | Built for synthetic use |
| Portfolio scorecard · 041 | Counts, separate denominators, net expectancy, single-slot return/drawdown, traded notional, closing-mark exposure, version-group selection and exclusions | Suitable market buy-and-hold benchmark and full planned portfolio acceptance; closing-mark exposure is not calendar-weighted | Partial |
| Validation and uncertainty · 042 | Grouped sample counts, descriptive intervals, chronological session assignments/gaps, exclusions, frozen audit policy and stable IDs | Real-history/complete-month validation, untouched-test and trial-ledger controls, fuller sector/regime acceptance | Partial |
| Private v0.2 release · 045 | Synthetic workflow evidence and limitations documented | Covered permitted historical example, full acceptance and authorized release | Partial |
| Broker reads and live feeds · 025–027 | Adapter foundations only | Authorized Upstox/Zerodha integrations, credentials, feed permissions, quotas/reconnect/freshness behavior | Open; not connected |
| Additional strategies · 034–036 | Core EMA baseline available | Ichimoku, additional indicators and independently evaluated strategy comparisons | Open |
| Documents, company research, news and IPO · 046–057 | Shared schema and navigation placeholders | Imports, extraction/citations, news classification, grounded research, IPO facts/analysis/outcomes | Open; feature workflows not implemented |
| Discovery, paper tracking and personal portfolio · 058–063 | Synthetic scan/jobs and sizing foundations | Ranked discovery, watchlists/alerts, scheduled forward paper tracking, holdings/cash ledger/reconciliation and exit reviews | Open |
| Intraday research · 064–066 | Shared daily engine foundation | Approved interval feeds, aggregation, intraday rules, latency/cost and replay/live parity checks | Open |
| Predictive models and LLM evaluation · 067–072 | Versioning/evaluation foundations | Feature datasets, model training/calibration, untouched evaluation, judged research cases and failure diagnosis | Open |
| v1.0 reliability and strategy lifecycle · 073–081 | CI, worker health and local recovery foundations | Full feed/cost monitoring, AI budgets, strategy registry/promotion/rollback, broad acceptance and v1.0 release | Open |

## Next work and external gates

1. Finish independent synthetic acceptance gaps in portfolio/benchmark and validation controls; keep partial tickets partial.
2. Close source permissions and permitted historical coverage before enabling real-data workflows.
3. Confirm region, final price and backup-key custody; obtain explicit authorization before any purchase or external deployment.
4. Complete host licence/security checks, off-host restore and alert acceptance before a private release.
5. Build later broker, research/news/IPO, portfolio, intraday and model workflows in dependency order.

**No external deployment, purchase, accepted release tag or real-money orders have been performed.** Hosting selection is final and will not be reopened.

## Tracking rules

- This Markdown file is the lightweight user-facing board requested by the owner. Update it at meaningful milestones; no hosted-board interaction is required for routine status updates.
- The hosted board has not been synchronized with recent work. Do not treat its older records as current.
- Keep [detailed ticket plan](stock-platform-kanban-plan.md) for scope/history and [work handoff](WORK-HANDOFF.md) for technical continuation.
- Done IDs: 001, 002, 003, 008, 010, 011, 012, 013.
- Synthetic implemented/release-pending IDs: 014, 015, 019, 021–024, 028–033, 037–040, 043, 044.
- Partial IDs: 009, 016–018, 020, 041, 042, 045. These remain Backlog in the detailed plan until their gates close.
- No fabricated hours, completion dates or effort-weighted percentages. Stop after the current authorized batch and await the owner's go.
