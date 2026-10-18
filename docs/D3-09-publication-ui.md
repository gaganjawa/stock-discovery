# D3-09 — Three-horizon recommendation pipeline and UI

STK-033/054/058/059 · baseline `b7e1be1` (D3-08 and PR #9 merged).

## Implemented boundary

The authenticated Dashboard now includes Swing (2–10 sessions), Short-term (1–3 months), and Long-term (1–5 years), with separate quantitative, fixed-RAG and bounded-agent cohorts. A queued run automatically ingests fictional source documents through D3-06, assesses all five declared fictional listings with D3-05, runs D3-07/D3-08 local mock research, validates the strict D3-01 v2 contract and frozen reference bundle, and atomically publishes all fifteen cohort records. Confirmed cutoff-known earnings events from the ingestion layer are retained as candidate-origin references; event-nominated candidates receive the same quantitative/risk gates. Rankings use action tier, quantitative readiness, a fixed zero AI component and stable listing ID. No AI scoring weight is activated.

The universe deliberately exercises ready, waiting, instrument-risk, missing-filing and conflicting-fact cases. Every cohort uses the same listing/horizon/cutoff and quant baseline. Fixture policy values and the 20% fundamental stop geometry are arbitrary software acceptance settings, not approved investment parameters. Valuation scenarios are displayed separately from swing trading targets.

Required missing/invalid inputs or unavailable research take precedence over adverse evidence, which takes precedence over pending conditions and BUY. Known adverse facts remain visible even when the overall action is INSUFFICIENT_EVIDENCE. AI cannot promote a quantitative WATCH, bypass an instrument prohibition, change numeric inputs or assign quantity. The current mock providers conservatively return WATCH; a quant BUY can therefore disagree with the researched cohorts. Unverified model assertions do not manufacture verified adverse facts. Every publication remains MOCK / SHADOW / NON-ACTIONABLE with blocked admission and null quantity. Capacity/admission is separate from the research action; D3-10 capital reservations and execution are not implemented here.

Fixed RAG gets the same separate local semantic judge/rubric as the bounded agent, without adding tools to its fixed-bundle mode. The judge charge shares the existing reserved per-run budget and appears in the publication artifact. Failed/budget-exhausted research never inherits the successful quant label. No remote models, API keys, managed vector service or broker adapter are used.

## Local use

Start the existing local stack with `python3 scripts/local.py start`. After sign-in, use **Dashboard → Three-horizon discovery → Run fictional discovery**. The existing PostgreSQL worker processes the request; the UI polls run status. Select a research mode, inspect a company, compare all modes, and inspect stored source citations. The original synthetic history, replay, charts, explanations, scorecard and portfolio pages remain available below/alongside discovery.

Runs are explicitly requested; this UI does not claim a currently active exchange schedule or live coverage. The shown observation cutoff is the fixture's historical clock, while publication time is the actual run time. Future calendar sessions are pinned preannounced fixture plans, not observations. Future price bars and filings are excluded from published input manifests. A failed run leaves the preceding complete publication visible with its original age; partial evidence, no published batch, unavailable sources, unavailable research and worker failure have distinct states. Next run is explicitly “on request.”

## Additive API

All `/v1` routes require the existing owner session or bearer authentication; cookie writes retain origin checks. Legacy `/api/v1` contracts remain unchanged. Only the pinned synthetic scope is installed; attempts to select live-market mode are rejected.

| Route | Behavior |
|---|---|
| `POST /v1/discovery-runs` | `{ "horizon": "swing" }`, `Idempotency-Key` required; 202 with run/status URL |
| `GET /v1/runs/{id}` | Queued/running/completed/failed stage, safe error code and timestamps |
| `GET /v1/discovery?horizon=&cohort=&mode=` | Latest published batch, last run, reconciled universe coverage and decisions |
| `GET /v1/recommendations` | Same filtered list; stable cursor and immutable `batch_id` pin subsequent pages |
| `GET /v1/recommendations/{id}` | Immutable recommendation, inputs, quantitative calculations, research, versions and permissions |
| `GET /v1/recommendations/{id}/comparisons` | Same-run, same-listing three-mode comparison |
| `GET /v1/recommendations/{id}/evidence` | Frozen quantitative evidence, research citations and permission manifests |
| `GET /v1/evidence/{revision}?recommendation_id=` | Source content only when referenced by that recommendation and still permitted |
| `GET /v1/coverage?horizon=&cohort=` | Batch coverage and latest execution state |

Duplicate keys with identical normalized requests return the same run. Changed request/code identity returns 409. Reads check current source controls and D3-06 permissions, including for cached detail, comparisons and source text; a revoked source returns 403 without content. The frontend clears already-visible detail on a denial. Permission manifests describe the frozen decision and never substitute for current authorization.

## Storage, recovery and reproducibility

Migration `0010` adds publication requests, batches, recommendations, source controls and an internal outbox. It does not alter legacy decisions or runtime role grants. One session advisory lock serializes the publication worker; each claim has a fencing token. Batch records, recommendations and the internal notification event commit together. Immutable triggers reject updates/deletes; request identity cannot be edited. Interrupted running requests fail closed and do not automatically retry ambiguous research calls. A separately keyed run is required for recovery. No external notifications are sent.

Each artifact records the v2 recommendation, complete strict contract bundle, cutoff-eligible input manifest, policy manifest, D3-05 calculations, research result and judge/model/prompt/rubric versions, source permissions, citations, deterministic risk context, explanation and publication status. `publication.reproduce_quant(artifact)` recomputes the quantitative result solely from frozen inputs and verifies exact parity. Research reports and bundles are preserved as artifacts; mock output is not proof of clean historical model knowledge or investment performance.

The source control row for `SYN-D309-source` can be revoked by an authorized database operator. This is a fictional acceptance control, not an API for granting real-source permissions. The final publication transaction locks this control while checking current permissions.

## Validation and remaining gates

Tests cover three horizons/four actions, risk precedence, model disagreement, missing/conflicting/future evidence, reproduction, immutable storage, concurrent duplicate submission, authentication, pinned pagination, cited-source membership, revocation, failed-run preservation and worker-version fences. Playwright covers the new workflow across every horizon and retains the original synthetic replay acceptance. CI requires all integration tests to execute with zero skips and checks upgrade/repeat/downgrade/re-upgrade/atomic migration failure rollback.

Real-source licenses and adapters, approved real quantitative/risk/cost policies, human-reviewed model calibration and restricted-runtime database grants remain unapproved. D3-10 reservations/outcomes and later scorecards/operations are not claimed. No paid call, purchase, external deployment, real-market activation or broker order is part of this delivery. Stop after D3-09; owner review/merge is required.

Local acceptance on 18 October 2026: 493 backend/worker tests, including all 129 PostgreSQL integration tests with zero skips; 10 script tests; migration lifecycle and existing contract validators; production frontend build; both discovery and legacy replay browser scenarios. The dedicated local stack used alternate ports to preserve the existing application stack. GitHub CI is the separate PR merge gate.
