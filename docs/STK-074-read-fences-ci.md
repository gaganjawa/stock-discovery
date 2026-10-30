# STK-074 — MVP read fences and required CI gates

Baseline: `26c3857bb89aeebeddb1b55e8b9b3323decddab7` (merged STK-014 PR #17).
Implementation and synthetic validation only. Independent review remains required.
No publication, paper admission, provider activation or trading approval changes.

## Protected boundary

`real_views.company` assembles the bounded-watchlist company response inside a
transaction-scoped read guard: identity, historical chart, calendar, descriptive
features, financial facts/events, fixed-RAG/agent history and published shadow
references. `publication_store.read_artifact` and live-paper `read_evidence` also
have standalone guards. Nested reads on the same connection/access object share
one dependency set. Synthetic and historical-reconstructed flows remain unchanged.
The real status endpoint uses the guarded company reader; configured listing IDs
and static readiness information contain no fetched source content.

Dependencies come from original immutable revision ownership, instrument parents,
known citation fields and persisted RAG bundles (including agent baseline/final
bundles). All contributing sources are required; one valid source never excuses a
restricted dependency. Missing revisions, grants, fences, malformed references or
unverifiable original identities deny the whole response. Current-file renewal
cannot authorize evidence acquired under a different grant version. Both the
original acquisition grant and current configuration must allow store/derive and
any captured downstream use, including embedding and financial-fact scopes.

The guard assembles data privately, closes dependencies, then locks every original
provider/account/grant scope using STK-074's SQL function in sorted identity order.
Only after all potentially blocking locks are acquired does it revalidate original
and current rights using fresh database time. SHARE locks remain until transaction
end. No scope registration, reopening, content writes or migration is introduced.
A read is not a read-only SQL transaction: PostgreSQL row locks require a writable
transaction, although this boundary performs only SELECT and SET LOCAL operations.

If restriction wins the lock race, the read fails. If the read wins, restriction
waits for its transaction to end. Repeatable-read serialization failures and lock
failures deny access without automatic retries. The wait is bounded to five
seconds per lock statement. Errors are replaced with `real_read_access_denied`;
the existing authenticated API emits only `Source permission denied`.
An enclosing transaction retains locks longer than the guard's savepoint: callers
must finish it promptly and must not stream partial results before authorization.
This is authorization of a response assembled at that boundary, not revocation of
bytes already returned or browser screenshots. Private grant-file edits are not a
transactional revocation authority; use the durable operator fence for concurrency.

## Saved scans and deferred coverage

Existing pilot receipts copy universe data without original universe revision IDs.
They now fail closed. A current universe grant cannot legitimize that historical
copy. The scan boundary requires `universe_revision_ids` and per-row
`source_revisions`, and checks all referenced originals. This ticket does not
backfill, alter immutable receipts or change the producer. The saved-scan test
isolates assembly with a controlled mock and checks its guard against real
PostgreSQL provenance; it is not evidence of a new production scan producer.
The company viewer is the supported manual MVP path.

General SQL access, worker-side inference/cache lifecycle, filesystem copies,
backup restoration, deletion, external exports and client-side cache removal are
not covered. Do not grant end users direct database access. Historical replay
rights retain their existing separate contract. Real-source permission evidence,
trusted qualification loading and operational acceptance remain external gates.
The guard is linear in referenced revisions with per-revision database queries;
10,000 revisions, 100 bundles and depth 64 are defensive limits, not a performance
qualification. Bulk dependency loading and end-to-end response latency limits are
P3 follow-ups; queries may assemble data before these limits reject it.

## Measured CI baseline and optimization

GitHub job timestamps (successful exact PR heads, not local estimates):

| Run | Total | Migration + all PostgreSQL | Application checks (repeated PostgreSQL) | Browser | Docker build/start |
|---|---:|---:|---:|---:|---:|
| PR #16, [40727068947](https://github.com/gaganjawa/stock-discovery/actions/runs/40727068947), `1f36760` | 791 s | 295 s | 292 s | 119 s | 22 s |
| PR #17, [40766138684](https://github.com/gaganjawa/stock-discovery/actions/runs/40766138684), `ab78249` | 696 s | 249 s | 258 s | 121 s | 19 s |

The existing migration validator executes the entire PostgreSQL suite and rejects
skips. The old following application command ran that suite again. The new `unit`
job excludes only that already-mandatory directory. Independent `postgres` and
`ui` jobs retain full migration lifecycle/atomic rollback, Docker smoke, browser,
UI build and runtime licence capture. Python and npm caches use locked inputs;
installs still verify pinned Python hashes. No test sharding or database fixture
parallelization is introduced. Docker build caching is deferred: measured build
cost is small, and Compose already reuses images within the UI job.

The existing `checks` job name remains as an unconditional fan-in. It requires
success from all three jobs, including when a dependency fails, skips or cancels.
Regression coverage executes its shell gate for all 64 result combinations and
checks that mandatory commands are unconditional. Branch protection must continue
to require `checks`; this change does not modify GitHub protection settings.
Feature pushes already avoid duplicate workflow triggers (PR plus main push only).

Projected wall time is approximately 5–6 minutes, versus 11m36–13m11 previously,
subject to runner queues and suite growth. This is NOT a measured optimized CI
result; no branch has been pushed and no new GitHub workflow has run.

## Validation

See the delivery report for freshly executed results. All PostgreSQL fixtures,
HTTP/model doubles and local Compose acceptance are synthetic and disposable.
The initial provider-fence regression reproduced the pre-change bypass by returning
stored company data after restriction; the corrected guard denies that response.
Tests cover each fence level, missing/expired/revoked/renewed grants, mixed sources,
price-account provenance, cached research, direct API denial, malformed/missing
lineage, scan refusal, rollback, read/restrict ordering, old snapshots and expiry
while blocked on a lock. No live provider or inference acceptance is claimed.

## Changed-file scope

- `.github/workflows/ci.yml`
- `shared/stock_discovery_analysis/read_fences.py` (new)
- `shared/stock_discovery_analysis/evidence_storage.py`
- `shared/stock_discovery_analysis/publication_store.py`
- `shared/stock_discovery_analysis/real_views.py`
- `shared/stock_discovery_analysis/real_scan_view.py`
- `backend/tests/integration/test_read_fences.py` (new)
- `backend/tests/integration/test_evidence_ingestion.py`
- `backend/tests/integration/test_real_evidence.py`
- `backend/tests/integration/test_real_publication_flow.py`
- `backend/tests/test_real_scan_view.py`
- `scripts/test_ci_gates.py` (new)
- `docs/STK-074-read-fences-ci.md` (new)
- `docs/SIMPLE-BOARD.md`

Existing fixture changes acquire identity/prices under the same original permitted
grant instead of retroactively extending a stored acquisition through renewal.
The live-mode mismatch assertion now expects a sanitized permission denial;
synthetic-mode validation exceptions remain unchanged. No migration, schema,
strategy, immutable evaluation fixture, frontend source or lockfile changes.

### Executed locally, 30 October 2026

- Backend/worker excluding integration: **672 passed**.
- Final complete PostgreSQL suite: **346 passed, zero skipped**, including **23**
  new read-fence cases. Upgrade, repeat upgrade, downgrade, re-upgrade, unrelated
  sentinel preservation and failed-migration atomic rollback passed.
- Affected PostgreSQL rerun during correction: **49 passed**; these overlap the
  complete suite and are not additional unique tests.
- Script tests: **13 passed**, including two CI-gate tests (64 outcome combinations).
- Focused API/unit recheck: **7 passed** (already included in the unit suite).
- Frontend production build, Compose smoke and **7 Playwright tests passed**.
- Runtime licence inventory captured on local Linux ARM (`aarch64`) outside the
  repository; Linux AMD64 capture remains a mandatory future GitHub CI gate.
- Changed/new Python syntax, all changed/new file whitespace, `git diff --check`
  passed. No frozen evaluation artifacts changed.

The first complete database run found two fixture/exception compatibility failures
(**343 passed, 2 failed**); both were corrected as described above, then the entire
suite and lifecycle were rerun successfully. Colima's existing profile was started;
tests used synthetic disposable databases only. Existing Starlette/AnyIO and
multiprocessing-fork deprecation warnings remain. These results do not establish
real-provider rights, real operational acceptance or optimized GitHub timings.

## Review corrections — live agent transaction and unique-bundle bound

The before-fix PostgreSQL regressions reproduced both findings: a permitted
observed-mode agent tool raised `real_read_access_denied` inside its READ ONLY
transaction, and revisiting the first bundle after 100 unique bundles failed.
Those regressions are retained in `test_live_agent_read_fences.py`.

For live agent tools only, `tool_read_transaction` owns a private sibling database
connection for fence locks. It pins the existing connection's actual host/address,
port, database and login, retaining connection security options. The password is
passed privately, never logged or included in diagnostics. Connection failures
are sanitized. This is not a separate service or a shared connection pool.

The data/tool connection still executes `SET TRANSACTION READ ONLY`. Initial
bundle dependencies are locked and checked before the tool begins. Nested evidence
reads add any newly discovered dependencies and authorize the complete set before
returning evidence to tool calculations or embeddings. Fresh database-time rights
validation follows the entire lock pass, and runs again at the outer boundary.
The sibling lock transaction outlives the reader transaction's commit or rollback;
exceptions close both owned contexts. Tool adapters receive only the read-only
data connection, never the sibling. There is no unlocked fallback.

The existing direct company/evidence/API guard retains its original single-session
behavior. Synthetic and historical agent tools retain their previous read-only
transaction. The only other explicit READ ONLY production transaction is the
STK-074 deletion-manifest traversal; it does not call evidence readers or this
guard and is unchanged. Generic external READ ONLY callers are not automatically
given sibling connections: the supported agent entry point owns this lifecycle.
One additional bounded connection per live tool and repeated dependency checks
are accepted costs for this small slice; performance work remains deferred.

Bundle traversal now checks already-visited keys before enforcing the 100-unique
limit. A duplicate does not add a node or consume another query; a 101st unique
bundle still fails closed. Existing cycle termination and depth limits remain.
Additional changed files in this review correction:

- `shared/stock_discovery_analysis/agent_storage.py`
- `backend/tests/integration/test_live_agent_read_fences.py` (new)

## Proposed GitHub protection — NOT APPLIED

Read-only GitHub inspection confirms this is a public, user-owned repository;
the authenticated account has admin permission. `main` has no legacy protection
(required-status-check endpoint returned 404, “Branch not protected”) and no
active branch rules (empty array). Its existing Actions check is named **checks**,
produced by **github-actions**, app ID **15368**. The optimized workflow retains
that exact job/check name; it is not `Validate and build / checks` in the API.

Minimum recommended legacy branch protection, exact branch `main`:

```json
{
  "required_status_checks": {
    "strict": true,
    "checks": [{"context": "checks", "app_id": 15368}]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

After explicit owner approval only, this is a supported
`PUT /repos/gaganjawa/stock-discovery/branches/main/protection` request. Re-read
existing settings before applying so concurrent settings are not overwritten.
Zero review approvals requires the PR workflow without imposing a new independent
review-count policy; the required check must succeed and the branch must be current
with `main`. Enforcing admins prevents the ordinary admin merge bypass. An owner
can still edit/disable protection itself; this is not tamper-proof against admins.
No actor bypass list, force pushes, deletion, merge queue or paid feature is needed.

[GitHub's protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
confirms protection is available for public repositories on Free plans, so there
is no identified plan blocker for this public repository. Binding the check to the
Actions app prevents a differently sourced status with the same name satisfying
it. Following approval, read back the protection and verify `strict`, app binding,
admin enforcement and PR requirement. CI is **not enforced** until GitHub confirms
that configuration. No settings have been changed during this task.

### Fresh correction validation

- Before correction: both new regression cases failed (permitted READ ONLY tool,
  duplicate bundle at the 100-unique boundary).
- Focused agent/read-fence integration run: **42 passed** before final test expansion.
- Final full PostgreSQL suite: **358 passed, zero failures/skips**, including all
  **12 correction cases**. These cover permitted tools/investigation, PostgreSQL
  SQLSTATE `25006` write rejection, recovery after rollback, all three fence levels,
  restriction waits under READ COMMITTED and REPEATABLE READ, newly discovered
  restricted evidence before embedding, connection failure sanitization, cached
  investigation reuse without extra inference/reservation changes, and 100/101
  bundle boundaries. An injected connection-failure test initially leaked its
  monkeypatch into fixture teardown; the patch now restores within its own context.
- Migration upgrade/repeat upgrade/downgrade/re-upgrade/atomic rollback: passed on
  a new task-owned disposable PostgreSQL container. No existing REAL database used.
- Full backend/worker excluding integration: **672 passed**. Combined with the
  PostgreSQL suite: **1,030 application tests**; no skipped cases in these runs.
- Script suite: **13 passed**, including fail-closed CI gate checks.
- Changed/new Python syntax and whitespace, `git diff --check`: passed.
- UI/browser/licence results above are prior evidence, not rerun in this correction;
  frontend and workflow code have not changed since that validation.

No code committed/pushed; no GitHub settings applied. Independent security review
is the next code gate. Required-check enforcement still needs explicit owner
approval and GitHub read-back confirmation. Publication/admission/trading remain
blocked. Broader worker/cache authorization and deletion/backup execution remain
outside this correction.
