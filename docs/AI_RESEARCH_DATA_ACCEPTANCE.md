# M1 — Research data acceptance checkpoint

31 October 2026. Existing STK-004–007, STK-014/046/048/052/059/060 infrastructure is reused. This document is not an acquisition grant or an operational acceptance record.

## Verified implementation and prior evidence

| Input | Existing implementation | Qualification limit / exact next evidence |
|---|---|---|
| NSE OHLCV / identity | `worker/worker/providers/upstox.py`, revision storage, instrument master and original grant linkage | Adapter labels historical bars split/bonus adjusted. STK-014/STK-079 accept raw windows only. Need permitted original raw prices or an independently validated point-in-time adjustment path; relabelling is forbidden. |
| Session calendar | Existing authenticated timings/calendar acquisition, immutable corrections and scheduler coverage | Need observed closed sessions covering all required bars, current future coverage and actual acceptance; weekdays cannot stand in for exchange evidence. |
| Corporate actions / volume | Typed action revisions and fail-closed coverage attestation | Need complete permitted action coverage and verified volume semantics; API availability is insufficient. |
| Filings | `worker/providers/documents.py`, HTML/PDF extraction, evidence blobs/facts/chunks | Exact source permission, full original document and authoritative availability timestamp, instrument identity, parser profile and unit/period validation. |
| Numerical financial history | `upstox_financials.py` and `factual_research.py` | Phase 7 records 24 actual retained facts, model-selected claims and narrow verified relations. These observed secondary facts do not prove original historical filing availability or complete filing coverage. |
| News/events | Existing news/document/event contracts and adverse-claim handling | Historical archives, coverage and permitted article processing unavailable; missing news cannot mean no adverse news. |
| Research / AI | Existing fixed RAG, bounded agent, Ollama interface, citation and arithmetic validators | Reuse these engines. Human-labelled quality benchmark and calibrated semantic acceptance remain absent. |
| Historical replay | Revision availability modes, frozen experiments and freeze/reveal infrastructure | Observed-now financial facts and current adjusted prices cannot become verified-archive evidence through a backdated cutoff. |

## Public policy verification performed this session

- [SEC webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) permits reuse of public EDGAR filing content. The existing report records a runtime 403. No filing/API retry or access workaround was performed in this session. Lawfully acquired original EDGAR material plus accession/publication/availability provenance remains a viable candidate for review.
- [Infosys terms](https://www.infosys.com/terms-of-use.html) restrict copying/derivative uses under the general limited licence; specific-area licences take precedence. No applicable report-specific exception was established. Keep automated IR corpus activation blocked pending verification.
- [Upstox historical V3 documentation](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) documents daily history from 2000 and a decade per request. This page does not itself establish raw/adjusted semantics, retention/deletion, original disclosure timestamps or AI processing rights. Existing Phase 4/5 permission evidence is narrow and must not be expanded to an issuer/news corpus.

Only public documentation was read. No authenticated market-data request, financial dataset mutation, private evidence inspection, model inference or purchase occurred.

## One-instrument acceptance procedure

1. Select INFY only after exact provider/account/grant/version rights are established for every contributing use and retention/deletion obligation. Keep unresolved operations denied.
2. Use existing adapters and disposable synthetic tests to verify configuration before authorized actual acquisition. Preserve source bytes/hash, original publication/availability and actual retrieval clocks. Never backfill unknown timestamps.
3. Establish >=30 complete closed raw sessions, action/volume coverage, effective instrument tick/lot and eligibility, complete filing/material-event coverage.
4. Ingest through existing transaction-fenced revision/evidence paths. Independently review and pin the typed coverage review and original grant hashes.
5. Exercise authenticated company and swing reads, repeat after a restriction in synthetic acceptance, and separately record actual provider execution and data coverage.
6. Advance real-data acceptance only when those records exist. Expand the watchlist afterward; do not fabricate empty negative evidence to clear a gate.

## Current result

M1 real-data acceptance: BLOCKED by the specific missing inputs above. Software integration already exists for prices, filings, numerical facts and local factual research; rebuilding it would not resolve these external requirements. No new active grant or qualified real instrument was created.

Independent work can continue on M2 verified-claim coverage, M4 deterministic synthesis, M5 replay integration and M6 UI using clearly labelled synthetic fixtures. Human reference labels and thresholds must be fixed before held-out research-quality evaluation. No synthetic score establishes predictive accuracy or AI superiority.

## Explicit one-instrument release checklist — 1 November 2026

Target: **INFY / NSE equity only**. No new provider request, private evidence review,
grant activation or legal verification was performed for this checklist. Statuses
describe missing **accepted repository evidence**, not a claim that the owner has
no private documents. Contractual requirements and possible provider permissions
remain **UNVERIFIED** until an applicable provider decision is recorded.

| Requirement / existing ticket | Exact evidence needed before genuine qualification | Current acceptance and consequence |
|---|---|---|
| Source identity and account — STK-004/014 | Provider/source ID, private account reference, immutable grant ID/version, approval-evidence reference, region/processor, valid-from/expiry/revocation clocks for each input; instrument/listing/issuer mapping | UNVERIFIED for a complete INFY input set. An API token proves neither rights nor account/grant provenance. Missing/unknown identities deny use. |
| Uses — STK-004/014/052 | Explicit permissions per **data scope** for acquisition, storage, extraction and derivation; embedding/local or external AI processing only when used; historical replay, evaluation, export and backup only when used | Complete applicable use matrix not accepted. Q-only need not require unused AI permissions, but may not consume copied restricted AI results. Original acquisition and current-use rights checked separately. |
| Retention/deletion — STK-074 | Applicable licence/version and provider-approved interpretation: retention days, trigger and deadline on expiry/revocation, treatment of derived text/facts/vectors/shared content, permitted minimal audit, filesystem/backups/restore, processor copies | UNVERIFIED. Manifest and durable write/read fences are implemented; neither executes deletion nor proves contractual compliance. `retention_compliant` and `deletion_obligations_supported` cannot be set from tests or token access. |
| Immutable acquisition — STK-005/007/014 | Stored `revision_id`, separate upstream `source_revision`, original grant/version and actual fetched/acquired timestamp; original bytes/canonical content hash; provider/account/stream linkage | Infrastructure exists, complete accepted input packet missing. A renewed grant cannot authorize restricted old-version acquisitions. Missing or conflicting ownership fails closed. |
| Raw prices — STK-006/014 | At least 30 distinct complete closed exchange sessions, original raw OHLC, declared currency/interval/timezone, actual publication/availability/fetch clocks, corrections and fresh latest closed bar | Existing adapter records adjusted historical prices. No accepted raw source/verified adjustment path. Never reinterpret split/bonus-adjusted bars as raw or use synthetic defaults. |
| Volume and adjustments — STK-006/014 | Provider-specific volume basis, adjustment factors/action effects and effective/as-of knowledge; validated price/volume compatibility | UNVERIFIED complete semantics. Current qualification supports raw price/raw volume and an evidenced action-free window; an adjustment engine would require separate validation, not a flag change. |
| Closed sessions/freshness — STK-005/006/014 | Authoritative observed NSE calendar revisions for every required bar, session open/close, observation/effective revision clocks, coverage/fresh-until and future endpoint coverage | Calendar ingestion/correction checks exist. Complete current accepted INFY coverage missing; no inferred weekdays, unclosed bars or unknown holidays. |
| Corporate actions — STK-007/014 | Permitted complete split/bonus/dividend/other material-action coverage for the price window, event/effective/publication/availability clocks; explicit verified no-action attestation where applicable | No accepted complete action-free/raw window. Missing events cannot mean no actions. Historical fills remain unsupported for action windows unless the existing evaluator supports and verifies that action. |
| Tick, lot, eligibility and risk — STK-014/028/058 | Latest eligible effective instrument revision at cutoff; tick/lot, exchange/series/ISIN/currency, eligible status and explicit risk prohibition decision, all with original provenance | Trusted loader exists; current accepted settings/eligibility packet missing. No guessed one-paise tick, lot=1 or eligibility. Historical identity parents remain authorized dependencies. |
| Substantive filings — STK-046/048 | Permitted original issuer/exchange/regulator filing; entity and consolidated/standalone scope, reporting period, currency/units, exact source locators, source publication and first-availability timestamps, fetched time/hash, revision/restatement lineage | Narrow retained numerical facts/development excerpts are not a complete filing packet. Coverage reviews never substitute for substantive filings. Missing source clocks cannot be backdated. |
| Material events — STK-049–051/014 | Permitted announcement/news source, issuer association, event/publication/first-available/fetch clocks, complete interval and fresh coverage attestation; conflicting/adverse events retained | Complete permitted interval not accepted. An empty response or missing feed does not establish absence of adverse news. |
| Coverage decision — STK-014/079 | Typed stored review pinned by hash and exact dependency IDs; every scope's covered-from/through, observation and fresh-until clocks; policy evidence and current original-grant fences; no extra/unpinned records | Implemented loader and synthetic tests exist; independently reviewed genuine packet missing. Stale or superseded reviews cannot authorize newly changed dependencies. |
| Historical use — STK-037–044 | Eligible archival availability **at/before historical cutoff**, revision known then, complete raw future observation series revealed only after freezing; original contemporary AI completion/model/prompt/verifier versions when claiming AI input | No qualified archived paired dataset. Today's financial reports, revised prices or current AI output cannot reconstruct what was known then. Missing financial/AI input → no eligible pair, AI metrics unavailable. |
| Actual supervised acceptance — STK-060/075 | Approved local configuration, authenticated read-only API/UI trace, true run/publication/cutoff clocks, no credential leakage, recovery/freshness/resource evidence and explicit retained limitations | Software/mock evidence exists; REAL-001 operational acceptance remains PARTIAL. Overnight, sleep/wake and restoration require actual separately authorized observations. No live probes initiated. |

The minimum owner/provider handoff is a **reference** to verified permission and
retention terms plus the scoped immutable coverage packet, not credentials in chat.
The trusted `swing_research.py` loader must resolve it through current fences and
original grants into `swing_qualification.py`; caller assertions cannot qualify it.

Independent M2 development review and the unseen 50-case evaluation remain
BLOCKED. The protocol is proposed, labels/reviewer/approval absent; no new labels
or accuracy metrics are created by this checklist. Publication, paper admission,
actionable real BUY promotion and trading remain separately blocked.
