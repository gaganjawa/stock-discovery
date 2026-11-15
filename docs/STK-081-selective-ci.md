# STK-081 / D3-13 — conservative change-based CI

The required check remains **checks**, with the existing PR/main triggers, pinned
actions, pip/npm caches, Python hash verification and concurrency cancellation.
No branch-protection change, production service, dependency or provider call is added.

## Selection and failure behavior

A small standard-library `changes` job checks the entire Git diff, validates the
selection/gate regressions and checks Markdown before exporting suite decisions.
Checkout fetches full history. PR selection compares the event base to the actual
checked-out merge tree and verifies both PR parents are ancestors. Push selection
compares event before/after, including every commit. `--no-renames` and NUL-separated
paths retain both old/new rename paths, deletions, spaces and newlines. Filenames
never enter shell interpolation. There is no API pagination or 300-file cutoff.
Missing/invalid history, empty changes or unknown paths select all suites; a failed
selector/document validator prevents the aggregate check passing.

| Changes | Selected checks after selection/documentation validation |
|---|---|
| Ordinary `docs/**/*.md`, root README/AGENTS only | Fast documentation path; no application suites |
| Frontend source/tests/public assets | Complete UI job, including build, browser, HTTPS and hosted acceptance |
| Backend/worker test files | Complete unit and PostgreSQL jobs; security/HTTPS test changes select all |
| Backend/worker/shared runtime Python | All three jobs because API, research and browser contracts share the runtime |
| Workflow, scripts, dependencies/lockfiles, migrations, security, deployment, unknown paths | All three jobs |
| Contracts, policies and licence evidence under docs | All three jobs; these are executable/test inputs, not ordinary prose |
| Mixed paths | Union of affected suites |

Security-sensitive filenames and dependency/build filenames take precedence over
component paths. Unknown frontend file types also select all suites. This is
conservative component selection, not individual-test selection. No materially
affected test, migration phase, permission assertion or browser flow is removed.

The `checks` job uses `always()` and requires successful `changes`, valid explicit
true/false decisions, success for every selected suite and `skipped` only for an
explicitly unselected suite. Failure, cancellation, missing decisions or accidental
skips cannot pass. Regression tests cover all **512** selection/result combinations,
missing/invalid outputs, actual multi-commit Git diffs, renames/deletions, advanced
bases, missing history, mixed scopes and a diff exceeding 1,000 files.

Documentation validation checks changed Markdown plus the board and both handoffs:
UTF-8, unresolved conflict markers, fenced-code closure and local link existence.
Deleted/renamed targets are checked against unchanged Markdown referrers. External
URLs and historical absolute owner paths are not fetched. No package install or
network access is required by this path after checkout.

GitHub documents that workflow-level path filters can leave required checks pending
and that skipped dependencies need an explicit always-running fan-in. Selection is
therefore inside the workflow, with the stable required gate retained:
[trigger filters](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow),
[job dependencies](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs).

## Measured timings and PostgreSQL inspection

Owner-reported planning baseline: unit ~1 minute, UI ~7 minutes, PostgreSQL ~15 minutes.
The completed **documentation-only PR #55** run provides the directly measured
baseline: [43719092489](https://github.com/gaganjawa/stock-discovery/actions/runs/43719092489),
head `b46db9044bfd13883c53b0fa78d4e6585b67538f`, all checks passed.

| Measurement | Before: GitHub run #55 | After: local replay of the same changed paths |
|---|---:|---:|
| Unit job | 40 seconds | Not selected |
| UI job | 463 seconds (7m43s) | Not selected |
| PostgreSQL job | 522 seconds (8m42s) | Not selected |
| Workflow creation → final gate completion | 532 seconds (8m52s) | Hosted elapsed time not yet measured |
| Selection + Markdown validation | No separate fast path | 0.0445 seconds on the Mac; four Markdown files |

The local replay used the real PR #55 base/head/merge SHAs and selected no application
suites. This is measured local logic time, **not** a GitHub before/after speedup claim:
runner queue, checkout, test and gate overhead are excluded. The workflow-changing
PR correctly selects the full suite. A later genuinely documentation-only GitHub
run will supply the hosted fast-path measurement; owner monitors CI without waiting.

Existing STK-096 timings in that PostgreSQL log:

| Phase | Seconds |
|---|---:|
| Initial migrations | 0.27 |
| All PostgreSQL integration tests | 478.22 |
| Downgrade and re-upgrade | 0.43 |
| Atomic rollback | 0.02 |
| Total validator execution | 478.94 |

All **633** integration cases executed, zero skipped. The separate online backup
regression passed in 1.152 seconds. Slowest setup cases were publication/governance,
discovery comparison/history, registered folds and paper: **9.84–9.98 seconds** each.
Inspection confirms these construct isolated three-horizon publication state.
The hosted reconnect test took **6.44 seconds**; permission expiry/lock tests took
**3.16–4.95 seconds**. These waits and independent mutable fixture databases support
recovery/security assertions; no safe removal was demonstrated. Migration work is
under one second, so optimizing it would not address the measured bottleneck.

The confirmed waste removed here is scheduling 478 seconds of database tests and
463 seconds of UI work for unrelated prose updates. No parallel tests on shared
mutable databases, weakened durability settings, reduced timeouts, fixture changes
or database-suite speedup is claimed. Runtime changes still run the full tests and
zero-skip integration-report guard. Existing phase/slow-test diagnostics are retained.

## Validation and release boundary

All 12 selection/gate/document and workflow-wiring tests passed locally in 0.448
seconds; Markdown/link validation and whitespace checks passed. Historical board
and work-handoff sections match main exactly. Runtime suites were not repeated locally;
all existing suite commands remain unconditional inside their selected job. This
change itself requires full exact-head CI before owner merge. Project planning
baseline remains 58%; infrastructure efficiency does not establish live candidate,
market-data qualification, off-server recovery or investment acceptance.
