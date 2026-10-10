# PostgreSQL migrations

STK-013 uses Alembic and PostgreSQL 16. Install `backend/requirements.txt` with `--require-hashes`, set DATABASE_URL privately, then run from the repository root:

```sh
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
```

Apply migrations explicitly before later database-backed application releases. The current API/worker continue to use synthetic in-memory data. No migration runs automatically on startup. Upgrade is transactional and serialized with a PostgreSQL advisory lock. A repeated upgrade is a no-op. Published migration files must not be edited after release; add a revision instead.

`downgrade base` removes all research tables and their data. Use only on a disposable database or after an explicit restore/rollback plan with a backup. It leaves unrelated schemas/tables intact. CI tests upgrade, repeated upgrade, downgrade, re-upgrade and rollback after an intentionally failing migration on a dedicated `stk013_test` database.

## Storage boundaries

- `instruments` has stable IDs; `instrument_symbols` stores dated source mappings. Real rows need an ISIN, synthetic rows may omit it. Symbol overlap/provider mapping validation belongs to the instrument adapter.
- `candles` preserves provider revisions, raw/adjusted basis, interval, event times and availability/fetch times. Indexes support instrument/time/cutoff queries; uniqueness rejects duplicate versions and checks enforce valid OHLC/volume.
- `documents` stores provenance, revision, rights reference and optional permitted storage/hash references. No document content is fetched. `facts` links an extracted JSON value and its unit/period/availability to a document. Full extraction and cross-record cutoff validation belongs to adapters.
- `runs` stores modes, cutoffs and version/manifest references. It is not a scheduler implementation.
- `decisions` stores indexed identity/action/timing fields alongside the full recommendation JSON. Identity projections must agree, holding exits require a holding of the same instrument, and revisions link within the same instrument. Full JSON validation, append-only enforcement, revision-cycle protection and version resolution remain STK-015; this schema alone does not enforce the whole recommendation contract. Existing validators remain the fixture authority.
- `forecast_outcomes` and `trade_outcomes` hold separate JSON records and link corrections within a recommendation. No replay or evaluation calculation is implemented.
- `accounts` contains opaque internal references only. `capital_buckets` separates unallocated, active trading and long-term capital. `holdings` stores dated snapshots, unavailable/reserved quantities and nullable cost basis; missing basis is never zero.
- `contribution_ledger` stores pending/posted/failed external flows and transfers. Only posted entries enter balances. Deposits add, withdrawals subtract; a transfer stores both source and destination buckets in one row and contributes zero to total external flows. No skipped-month entry is created. Zero deposits are allowed. A reversal repeats the original event fields and negates their signed effect; reversal matching and uniqueness are checked. Replacement events are separate records. Calculate net flows including reversals, never sum gross deposit amounts as returns. No balance, sizing or loss-reset logic is implemented.

Money is NUMERIC(24,8), shares are nonnegative BIGINT and event instants are TIMESTAMPTZ. Display timezone remains Asia/Kolkata. JSON preserves decimal strings from contracts. SQL precision limits and non-finite checks are explicit. Historical fetching/generation may occur later than the information cutoff. No credentials or licensed market data are seeded.
