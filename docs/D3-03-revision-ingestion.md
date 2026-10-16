# D3-03 — Revision storage and ingestion

STK-014 / STK-015 / STK-019–024 · SD ARCH 3.0 §6–7 · 15 October 2026

## Delivered scope

An additive `0005` migration creates the `discovery` namespace beside the unchanged `research` tables. It stores immutable source-grant versions, typed source revisions, batch membership, page receipts, quarantine hashes and snapshot manifests/items. Streams carry the only mutable ingestion checkpoint. Existing recommendation/evaluation fixtures and synthetic runtime paths are unchanged.

Typed inputs cover dated instrument identity/status, universe membership and selection-input hashes, daily raw OHLCV, split/bonus/dividend/unsupported actions, filing/news metadata and exchange sessions. Each input records source revision, sequence, publication/availability/fetch clocks, exact archive proof where relevant, original instrument revision and supersession links. Prices remain decimal strings. Records reject malformed values, unknown fields, unclosed bars, conflicting source revisions and unresolved instrument references.

`PageAdapter.fetch(cursor, limit)` is the bounded acquisition interface. `ingest_next` checks current acquisition rights before calling it, uses an injected trusted clock and reloads rights at the actual storage time, then commits the validated records, quarantined record hashes, page receipt and cursor together. This package ships a deterministic synthetic adapter only. Real adapters remain disabled pending D3-02 grants and provider selection; no OpenAI client or key is used.

The ingestion transaction serializes a stream. Duplicate pages are idempotent; a retry with changed content fails. Old/out-of-order cursors and cursor cycles fail. Each batch has a distinct stream ID, with fixed source/account/scope. Overlapping batches can reference an identical immutable revision without copying or modifying it. A changed payload or reused provider revision is quarantined. Invalid records retain only content hashes and stable error codes, not raw payloads or validation exceptions. Grant/version identity conflicts fail the page rather than silently replacing permission evidence.

## Point-in-time snapshots

`freeze_snapshot` accepts explicit stream IDs, mode, cutoff, creation time, universe version and calendar version. It checks current rights, locks included streams in stable order, selects the latest eligible source revision for each logical observation, and persists a content-addressed manifest with foreign-key links. It retains original instrument dependencies when a symbol changes and pins original/current grant references by hash. Multiple sources for the same logical observation are rejected; provider data is never silently spliced.

Live inputs must be observed and fetched by cutoff. Historical reconstruction requires exact-revision archive evidence; fictional inputs remain synthetic. Future filings/restatements cannot enter a past snapshot. The persisted snapshot never changes when subsequent corrections arrive. Reads recheck current source/account/scope rights before retrieving the stored content, so a frozen snapshot does not bypass revocation.

Snapshots reconcile universe total, eligible and ineligible membership counts. Delisted/suspended/ineligible listings remain visible in the denominator. Missing mandatory scope, universe/calendar, required sessions, positive-volume candles, incomplete pages or quarantined records prevent a complete snapshot claim. Effective unsupported actions exclude affected members and flag the snapshot. These counts describe input coverage, not D3-04 discovery-stage candidate/research counts or production full-market coverage.

`adjusted_close` provides a separate split/bonus-adjusted research feature using only cutoff-known, effective actions. It never mutates raw executable prices. Dividends are retained as explicit cash events, not silently treated as split adjustments; unsupported actions refuse adjustment. Portfolio cash/receivable processing and execution simulation remain D3-10.

## Files and use

- `shared/stock_discovery_analysis/revisions.py`: strict inputs, as-of selection, snapshot assembly and adjustment.
- `shared/stock_discovery_analysis/revision_storage.py`: adapter protocol, rights checks, atomic ingestion, quarantine and snapshot persistence/reads.
- `shared/stock_discovery_analysis/revision_fixtures.py`: fictional paged provider, grants and records for deterministic acceptance.
- `backend/migrations/versions/0005_revision_ingestion.py`: additive tables, indexes, uniqueness/foreign-key checks and mutation guards.
- `backend/tests/test_revisions.py` and `backend/tests/integration/test_revision_ingestion.py`: T02/T04/T05/T11 input-boundary checks and failure injection.

A completed batch is immutable; start a new stream ID for a new scheduled occurrence. There is no scheduler or API endpoint in this package; D3-04 connects occurrence scheduling, retries and operational coverage. Source-specific networking/rate-limit backoff, document text extraction, embeddings and agents remain later work. Grant revocation and aggregate quota reservations still require transactional coordination in production adapters; the synchronous checks here do not claim to solve in-flight revocation. Retention/deletion enforcement against actual provider content is still an activation requirement; the D3-02 cleanup plan is not executed by this migration.

## Validation and release boundary

Test against a disposable database named `stk013_test` using `scripts/validate_migrations.py`. The lifecycle check exercises upgrade, repeat upgrade, all integration tests, downgrade without touching unrelated public objects, re-upgrade and rollback after an intentionally failing migration. The failure fixture now follows revision `0005`. No migration was applied to the running application database; local validation used a separate disposable PostgreSQL container.

Contract tests cover future revisions and late fetches, archive identity, symbol dependencies, missing sessions, delisted membership, raw/adjusted separation and unsupported actions. Database tests cover automatic paged resume, duplicate/revised records, immutable snapshot round trips, quarantine, page/checkpoint rollback, grant revocation before fetch/storage/read, FK boundaries and overlapping-batch deduplication. Existing historical fixture hashes remain part of the regression suite.

This is software acceptance with fictional inputs. It does not establish real-source rights, correct vendor coverage, completed storage-retention operations, full NSE capacity, investment performance or deployment readiness. All these limits remain visible in the architecture board. D3-04 is not started by this delivery.

Final verification — 16 October 2026: isolated staged snapshot passed 243 application/worker/database tests (32 database cases, 39 new D3-03 cases) and 7 script tests. Full migration lifecycle passed. The final disposable validation container was stopped and removed.
