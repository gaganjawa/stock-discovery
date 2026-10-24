# D3-11 acceptance record

Scope: STK-041/042/044/069/072/076–078; SD-ARCH-3.0 T14/T15. Separate branch from merged main `a0846b5784a44bde3a8b9a6b172600a1a98259c3`. Draft PR #12 remains unchanged at `a72e487e2076d4a86a2c31b8cf8d35b2a556ddef`; its successful CI was inspected read-only.

## Implemented acceptance

- Immutable experiment manifests, trial requests/results, denied-access history and future-only controls.
- Three mandatory arms with original D3-09 artifacts and D3-05 reproduction; optional ML disabled.
- Paired set equality and end-to-end selection differences; all published failures/abstentions retained.
- Chronological ordering, maximum-label embargo, label purging, shared snapshot/revision/event grouping and training-only preprocessing.
- Holdout reservation before outcome access, concurrent single winner, crash recovery, renamed/relabelled holdout rejection and immutable validation selection.
- Original versus later restated financial evidence, PIT research documents and post-cutoff financial observations checked.
- D3-10 pinned ledger revision, separate forecast/trade denominators, immature long-term forecasts and unchanged history after new observations.
- Failed AI accounting remains unavailable; zero picks and missing research are distinct. Benchmarks, uncertainty, cost stress and unsupported forecast labels are explicit unavailable results.
- Promotion fails closed with unset thresholds, missing samples, missing prospective evidence and unverified independent approvals. Supplied references do not self-approve.
- Existing Scorecard shows registry, arms, outcomes, promotion blockers and immutable history. Revoked source access clears/hides results.

## Validation

Local validation on 24 October 2026:

- 394 backend/worker non-database regression tests passed before final additions; the final targeted run passed all 43 D3-11 cases (10 unit and 33 PostgreSQL cases). Together with unchanged baseline coverage, **589 unique application/worker tests were exercised**: 396 non-database and 193 database integration cases, zero skips.
- Full migration acceptance executed **190 database tests with zero skips** before the three final targeted database additions. Upgrade, repeat upgrade, downgrade to base, re-upgrade and deliberate atomic failure rollback passed. The three additions also used freshly migrated isolated databases.
- **10 script tests**, all three existing contract/evaluation/capital-risk validators and the production frontend build passed.
- **4 browser workflows passed** against the isolated local API, worker and UI: discovery, governance, paper portfolio and replay/scorecard.
- Exact-commit CI is tracked by the new draft PR's checks. Its verified run link and commit are supplied with delivery; no self-referential commit hash is embedded here.

The initial browser fixture import was adjusted for the local Node runtime; all four workflows then passed. Final targeted regressions cover the observed UTC-ledger adapter issue, forward-registration retries after the window opens, missing-decision snapshots, source revocation, future financial facts and pagination. No skipped database case is counted as acceptance.

Tests use a task-owned disposable PostgreSQL 16 container on port 5551, separate from REAL-001 and other development databases. The three horizon research inputs and local providers are existing fictional fixtures. No genuine financial efficacy, clean historical model knowledge, research calibration, forward investment performance or strategy approval is claimed.

## External blockers and limits

The software governance package does not require unmerged REAL-001 code. Genuine investment acceptance still requires independently ratified horizon thresholds/approvals, qualified sources, prospective tracking admission, mature independent observations, comparable permitted benchmarks and a validated dependence-aware uncertainty/cost-stress design. On main, D3-10 forward admission is deliberately blocked. These are visible unavailable/promotion blockers, not waived criteria.

No live operations, paper positions outside disposable fictional tests, broker orders, paid APIs, model downloads, launchd activation, merge or deployment occurred. D3-12 was not started.
