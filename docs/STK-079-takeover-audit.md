# STK-014/074/079/080 — Takeover audit, recovery path and critical-path plan

3 November 2026 (IST). Read-only audit of `main` `63e2cfc`, PR #35 head `8611904`.
This branch is based on PR #35. This document does not replace `SD-ARCH-3.0.md` or
`SIMPLE-BOARD.md`. It records what was verified, what this branch adds, and what is
still outside engineering control.

## 1. Verified state, kept separate from earlier reports

| Fact | Status | Evidence |
|---|---|---|
| PR #35 is open, not a draft and not merged. Its head is `8611904`. | Verified | `git ls-remote refs/pull/35/head` |
| All four exact-head checks passed: `unit`, `postgres`, `ui` and `checks`. | Verified | GitHub check-runs API for `8611904` |
| PR #35 has no submitted reviews. | Verified | PR page |
| `main` has migrations 0001–0015. Two files are numbered 0012: the D3-11 one and `real_0012`. 0014 is a no-op join, and 0015 adds the grant fences. | Verified | `backend/migrations/versions` |
| The retained database `stk_real001_private` is at 0013. | Reported, not yet re-checked | REAL-001 reconciliation, owner investigation |
| INFY has 419 candle revisions across 13 streams, observed about 2 Sep–23 Oct, with prices `split_bonus_adjusted`. | Reported, not yet re-checked | Owner investigation |
| A saved Upstox grant is active, with 30-day retention in the view configuration. | Reported, not yet re-checked | Owner investigation |
| Two pending investigation documents exist as untracked files. | Reported, not yet re-checked | Owner investigation |

Re-checking the reported rows needs the Mac. `scripts/audit_retained_database.py` (§4) re-checks
all of them read-only and prints sanitized JSON.

### Root cause of the INFY HTTP 403, reproduced on invented data

- `guarded_read` calls `discovery.lock_grant_fences`, which only exists after 0015. On a 0013
  schema every permitted read fails closed, and the API mapped that to "Source permission denied".
- `test_legacy_real_recovery.py` builds the old 0013 graph and seeds rows the way the old
  ingestion did, with no page attribution. It then confirms three things:
  - The read is denied before the upgrade.
  - `upgrade head` changes no pre-existing row and registers OPEN provider, account and grant fences.
  - Reads work after the upgrade.
- Reads do not need page attribution (`discovery.ingestion_grants`). Legacy pages stay
  unattributed and immutable by design. Only new writes record attribution.

### Second, independent blocker: rolling streams

`describe()` qualifies adjusted prices only when every selected bar comes from one complete
ingestion stream. Rolling daily refreshes, such as 13 streams, return
`batch_identity_missing_or_ambiguous`. Fixing the schema alone does not bring the chart back.

## 2. Completion assessment (by evidence; no single percentage)

| Area | Assessment | Basis |
|---|---|---|
| Code implementation | **High.** D3-01 to D3-11 are merged. D3-12 (deployment) and D3-13 (release) are missing, apart from the STK-079 slice. | Board, merged PRs #2–#34 |
| End-to-end integration | **Synthetic: high. Real: one instrument path,** currently broken by the schema gap. | REAL-001 PARTIAL, INFY 403 |
| Real data readiness | **Low.** There are only adjusted descriptive prices. Original prices, a filing corpus and complete corporate-action evidence are all missing. | PR #35, provider matrix |
| Research/AI quality | **Not established.** The 50-case holdout is empty and there is no independent reviewer. | STK-052 records |
| Investment evaluation | **None genuine.** There are synthetic scorecards only. | D3-11, STK-041/042 |
| UI functionality | **Good.** All workflows exist and the denial states are correct. | 13 browser workflows in CI |
| Operational readiness | **Low to partial.** Recovery drills were done. There is no unattended schedule, no off-host backup and no approved deployment. | REAL-001 operations |

## 3. What this branch adds (STK-014/074/079)

All four items are limited to fixing the blocker.

1. **Diagnosis instead of a misleading denial.**
   - When the schema is behind 0015, company and scan reads return
     `503 Database migration required…`. Status now reports `database` (schema version vs required).
   - Genuine source denials still return 403.
   - No data is read and no fence is bypassed.
2. **Readiness banner, "What you can do today".**
   - It reads `none` or `level_1_descriptive` from the actual company read.
   - It lists what each later milestone adds.
3. **Multi-stream recovery remains unavailable after security review.**
   - `approved_v1` alone is not adjustment-vintage evidence. Matching recent overlap
     cannot establish whether an older, non-overlapping segment was subsequently adjusted.
   - All full-stream revisions (including superseded overlaps), parents and original grants
     are now temporally checked and fenced before page verification. Unauthorized dependencies deny access.
   - Even authorized, matching streams return `adjusted_vintage_unverified`; charts and
     metrics are withheld. Single verified observation batches retain their existing contract.
4. **Owner tooling (read-only on the original).**
   - `scripts/audit_retained_database.py` prints, all sanitized:
     - schema version and whether the fence tables exist;
     - per-table row counts and SHA-256 fingerprints;
     - grant expiry, scopes and uses (identifiers digested);
     - for each INFY stream: clocks, coverage, quarantine and retention age;
     - a qualification dry run of the stream rule;
     - the current file-grant decision for each stream;
     - hashes of untracked files, which covers the two pending documents.
   - `scripts/rehearse_migration.py`:
     - fingerprints the original and takes an `O_EXCL` 0600 dump;
     - re-checks that the original did not change;
     - restores the dump into a new `stk_rehearsal_*` database and proves it identical;
     - upgrades only the copy, twice;
     - proves every pre-existing table is unchanged and that every grant got OPEN fences with no
       restrictions;
     - re-checks the original once more.
   - `--keep-copy` keeps the upgraded copy for browser acceptance before the original is touched.

Validation in this workspace (disposable PostgreSQL, invented rows only):

- Full unit, integration and migration-lifecycle suites.
- 4 new multi-stream integration cases: off by default, agree, conflict and gap.
- The 0013 → 0015 legacy recovery case.
- 1 new API test.
- 2 new Playwright viewports (1280 and 390).
- An end-to-end browser run against a simulated retained 0013 database: migration message first,
  then a chart and indicators on the rehearsed copy.

No genuine market data, provider call or retained database was used.

## 4. Owner recovery runbook (on the Mac; nothing here calls a provider)

1. Stop the worker and launchd jobs, so there are no writers.
2. Run `DATABASE_URL_FILE=<private> python scripts/audit_retained_database.py --listing NSE:INE009A01021 --view-config <private view config> > audit-before.json`
   and share the JSON. It contains no prices, tokens or account IDs.
3. Run `DATABASE_URL_FILE=<private> python scripts/rehearse_migration.py backups/pre-0015-<date>.dump --keep-copy`.
   It must print `"pass": true` and `"original_unchanged": true`.
4. Point a local API at the kept copy. Repeat step 2 against it, then open INFY in the browser.
   - `batch_identity_missing_or_ambiguous` or `adjusted_vintage_unverified` remains blocked.
     Owner approval alone cannot establish adjustment consistency across downloads.
   - The dry run checks structural integrity only, not authorization or qualification.
5. Only after explicit approval: run the normal `alembic upgrade head` on the original,
   then repeat step 2 and the browser check.
6. Keep the dump. Never run `validate_migrations.py`, a downgrade or a reseed against the original.

Retention check: if `beyond_configured_retention` is true for any stream, the stored observations
are older than the configured 30-day retention. This app does not delete them automatically (the
grant does not authorize tombstones). The owner has to decide under the Upstox terms whether the
data can still be used, renewed or must be deleted. This decision may block Level 1 for older
windows, and no code change can resolve it.

## 5. Critical blockers

| # | Blocker | Fix it alone? | Owner/provider action | Cost/time | Resolution |
|---|---|---|---|---|---|
| 1 | Retained database at 0013 | Tooling done; execution is on the Mac | Run §4, approve migrating the original | ₹0, 1–3 days | Rehearse, approve, then upgrade |
| 2 | 13 rolling streams | BLOCKED | Establish permitted coherent observation-batch evidence | Unverified | Matching overlap is insufficient; no combined chart |
| 3 | Retention of older observations | No | Confirm the Upstox retention terms | ₹0; provider-dependent | Audit flags affected streams |
| 4 | No original (unadjusted) prices | No | Choose a source: NSE licence quote, Kite (₹500/month, basis unverified), or defer | Unknown | Level 1 stays descriptive; no execution-grade backtests |
| 5 | Filing/news corpus rights and publication times | No | Send the drafted inquiries, or accept structured fundamentals only | ₹0; reply time unknown | Filing RAG after rights are confirmed |
| 6 | Independent AI evaluation (50 cases) | No | Name a reviewer: about 10–15 hours of owner time, or a paid reviewer | Unknown | AI stays shadow |
| 7 | Strategy, risk, cost and benchmark policies | Drafts only | Approve the policy sheet | ₹0; 1–2 sessions | Conservative defaults proposed |
| 8 | Forward evidence takes calendar time | No | Authorize forward paper tracking | ₹0; months | Start as early as possible |

## 6. Timeline (go/no-go gates; no date depends on unconfirmed rights)

- **Level 1, usable real-data app (12-stock pilot, adjusted descriptive data):** late November 2026.
  - Gate: §4 passes on the copy, INFY is shown in the browser, and the original is migrated.
- **15 December 2026 release candidate:** achievable only as Level 1 plus shadow research on all
  three horizons. A Level 2 release by that date is not achievable, because blockers 4–6 are external.
- **Level 2, full three-horizon private release:** February–March 2027 at the earliest.
  - Gated on an original-price source, filing rights, the 50-case review, approved policies,
    operations, backups and D3-13 checks.
- **Level 3, validated performance:**
  - Swing: at least 3 months of forward paper after Level 2.
  - Short-term: 6–12 months.
  - Long-term: multi-year.
- **Extensions:** IPO, news-driven discovery, read-only Upstox/Zerodha holdings, optional ML and
  intraday. Each one is scoped separately after Level 2.

## 7. Cost

| Item | Cost | Status |
|---|---|---|
| Current operation | ₹0/month (Upstox Analytics, local Ollama) | In use |
| Kite data | ₹500/month | Unproven for original prices |
| Hetzner CX23 + B2 | About €5–7/month | Only if hosting is approved |
| NSE EOD licence | Quote required | Unknown |
| Paid reviewer | Optional | Unknown |

## 8. Owner decisions (not already recorded in the repository)

1. Approve migrating the original after the rehearsal passes.
2. Approve merging PR #35, then this branch, after review.
3. Accept adjusted descriptive research as the Level 1 basis.
4. Resolve coherent adjusted-batch evidence; multi-stream approval alone is insufficient.
5. Retention: confirm continued use of observations older than 30 days.
6. Choose the original-price path.
7. Choose whether to send the rights inquiries.
8. Name the 50-case reviewer.
9. Approve the policy sheet.
10. Choose local-only operation or Hetzner.

## 9. What the owner can do, now and after each milestone

| When | What the owner can do |
|---|---|
| **Today** | Synthetic workflows only. Real company reads fail closed. The UI now says why: the database needs migrating. |
| **After §4 and the migration** | Authorized reads can proceed; adjusted charts still require a coherent, qualified batch. Migration alone does not qualify the retained rolling streams. |
| **After the pilot extension** | The same for the 12 pilot stocks, with discovery ranking marked as descriptive. |
| **After Level 2** | Qualified shadow BUY/WATCH/AVOID/INSUFFICIENT EVIDENCE decisions, point-in-time replay, and a paper portfolio with measured outcomes. |
| **After Level 3** | Evidence of whether each horizon and the AI arms actually add value, reported as measured. |

## PR #36 review corrections

Successful corporate-action fetches now append grant-attributed empty ingestion-page receipts,
including empty and unchanged responses. Weekly scheduling uses the receipt clock; it does
not rewrite original evidence observations. These receipts survive worker restart.

Rehearsal first proves that the configured URL and Compose psql share the same database
using a random, database-scoped advisory-lock challenge, before any dump or copy creation.
Shutdown retains the plist on bootout failure or when service absence cannot be verified.
These checks do not authorize source activation or migration of the retained original.
