# STK-083 — D3-04/D3-09 INFY stored-evidence daily research

4 November 2026. A bounded research workflow, not investment or model-quality acceptance.

## Reuse and gaps

| Area | Existing implementation reused | STK-083 addition / remaining gap |
|---|---|---|
| Acquisition | `real_market`, Upstox adapter, grant fences, revision/page ingestion | Stored mode never acquires. Existing provider failure/recovery tests retained; recurring INFY acquisition is not activated. |
| Price qualification | `real_views`, `adjusted_research`, `read_fences`, STK-082 policy | Unified report projects the verified batch, coverage and freshness without relaxing them. |
| Technical analysis | Existing `indicators.features` via guarded company view | Decimal comparisons, trend alignment, ATR as percent of close, support/high distances and descriptive conditions. |
| Financial/AI | Guarded company facts, `combined_research.financial_projection`, existing factual verifier and RAG bundle recheck | Reported periods, ages, source locators/URLs, missing inputs, explicit unavailable AI/conflict validation. No new inference engine. |
| Strategy/replay | `strategy`, `swing_research`, `swing_qualification`, `quant_policies`, `historical_research`, replay/evaluation | No new strategy, levels, ranking or performance claim. Gates remain blocked. |
| Automation | D3-04 `tick`, jobs/leases/outbox, catch-up, pilot singleton, existing launchd tools | INFY-only stored worker adapter and separate inactive service label. |
| UI | Existing real company chart, qualification and research panels | Daily report, interpretations, operational metadata and refresh clearing. |

## Report and safety boundary

Authenticated `GET /v1/real-research/companies/NSE:INE009A01021/insight`
(or the URL-encoded listing) generates `infy-daily-insight-1`. It reads current
permitted stored evidence each time, returns `Cache-Control: no-store`, and never
calls providers/models or writes a report to the original database. Other listings
are not admitted to this first slice. Loading the company page automatically reads
the report after the company read succeeds. Refresh clears the company/chart and
report together; denial withholds content instead of replaying a cached response.

The report reuses single-batch page verification and current/original grant
checks. It contains price coverage, six existing indicators, deterministic
bullish/bearish/context observations, reported facts with period-end age and source
locators, financial uncertainties, AI status, a research conclusion, and scheduler
metadata. News is explicitly unavailable without permitted complete coverage.
Displayed interpretation values are rounded to two decimals; comparisons use the
unrounded existing indicator values. No forecast of returns is implied.

AI means **revalidated stored factual research**, when available; it does not mean
new inference. Old prose is not trusted merely because it has citations. A report
that fails the current factual verifier yields `AI_RESEARCH_UNAVAILABLE`. Conflict
validation is separately unavailable when there is no valid factual report; zero
returned conflict entries is not evidence of no conflict. Reporting-period age is
not publication age. No revenue growth, EPS, ratio, valuation or price level is
invented. Current raw-price/strategy/policy qualification does not support INFY
entry/stop/target, so all three stay unavailable. Publication, paper admission and
trading flags remain false.

States distinguish current-in-stored-calendar descriptive data, one-session delay,
unavailable data, denied HTTP reads and unavailable analysis. Scheduled failures,
rights blocks, partial results and catch-up appear separately in run metadata.
Session-list completeness is not asserted. The research evidence hash permits an
honest unchanged/changed comparison with the previous successful scheduled run;
it does not invent a detailed change narrative when no earlier run exists.

## Daily execution and activation boundary

The existing worker accepts `--stored-research-view VIEW --schedule-config SCHEDULE`.
It rejects mixed adapter modes and non-INFY scopes. The existing schedule resolves
post-close +30 minute jobs, validates calendar availability/coverage/next-session
boundaries, uses durable claim/finish/outbox contracts and records failures. An
expired publication window becomes an explicit catch-up read at **execution time**,
never a backdated forecast. A single process lock and database lease fencing prevent
duplicate completion. The configured calendar must agree with the guarded stored
calendar. An invalid or exhausted calendar blocks analysis; weekdays are not inferred.

Successful receipts contain report/evidence hashes, timestamps, status and zero-call
acquisition/model metadata, not a second financial corpus. Reads recompute the
report under current permissions; receipts cannot expose stale source content.
The latest successful timestamp is queried independently of recent failures.

Prepare an isolated derivative without editing the 12-stock configs:

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/prepare_stored_research.py \
  --view /private/existing-view.json --schedule /private/existing-schedule.json \
  --starts-on YYYY-MM-DD --code-version REVIEWED_COMMIT --output /private/new-infy-directory
```

The input calendar must already be verified and cover the requested start. This
command performs no acquisition and cannot renew a calendar. It preserves grants,
retention and calendar contents and selects INFY with the explicit one-session policy.
Use the resulting view for the API and the resulting schedule/view for the worker.
A bounded `worker.main --once` processes at most one due job, as before.

Use the existing `prepare_pilot_launchd.py` with `--stored-research` and `--pilot`
pointing to the new view; the other existing arguments remain required. It prepares
an **inactive** plist with label `local.stock-discovery.infy-stored-research`.
The existing activation tool accepts this reviewed label, keeps the schema check
and owner approval phrase, and refuses provider-mode arguments mixed into it.
Its `status --stored-research` and `deactivate --stored-research` target only this
service. The 12-stock service label and defaults are unchanged.

**Implemented and validated offline; not installed or activated.** No unattended
worker was started against the original database. No new schema is required.
Activation should follow owner review/merge and confirmation of the isolated
schedule's current verified calendar. Continuous operation still depends on the
Mac being awake; launchd restart plus D3-04 catch-up does not make a sleeping Mac
always-on. Existing calendar renewal uses provider calls and is intentionally not
invoked by stored mode.

**Acquisition disabled:** the prior two-request STK-081 approval does not establish
recurring acquisition activation. Existing source-use grants alone do not establish
owner approval of recurring calls, quota/budget or calendar renewal. The report
therefore says no acquisition attempt occurred **in this stored-evidence pipeline**;
it does not erase or reinterpret historical provider attempts elsewhere. There is
no config boolean here that bypasses this boundary. The existing provider adapter,
request-budget and recovery infrastructure remain the route for a separately
approved acquisition increment. No automatic intraday stitching, financial refresh,
corporate-action acquisition, model execution or paid calls are introduced.

## Historical evaluation and training disposition

`strategy.py` already implements the EMA10/EMA30, volume, breakout and ATR-based
synthetic swing strategy (`ema-breakout-1.0.2`). `quant_policies.py` already assesses
swing, short-term and long-term policy inputs. `historical_research.py` explicitly
freezes **synthetic** full-replay snapshots; existing replay/experiment contracts
provide cutoff, freeze/reveal, holdout and outcome controls. Their synthetic tests
remain useful software tests, not real performance evidence.

INFY's observed-now split/bonus-adjusted candles are descriptive evidence, not
original point-in-time raw prices or an independently qualified adjustment ledger.
Volume and complete action coverage, original financial disclosure availability,
complete event coverage, policy approval and an independent evaluation plan are
missing. No qualified real out-of-sample result can be claimed from this batch.
Predictive training is unjustified: missing point-in-time features/labels,
leakage-safe time splits, adequate independent samples, cost/benchmark assumptions
and untouched validation evidence. No model was trained and no gates were changed.

## Actual acceptance and validation

Private original database `stk_real001_private`, schema `0015`: guarded report and
actual React page returned 43 bars through November 3, latest verified closed stored
session November 4, six non-null descriptive price indicators, 24 reported numerical
facts, period ages/citations, deterministic interpretation and a non-actionable
conclusion. AI was unavailable (`financial_report_validation_unavailable`, differing
cutoffs and unqualified evidence); hypothetical levels and complete news coverage
were unavailable. Original revision/payload hashes are checked before/after; private
JSON receipts and screenshots stay outside Git. Zero actual provider/model calls.

Validation: 985 backend/worker tests; 37 focused PostgreSQL cases plus 24 existing
provider/recovery/combined-research integration cases on disposable databases;
10 launchd/preparation tests; frontend production build and 18 browser cases.
Existing one/two-session, provenance, grant revocation, cached-factual verification,
provider failure, singleton, replay and non-admission tests are reused. New cases
cover interpretation, incomplete facts, AI unavailable, guarded endpoint denial,
catch-up execution clocks, receipt idempotency, terminal processing failure and UI
clearing. No original database migration or historical fixture edit occurred.

Initial validation exposed strict tuple construction in the new preparation helper
and an incomplete invented next-session calendar; both were corrected. Legacy
scheduler tests initially lacked migrations in their disposable base database;
existing migrations were applied there only. Browser fixtures also encountered a
stale Vite-served component; the isolated server was restarted and verified against
the current source. The untracked ImportPreview WIP remains untouched and is excluded
from the isolated frontend build.

## Capability matrix

| Capability | Before | After | Evidence |
|---|---|---|---|
| Real price analysis | Guarded chart and six indicators | Same engines plus deterministic interpretations | Actual 43-bar INFY page and contract tests |
| Fundamentals | Guarded facts and separate research history | 24 reported facts with age/locators and explicit gaps in daily report | Actual guarded read |
| AI research | Existing factual/RAG/agent engines | Existing verifier reused; current INFY AI report explicitly unavailable | Current verifier result, no inference |
| Stock ranking | Existing limited watchlist/synthetic screening | No new real ranking; INFY-only investigation | Scope validation |
| Historical evaluation | Synthetic replay and qualification gates | Existing gates retained; real OOS/training blocked | Existing regression tests and input audit |
| Daily automation | Coupled 12-stock acquisition/research pilot | Separate stored-only mode using same scheduler/launchd; inactive | Disposable catch-up/idempotency/failure tests |
| User dashboard | Separate chart/facts/research panels | Unified daily insight and operational status | Actual browser receipt and scripted UI tests |

Next smallest increment: after merge, review and activate the isolated **stored-only**
INFY schedule with a currently verified calendar and verify one real due/catch-up
receipt. Recurring acquisition requires a separately scoped owner/provider decision;
M1 and M2 remain incomplete.
