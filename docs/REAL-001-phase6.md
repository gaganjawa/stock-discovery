# REAL-001 Phase 6 — grounded research reliability and publication readiness

**Status: PARTIAL.** This phase preserves the real-data and publication gates. It
does not qualify a financial model, approve a policy, publish a recommendation,
or create a prospective reference. Continue draft PR #12; stop before D3-11–13.

## Citation and request reliability

The Phase 5 rejection code was `citation membership/locator`. The deterministic
validator required both a known `evidence_id` and equality of the complete model
citation with the citation stored in the retrieved bundle. Equality includes the
revision, source locator, URL, attribution and excerpt. The Phase 1.3 prompt asked
the model to reproduce these full objects. A regenerated or altered field fails
closed. The rejected model responses were intentionally not persisted, so the
three historical runs do not establish which individual field differed; no
field-level explanation is inferred.

Phase 6 changes the model-facing response to cite only bundle `evidence_id` values
and structured `fact_id` values. The service resolves those identifiers to the
exact immutable bundle objects before running the existing deterministic
validator. Unknown IDs, missing fact references, wrong fact citations, altered
financial wording, unsupported quotes, numeric inferences, omitted conflicts,
and non-abstaining incomplete assessments still fail. This changes serialization,
not evidence or acceptance criteria.

The Ollama adapter now sends the response schema as Ollama's structured-output
grammar rather than repeating its full JSON Schema inside the text prompt. The
whole request remains byte-bounded; context reservation is checked against the
actual model prompt and output allowance. No truncation, fallback or validation
relaxation is introduced. The opt-in evidence runner's default document bound is
three, sufficient to include the three existing numerical statement snapshots;
all rights and age filters still apply.

## Genuine evidence and known limitations

The private acceptance database contains the previously observed INFY series,
three numerical statement snapshots and 24 facts across four annual periods.
Only these persisted records and the existing active Upstox grant are used for
Phase 6 research. The grant is copied only to a short-lived, owner-local file for
the rights-aware reader and removed after execution. No new permission is created.

The original filing publication timestamps are unknown. Observation timestamps
are not substituted as filing dates. Cash-flow line items do not reconcile to the
observed cash-balance movement; no balancing item is inferred. Debt, total
equity, EPS units, capex, diluted shares and period-aligned valuation inputs are
missing or unverified. The ratios endpoint is not joined because its reporting
and valuation as-of basis is unverified. No actual issuer PDF, news text, or
official announcement coverage is available. Adjusted prices remain
descriptive-only; action, volume and point-in-time qualifications remain open.

These conditions keep the evidence-quality and quantitative gates closed. They
must remain explicit in the private research view and cannot be converted to zero,
no-news, or a favorable interpretation.

## Phase 6 actual local Ollama execution

The three prior Phase 5 v1.3 broader outputs are not retained, so their specific
altered citation field cannot be reconstructed. The code establishes the exact
failure boundary described above. Phase 6 also found and corrected two execution
configuration issues before a final inference: the query runner's two-document
default excluded the third existing statement snapshot, and its context check
counted the JSON schema as prompt text even though Ollama receives that schema
separately as a constrained-output grammar. Those rejected setup attempts remain
in the private database; no model request was made for them.

Using the existing permitted INFY bundle and all three stored statement snapshots,
the final local run called `nomic-embed-text:latest` and
`qwen2.5-coder:7b` once for each horizon. All three returned `completed` with
deterministic validation `passed`, semantic validation `not_evaluated`, judge
`not_implemented`, and action `INSUFFICIENT_EVIDENCE`. Each response contained
zero claims. Thus no citation-bearing model claim was accepted or silently
rewritten; source citations remain canonical in the evidence bundle. Ollama
reported 3,890–3,891 prompt-evaluation units and 66–67 generated units per run;
observed generation wall time was approximately 13–17 seconds per horizon.
Embedding requests reported 861 input units each. Model and embedding usage
reported zero cost.

An intermediate v1.4 attempt exposed a separate response-contract mismatch: the
model did not reproduce the bundle's missing/contradiction arrays exactly. These
fields are now service-owned and inserted unchanged into the internal assessment;
the model cannot alter them. This did not produce a recommendation: all final
responses still abstained. All rerun and rejected manifests remain in the private
database. Public evidence deliberately omits output text, financial values,
citations' source payloads and grant contents.

## Versioned policy proposals — not approved

Each proposal below uses policy schema 2.0.0 and proposal version `1.0.0`. Its
status is **unconfigured**, with `approval_ref = null`; the version label is not
an approval. Required values are intentionally unset until owner review and
evidence qualification. No synthetic fixture or prior illustrative risk value is
carried into a real policy.

| Proposed policy | Scope and required configuration | Blocking evidence / decision |
|---|---|---|
| `REAL-001-SWING-1.0.0-PROPOSED` | `duration`, `entry_sessions`, `max_price_age_days`, `max_evidence_age_days`, `forecast_sessions` | Real closed-bar action basis, volume semantics, instrument tick/lot and forecast/execution rules |
| `REAL-001-SHORT-TERM-1.0.0-PROPOSED` | Shared freshness/duration fields plus `report_months`, `max_statement_age_days`, `min_revenue_growth`, `min_earnings_growth`, `min_price_to_sma`, `bear_pe`, `base_pe`, `bull_pe`, `min_margin_of_safety` | Verified EPS/shares and valuation date, current results, comparable periods, price confirmation and approved thresholds |
| `REAL-001-LONG-TERM-1.0.0-PROPOSED` | Short-term fundamental fields plus `min_ocf_margin`, `min_roe`, `max_net_debt_to_ocf`, `durability_years`, `min_fcf_yield` | Cash-flow reconciliation, debt/equity/shares, multi-year quality, business/governance evidence and valuation inputs |
| `REAL-001-HORIZON-1.0.0-PROPOSED` | Exact holding duration, entry window, review cadence and calendar endpoint per profile | Complete observed exchange calendar and owner-approved intended holding choices |
| `REAL-001-RESEARCH-1.0.0-PROPOSED` | Source allowlist, per-horizon required-evidence coverage, blocking-missing rules, contradiction rules, supported-claim threshold, independent judge/rubric and model/prompt hashes | Current human-reviewed, issuer/time-separated calibration and holdout; thresholds frozen before evaluation |
| `REAL-001-RISK-1.0.0-PROPOSED` | Eligibility and instrument-risk gates; `admission_enabled = false`; explicit shadow-only scope | Risk inputs and approved policy version. Capital sizing is not needed to display non-actionable evidence, but unknown risk must block any BUY or paper admission |
| `REAL-001-COST-1.0.0-PROPOSED` | Local zero-cost research execution; no orders or paper fills | Separate owner-approved cost/slippage assumptions before any execution modeling |
| `REAL-001-RETRIEVAL-1.0.0-PROPOSED` | Bounded source/document/chunk/byte limits, freshness and event allocation | D3-07 retrieval limits do not imply evidence completeness or semantic quality |
| `REAL-001-SCHEDULE-1.0.0-PROPOSED` | Explicitly disabled until research, publication and observation stages pass | No unattended live acceptance or runtime activation |
| `REAL-001-UNIVERSE-1.0.0-PROPOSED` | Single configured listing only; no broad-market coverage claim | Approved membership, liquidity and coverage criteria |

Research-only publication is not a permission to publish ungrounded output.
Minimum gates are: valid use-specific rights for every cited revision; a coherent,
immutable as-of snapshot; complete, period/scope/unit-checked and locatable facts;
source timestamp uncertainty and unresolved discrepancies shown; deterministic
citation/fact/claim checks passed; an independently reviewed semantic-quality
gate for claims; an approved, effective policy manifest for the selected horizon;
known eligibility and instrument-risk status; actual publication time after the
cutoff; full provenance and policy/model/prompt hashes; immutable shadow status;
and paper admission explicitly blocked. The research judge cannot replace
deterministic checks. No policy or judge threshold is active until approved and
qualified.

## Publication and prospective tracking

No Phase 6 policy is approved, no independent semantic qualification or human
holdout is available, and the quantitative engines still return
`INSUFFICIENT_EVIDENCE` for all three horizons. The cash-flow and financial-field
gaps also remain unresolved. Therefore D3-09 must not publish an assessment and
D3-10 must not register a prospective reference. Existing real publication,
source-rights, shadow-only and paper-admission safeguards remain unchanged.

The existing Real Research view identifies research quality and retrieved source
locators separately from immutable publications, lists the exact known publication
blockers, and labels unknown publication dates and unresolved financial inputs.
Failed or unqualified runs are history, not published recommendations.

Actual model executions, citations, and measured results are recorded below only
as non-content operational metadata after Phase 6 reruns. Provider payloads,
financial values, full model output, grant contents and screenshots remain in
the owner's private database.

## Validation and delivery

On the isolated REAL-001 branch, focused research tests passed (44); the full
backend/worker regression passed (622). PostgreSQL integration and migration
lifecycle validation passed (164 integration tests, zero skips), including
upgrade/repeat-upgrade, downgrade/re-upgrade and atomic migration-failure
rollback. Contract, evaluation and capital-risk validators passed; all 10 script
unit tests passed. The frontend TypeScript/production build passed, and all five
Playwright browser workflows passed when run with the local synthetic worker.
The earlier browser attempt without a worker left jobs queued; no product defect
was inferred from that environment setup failure. The genuine Ollama execution
and zero-cost usage are reported separately above. CI was green on the original
PR head before these changes; the updated branch requires its new PR checks.
