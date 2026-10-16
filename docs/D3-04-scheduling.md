# D3-04 — Scheduling and coverage

STK-017/058/060/073 · SD ARCH 3.0 §8 · 16 October 2026

The opt-in scheduler persists exchange-calendar occurrences and executes one bounded job per worker tick. The legacy synthetic queue stays compatible. This package supplies orchestration and fictional unattended acceptance; investment policies, evidence extraction, grounded AI and paper outcomes remain their later packages.

## Delivered behavior

- Strict versioned calendar/policy configuration, with a generated [schema](contracts/scheduling/schedule.schema.json) and [fictional configuration](contracts/scheduling/synthetic-schedule.json). IST close +30-minute readiness, next-open minus60-minute swing cutoff, final weekly/monthly trading sessions, explicit special sessions and calendar-coverage checks. Missing next-session information is visible. Policy content, hashes, calendar revision and resolved times are retained in immutable occurrences. Configuration corrections generate new identities without rewriting earlier records.
- Durable occurrence/job identities, restart checkpoints, queued/running/retry/blocked/failed/partial/completed/missed states; dependency jobs and stage writes commit together. Internal result/outbox writes are atomic. No external notification sender is installed.
- Expiring leases and fencing tokens reject stale completion. Three execution attempts, exponential bounded jitter, 15-minute readiness retry and Retry-After support. Rights/credentials/budget/policy and ambiguous-billing failures block; audited evidence is needed to resume. Unknown failures fail closed. No billable transport is installed.
- Historical catch-up cannot become a forward signal. Missed event polling is recorded without reconstructing old news from current material. Poll catch-up advances at most31 days per tick. Safety/event and outcome jobs precede discovery; replay follows it. Future production scans must expose bounded handler chunks.
- Trusted normalized event hooks validate source/listing association against a current-rights-checked immutable snapshot and require eligible universe membership. Supported normalized categories are earnings, restatement, default, auditor change and regulatory action. Deduplication and 15-minute queued-job coalescing retain every source. Events arriving after work starts create another job. Adverse events write immutable admission-pause signals and queue reassessment.
- Frozen member reconciliation retains exclusions and incomplete members; all four denominator equations are checked. Operational reports require scope/mode/horizon and retain the previous complete result with publication age and input age. Failure/partial/unknown states cannot display a successful empty scan.

## Local use

Apply migration0006 to an authorized local database first. Supply its connection through the existing DATABASE_URL setting; never commit credentials.

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python -m worker.main \
  --schedule-config docs/contracts/scheduling/synthetic-schedule.json \
  --synthetic-schedule
```

`--once` executes one scheduler tick. The shipped configuration and adapter are explicitly fictional and date-bounded; their mock rights expire on1 January2027. Each cycle automatically ingests the pinned fictional pages, freezes a D3-03 snapshot, then applies a test-only noncandidate classifier. This exercises scheduling without pretending to implement D3-05 investment policies. It produces no BUY and uses no model, network source or owner API key.

Without `--synthetic-schedule`, no provider or research handler is installed: ingestion/polling blocks on credentials and screening/reassessment blocks on policy. A calendar beyond its coverage reports expiry. The explicit 24-hour short/long fixture windows are engineering fixture settings, not approved real-market strategy parameters.

## Integration boundaries and blocker

D3-05 supplies horizon policies; D3-06 supplies authenticated event extraction and additional materiality categories; D3-09 supplies dashboard/publication integration; D3-10 consumes admission-pause signals, implements outcome evaluation and portfolio macro fan-out. The hooks do not modify legacy decisions, fills or portfolios, and do not claim those future integrations are already active.

**Restricted runtime-role activation remains blocked.** Automatic approval review rejected a proposed change to `deploy/roles.py` that would grant discovery-schema access. That file and all database role privileges remain unchanged. The new worker is tested only with the owner of a disposable database; do not switch the private runtime worker to this scheduler until the owner approves and a separate least-privilege grant/test change is reviewed. The required operations are SELECT/INSERT on the new immutable records, UPDATE on stream/queue/checkpoint state, schema usage and audit-sequence usage. No grant is applied by this PR.

No real-source permissions, paid API calls, external deployment or broker actions are included. The owner reviews/merges the ticket branch before D3-05 starts.

## Acceptance evidence

Deterministic tests cover special/holiday/week/month boundaries, truncated/revised calendars, monitoring hours, full-universe reconciliation, missed-forward conversion, event deduplication/coalescing, admission pauses, stage rollback, dependency/outbox atomicity, stale workers, retry exhaustion, Retry-After and last-complete age. A disposable PostgreSQL database exercises unattended fictional ingestion → snapshot → screening and migration upgrade/repeat/downgrade/re-upgrade/failure rollback. Final test totals are recorded on the [board](SIMPLE-BOARD.md).
