# STK-041/042 — Registered fold result reporting

2 November 2026 (IST). M3 / D3-10–11 integration; no new evaluation framework.

In **Scorecard → Experiment governance → Registered fold results**, select up to
10 existing experiments and read their registered trials. The existing resource
adds `GET /v1/experiments/fold-results?experiment_id=…` (repeat the parameter for
multiple experiments). Authentication and no-store conventions are preserved.
At most 100 trials are read; an oversized selection fails explicitly rather than
silently dropping failures or distorting denominators. Narrow the selection.

## Evidence and identity

`fold_reporting.py` reads only existing experiment manifests, trial registrations,
sealed D3-11 results, audit receipts and pinned D3-10 ledger revisions. It never
calls `begin_trial`, `evaluate`, a provider, model, admission or publication path.
The API accepts IDs only, not caller-supplied observations or claimed performance.

Manifest/request/result hashes and experiment/trial identities must agree. The
stored split audit must reproduce through the existing `split_samples` contract.
A completed result needs its immutable evaluation receipt, original artifact
hashes, matching registered samples/input/configuration hashes, label bounds and
financial observation cutoffs. Test trials must retain their existing holdout
reservation and selected completed validation trial. Forward samples must follow
registration and fit their registered window/embargo. No new threshold is added.

Fold identity binds manifest and request hashes and stays fixed when an existing
pending trial acquires its sealed result. Result hash remains a separate reference.
The report hash changes when selected immutable evidence changes; no prior record
is overwritten. Failed and registered-but-unevaluated trials remain visible with
no fabricated metrics. Unregistered phases are labelled as such, not empty results.

## Current authorization and temporal checks

Reads reauthorize cached artifact/ledger lineage through existing readers and
validate original acquisition grants for declared and researched revision
dependencies, including instrument parents. Rights, current identity and durable
fences are checked at fresh database time after locking. Synthetic publication
source-control rows are share-locked through the report transaction. A final pass
rechecks validity after all potentially blocking dependencies; expiry while waiting
cannot silently release an earlier grant's metrics.

Pinned portfolio/sequence/hash/policy references must match the registered request.
Every included ledger revision's event, as-of and availability clocks must be at
or before the registered outcome cutoff. Later ledger appends do not change the
reported result. Current restrictions still deny an old sealed result. A denied
selection exposes no partial report; other authorized selections remain usable.
Errors are sanitized and transaction failures roll back/release locks. “Read-only”
means no data/trial/budget mutation; ordinary PostgreSQL transactions are necessary
for `FOR SHARE` fencing, so the connection is not marked SQL `READ ONLY`.

## Results and aggregation

The screen displays development, validation, protected test and forward separately:
registration/evaluation/knowledge clocks; declared and actual ledger windows;
samples, missing observations, provisional forecasts, research failures; original
returns/drawdown, costs, benchmark availability and version references. It preserves
the distinction between completed no-pick scans and unavailable research/runs.

Groups require matching phase, horizon, mode, comparison, universe, arm-specific
configuration, evaluator and ledger-policy hashes. Repeated samples/decisions or
overlapping label windows invalidate aggregation. Incomplete folds stay visible
and cannot supply aggregate performance. Disjoint eligible trade observations reuse
`paper_reporting.cohort_metrics`; counts and denominators are explicit. Separate
capital histories are never summed/compounded: pooled return/drawdown stay
unavailable without a continuous registered ledger. A registered benchmark reference
is not a benchmark observation; absent comparable sealed observations stay null.

Technical, RAG and agent arms are never pooled. Synthetic/exploratory trade statistics
are not independent AI quality evidence. Eligible qualified AI pairs remain zero and
AI performance unavailable under current M1/M2 gates. The view does not certify
holdout independence or turn the legacy synthetic split into untouched walk-forward
acceptance. Existing registry controls remain authoritative; owner SQL/exports and
human knowledge cannot be undone by a report.

## Validation and limits

Adversarial cases cover pending/sealed identity, no implicit holdout evaluation,
failed trials, frozen strategy mismatch, forged result/receipt consistency, late
financial revisions, future outcomes, missing/immature observations, source and
grant fencing, concurrent restriction, final validity recheck, database failure and
connection recovery, deterministic selection, bounds and honest aggregation.
The existing governance browser workflow reads actual registered synthetic records,
checks a pending protected test remains unevaluated and verifies denied reads clear
both fold and cached experiment details. No new market/model experiment is run.

P3: authorization/lineage work can be expensive for large selections; limits bound
input size but are not a full-universe latency guarantee. Exact measured tests and
CI belong in the checkpoint/PR. M1/M2, EP-1, real benchmark/forward acceptance,
publication, paper admission and trading remain blocked. See
[the remaining product acceptance handoff](PRODUCT-ACCEPTANCE-HANDOFF.md).
