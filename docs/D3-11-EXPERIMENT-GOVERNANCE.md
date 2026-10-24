# D3-11 — Experiment governance

Tickets: STK-041/042/044/069/072/076–078. Specification: SD-ARCH-3.0 §§12, 15 (T14/T15), 16.

Built on merged D3-01–D3-10 at `a0846b5784a44bde3a8b9a6b172600a1a98259c3`. No code, private evidence or operational changes from draft REAL-001 PR #12 are dependencies. No strategy, model, recommendation, paper admission or operating-system service is activated.

## Registry and execution

`discovery.experiments` freezes an ID, hypothesis, horizon, mode, eligible universe and its version/hash, chronological windows, input snapshots, label endpoints, event/document groups, candidate selection, strategy/model/retrieval/prompt/policy/cost/risk hashes, primary metrics, stopping rule and trial budget. Retrieval hashes cover both ranking and embedding references. Model knowledge contamination disclosure is mandatory. Q+ML is rejected until separately authorized.

`experiment_trials`, `experiment_events` and `experiment_results` append trial requests, access decisions, failures and results. PostgreSQL rejects UPDATE, DELETE and TRUNCATE. Retrying an identical experiment/trial ID returns the existing record; changing its body conflicts. Results include their evaluator source hash, original artifact hashes and exact paper-ledger event hashes. Each completed result is immutable, including missing or negative findings. New outcome revisions require a new trial and remain separate; they do not silently update an earlier scorecard.

The execution path reuses existing D3-09 publication runs, their worker/scheduler and the D3-05 quantitative reproduction function; it does not create another scheduler or call models. Q is `quant`, Q+R is `quant_rag`, Q+A is `quant_agent`. The three existing arms must all be present in every registration and trial. D3-10 supplies immutable order, observation and ledger records. Governance reads a specified ledger sequence, never “latest”. Evaluations are bounded reads of already published artifacts, not synchronous scans or inference jobs.

Paired trials require identical candidate/snapshot sets and cost/risk/selection assumptions. End-to-end trials expose candidate-set differences and failure counts alongside descriptive deltas against Q. Differences in selection are not attributed to improved research judgment. The complete set of published decisions in the registered universe/window must be represented; omitting a failed decision or its sample is rejected. Explicit purge exclusions remain visible.

## Leakage and access controls

- Train precedes validation, which precedes the untouched test window. Forward windows follow test and must be registered before they start.
- Label overlap and boundary embargo purge earlier samples. Embargo cannot be less than the maximum actual registered label span. Labels extending outside a historical split are excluded, not prematurely matured.
- Declared related groups, duplicate frozen input hashes and revision references cannot cross accepted splits. Duplicate sample observations cannot inflate denominators. Preprocessing is restricted to training.
- Stored revisions, original publication/availability clocks, contract snapshots, retrieved documents and financial period endpoints are checked against the decision cutoff. A later restatement cannot replace an earlier filing. Existing source-rights checks still apply, including when reading cached results or the dashboard.
- A PostgreSQL advisory lock serializes trial registration. Test access is reserved and committed before reading outcomes. Crashes leave the reservation consumed; an identical retry can finish that same trial. A new trial, renamed experiment, changed hashes or relabeling the old test period as validation cannot create independent evidence. Any earlier registered access overlapping the test universe/window prevents calling it untouched. The selection must reference a completed validation trial.
- These controls govern accesses through this registry. They cannot erase human/model knowledge or police direct owner SQL and preexisting exports. Historical AI results are explicitly exploratory; synthetic results are software evidence only.

Forward cohorts preregister their universe, strategy and window before data arrives. A forward trial then freezes `forward_samples` (observed input hashes and their label endpoints) and the original decisions. Cutoffs and decision generation must follow experiment registration; the configured embargo must still cover their actual label spans. A retrospective window cannot be renamed forward. On merged main, genuine qualified forward observations remain blocked by D3-10 admission and source/policy approvals. The new contracts do not relax those gates.

## Outcomes and metrics

The adapters preserve all actions, research failures, abstentions, no picks, no entries, ambiguous outcomes, missing outcomes and maturity states. A missing/failed research run is distinct from a completed run with no BUY picks. Published-decision, researched-candidate, admitted, resolved-trade, forecast-maturity and missing-outcome denominators remain separate.

D3-10 computes resolved-trade win rate, net expectancy, average trade return and profit factor. Recorded research accounting supplies cost and latency; missing accounting is unavailable, never assumed zero. Cost per researched candidate and admitted decision retains its own denominator. An arm-specific pinned chronological ledger supplies flow-neutral full-capital return, drawdown, fees, slippage, turnover, exposure and issuer concentration via the existing evaluation arithmetic. A portfolio containing other decisions cannot stand in for an arm's portfolio. Missing/stale/ambiguous position marks block valuation.

The four-action outcome contract does not establish a common directional forecast or barrier-ordering label; direction, target attainment and target-before-stop quality therefore remain explicitly unavailable rather than inferred from trade wins. Long-horizon forecasts remain provisional until their own endpoints. Interim portfolio marks do not mature a five-year strategy.

Permitted comparable market benchmarks, exposure-matched benchmark series, qualified cost-stress observations and a preregistered resampling design are not supplied by merged main. Their metrics remain unavailable with reasons. Cash is a zero-return comparator only when a comparable chronological portfolio interval exists. Descriptive challenger-minus-Q deltas retain both sample counts and do not claim causal improvement. Risk-adjusted return and dependence-aware uncertainty are explicitly unavailable; daily overlapping samples are not treated as independent evidence.

## Promotion and rollback

All EP-1 proposals remain **unratified**. No numeric promotion threshold is invented. Missing sample, maturity, coverage, forward duration, cost stress, drawdown or benchmark requirements fail closed. The report evaluates available test counts, maturity, coverage and drawdown against supplied bounds, while separately blocking unsupported prospective/benchmark/uncertainty requirements.

Software correctness, research quality, operational release and investment-strategy approval remain independent. Client-provided approval references cannot self-approve a strategy. `request_promotion` records the denied gate result; it never activates a strategy. Genuine approved prospective tracking is an external prerequisite, not demonstrated by fixtures.

Pause blocks future trials immediately. Rollback names an existing same-horizon registered target and blocks future trials on the old experiment. Runs on the target use its frozen manifest. Prior trials, outcomes and hashes remain unchanged. There is no deployment, automatic retraining, broker execution or live policy switch.

## Local API runbook

Use the existing owner authentication and same-origin controls. OpenAPI exposes the complete `Experiment` and `Trial` schemas. The illustrative `frontend/tests/fixtures/governance.json` contains **no observations** and is browser-test plumbing only.

1. Before observing outcomes, POST a manifest to `/v1/experiments`, with `Idempotency-Key` equal to `experiment_id`.
2. Execute the existing publication worker/scheduler path (`POST /v1/discovery-runs` on main produces explicitly fictional research). Register the frozen version hashes and samples from the intended input/strategy configuration; mismatching actual artifact versions fail evaluation. Do not infer historic registration from a later manifest.
3. POST to `/v1/experiments/{id}/trials`, with `Idempotency-Key` equal to `trial_id`. Supply all three arms, the original publication run and complete decision IDs, plus optional `portfolio_id`/`ledger_sequence`. Supply an outcome knowledge cutoff. Test requires `selected_validation_trial`.
4. POST `/v1/experiments/{id}/trials/{trial_id}/evaluate` using the same trial ID as key. A crash can retry this trial; validation failures are sealed and require a separately recorded trial. Never obtain a fresh independent holdout by retrying with another ID.
5. GET `/v1/experiments` (stable `limit`/`cursor` pagination) and `/v1/experiments/{id}`, or open **Scorecard → Experiment governance**. Inspect arms, unavailable results, promotion blockers and immutable history.
6. POST `/v1/experiments/{id}/controls` with a unique `Idempotency-Key` and `{action, reason, target}`. Actions are `pause`, `rollback` and `request_promotion`; only rollback requires a target. Reusing the key with another body conflicts.

Keep source artifacts in their existing rights-aware storage. Governance stores hashes, references and aggregate results, not copied filing text. Current revocation hides stored results. Original recommendation/outcome contracts and historical fixtures are unchanged.

## Acceptance evidence

The local acceptance record is in `docs/D3-11-ACCEPTANCE.md`. Genuine PostgreSQL/browser/worker execution is distinguished from the explicitly synthetic market/model inputs used to exercise it. These tests establish software behavior, not financial performance or calibrated AI research quality. No model downloads, paid calls, private REAL-001 evidence, strategy approvals or PR #12 changes are required.
