# Stock Discovery — Audit, Critical Path and Takeover Plan

A read-only audit of the existing Stock Discovery repository, followed by a plan to finish it as a private, three-horizon NSE research application.
The existing architecture (FastAPI, worker, PostgreSQL, React/TypeScript, local Ollama) is kept. No rewrite is proposed, because the audit found no requirement the current design cannot meet.

## Who it's for
One owner investing about ₹50,000 a month in NSE stocks with a conservative risk appetite. The owner wants to see real prices, company research and three-horizon views, and to make their own decisions. The app gives research support only and never places real orders.

---

## Audit findings (verified 3 Nov 2026 from public GitHub; nothing changed)

**Verified on GitHub**
- `main` is at `63e2cfc` (PR #34 merged 1 Nov). There are 160 commits, 4 branches, no tags and no releases.
- PR #35 is open, ready for review and unmerged. Its head is `8611904`, and it has **no reviews**. CI status for that head could not be read from the public page, so it must be re-checked before merging.
- `main` has migrations **0001–0015**. Two files are both numbered 0012 (experiment governance and real shadow), and 0014 reconciles them. **0015 adds the grant fences.**
- The local database that was kept is reported to be at **0013**. That puts it two migrations behind: **0014 (governance reconciliation) and 0015 (grant fences)**. This matches the HTTP 403 "Source permission denied" seen for INFY. The read fence correctly fails closed because the fence tables don't exist.
- The board shows D3-01 to D3-11 merged and D3-12/13 not started, apart from the STK-079 swing slice. The REAL-001 pilot is PARTIAL: 408 candles, 96 validated facts and two local model reports.
- Upstox is free and read-only. Provider replies support private storage, research and replay of market data. Filing and news corpus rights are unresolved. The NSE feed is paid and unlicensed. Kite costs ₹500/month and hasn't been purchased. A SEC EDGAR request returned 403 from the earlier runtime.

**Reported but not verified (needs the owner's read-only checks)**
- The 419 INFY revisions across 13 streams, the active saved Upstox grant and 30-day retention, the two pending investigation documents, and the state of the backups.

### A. Completion assessment (by evidence, not a single percentage)
| Area | State | Basis |
|---|---|---|
| Code implementation | **High.** All core packages D3-01 to D3-11 are merged. D3-12/13 are missing. | Board and merged PRs |
| End-to-end integration | **Synthetic: high. Real: low.** One real instrument path exists, and it is currently broken by the schema gap. | REAL-001 PARTIAL, INFY 403 |
| Real data readiness | **Low.** The only price data is split/bonus-adjusted descriptive data. There are no qualified original prices, no filing corpus and no complete record of corporate actions. | PR #35, provider matrix |
| Research/AI quality | **Not established.** The 50-case holdout is empty, there is no human reviewer, and the development benchmarks are mixed. | STK-052 records |
| Investment evaluation | **None genuine.** Results so far are synthetic scorecards only. No real backtest, benchmark or forward paper result exists. | D3-11, STK-041/042 |
| UI functionality | **Good.** Discovery, company view, charts, replay, scorecard, paper portfolio, history and denial states all exist. | 13 browser workflows pass in CI |
| Operational readiness | **Low to partial.** Local worker recovery is proven. The launchd job is inactive, there's no unattended run, and the deployment is unapproved. | REAL-001 operations |

### B. Remaining work by type
- **New engineering (small and bounded):**
  - A verified way to combine the 13 adjusted-price streams. Each stream is verified on its own, overlapping candles must match exactly, and any conflict fails closed.
  - Extending real discovery from INFY to the 12-stock pilot universe.
  - Wiring Upstox corporate actions and the calendar into ingestion.
  - Building D3-13 release checks.
  - Making the remaining real-data unavailable states read clearly.
- **Configuration:** migrating the database to 0015 after a rehearsal, recording a grant for each allowed use, activating launchd, and setting AI budgets.
- **Data acquisition:**
  - A permitted source of original (unadjusted) prices.
  - Original filings with reliable publication times.
  - A benchmark index series.
- **Validation:** independent human review of 50 untouched cases, real financial extraction quality, and point-in-time strategy comparisons.
- **Owner approval:** strategy thresholds, risk and exposure, cost/slippage assumptions, benchmark, promotion rules, deployment target, and every change to the original database.

### C. Critical blockers
| # | Blocker | Evidence | Can I fix it alone? | Owner/provider action | Cost/schedule | Resolution |
|---|---|---|---|---|---|---|
| 1 | Kept database at 0013 while code needs 0015 | INFY returns 403; 0014/0015 exist on main | Only tooling and rehearsal. The real database is on the Mac. | Run backup, restore and rehearsal commands; approve migrating the original | ₹0, about 3–5 days | Back up → restore to a separate copy → upgrade the copy → compare row counts, hashes and grants → owner approves → migrate the original |
| 2 | 13 INFY streams can't qualify as one batch | PR #35 known limitation | Yes (engineering) | Approve the stream-combining rule | ₹0, about 1 week | Combine streams only when each is verified and overlaps agree. Never merge silently. |
| 3 | No original (unadjusted) prices | Upstox prices are adjusted; Breeze is unqualified; NSE MCP matches closes only | **No** | Choose a source and possibly pay for it | NSE licence: quote unknown. Kite: ₹500/month, adjustment basis unverified | Level 1 runs on adjusted descriptive data. Execution-grade backtests wait for this. |
| 4 | Filing/news corpus rights and publication times | Provider matrix Phase 3–5 | **No** | Send the drafted Upstox/Infosys inquiries, or accept a decision on structured Upstox fundamentals only | ₹0; provider reply times unknown | Use Upstox structured numbers now. Add the filing RAG once rights are confirmed. |
| 5 | Independent AI evaluation | 50-case set empty; no reviewer | **No.** A model can't be its own ground truth. | Owner or a hired reviewer labels 50 cases | Owner time about 10–15 hours, or a paid reviewer (cost unknown) | AI stays labelled "shadow" until this passes |
| 6 | Strategy and risk policies not approved | Phase 8 policy review is unapproved | Drafts only | Approve thresholds, risk, costs and benchmark | ₹0, 1–2 review sessions | I prepare one approval sheet with conservative defaults |
| 7 | Forward evidence takes calendar time | Swing horizon needs weeks of outcomes; long-term needs years | **No.** No code can shorten this. | Authorize forward paper tracking | ₹0; months of elapsed time | Start forward paper tracking as early as possible |

### D. Timeline (assuming owner checks come back within 2 days, and no dates depend on unconfirmed rights)
- **Usable real-data app (Level 1, 12-stock pilot, adjusted descriptive data):** about **late November 2026**. Go/no-go gate: the rehearsed migration passes and INFY works end to end in the browser.
- **Private release candidate by 15 Dec 2026:** **achievable only as Level 1 plus shadow (non-actionable) research on all three horizons.** A Level 2 qualified release by 15 Dec is **not achievable**, because blockers 3–5 are outside engineering control.
- **Full three-horizon private release (Level 2):** **February–March 2027 at the earliest.** It is gated on an original-price source, filing rights, the 50-case review and approved policies.
- **Independent research and performance validation (Level 3):**
  - Swing: at least 3 months of forward paper tracking after Level 2 (about mid-2027).
  - Short-term: 6–12 months.
  - Long-term: multi-year. It can only be evaluated over time, not certified on release.
- **Roadmap extensions:** each starts only after Level 2 and gets its own scope (see Phase 3).

### Cost estimate
- **Current:** ₹0/month. Upstox Analytics is free and Ollama runs locally.
- **Optional recurring:**
  - Kite data at ₹500/month (not yet shown to supply original prices).
  - Hetzner CX23 plus B2 backups at roughly €5–7/month, if hosted deployment is approved.
- **One-time or unknown:**
  - An NSE EOD licence (quote required).
  - A paid human reviewer (optional).
- **Recommended path:** stays at ₹0 until the owner chooses a source for original prices.

### E. Immediate next three tasks
1. **Database recovery rehearsal:** the owner runs read-only checks and a backup. I supply exact commands and check the results against a restored copy upgraded 0013 → 0015.
2. **Close PR #35:** re-verify CI on the exact head commit, do an independent review pass, and merge only with the owner's approval.
3. **Qualify the INFY streams:** build the fail-closed stream-combining verification, then show INFY end to end in the browser with real adjusted prices.

---

## Core features and experience (target product)
- Discovery and rankings across the pilot universe, with reasons for each shortlist and honest "insufficient evidence" results.
- A company page with:
  - OHLC charts and indicators: SMA, EMA, ATR, support/resistance, breakouts and momentum. Relative volume shows only where it's supported.
  - Fundamentals, corporate actions and cited research.
- Swing, Short-term and Long-term views, each with its own rules and risk limits.
- Research decisions: BUY / WATCH / AVOID / INSUFFICIENT EVIDENCE. Every decision is labelled "shadow" until the qualification gates pass.
- Historical replay, a scorecard comparing Q, Q+RAG and Q+agent, and benchmark comparisons.
- A paper portfolio with virtual cash, costs, risk limits and a permanent history of decisions and outcomes.
- Data freshness, source provenance and clear reasons whenever data is denied or unavailable.

## User flow
1. Sign in on the Mac, then open Real research.
2. Review the discovery list for a horizon, then open a company.
3. Inspect the chart, indicators, fundamentals, citations and decision status.
4. Save the research to history and optionally track it in the paper portfolio.
5. Check the scorecard and outcomes over time. Daily, weekly and monthly runs happen automatically.

## UI/UX feel
The existing UI is kept. Changes are limited to clearer empty and denied states, and a "What you can do today" status banner that shows Level 1, 2 or 3 readiness for each horizon.

---

## Implementation phases

### Phase 1 — MVP (built now): Usable real-data application (Level 1)
- Clone the repository into this workspace, re-check PR #35, and write the final audit as a repository document under a new STK ticket.
- Prepare scripts for the owner's read-only checks: migration version, row counts and hashes for each table, grants, retention, and confirmation that the two pending documents exist.
- Prepare scripts for backup, restore and a migration rehearsal on a separate copy. The owner runs them on the Mac and I verify the results. The original is migrated only after the owner approves.
- Build the fail-closed multi-stream verification for adjusted prices. This comes as a focused PR with STK references and exact-commit CI.
- Extend real descriptive research to the 12-stock pilot, using the existing Upstox grant only where it already allows the use.
- Add a readiness banner and clearer reasons for unavailable states.
- Show INFY, then the pilot universe, working end to end in the owner's browser.

### Phase 2 — Qualified three-horizon private release (Level 2)
- Bring in an original-price source, or validated corporate-action adjustments, once the owner chooses one.
- Add filings and announcements to the RAG once rights are confirmed, plus structured Upstox fundamentals and corporate actions.
- Get the policy approval sheet signed off, run the 50-case independent review, and run point-in-time Q vs Q+RAG vs Q+agent comparisons against the approved benchmark.
- Activate scheduling (launchd or Hetzner), backups with a tested restore, monitoring, the D3-13 release checks, and owner acceptance.
- Start forward paper tracking.

### Phase 3 — Validation and roadmap extensions
- Measure forward paper outcomes for each horizon. Results are reported as measured, including when they're negative.
- Each extension is scoped separately:
  - IPO analysis
  - News-driven discovery
  - Read-only Upstox/Zerodha holdings
  - Optional predictive ML
  - Intraday analysis

---

## Owner decisions required (none are already recorded in the repository)
1. Approve migrating the original database to 0015 after the rehearsal on a separate copy passes.
2. Approve merging PR #35 after review.
3. Accept adjusted-price descriptive research as the Level 1 basis, with no execution-grade P&L.
4. Approve the multi-stream combining rule: each stream verified, overlaps must match, conflicts fail closed.
5. Choose an original-price path: an NSE licence quote, a Kite trial, or deferring execution-grade backtests.
6. Choose whether to send the drafted Upstox/Infosys rights inquiries.
7. Name the human reviewer for the 50-case set.
8. Approve the policy sheet: thresholds, risk, costs and benchmark.
9. Choose local-only operation or Hetzner deployment.

## Assumptions
- The dates in the repository (Nov 2026) are the current project timeline.
- The local database state, the 13 streams, the grant and retention settings, and the pending documents are as described, until the owner's checks confirm them.
- Engineering for Phase 1 happens in this workspace on a clone of the repository, but real data stays on the owner's Mac. The owner runs any command that touches the database or providers and pastes back sanitized output.
- A fresh, separate database is created in this workspace for code, tests and migration rehearsal using synthetic data. Real market data never comes into this cloud workspace.
- Real data recovery upgrades the existing database on the Mac, which keeps the original history and provenance. If the rehearsal fails, the fallback needs owner approval. In that case the old database is kept untouched as an archive, a new database is created on the Mac, and the price history is downloaded from Upstox again as one fresh batch.
- Pushing branches or opening PRs needs either owner-supplied GitHub access or the owner applying patches. No merges happen without approval.
- No new provider calls are made beyond what existing grants allow. Nothing is purchased and no real orders are placed.
- The pilot universe stays at the existing 12 stocks until data rights support expanding it.
- "Shadow" labelling stays on every decision until the Level 2 gates pass.
- Cost figures for the NSE licence and any paid reviewer are unknown until quoted.
