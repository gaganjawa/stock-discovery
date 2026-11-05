# STK-093 — D3-09 real research workbench

Discover, filter, compare two to four configured companies, save private notes and
return to the original company research page. This reuses the existing company
and saved-scan readers. It introduces no provider/model requests, market-evidence
migration, policy, ranking formula, or actionable output.

The workbench labels saved ranks only when the original assessment is eligible.
Dates, basis, missing qualifications and unavailable companies remain visible.
The calendar's session list does not attest current-market completeness; the
summary therefore reports zero verified current-market coverage. Latest stored
session and acquisition time are separate. Prices never determine comparison order.

## Private persistence

`REAL_WATCHLIST_DIR` selects a stable private directory; the default is
`backups/private-watchlist` relative to the API working directory. Use an absolute
path for launches from different directories. Keep this directory outside Git.
The single-owner session/Bearer authorization and cookie origin checks protect
all endpoints. Notes are limited to 2,000 characters and never enter market
revisions, prompts, recommendations, or request logs.

The directory is 0700; the JSON and lock files are 0600. Writes take an exclusive
process lock, fsync a temporary file, atomically replace JSON, and fsync the
directory. Invalid/over-permissive existing stores fail closed. A filesystem
failure is an API error, not a successful save. No automatic external backup is
created. Back up this directory privately with the API stopped, preserving
permissions; restore it before restarting the API. The market database backup
alone does not contain watchlists. Simultaneous editors use last successful save.

“Mark observations reviewed” records the maximum acquisition timestamp of the
currently permitted price series. A later readable acquisition timestamp produces
“New stored price observation since review.” No previous review, denied evidence,
or no newer readable observation never implies a real-time market change. This
indicator concerns price observations, not new filings or all research revisions.

## Real local acceptance (5 November 2026)

The authenticated app read the original private stored database using the existing
read fences. A private acceptance configuration reused the original 12 pilot
listing IDs and the existing descriptive view settings. No original evidence or
source permissions changed. No services or database engines were restarted.

- INFY: 44 readable bars through 4 November 2026.
- Other 11 companies: prices/indicators withheld for `recent_sessions_not_ingested`
  and `session_coverage_unavailable`. INFY versus 20MICRONS demonstrated unequal
  availability; no second readable company was fabricated.
- Browser sign-in, symbol search, comparison, watchlist save, note save, browser
  reload, recovered note, and original 44-bar company chart passed against actual
  API responses. Acceptance note was cleared after proving persistence.
- Private artifacts: `backups/stk093-acceptance/{api-summary.json,browser.json,
  workbench.png,comparison.png,watchlist-reloaded.png}`. These are ignored local
  artifacts, never committed. Private launcher and API logs are in the same folder.
- Local UI: `http://127.0.0.1:5193/#real-research`; owner key is the existing private
  local key. Watchlist directory for this instance is
  `backups/stk093-acceptance/watchlist`.

## Boundaries

Stored instrument identities do not contain company names. Names are shown when
the permitted saved scan supplies them; otherwise “Name unavailable” is explicit.
The current private saved scan is not readable under its original lineage gates,
so names and saved research priorities are unavailable in this acceptance.
No gate was relaxed to fill these gaps. Missing financial and valuation fields
remain missing; reported facts retain reporting periods and source locators.

STK-092 CAS/calendar work remains deferred. This workbench is a descriptive
workflow, not full D3-13 release, market coverage certification or investment
readiness. No launchd activation, broker order, paid service or deployment occurs.

Validation: 1,016 backend/worker regression tests passed, followed by all four
focused watchlist tests including durable review-marker preservation and denial.
41 disposable PostgreSQL read-fence/freshness cases passed with zero skips.
The isolated production build and 21 browser regressions passed. The unrelated
untracked ImportPreview syntax error was excluded via an isolated tracked-source
copy; it was not modified. Real browser acceptance also passed against a fresh
API process reading the same private watchlist directory. Stale counts require a
readable dated price series; missing observations are counted separately.
