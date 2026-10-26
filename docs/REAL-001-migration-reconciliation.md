# REAL-001 / D3-11 migration reconciliation

STK-042/059/060. Reconciles REAL head `a72e487` with main `787c1d2`.
No strategy activation or research behavior changes are part of this work.

Before reconciliation, both branches named different children of `0011` as
`0012`: D3-11 experiment governance on main, and REAL shadow tables on PR #12.
REAL additionally had `0013` for maintenance audit reservations.

The combined graph is:

```text
                  0012 (D3-11, unchanged) ───────────┐
0011 ────────────┤                                  ├─ 0014 (no-op join)
                  real_0012 (REAL shadow) ── 0013 ───┘
```

Only the REAL shadow revision identifier and its child's dependency change;
their upgrade/downgrade SQL remains unchanged. Installed REAL databases retain
their `0013` marker. Main's deployed `0012` identity and governance SQL are
unchanged. The new join does not alter application tables or data.

## Verified source state and permitted upgrade paths

Read-only inspection of `stk_real001_private` found version `0013`, both shadow
tables, the maintenance constraint and nullable audit job ID, 32 maintenance
reservations, and no experiment tables. For that state, normal `upgrade head`
creates D3-11's four experiment tables and advances to `0014`; it does not rerun
REAL's shadow or maintenance migrations. No stamping or data replacement is
necessary. The actual database was not upgraded during this reconciliation.

A main database at `0012` applies `real_0012`, then `0013`, then the join.
A clean database applies both branches and reaches the single head `0014`.

**An older REAL database still stamped `0012` is ambiguous and is not covered
by this path.** Do not stamp it as main or run the combined upgrade blindly.
Inspect its schema and establish a separately verified legacy transition first.
Likewise, stop on missing expected tables/constraints or a different source head.

Use the existing private database configuration for an approved actual upgrade.
Never run `scripts/validate_migrations.py`, downgrade/base, fixture seeding or
database recreation against the actual research database. The lifecycle validator
is exclusively for a new disposable `stk013_test` database. The existing `0013`
downgrade guard still rejects rollback when maintenance reservations exist.

## Validation method

`test_migration_reconciliation.py` builds the original REAL graph (including its
old `0012` ID) in a disposable database, adds fictional publication/shadow/audit
history, upgrades twice, and compares every pre-existing application table row.
It also verifies unchanged D3-11 registry history and a clean installation.
A rejected destructive rollback must leave both version and all rows unchanged.

Separately, a schema-only dump from the actual REAL database was restored into
the new disposable service, given its verified `0013` marker and 32 synthetic
audit sentinels, then upgraded twice. No private evidence rows were copied.
The combined lifecycle/integration checks run only in that disposable service.

Validation recorded on 25 October 2026: three PostgreSQL upgrade-path cases
passed with zero skips, including unchanged application rows and rollback
refusal; the actual-schema replica upgrade/repeat also passed. Sixteen focused
governance/REAL application tests, eleven script tests and the frontend production
build passed. Offline SQL confirms the REAL upgrade adds only the governance
schema and version bookkeeping. No existing application table is altered or
dropped on that path. Conflict-marker/index and whitespace checks passed.

The first full lifecycle/integration invocation could not connect because Colima
was unavailable; it failed before migrations or integration tests ran. After the
runtime became available on 25 October, a fresh task-owned disposable container
ran `scripts/validate_migrations.py`: **210 PostgreSQL integration tests passed,
zero skipped**, including the three upgrade-path regressions. Upgrade, repeat
upgrade, constraints, downgrade, re-upgrade and atomic failure rollback all passed.
The existing Starlette/AnyIO deprecation warning is non-blocking. The disposable
container was removed after validation. The source REAL database was inspected
read-only in the earlier step and remains unmodified by this work; it was not
started or migrated during the resumed validation.
