# REAL-001 Phase 3 — conditional publication and prospective references

**Subsequent Phase 4 finding:** [Permission review](REAL-001-phase4.md) resolves private market-data retention/replay through newly located Upstox developer replies. The historical Phase 3 blockers below describe what was known then; financial-source and actual end-to-end acceptance remain blocked.

**20 October 2026 (IST) · PARTIAL · actual INFY acceptance BLOCKED.**
Continues `feat/stk-014-046-052-060-real-001`, draft PR #12, baseline `d10ff6b`.
STK-004–007/046/048/052/059/060; existing D3-02/03/05/06/07/08/09/10.
No D3-11/12/13, purchase, deployment, broker execution or merge.

## Actual evidence, not software test results

No genuine financial document was processed in this phase. No financial figure,
financial citation, grounded Ollama result, actual-stock quantitative assessment,
INFY recommendation or INFY prospective reference was created. The earlier
Upstox access diagnostics and Ollama protocol smoke remain historical evidence;
they are **not** ingestion/RAG acceptance. No SEC endpoint was retried.

The actual Infosys annual-report candidate is
[Integrated Annual Report 2025–26](https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-26.pdf),
listed through the [official annual-report index](https://www.infosys.com/investors/reports-filings/annual-report/annual-reports.html).
Document type: PDF integrated annual report; labelled reporting year: 2025–26.
Exact publication timestamp, table scope/units, page locations and reported values
have **not** been independently verified by the ingestion pipeline. Discovery of
an indexed URL does not authorize fetching and persisting its contents.

[Infosys terms](https://www.infosys.com/terms-of-use.html) provide limited site
access/display rights and restrict reproduction and derivative use. No applicable
filing-specific permission for this automated retained corpus was established.
The official quarterly/exchange filing candidates are retained in the provider
matrix, also unactivated. NSE website restrictions and the requirement for an
applicable data agreement do not provide a free scraping fallback. BSE's official
corporate-data product does not establish a licence for this installation.
Upstox's documented Analytics Token supports read-only integrations, but the
required retention, derivation, embedding/AI and prospective-evaluation evidence
remains unresolved. No grant was manufactured and no provider message was sent.

The first Phase 3 local Ollama inventory request failed while the T9 model
folder was absent. After the owner confirmed the same path, the recheck passed:
`/Volumes/T9/ollama-models` exists and `/api/tags` returned HTTP 200 with the
previously recorded `qwen2.5-coder:7b` and `nomic-embed-text:latest` digests.
See [readiness metadata](../evidence/real-001/phase3-local-readiness.json), which
preserves both checks. Runtime availability is resolved. No model was executed
or downloaded this phase because no permitted financial corpus is available.
A quote-copying protocol smoke cannot establish financial reasoning suitability.
A distinct usable local judge and financial claim/citation evaluation remain
necessary for D3-08 acceptance; no unsupported AI conclusion is promoted.

## Implemented and verified conditionally

- The existing D3-09 `build_artifact` now accepts explicit real context and
  observed inputs. Synthetic assembly remains intact. Real publication requires
  an observed calendar and a complete non-fixture policy manifest; missing
  coverage/risk/eligibility leads to insufficient evidence. No policy approval is
  shipped. Missing justified stops cannot acquire synthetic fallback values.
- A dedicated real orchestration function loads current permitted observations
  through the existing company reader, D3-05 assessments, and stored D3-07/08
  results. It uses the existing publication runs, batches, recommendations and
  outbox. It freezes actual server publication time, cutoff, policy/model/source
  versions, citations and material events atomically. Duplicate keys return the
  original artifact; conflicting requests fail. Interrupted/failed runs require
  a new key. Source rights are checked again on publication and subsequent reads.
- A PostgreSQL migration adds immutable shadow references and observation receipts
  under D3-10's `paper` schema, separate from portfolio admission and fills. No
  portfolio, reservation, ledger, execution engine or return formula was rebuilt.
  Original conditions and clocks are immutable. A later permitted observation
  appends a receipt; corrections append a superseding revision. Future-unavailable
  observations and pre-publication sessions cannot create an outcome.
- No later observations returns `pending_future_observation` without an outcome
  row. An insufficient-evidence record has no directional prediction, so later
  receipts are `not_applicable`. Missing sessions/actions are explicit. **Mature
  directional returns remain blocked by unqualified corporate-action coverage**;
  this delivery does not claim a completed real outcome evaluator. No percentage,
  profit, simulated execution or paper position is invented.
- The real company reader exposes currently authorized frozen publications and
  their prospective histories. React shows actual publication/cutoff times,
  decisions, missing inputs, frozen citations and tracking status. Revocation
  removes cached display content. Synthetic discovery's latest-run query remains
  mode-isolated. Source inspection uses the recommendation's actual mode/rights.
- Operator entry point: `scripts/real_research_publication.py --config <private-view-config>
  publish --listing <configured-listing> --horizon swing --key <unique-key>`;
  the separate `observe` subcommand processes already-ingested eligible later
  observations. Both require the existing database configuration. Publication
  additionally requires `CODE_VERSION` and an explicit eight-kind policy file.
  No recurring schedule, source grant or real configuration was activated.

Migration 0012 permits `live_paper` publication batches. Downgrade refuses to
restore a synthetic-only constraint while real batches exist; do not delete
immutable publications to force a downgrade. Normal empty/disposable lifecycle
and transaction rollback checks pass.

## Required actual acceptance

| Check | Status and exact blocker |
|---|---|
| A1 genuine permitted INFY filing | BLOCKED: Infosys reuse/automation grant unresolved; SEC runtime previously denied access and was not retried. |
| A2 real document parsing | BLOCKED by A1; PDF helper deployment and source-specific extraction profile still need qualification. |
| A3 actual financial facts | BLOCKED by A1/A2; no actual values extracted. Operating-profit/EPS fields need explicit supported mappings before claiming coverage. |
| A4 independent figure verification | BLOCKED: no admitted document or extracted figures to compare. |
| A5 persisted permitted facts/citations | BLOCKED: no qualifying source grant/corpus. |
| A6 real local embeddings | BLOCKED by A5; local model inventory is now reachable. |
| A7 real financial retrieval | BLOCKED by A5/A6; fabricated contract tests are not acceptance. |
| A8 grounded Ollama research | BLOCKED by A7; model financial suitability unqualified. |
| A9 claims/citations validated | BLOCKED by A8; no actual result or qualified independent judge. |
| A10 actual market data reaches D3-05 | BLOCKED: Upstox retention/derivation rights, observed calendar/actions/coverage and real policy qualification. |
| A11 real INFY publication | BLOCKED: required real inputs, calendar/policies and research acceptance missing. Conditional code tested only. |
| A12 dashboard displays that record | BLOCKED by A11. UI tests use explicit fabricated HTTP responses; actual screen remains blocked. |
| A13 real prospective reference | BLOCKED by A11. No INFY reference exists. |
| A14 later observation processing | CONDITIONAL SOFTWARE IMPLEMENTED; ACTUAL ACCEPTANCE BLOCKED: permitted later observations, operational configuration and corporate-action coverage missing. No mature outcome exists. |

## Validation

- Full backend/worker suite: **606 passed**, PostgreSQL enabled, zero skips.
- Migration lifecycle: **164 PostgreSQL integration cases passed, zero skips**;
  upgrade, repeat upgrade, downgrade, re-upgrade and intentional failure rollback.
- Final publication/evidence/API targeted regression: **21 passed**.
- Script tests: **10 passed**; all three contract/example validators passed.
- Frontend production build passed; **five browser workflows passed** (33.2s).
  Real publication rendering/revocation uses explicitly fabricated responses;
  disposable observed-mode database tests use fabricated grants and records.
- No actual filing network smoke was run against restricted/previously blocked
  endpoints. The local readiness recheck passed after the drive returned; no inference acceptance is claimed. No token retry.
- CI for the delivered commit is reported on PR #12; these local results do not
  assert CI success before the new commit is tested.

Costs incurred: **₹0** in services/subscriptions/models. Existing local hardware
and disposable PostgreSQL/browser infrastructure only. Unrelated main-checkout
WIP, historical fixtures and existing D3-10 admission controls are preserved.

**REAL-001 remains PARTIAL. Stop after Phase 3.**
