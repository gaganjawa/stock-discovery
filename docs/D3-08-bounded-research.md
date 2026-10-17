# D3-08 — Bounded research agent and semantic judge

Tickets: **STK-052/070/071/072**. Baseline: PR #7 merge `d7f3381`.
Authority: [SD ARCH 3.0](SD-ARCH-3.0.md), sections 10.2–10.4.

## Delivered software

`agent_storage.run_investigation` starts with the same D3-07 query, retrieval policy and eligible bundle as fixed RAG. It reserves budget using the existing account/day/month ledger before retrieval or model work. A typed controller permits at most **four read-only tool calls**, including failed calls, followed by one final assessment; there are at most five agent responses and one judge response. Defaults retain a 120-second total deadline. No repairs or recursive investigations run.

The only tools are:

- `retrieve`: bounded existing PostgreSQL lexical/local semantic retrieval; the controller pins issuer, listing, horizon, mode, financial period/scope and cutoff. Category requests may broaden coverage, never remove original requirements. Evidence is merged without silently dropping contradictions.
- `inspect_conflicts`: returns compatible conflicting facts already in the authorized context.
- `calculate_ratio`: calls D3-07 Decimal arithmetic on existing fact IDs; validates period/scope/unit compatibility and records formula, inputs, locators and result. The generated financial fact can be cited and checked deterministically.

PostgreSQL `SET TRANSACTION READ ONLY` enforces the tool boundary. The model receives JSON, never a connection, SQL, shell, browser, broker or orchestration capability. `rag_retrieval.retrieve(persist=False)` is the additive read-only entry point; default D3-07 behavior remains unchanged. Only the orchestrator persists manifests after permission checks.

`agent_research.investigate` reuses the strict D3-07 assessment schema and deterministic validator. Fabricated citations, wrong locators, altered financial values/units/periods and omitted missing/conflicting evidence stop processing before the judge. Source permissions are checked around each step, including cached reads; future evidence remains ineligible. Calculation outputs come from approved deterministic tools, not model arithmetic. Document instructions are untrusted evidence.

The separate provider-neutral judge receives the assessment **and its eligible source bundle**, with a versioned rubric covering claim support, contradictions, negative evidence, completeness, causal support and abstention. Its response contains bounded categorical findings and source IDs: it has no price, size, return probability or trading-action fields. Every claim must receive exactly one judgment with valid evidence references. A judge disagreement, uncertainty or invalid response produces abstention; it cannot override deterministic failure. Separate configuration does not establish independent model errors.

All outcomes stay **shadow/non-actionable**, with paper admission blocked. The rubric's human calibration gate is explicitly unconfigured and cannot be switched on through model output. No actionable BUY or profitability inference is introduced.

## Bounds and immutable records

Each model request/response, tool result, merged evidence set and embedding operation is bounded by bytes, rows, available units and remaining deadline. Token accounting uses the D3-07 conservative UTF-8 byte upper bound, not a claimed real-provider tokenizer. The shared durable reservation covers retrieval embeddings, planning, final research and judgment. Every installed adapter is local and zero-cost; nonlocal or nonzero-cost providers are rejected before reservation.

POSIX main-thread timers interrupt local operations; late results are rejected. Installed adapters are trusted code and must not suppress timeout exceptions. Failed tools count before dispatch. Ambiguous failures retain the reservation and never trigger an automatic retry. No automatic budget refund exists.

Migration **0009** adds immutable `discovery.agent_results` linked to D3-07 reservations and baseline/final bundle hashes. Records include tool traces and evidence IDs, validator and judge reports, missing/conflicting evidence, model/prompt/rubric/policy versions, usage and latency. Permissions revoked mid-run suppress the assessment and retain only safe trace metadata. Cached results require identical run configuration, current rights and unchanged eligible revisions. No application database or runtime grants were changed.

## Comparative evaluation

[Labels](evaluation/d3-08/labels.json) contain **54 provisional synthetic cases** across three horizons, nine scenarios and two disjoint synthetic issuer/document-family/time splits. They include support, invented citations, contradictory filings, stale evidence, incorrect financial values, missing negative evidence, prompt injection, insufficient information and unsupported causal inference. Source documents, content hashes and exact locators are generated through D3-06 extraction. Reviewer labels/adjudication are intentionally empty: these are **not human-labelled calibration data**.

[Measured mock results](evaluation/d3-08/mock-results.json) compare the D3-07 early-abstention/single-response validator path with the bounded controller plus conservative mock judge. Both start from identical bundles and injected response defects. The fixture tools do not discover new market evidence. Results include claim classification coverage, support accuracy, material-error false acceptance with a Wilson interval, negative-evidence detection, abstention quality, false rejection, requirement coverage, observed controller latency, usage and zero actual model cost.

In this run, material-error shadow acceptance was **6/18** for fixed RAG and **0/18** for agent plus mock judge. The six cases are deliberately injected unsupported inferences; the mock judge rejects inference by construction. This demonstrates the additional abstention gate, **not agent superiority, actual LLM accuracy or calibrated reliability**. Zero errors in 18 cases still has a roughly 17.6% upper Wilson bound; template cases are not independent market samples. All research remains non-actionable in both arms. Claim-support accuracy is reported only for classified emitted claims, alongside classification coverage, so abstention cannot masquerade as comprehensive claim checking.

Reproduce offline from the repository:

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python scripts/evaluate_d3_08.py --output-dir /tmp/d3-08-evaluation
```

Semantic results are deterministic under the frozen mocks; measured latency varies by run. The report records dataset, model, prompt, rubric and policy identities. No API key is read and no external request is made.

## Remaining gates and boundaries

Human-reviewed development/holdout labels, reviewer disagreements/adjudication, preapproved calibration thresholds, independent real-model evaluation, source rights and model/provider qualification remain blockers to actionable AI. Existing restricted-runtime database permissions remain unresolved. D3-09 publication/UI integration is not implemented here. Synthetic and legacy workflows and historical evaluation fixtures are preserved. No paid service, live-market activation, broker action, infrastructure purchase or deployment occurred. Stop after the review PR; await owner merge and confirmation before D3-09.

Validation on 17 October 2026: 465 application/worker tests (42 new; 116 database cases), 7 script tests, migration lifecycle, legacy contract examples, paired dataset/hash checks and whitespace checks passed from an isolated staged snapshot. One existing Starlette/AnyIO deprecation warning remains.
