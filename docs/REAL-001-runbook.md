# REAL-001 local adapter runbook

Status: **PARTIAL; limited research-only local beta READY**. Publication, prospective pilot and unattended operation remain unactivated. [Phase 9 executed checklist](REAL-001-phase9.md). Read the [acceptance record](REAL-001-acceptance.md)
and [provider matrix](REAL-001-provider-matrix.md) before interpreting results.
This uses the existing app, worker, PostgreSQL and native Ollama; no extra frontend.

## Local model verification

Connect the existing model drive and start native Ollama. `scripts/verify_real_ollama.py`
uses only installed `qwen2.5-coder:7b` and `nomic-embed-text:latest`. It never pulls
models. From the repository, using the project's locked Python environment:

```sh
PYTHONPATH=shared:worker python scripts/verify_real_ollama.py --output /tmp/ollama-smoke.json
```

This copies one source excerpt and citation and verifies abstention. It is **not**
a financial calibration set or complete hybrid-RAG test. Caller-owned D3-07/08
budgets, permission checks, deterministic citation checks and semantic qualification
must remain in place. For a separate judge, select a separately qualified installed
model; reusing the research model is not an independent judgment.

## Read-only provider diagnostic

Store a token in a private owner-only file outside Git. Do not use `.env.example`.
The explicit diagnostic retains URLs, statuses, instrument identifiers and counts;
it does not persist source prices, financial values or news text and does not
register an active source grant:

```sh
python scripts/verify_upstox_access.py --token-file /absolute/private/upstox.token --financial-news --output /tmp/upstox-access.json
```

The diagnostic pins the October 2026 acceptance window. It is not an ongoing daily
job and does not claim that the current session is complete. No portfolio/account
holdings or order endpoint is used.

## Conditional D3-03 price ingestion

Requires a verified D3-02 grant and an approved observed calendar already stored
in D3-03. Unknown rights fail before acquisition. Read-only diagnostic success is
not permission to create a grant. Use an owner-local configuration file:

```json
{
  "account_ref": "owner-local-account-reference",
  "grant_file": "/absolute/private/approved-source-grants.json",
  "token_file": "/absolute/private/upstox.token",
  "symbols": ["INFY"],
  "lookback_days": 365,
  "retention_days": 30,
  "region": "IN"
}
```

The retention number is an **example request**, not a permitted term. Set it within
the documented grant. The grants file is a JSON array of existing `Grant` records;
none ships activated. D3-02 rejects absent, expired, revoked, wrong-scope or wrong-use
grants. Calendar rights are checked independently. Keep credentials and grants out
of tracked configuration and output.

```sh
PYTHONPATH=shared:worker python scripts/ingest_real_prices.py --config /absolute/private/real-market.json
```

`DATABASE_URL` / `DATABASE_URL_FILE` use the existing runtime setting mechanism.
The command records permitted revisions in the existing tables. It preserves first
observation time on unchanged records and appends corrections. Adjusted prices are
re-observed across the full configured window; do not splice adjustment anchors. No historical archival availability is inferred. Symbol lists
are bounded at 100; no automatic liquid-universe selection is claimed. Quota caps
are conservative per adapter process; multiple clients sharing the account need a
shared owner quota allocation. A retry follows normal scheduler controls; the
adapter itself never blindly retries authenticated failures.

For D3-04, supply `--real-market-config` alongside the existing `--schedule-config`.
The schedule must be `live_paper` and its input hash must equal the canonical hash
of the market configuration. Real and synthetic adapter flags are mutually exclusive.
Only price ingestion is installed; downstream stages explicitly block. The scheduler
is not considered activated until an actual eligible occurrence finishes and its
stored result is checked. No synthetic occurrence may be relabelled forward.

## Evidence and dashboard limits

The HTML extractor accepts one unambiguous source-specific table mapping into
D3-06 `StructuredReport`. It retains original units/locators and rejects merged
cells, mixed scopes, malformed numbers, wrong unit markers and duplicate rows.
The separate existing PDF path is conditional on source rights; this HTML path does
not discover issuer filings or qualify publication timestamps. Genuine acceptance
uses permitted secondary numerical observations, not an issuer PDF corpus.
Do not pass an unqualified provider snapshot off as an original company filing.

Sign into the existing frontend and choose **Real research**. The API
`GET /v1/real-research/status` is authenticated. It reports implementation gates,
not token existence as operational readiness. The view contains no synthetic
fallback, invented values or implied approved paper admission. Open `/#real-research` directly for the real workspace. The unqualified real research
view is distinct from the default synthetic workspace.

No real publication or outcome is produced by these ingestion commands. Existing
conditional D3-09/D3-10 integration remains gated; actual publication/reference
acceptance has not passed and forward-paper admission stays blocked.

## Phase 5: numerical financial observations (private local use)

Continue the existing REAL-001 branch. The narrow numerical-data permission
finding and exclusions are in [Phase 5](REAL-001-phase5.md). Do not copy an
example grant into active configuration or infer issuer-PDF rights from it.
Keep source configuration, credentials, provider values and model output outside
this public repository. Existing `SourceConfig` points to the private grant file.

Use the existing local PostgreSQL installation with a separate real-research
database. Never point migration lifecycle tests at that database. Set
`PYTHONPATH=backend:shared:worker` and supply the existing `DATABASE_URL` securely.

- `scripts/ingest_real_prices.py --config /private/path/market.json --refresh-calendar`
  acquires dated sessions before the configured bounded price window. The calendar
  refresh currently supports `lookback_days` from 40 to 44, with a closure buffer.
  Full adjusted windows are re-observed; old stored revisions remain immutable.
- `scripts/ingest_real_financials.py --sources /private/path/sources.json --token-file /private/path/token --listing NSE:INE009A01021 --account-ref OWNER_REFERENCE`
  reads the already observed identity and routes the three numerical statements
  into D3-06. It checks both financial-fact and evidence-container permissions.
- For existing D3-04 configuration, the optional market settings
  `refresh_calendar: true` and `financial_statements: true` enable these operations
  in its ingestion stage. Recompute its configuration hash explicitly. This does
  not activate unqualified downstream research/publication stages.
- `scripts/run_real_evidence.py --config /private/path/research.json` may use
  `filings: []` to research already stored numerical evidence. Queries must be
  `live_paper`; configure permitted annual periods/metrics, installed local models,
  bounded retrieval and the existing durable budget. Empty or insufficient evidence
  still abstains. Failed runs are not silently retried or overwritten.
- Set `REAL_RESEARCH_VIEW_CONFIG` to the private existing `ViewConfig` to see
  currently permitted observations and immutable analysis history. A readable
  configuration or successful generation is not publication/financial qualification.
- Existing `scripts/real_research_publication.py` still requires actual real
  policy/horizon configuration. Do not manufacture approval references to make an
  insufficient-evidence publication appear successful. Its `observe` action has
  nothing to evaluate until an actual publication/reference exists.

The actual Phase 5 data was stored in `stk_real001_private` in the pre-existing
local PostgreSQL container. Local grant review/retention is 30 days; it is an
operational limit, not a provider-imposed term. No unattended scheduler or automatic
retention-cleanup success is claimed. Recheck rights before further use and honor
expiry/revocation with the existing retention/deletion controls.


## Phase 9: verified local beta start and stop

Use the existing checkout, locked Python environment, PostgreSQL container and native
Ollama. Connect the configured model drive before starting Ollama; do not download
models. The executed owner-local setup uses the existing `stk_real001_private`
database. Never run destructive migration tests or fictional workers against it.

Keep an owner-only private directory outside Git containing the existing source/view
configuration, token, a strong random owner key (at least 32 characters), and database
URL. Files must be mode 600 and the directory 700. Do not put secrets in shell command
arguments, screenshots, tracked examples or the PR. The actual paths are recorded
in the private owner report; the placeholders below must point to those existing files.

From the feature checkout, start the API in one terminal:

```sh
export PYTHONPATH=backend:shared:worker
export AUTH_TOKEN_FILE='/absolute/private/local-owner.key'
export DATABASE_URL_FILE='/absolute/private/local-database.url'
export REAL_RESEARCH_VIEW_CONFIG='/absolute/private/phase9-view.json'
export COOKIE_SECURE=false
export APP_ORIGIN=http://127.0.0.1:5173
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use the project's installed Python environment for `python`. In another terminal,
from `frontend`, run the installed Vite entry point:

```sh
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/#real-research** and enter the key from the private
owner-key file locally. These cookie/origin settings are for loopback only; this
is not a public deployment recipe. No worker or unattended scheduler is needed to
read saved genuine research. The provider and database credentials never go to the browser.

Check the INFY chart, financial facts, three historical research tabs, citations,
cutoff, session freshness and exact publication blockers. “Refresh real evidence”
reads the latest stored observations; it does not fetch the provider or run a model.
For a manual acquisition, use the existing ingestion commands above with current
permitted scopes. Refresh the dated calendar first (bounded 40–44-day setting),
then a covered price window. The Phase 9 check used 50 days of prices within the
observed calendar. Current source access is rechecked; do not broaden grants to
make a command pass. A stopped fetch can be retried through the normal adapter;
retain prior revisions and inspect the resulting report for gaps/quarantines.

Session freshness compares the latest verified closed session to the last observed
bar. Elapsed hours are context, not a newly approved weekend/holiday strategy rule.
The source calendar itself is not a completeness attestation. Current provider lag,
unknown action/volume basis and unapproved policy remain visible. The current
financial report is historical factual research, not an investment recommendation.

Sign out when finished. Stop each task-owned frontend/API terminal with Ctrl+C.
Keep PostgreSQL volumes and private files; never use `down --volumes` for the real
research database. Restart with the same configuration. Phase 9 verified that this
stop/start preserves research, financial facts and revisions, and separately verified
safe recovery from a process interruption after genuine fetch and before commit.
No unattended catch-up, resource scheduling, backup/restore or external deployment
qualification is implied. The proposal still has no owner approval; neither source
access nor a successful model response authorizes publication or paper admission.
