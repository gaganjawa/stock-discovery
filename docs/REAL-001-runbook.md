# REAL-001 local adapter runbook

Status: **PARTIAL / unactivated**. Read the [acceptance record](REAL-001-acceptance.md)
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
observation time on unchanged records and appends corrections; incremental requests
overlap seven days. No historical archival availability is inferred. Symbol lists
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
It does not discover issuer filings, qualify publication timestamps or parse PDFs.
Do not pass an unqualified provider snapshot off as an original company filing.

Sign into the existing frontend and choose **Real research**. The API
`GET /v1/real-research/status` is authenticated. It reports implementation gates,
not token existence as operational readiness. The view contains no synthetic
fallback, invented values or implied approved paper admission. The default remains
the synthetic workspace because no real research pipeline is qualified yet.

No real publication or outcome is produced by these commands. D3-10 forward-paper
admission stays blocked, and actual research-only tracking is still to be integrated.
