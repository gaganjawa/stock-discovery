# STK-052 / M2 — Model-proposed financial rows and independent verification

This incremental vertical slice reuses filing ingestion, immutable facts, fixed-RAG, local model interface, budgets, result storage, company API and factual-report UI. It is not completed general financial-research acceptance.

## Execution

Opt in with `factual_report=true`, `extraction_only=true` in the existing EvidenceConfig. Fixed RAG passes retrieved source passages, entity/cutoff and reference cell locators to the model; the precomputed financial candidate values are omitted in this mode. The response can propose `extracted_claims` with entity, stored revision, evidence ID, exact quote and typed FinancialRow fields. No proposed fact is ingested as authoritative evidence.

The service independently matches the original retrieved passage and document, requires an explicit supported source row, rejects future reporting periods, normalizes through the existing unit/currency implementation, compares value/unit/period/scope/metric/source cell with exactly one reported deterministic filing fact, and rejects conflicting references. Model arithmetic and derived facts cannot be passed off as reported source facts; existing deterministic candidate calculations remain available separately. Unsupported claims are rejected individually; valid findings survive unrelated errors. Cached results preserve source reauthorization, model/prompt identity and durable reservation accounting.

The first source-row grammar is deliberately narrow:

`revenue = 100 INR_crore; 2025-04-01T00:00:00Z/2026-03-31T00:00:00Z; annual; consolidated`

It requires a whole explicit row, not numbers/date fragments borrowed from elsewhere. Ordinary PDF/HTML table layouts that do not expose that row grammar abstain; expanding support requires a verified parser/span profile, not inferred units or periods. The regression document is an invented filing whose deterministic extraction is rendered into these explicit rows. This does not qualify any real issuer filing layout.

Verified fields render through the existing accepted-claims report, with source and fact citations, raw proposed fields and reference fact ID. Parent run records preserve the exact bundle/revisions, cutoff, model and prompt hash. Version `historical-factual-1.4.0` changes cache identity; extraction-only mode has its own request identity. An existing run ID cannot silently switch modes or reset its budget.

## Validation and actual execution limits

- Full backend/worker: 729 passed.
- Focused financial/factual/filing-parser tests: 64 passed.
- Affected PostgreSQL: 64 passed, including three filing-to-company-report cases; final same-mode cache, changed-mode rejection and no-duplicate-call assertions were rerun in those three cases.
- Frontend TypeScript/production build passed. Existing UI receives the same accepted-claim envelope.
- The first parameterized integration attempt reused immutable identities across cases; it was corrected to use the existing disposable database fixture per case. No immutability enforcement was relaxed.
- All input documents and model responses in these executions were synthetic/scripted. No actual LLM analyzed a filing in this slice. The configured T9 model folder is absent and localhost Ollama metadata returned ConnectError; no download, inference or external provider request was attempted.

Full exact-commit CI/migration gates remain required before merge. Human quality metrics are UNAVAILABLE. The owner requested a review packet: `research-quality/M2-financial-review-packet.json` has ten invented development cases with null expected labels and `human_verified=false`. The protocol defines proposed thresholds/denominators before any held-out evaluation; independent human labels, approval, reference hash and a separate untouched holdout are still required. No second LLM or developer assertion substitutes for that review.

Real-data rights, full filing/event coverage and historical publication/availability evidence remain blocked under M1. All findings remain research-only; no publication, paper admission, strategy approval, broker execution or profitability claim is introduced.
