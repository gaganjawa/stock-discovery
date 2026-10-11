# Stock Discovery — work checkpoint, 11 Oct 2026

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
