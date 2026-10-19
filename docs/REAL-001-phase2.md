# REAL-001 Phase 2 — integration progress (PARTIAL)

19 October 2026 · continues draft PR #12 · STK-014/046/048/052/053/059/060.
This is **not** an accepted end-to-end INFY research workflow.

## Source investigation and genuine execution

SEC's [webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
explicitly permits access and reuse of EDGAR public filing content. This is stronger
permission evidence for that content than the Infosys website's limited display
licence. It is not a market-price licence.

The genuine INFY [2026 Form 20-F](https://www.sec.gov/Archives/edgar/data/1067491/000119312526270520/infy-20260331.htm)
was located through the official [filing index](https://www.sec.gov/Archives/edgar/data/1067491/000119312526270520/0001193125-26-270520-index.htm).
The filing is dated 15 June 2026, reporting period 31 March 2026. A direct identified
GET from the task runtime returned **403**, 4,819 response bytes. The denial body
was not retained. No proxies, alternative identities or controls bypass were used.
The initial execution approval timed out; one permitted retry performed this GET.

The owner has no additional Upstox permission evidence. Phase 1's successful
read-only price/fundamentals/news probes remain the actual access evidence; they
are not storage/AI approvals. No active source grant was manufactured in Phase 2.
No genuine financial filing or facts were newly ingested; no new genuine INFY
recommendation, publication or prospective outcome was produced. No additional
Ollama inference was executed in Phase 2; the successful Phase 1 native model
smoke is retained separately and is not claimed as financial RAG acceptance.

## Implemented and connected

- `OfficialDocument` retrieves configured official HTTPS documents, rejects
  redirects/unapproved hosts, bounds content size, and checks rights before
  network and extraction. HTTP denials do not trigger evasive retries. Profiles
  pin source identity, publication date, extraction rules and optional raw hash.
- Exact HTML tables, visible HTML announcement text, and page-bounded PDF table
  text map to existing `StructuredReport`, `FinancialRow` and `EventRow` contracts.
  Numeric parsing is deterministic. D3-06 owns normalization, reconciliation,
  source locators, chunks, event confirmation and atomic storage.
- PDF extraction uses an installed Poppler `pdftotext` executable with a per-page
  deadline and at most ten specified pages. It is **not bundled/installed here**.
  Missing executable, image-only pages, ambiguous rows and missing markers fail
  explicitly. No OCR or real-document parser qualification is claimed.
- Source hashes and parser/profile versions identify revisions. Unchanged
  documents preserve their original observation; changed content appends a linked
  revision. Structured source text and facts persist through D3-06; original PDF
  binary retention is not implemented.
- `run_real_evidence.py` orchestrates real-mode ingestion into existing D3-06,
  then D3-07 retrieval/embeddings/citation validation using native Ollama. Optional
  D3-08 investigation requires a distinct configured judge model; no mock provider
  or paid/cloud fallback exists in the runtime path. Cutoff is frozen after actual
  ingestion, not taken from a backdated configuration value.
- Shared source configuration reloads grants on every use. Authenticated company
  readers expose only configured, observed records, recheck source rights,
  preserve missing facts and read immutable D3-07 research history. Revocation
  hides stored source content and results.
- Actual stored candles and normalized statements feed existing D3-05 engines.
  Missing real policies/calendar/coverage produce insufficient assessments. A
  missing calendar now abstains rather than raising an attribute error. No
  fabricated sessions, assumed source completeness or synthetic strategy policy.
- Existing Real Research UI can display configured stored candles using the
  existing chart, facts, source documents, events, all three quantitative views,
  citations and research history. API errors clear visible data. No source
  configuration means the existing blocked view; no synthetic fallback.

## What remains incomplete

The automatic source-specific INFY extraction profile is **not qualified or
shipped**: an inaccessible filing cannot establish its actual table layout. EPS
and EBITDA remain outside the current D3-06 metric contract. The name field is not
persisted in the existing instrument contract; the view explicitly reports it
unavailable rather than inferring it. There is no independent financial-news
adapter, full event classification/materiality policy, or complete action/calendar
coverage. Configured lists support up to 100 companies but are not discovery or
liquidity screening acceptance.

D3-09 publication is not yet generalized from its synthetic-only database/strict
v2 assembly. D3-07 research results are immutable **analysis history**, not published
v2 recommendations or prospective predictions. Real strategy policies, complete
calendar horizons, evidence coverage and model qualification also remain absent.
D3-10 real shadow forecast registration and observation/outcome jobs are not
connected. No later outcome can legitimately be claimed. Paper admission gates
are unchanged. The new evidence command is opt-in; no real recurring job was
activated or claimed to have run.

## Validation

- **601 backend/worker tests passed** with PostgreSQL enabled.
- **163 database integration tests passed**, zero skips; migration upgrade,
  repeat upgrade, downgrade, re-upgrade and atomic failure rollback passed.
- **10 script tests**, three historical contract validators and frontend build passed.
- **Five browser workflows passed** (34.2 seconds). The configured company-data
  case uses explicitly fabricated HTTP responses to test rendering and revocation;
  it is not evidence of a real INFY dashboard. Existing discovery, paper and replay
  workflows also passed.
- New fabricated tests cover HTML normalization, raw hash/revision reuse and
  correction, pre-network denial, mid-fetch revocation, official-host enforcement,
  403/429/redirect handling, PDF missing-parser/page-context handling, announcement
  quote parity, pipeline mode isolation, D3-06 to D3-07 persistence, current rights
  on dashboard reads, three-horizon insufficiency and immutable research results.
- These provider/model doubles are software acceptance only, **not** real financial
  data, source access, native model execution or prospective performance.

Costs: ₹0; no purchase, deployment, model download or broker order.

## Local configuration boundary

A private `EvidenceConfig` JSON file specifies `sources` (`grant_file`, region,
retention_days, primary_source_ids), `filings` (one `FilingSpec` per known official
document), `queries` (existing D3-07 query contracts), and `budget` (existing durable
account limits). It can optionally select `mode: agent` and a distinct judge.
Do not copy test grants or test extraction profiles into operational configuration.
An observed instrument identity must already exist in D3-03 and match the filing.

Run from the worktree with `PYTHONPATH=backend:shared:worker`:

```sh
python scripts/run_real_evidence.py --config /absolute/private/evidence-config.json
```

`DATABASE_URL`/`DATABASE_URL_FILE` selects the existing database. There is no token
argument for official documents. The command logs only run IDs and status.
`REAL_RESEARCH_VIEW_CONFIG` points to a private `ViewConfig` JSON file containing
`sources`, `listing_ids`, and optionally a file of approved strategy policies.
The backend reads it afresh; it does not expose the file or its path to browsers.
This configuration cannot grant provider rights or qualify a parser/model/policy.

Overall: **PARTIAL**. The remaining blockers include both source access/permissions
and unimplemented publication/prospective integration; permissions alone will not
complete REAL-001. D3-11, D3-12 and D3-13 remain unstarted.
