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
