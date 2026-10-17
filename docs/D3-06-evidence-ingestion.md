# D3-06 — Evidence ingestion

STK-046–051 · SD ARCH 3.0 §§6–8 · 17 October 2026

## Delivered foundation

Provider-neutral bounded adapters automatically poll source pages and commit them through D3-03 revision/checkpoint storage. The installed adapters are fictional; no real provider, scraping, credentials or paid service is activated. Annual reports, quarterly reports, announcements and company news use strict [document](contracts/evidence/document.schema.json) and [structured report](contracts/evidence/structured-report.schema.json) contracts.

Migration0007 adds immutable source blobs, document metadata, chunks, financial facts, event claims, ingestion manifests and deduplicated dispatch records. Existing research/legacy tables and historical evaluation fixtures are unchanged. Exact content hashes deduplicate source blobs while preserving each revision, URL and attribution. Case/punctuation/whitespace-normalized text/event fingerprints identify conservative near duplicates without erasing source references or treating syndication as independent confirmation.

The shipped parsers accept bounded UTF-8 plain text or the provider-neutral structured JSON report format. Plain text supports precise character-located chunks but does not pretend to extract financial tables. Structured facts retain JSON row paths and provider locators, source values/units, normalized INR/shares/ratios, reporting periods and consolidated/standalone scope. Derived net margin is explicitly labelled `earnings/revenue` with input-fact IDs; it is never presented as a reported value. Balance-sheet equality and reported margins reconcile only within matching periods/scopes. Missing values remain null with reasons; undefined ratios remain unavailable. A mapping feeds normalized annual/quarterly facts into the existing D3-05 Statement contract.

PDF, HTML, scanned/OCR and arbitrary-layout financial extraction are **not implemented**: unsupported formats are quarantined, not silently converted into complete evidence. Real provider adapters and document-format qualification remain source-activation work. No real-market acceptance is claimed.

## Permissions and point-in-time reliability

D3-02 permissions are rechecked before acquisition, storage, parsing/extraction, commit and downstream reuse. Structured financial parsing additionally requires financial-facts extraction/storage scope. Source identity resolution checks current universe rights and the pinned instrument-to-issuer mapping. Source attribution must contain the required grant attribution. Revocation during acquisition or extraction aborts the transaction and its checkpoint; cached reads also recheck current rights. Embedding/external-AI/export/paper-evaluation retrieval requires the corresponding explicit grant; this package makes no such service call.

The trusted worker supplies operation time. Retrieval separately enforces cutoff, synthetic/live/archive provenance, live fetch availability and exact revision identity. Corrections append through the existing supersession chain. As-of views select the latest eligible revision per source/document, retain missing/stale categories and flag incomplete financial coverage. Fresh document arrival is not proof of fresh financial periods; D3-05 applies its registered financial-period age rules.

Malformed data, issuer conflicts, changed content, unsupported formats and unit/period/total conflicts retain hash-only D3-03 quarantine records plus safe reason codes in ingestion manifests. Changed retry pages fail rather than overwrite a prior checkpoint. No raw rejected document is retained. Source blobs and derived records are immutable. Revocation blocks access immediately; provider-specific deletion/backup cleanup is not activated by this delivery and must be reviewed before real retention is enabled.

## Events and scheduling

A source-provided `confirmed` label is insufficient. Confirmation requires both verified issuer/instrument linkage and an explicit trusted-primary-source registration supplied by installed adapter configuration. Only the fictional source is registered in the shipped mock configuration. Secondary news remains unverified. Supported material categories are earnings, restatement, default, auditor change and regulatory action; every event statement must occur in the source text. Additional categories require deterministic rules in a later version.

Confirmed events use D3-04 nomination against a current-rights-checked complete snapshot containing that exact document revision. Eligible-universe and adverse-admission-pause rules remain intact. Dispatch deduplicates normalized issuer/event claims, while preserving source-level claims. No old recommendation, fill or ledger row is rewritten.

The D3-04 handler processes one bounded page per job. Continuation jobs, content and completion commit atomically, use the same source watermark and survive restarts. Every new polling occurrence starts a new source scan so a completed earlier scan cannot stop future ingestion. Existing leases, transient retries and rights-blocked states apply. Quarantined batches report partial, not successful empty research.

## Run the automatic fictional workflow

After migration0007 on an authorized local test database, provide DATABASE_URL through the existing configuration and run:

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python -m worker.main \
  --schedule-config docs/contracts/scheduling/synthetic-schedule.json \
  --synthetic-schedule --synthetic-evidence
```

`--once` runs one bounded tick. No upload is involved: installed mock universe, filing and news adapters supply their pages automatically. The schedule/data are explicitly date-bounded fictional fixtures and mock grants expire on1 January2027. The legacy worker and D3-04 synthetic mode remain unchanged unless the new flag is supplied. The earlier restricted-runtime database-grant blocker remains: this delivery does not change roles or activate a private deployment.

## Validation and next dependencies

Deterministic and PostgreSQL tests cover extraction/locators, normalization, annual/quarterly scopes, missing/zero data, margins/totals, publication cutoffs, revisions, stale/missing coverage, duplicates, primary-source trust, permission denial/revocation, unsupported formats, quarantine, retries, page continuation, transaction rollback and scheduler reassessment. Migration upgrade/repeat/downgrade/re-upgrade/failure rollback passes. Final counts are recorded on the [board](SIMPLE-BOARD.md).

D3-07 may consume the rights-gated evidence/fact interfaces for RAG. No retrieval model, embedding call, LLM, AI agent, broker transaction, purchase or deployment is implemented here. Owner review/merge is required before the next package.
