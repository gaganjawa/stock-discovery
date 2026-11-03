export const ASSESSMENT = [
  ["Code implementation", "High. D3-01 to D3-11 are merged. D3-12/13 are missing, apart from STK-079.", "Board, merged PRs"],
  ["End-to-end integration", "Synthetic: high. Real: one instrument path, broken by the schema gap.", "REAL-001 PARTIAL, INFY 403"],
  ["Real data readiness", "Low. Adjusted descriptive prices only. No original prices or filing corpus.", "PR #35, provider matrix"],
  ["Research / AI quality", "Not established. The 50-case holdout is empty.", "STK-052"],
  ["Investment evaluation", "None genuine. Synthetic scorecards only.", "D3-11"],
  ["UI functionality", "Good. All workflows exist and denial states are correct.", "13 browser workflows in CI"],
  ["Operational readiness", "Low to partial. No unattended schedule and no off-host backup.", "REAL-001 ops"],
];

export const CHANGES = [
  "An unmigrated database now returns a clear “Database migration required” instead of “Source permission denied”. Real denials still return 403.",
  "A “What you can do today” banner shows Level 1, 2 or 3 readiness from the actual company read.",
  "A multi-stream rule you have to approve, off by default. Each price stream is verified on its own, streams must overlap, every shared candle must match, and any conflict fails closed.",
  "audit_retained_database.py: a read-only, sanitized audit of the version, row hashes, grants, INFY streams, retention age, a dry run of the stream rule, and the pending documents.",
  "rehearse_migration.py: dumps, restores into a copy, upgrades only the copy, and proves no rows changed and all fences are registered.",
  "Tests: 937 unit tests and the full PostgreSQL and migration suites pass. New tests cover the 0013 → 0015 legacy recovery and the agree, conflict and gap stream cases, plus Playwright at 1280 and 390 wide.",
];

export const RUNBOOK = [
  "Apply the patch on top of PR #35 (branch feat/stk-014-074-079-real-data-recovery). Stop the worker and launchd.",
  "python scripts/audit_retained_database.py --listing NSE:INE009A01021 --view-config <private> > audit-before.json, then share the JSON. It contains no prices, tokens or account IDs.",
  "python scripts/rehearse_migration.py backups/pre-0015-<date>.dump --keep-copy. This must print \"pass\": true and \"original_unchanged\": true.",
  "Point a local API at the kept copy and open INFY. If it shows batch_identity_missing_or_ambiguous, decide on adjusted_multi_stream: \"approved_v1\".",
  "Only after your approval: alembic upgrade head on the original, then repeat the audit and the browser check.",
];

export const BLOCKERS = [
  ["1", "Retained DB at 0013", "Tooling done", "Run the rehearsal, approve the migration", "₹0 · 1–3 days"],
  ["2", "13 rolling INFY streams", "Done (rule v1)", "Approve or decline rule v1", "₹0"],
  ["3", "Observations older than the 30-day retention", "No", "Confirm Upstox retention terms", "₹0 · provider"],
  ["4", "No original (unadjusted) prices", "No", "NSE quote, Kite trial, or defer", "Unknown / ₹500 per month"],
  ["5", "Filing and news rights, publication times", "No", "Send the drafted inquiries", "₹0 · reply time unknown"],
  ["6", "Independent AI review (50 cases)", "No", "Name a reviewer (10–15 hours)", "Owner time"],
  ["7", "Strategy, risk, cost and benchmark policy", "Drafts only", "Approve the policy sheet", "₹0 · 1–2 sessions"],
  ["8", "Forward evidence needs calendar time", "No", "Authorize forward paper tracking", "Months"],
];

export const TIMELINE = [
  ["Level 1 · usable real-data app (12-stock pilot)", "Late Nov 2026", "Rehearsal passes, INFY shown in the browser, original migrated"],
  ["15 Dec 2026 release candidate", "Level 1 + shadow only", "Level 2 by this date is not achievable (blockers 4–6 are external)"],
  ["Level 2 · full three-horizon private release", "Feb–Mar 2027 at the earliest", "Original prices, filing rights, 50-case review, approved policies"],
  ["Level 3 · validated performance", "Swing at least +3 months; short-term 6–12 months; long-term multi-year", "Forward paper outcomes, reported as measured"],
  ["IPO, news, holdings, ML, intraday", "After Level 2", "Each scoped separately"],
];

export const TODAY = [
  ["Today", "Synthetic workflows only. Real reads fail closed, and the UI now explains why."],
  ["After the rehearsal and migration", "Real INFY adjusted chart, SMA/EMA/ATR/breakout/support, cited stored facts, research history"],
  ["After the pilot extension", "The same for all 12 pilot stocks, with discovery marked descriptive"],
  ["After Level 2", "Qualified shadow BUY / WATCH / AVOID / INSUFFICIENT EVIDENCE, point-in-time replay, paper outcomes"],
  ["After Level 3", "Measured evidence of whether each horizon and the AI arms add value"],
];

export const DECISIONS = [
  "Migrate the original database after the rehearsal passes",
  "Merge PR #35, then this branch, after review",
  "Accept adjusted descriptive research as the Level 1 basis",
  "Approve or decline multi-stream rule v1",
  "Confirm continued use of observations older than 30 days",
  "Choose the original-price path",
  "Send the Upstox and Infosys rights inquiries, or don't",
  "Name the 50-case reviewer",
  "Approve the policy sheet",
  "Choose local-only operation or Hetzner",
];

export const NEXT = [
  "Database recovery rehearsal on your Mac. You run the two scripts and I verify the JSON.",
  "Close PR #35. CI is green on 8611904, so it needs a review and your merge approval.",
  "Qualify the INFY streams and show them end to end in your browser, then extend to the 12-stock pilot.",
];
