# Stock Discovery — work checkpoint

## STK-043 continuation — 13 October 2026

Owner authorized another bounded task. Replay now exposes its supported strategy version and rejects unsupported versions. 49 local tests/build passed; implementation `83f8fa8` passed full CI including browser acceptance and database migrations. See [STK-043](STK-043.md). Pause after status report. Hosted board synchronization remains pending for STK-033/043.

## STK-033 continuation — 13 October 2026

Owner authorized the next bounded task with minimal usage. STK-033 now displays frozen rule results and complete version provenance; see [acceptance notes](STK-033.md). Implementation `039c492` passed full CI including browser acceptance and migrations. Hosted board synchronization remains pending; local status is Ready for Release for synthetic scope only. Stop after reporting this task and wait for the owner's next go. Foundation external gates remain unchanged.

## Latest continuation — foundation work complete to external gates

Owner approved Hetzner CX23/Linux/Compose and encrypted restic/B2; do not reopen hosting alternatives. STK-008 is Done. STK-009/016/017/018 remain PARTIAL (Backlog + Blocked), with secure private configuration, runtime privileges, worker/monitoring controls, encrypted local recovery and rollback verification delivered. See [current STK-018 acceptance](STK-018.md#current-foundation-acceptance--supersedes-historical-configuration-findings-below) for exact tests, commits and remaining gates. Native AMD64 CI evidence is retained in docs/licenses/linux-amd64-6e3886d.json.gz; no blanket licence clearance.

Hosted board updates for these five tickets were saved and verified after reload. No purchases, B2 connection, external deployment or accepted release tag. Earlier unresolved-provider and configuration-gap descriptions below are historical. Unrelated .idea/, main.py and root pyproject.toml remain untouched.

**Owner instruction: wait for explicit go after the current foundation status report.** Do not start another milestone or provision services automatically. Required before provisioning: region, final checkout price, backup-key custody and explicit authorization. Remaining deployment gates include native/host licences, actual private HTTPS/firewall, B2 disaster recovery and external alert/dead-man acceptance.

Local preview: from this repository, use the existing ignored local .env owner key and run `COOKIE_SECURE=false APP_ORIGIN=http://127.0.0.1:5173 docker-compose up --build -d`, then open http://127.0.0.1:5173. Never carry the HTTP override to private hosting. Isolated verification containers are stopped after testing; their explicitly named test volume is retained, not substituted for preview data.


## Hosted tracking synchronized — 12 Oct 2026

39 tickets synchronized and their saved fields verified after reload; 51 unrelated tickets unchanged. See the [local Kanban synchronization record](stock-platform-kanban-plan.md#hosted-board-synchronization--12-oct-2026). Existing Done and synthetic Ready for Release statuses retained. Partial work uses Backlog + Blocked (not Done); no tickets remain In Progress or Review/Test. STK-004–008 remains outstanding, STK-008 not started. No deployment/tag or application changes. Historical notes below about the hosted board being untouched are superseded by this synchronization.

Current release decision: **PARTIAL**. [STK-009 software audit](STK-009.md) records dependency inventory, corrected browser notices and remaining native/platform licence evidence gaps. See [STK-018 acceptance, release notes and recovery/rollback runbook](STK-018.md). Local synthetic preview verification passes; private deployment and formal release gates remain open.

## Verification update — 12 Oct 2026

- Replay root cause: global table margins/borders reached Lightweight Charts internal table. With an unconstrained autoSize host this formed a resize feedback loop: measured chart height grew 48px per two frames, moving the reveal button continuously. No animations or DOM replacement were observed during measurement. Fixed a 340px chart host and scoped table styles to application tables; added geometry assertions without changing timeouts or forcing clicks. Replay fix: `17e4300`.
- Focused headed Replay test passed (1.9s); full E2E suite passed (one workflow, 1.7s), and passed again after runtime changes. Production frontend build passed.
- Python regression: 42 passed; 7 PostgreSQL cases passed separately. Migration upgrade/repeat upgrade/downgrade/re-upgrade and intentional atomic failure rollback passed. Original contract, evaluation and capital/risk fixtures and two smoke-script tests passed.
- Full Compose source rebuild passed; migration exited 0, database healthy, API/UI/worker smoke passed. Running worker completed a queued synthetic scan for three instruments. API and worker run as UID/GID 10001; worker now receives CODE_VERSION.
- Authentication now rejects non-ASCII invalid credentials with 401 rather than raising a server error. Tests cover expiry, tampering, key rotation, fail-closed configuration and cookie origin protection. Local access key is ignored, owner-only (0600), and absent from tracked files.
- Backup was restored into a new disposable database with matching hashes for every research table; disposable restore database removed and services restarted. The verification dump is a temporary local artifact, not an operational backup policy.
- GitHub CI passed for `067860fd16b3ee26d207e4bd67d47935a448d4d4`: [verified run](https://github.com/gaganjawa/stock-discovery/actions/runs/38176118150). The old WIP baseline `002ddf0` had failed CI.

Remaining release limits: synthetic-only scope; real source rights/imports, full corporate actions, market benchmark/EP-1 acceptance and full notice audit remain unresolved. Before external deployment, configure HTTPS/secure cookies, strong database credentials and a separate least-privilege runtime database role (Compose currently shares the bootstrap owner), login abuse controls, and encrypted off-host backups with retention/restore procedures. Nginx retains its standard root master/non-root worker model. No release tag, external deployment, live feed, broker orders or Kanban changes were made. These verification results do not imply full release readiness.

The earlier checkpoint below is historical; the checks above supersede its pending local-verification notes.

Paused at the owner's request to commit completed work separately from work in progress. No v0.2 release tag or external deployment was created.

## Completed and validated implementation

- M1: availability-aware clocks/adapters, immutable decisions/outcomes, point-in-time identities/universe, synthetic raw daily history, PostgreSQL ingestion, dataset manifests and quality/chronological gates. STK-014, 015, 019, 021–024 are Ready for Release for synthetic scope. STK-020 remains partial: known-action price normalization and conservative exclusions exist; full action execution and real exchange imports do not.
- M2: deterministic SMA/EMA/ATR, relative volume and prior-window breakout; frozen EMA/volume/breakout BUY/WAIT/INSUFFICIENT_EVIDENCE strategy; entry/stop/target/expiry and Decimal cash/risk/exposure sizing. STK-028–032 implemented for synthetic scope; private release acceptance pending.
- M3: persisted freeze/reveal, daily fills/gaps/expiry, date-effective fictional fees/slippage, ambiguity and missing-data handling, unchanged STK-002 metric parity. STK-037–040 implemented for synthetic scope. STK-041/042 have core metrics, a predeclared single-position portfolio and grouped descriptive reports, but full market/benchmark/EP-1 acceptance remains partial.
- Completed-work checkpoint: `62a9860` (portfolio/report tests and PostgreSQL ingestion/service tests pass).

## Separate WIP snapshot

Authenticated owner sessions and API routes; persistent leased/retried jobs; daily synthetic scans, replay jobs, sample batches and audit export; API-backed React Dashboard/Research/Replay/Scorecard; Lightweight Charts attribution; Portfolio/IPO future placeholders; Compose migration service; browser test/CI wiring; backup/restore verification script; source-rights register.

These changes are committed as WIP, not completed tickets. Main remaining checks: browser acceptance; final rebuilt-stack smoke test; executing backup/restore; runtime privilege/security review; final CI; release documentation/rollback acceptance. API/UI and worker files changed after the first local image build, so the running stack may lag the saved source until rebuilt. The test browser download was cancelled at this checkpoint; rerun installation before browser tests.

## Verification recorded

- Latest full local Python run: 40 passed, 7 database cases skipped in that unit-only invocation.
- Separate database migration run: 7 integration cases passed; upgrade, repeat upgrade, downgrade, re-upgrade and intentional atomic failure rollback passed.
- Additional checkpoint: 4 portfolio/report/metric parity tests plus 2 PostgreSQL ingestion/service tests passed.
- React production build passes. Dependency install audit reported 0 vulnerabilities; this is not a complete security audit.
- Last confirmed green GitHub CI: `0603132` (replay milestone). New checkpoint CI must be checked after push.
- Local Compose build/start succeeded, bound to loopback. Browser workflow and backup/restore have not been executed successfully. No public deployment, real provider, broker order or paid service activated.

## Resume / local preview

Repository: `/Users/gaganjawa/Documents/Code/stock-discovery`.

An owner-only `.env` was generated locally with a random owner access key; it is ignored by Git and Docker build context. Read the key locally to sign in; never commit or send it. Local HTTP uses `COOKIE_SECURE=false` and `APP_ORIGIN=http://127.0.0.1:5173`; external deployment requires HTTPS and secure cookies.

```sh
docker-compose up --build -d
# Open http://127.0.0.1:5173 and sign in with the local AUTH_TOKEN.
# Dashboard: Load synthetic history; Replay: choose instrument/date,
# Freeze recommendation, then Reveal future prices and outcome.
cd frontend
npx playwright install chromium
npm run test:e2e
```

Before release, set CODE_VERSION to the tested commit, rebuild, rerun migrations/smoke/browser tests and verify backup into a disposable database. The current backup script does not encrypt off-host copies. No hosting/backup provider or source subscription has been selected.

## Copy-ready Kanban update

STK-014/015/019/021–024/028–032/037–040: synthetic implementation validated; Ready for Release, not Done. STK-020/041/042: partial with documented limits. STK-016–018/033/043–045: WIP/release verification pending. STK-004–008: source/account/hosting permissions or decisions unresolved; real integrations disabled. STK-009: chart attribution included; full notice audit pending. Original completed tickets remain unchanged. Hosted Kanban was not modified.

Unrelated `.idea/`, `main.py`, and root `pyproject.toml` were preserved and excluded from these commits.
