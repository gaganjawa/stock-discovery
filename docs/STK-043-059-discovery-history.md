# STK-043/059 — Discovery to saved evidence

2 November 2026 (IST). Synthetic software acceptance; no real-data approval.

## User workflow

Dashboard → Discovery → Inspect company → citations/source inspection → **Open
saved historical evidence**. Publication history contains only the same stored
listing, horizon, arm and mode. **Inspect frozen recommendation** opens the actual
immutable publication through the existing recommendation API, retaining its ID,
information cutoff, generated timestamp, versions, evidence and original terms.
Opening an older record does not claim fresh market eligibility.

The saved panel lists actual portfolio/ledger references without fills, returns or
outcome status. **Reveal recorded outcome** reads that exact sequence and hash from
the existing outcome API. The observation and knowledge cutoffs, forecast maturity,
execution result, costs and recommendation-specific audit history are separate from
decision-time research. Later ledger appends cannot replace an already pinned read.
Audit payloads are recommendation excerpts; their event hashes identify the original
whole immutable ledger events, not hashes recomputed from the filtered excerpt.

An existing trial's explicit recommendation IDs supply a **View registered
evaluation** link into Scorecard. The exact experiment is preselected; the user must
request its source-authorized registered fold report. This does not register,
evaluate, reserve or open a holdout. Registration alone does not establish valid
performance or completed evaluation.

No matching outcome/trial produces an explicit unavailable state. No legacy Replay
Dataset association is inferred from symbols or dates: `SYN-D309-*` publication
identities remain distinct from `SYN-ALPHA/BETA/GAMMA`. This is a connected existing
publication/ledger/registry journey, not a relabelled legacy replay experiment.

## API and authorization

- `GET /v1/recommendations/{id}/history?before=…&limit=…` extends the existing
  authenticated recommendation resource. Stable cutoff/ID pagination is scoped to
  the selected listing/horizon/arm/mode; limits are 1–50 publications, 20 portfolio
  references and 50 trial references. Excess relationship counts fail explicitly.
- `GET /v1/paper-portfolio/{portfolio}/outcomes/{id}?sequence=N&expected_hash=…`
  adds an optional immutable reference to the existing outcome API. Both parameters
  are required together. The previous unpinned API remains compatible. An unknown
  sequence, foreign decision or mismatched hash never falls back to latest state.
- New reads use no-store, authenticated access and sanitized errors. Ordinary SQL
  transactions hold grant-fence and synthetic source-control locks through response
  assembly. Existing live readers enforce original acquisition/current permissions;
  synthetic original permission snapshots also receive current rights/fence checks.
  A final pass refreshes earlier rights after later dependencies have been locked.
- Mixed portfolios reauthorize every dependency before exposing a pinned result.
  Restriction or unverifiable lineage denies the entire response. Denied UI requests
  clear related research, citations, comparisons and outcomes; selection/unmount
  aborts pending saved-record requests.

All navigation calls are reads. No schema, historical evaluator, strategy, model,
grant recovery or policy is changed. No inference, outcome processing, publication,
portfolio admission or budget reset is invoked to populate this view. Synthetic
acceptance setup explicitly creates fictional publications/observations/registrations
before read-only navigation and measures that navigation performs zero POSTs.

## Validation and remaining acceptance

PostgreSQL/API cases exercise identity/pagination, no unrelated fixture mapping,
missing references, immutable pinned reopening after later appends, foreign/missing
references, source/grant restrictions, mixed dependencies, expiry, lock serialization,
final rights refresh, sanitized SQL errors, connection recovery and unchanged receipts.
The browser follows ranking → citations → saved record → recorded outcome → prior
record with no outcome → matching registration → pending fold report, then denies a
cached reveal and verifies related content is removed. It opens no protected test.

Exact fresh counts and CI belong in the checkpoint and PR. P3: bounded selections
still perform repeated authorization work; large ledger/query latency needs measured
optimization if it becomes a product bottleneck. No general performance claim.

M1 permitted NSE raw prices, rights/retention and complete point-in-time coverage;
M2 independent human/50-case labels/protocol; genuine strategy/benchmark/forward
evidence; policy, operational/publication, paper admission and trading acceptance
remain blocked. The minimal external checklist is in
[the acceptance handoff](PRODUCT-ACCEPTANCE-HANDOFF.md). No model/provider experiment
or invented benchmark was needed for this software workflow.
