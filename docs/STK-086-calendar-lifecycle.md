# STK-086 — D3-04 / D3-09 stored INFY operational readiness

Stored research checks calendar evidence, current rights and deployment identity
before the existing worker claims a job. This is operational readiness, not
current market analysis, source qualification or trading approval.

| Reused | Addition |
|---|---|
| D3-04 occurrences, catch-up, singleton, leases, receipts/outbox | Read-only lifecycle gate before `tick`; no new scheduler |
| Original revision grants and durable read fences | Session lineage, hashes, page completeness and retention checks |
| Existing calendar and `pilot_operations.renew_calendar` | Finite coverage and explicit renewal blockers; no stored-mode provider access |
| Existing preparation and launchd tooling | Private manifest, merged code pin, path/hash/permission checks |
| Daily insight and run-status projections | Readiness CLI and bounded private `health.json` |

## Lifecycle and renewal boundary

`calendar_lifecycle.lifecycle` reports valid, expiring soon (four calendar days),
expired or blocked coverage. It reports the next verified opening and the next
post-market execution. That execution also needs the following verified opening
for the existing swing expiry fence. A future opening alone is insufficient.
No calendar, `ends_on`, schedule hash or occurrence identity is rewritten.

The read gate corroborates configured sessions with eligible observed revisions,
original source identity, availability, content hashes, supersession lineage and
original grants. Missing/conflicting sessions, incomplete/quarantined page
chains, denied rights and retention expiry block readiness. Additional stored
sessions inside the declared coverage that disagree with the configuration also
block it. Corrected coverage requires explicit review and a new preparation.

`SessionData` contains **positive sessions only**. A complete ingestion page does
not prove every intervening date was checked for closure. Permitted future
revisions are reused for corroboration, but cannot extend coverage. Renewal is
`RENEWAL_BLOCKED`, with `closed_date_coverage_not_in_session_revisions` and
`recurring_calendar_acquisition_not_authorized`. Missing/conflicting evidence or
authorization failures add specific reasons. JSON consistency is not exchange
authority. No safe stored-only extension is established by the current contract.

Existing Upstox `renew_calendar` already requests each date in a bounded range,
checks acquire/derive/store rights, validates all replies and ingests sessions.
Its returned report records closed dates; the durable session table does not.
Its live `Operations.preflight` wrapper invokes renewal automatically, so that
wrapper remains excluded from stored mode. There is no duplicate provider path.
Using it later needs explicit calendar-only owner activation and applicable
source-use/retention permission; acquire/store rights alone do not authorize
recurring calls. The new path never reads a token or calls a provider.

## Preparation and operation

Use a clean isolated checkout of reviewed merged main, the existing private INFY
view/schedule, existing private database connection file and existing venv.
Keep the original 12-stock files and STK-085 evidence untouched.

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/prepare_stored_research.py \
  --view "$EXISTING_INFY_VIEW" --schedule "$EXISTING_INFY_SCHEDULE" \
  --output "$NEW_PRIVATE_DIRECTORY" --code-version "$MERGED_SHA" \
  --starts-on "$REVIEWED_START_DATE" --repo "$CLEAN_MERGED_CHECKOUT" \
  --python "$EXISTING_VENV_PYTHON" --database "$EXISTING_DATABASE_FILE"
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/prepare_pilot_launchd.py \
  --stored-research --python "$EXISTING_VENV_PYTHON" --repo "$CLEAN_MERGED_CHECKOUT" \
  --pilot "$NEW_PRIVATE_DIRECTORY/view.json" --schedule "$NEW_PRIVATE_DIRECTORY/schedule.json" \
  --database "$EXISTING_DATABASE_FILE" --operations "$NEW_PRIVATE_DIRECTORY" \
  --output "$NEW_PRIVATE_DIRECTORY/inactive-launchd.plist"
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/check_stored_research.py \
  --deployment "$NEW_PRIVATE_DIRECTORY/deployment.json"
```

Preparation is exclusive: a second attempt fails without changing previous
files. Directories are 0700, files 0600; credentials remain external references.
View/schedule/policy hashes are pinned. Grants remain reload-on-use. The gate
checks clean pinned code and local `origin/main` ancestry without network access;
fetch main during reviewed preparation after merge. Old runtimes lacking the
gate and unmerged code cannot pass activation. The running module, arguments and
database reference must match the manifest. Unrelated untracked WIP is preserved.

Readiness is `READY_WITH_LIMITATIONS` while the next run is supported but renewal
needs intervention, or `BLOCKED` with reasons. Examples include
`next_execution_opening_unverified`, `calendar_expired`, `source_grant_expired`,
`source_grant_expires_before_next_execution`, `stored_retention_expired`,
`retention_expires_before_next_execution`, `deployment_code_mismatch`,
`deployment_code_not_merged` and `deployment_runtime_preflight_missing`.
Grants within seven days warn; schema must be 0015. A successful preflight is an
instantaneous observation, not a future authorization lease.

After review/merge and **only if a fresh check permits activation**, use the
existing commands below. None was activated for STK-086.

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/activate_pilot_launchd.py activate \
  --reviewed-plist "$NEW_PRIVATE_DIRECTORY/inactive-launchd.plist" \
  --approval 'I approve unattended local research refresh'
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/activate_pilot_launchd.py status --stored-research
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/activate_pilot_launchd.py deactivate --stored-research
```

LaunchAgent isolation, KeepAlive/throttling and the common singleton remain.
Recurring stored mode requires the manifest; supervised legacy `--once` remains
available. Every iteration rechecks readiness. Blocks leave scheduler/evidence
tables alone and update bounded private health, then wait at least 30 seconds.
Normal receipt failures remain visible. Sleep/wake uses existing actual-clock
catch-up, never reconstructed predictions. Local health is not off-host alerting
or proof the Mac is awake. A code/calendar change preserves old receipts but
changes schedule identity; review the start date rather than replaying by accident.

## Validation and private observation

Offline/disposable tests cover lifecycle boundaries, permitted stored sessions,
incomplete/conflicting revisions/pages, absent/expired/revoked grants, expiry
before the next execution, repeat preparation, stale deployment, disabled
providers/models, blocked-worker health, and catch-up/idempotency with partial
stale analysis. Existing scheduler/freshness/authorization regressions remain.
Invented fixture sessions are not real market qualification.

The private 5 November preflight confirmed schema 0015 and the unchanged
43-candle INFY batch through 3 November. Latest stored closed session: 4 November;
analysis: delayed descriptive. Next opening: 5 November; next post-market run:
5 November 16:00 IST, fenced by 6 November's opening. Coverage ends 7 November;
no opening after 6 November is verified. Grants expire 20 November 02:42:18 IST.
Both LaunchAgents were inactive. Receipts/fingerprints remain outside Git.
No real worker job, provider/model call, database mutation, migration or
activation was performed for this ticket.

A durable isolated configuration pinned to pre-PR merged main was prepared
without overwrites. It correctly reports `deployment_runtime_preflight_missing`:
that code predates this correction. Review/merge and new pinned preparation are
required before enabling the improved worker. Calendar renewal and recurring
acquisition still need separate verified coverage and owner authorization.
