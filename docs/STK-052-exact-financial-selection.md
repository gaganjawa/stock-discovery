# STK-052 / D3-07 M2 — Exact financial selection

PR26 passed all mandatory checks for `b9d48908eef665f7e1416bd8056d41911751b8c6`, including 429 PostgreSQL tests with zero skips and migration upgrade/repeat/downgrade/re-upgrade/atomic rollback. Review of period lists, row counts, explicit abstention, source guards and unchanged verification found no substantiated P1/P2 blocker in its development-only scope. Protected-main requirements remained active. Merge: `54b27deb950322846183671c334bc634bc6b0ec0`.

## Confirmed failure and smallest correction

Saved v3 output selected the correct total-revenue row but **Three months ended March 31, 2024 / 37923** for **Year ended March 31, 2024 / 153670**. V4 selected **Three months ended March 31, 2025 / 40925** for **Year ended March 31, 2025 / 162990**. Source evidence and the existing deterministic parser distinguish these columns unambiguously. The integration unnecessarily delegated an exact lookup to a stochastic cell selector. The model's internal reasoning remains unknown; no new prompt tuning or model calls were performed.

The existing development entry point now defaults to exact row-label/period/scope selection through `table_spans.cell_reference` and the unchanged `verify_cell`. Unknown labels, periods, units, scopes, missing values, duplicated/conflicting rows, ambiguous headers and changed snapshots fail closed. No synonym, nearest year or quarterly substitute is inferred. Source profile, captured-source hash and cutoff checks still run. Expected evaluation labels do not participate in lookup or request identity.

The old model mode remains explicitly selectable; historical experiments and model/prompt identities are unchanged. Existing broader AI research remains available under its existing gates for semantic matching and interpretation; this increment neither implements unreviewed semantic aliases nor claims reasoning quality. A missing/ambiguous exact input does not silently invoke inference or produce a recommendation.

Exact results are deterministic read results. Initially trying to persist them as RAG outputs failed two PostgreSQL tests because the existing schema requires a positive AI reservation. That constraint remains intact: the correction returns the result without database writes and preserves the evaluation in a separate artifact. No schema, zero/fabricated AI reservation or new storage framework was introduced. Prior model receipts/budgets remain unchanged, including under concurrent exact requests.

## Combined development results

| Measurement | Saved v4 model run | New exact route |
| --- | --- | --- |
| Correct positive selection | 1/2 | 2/2 |
| Correct negative abstention | 2/2 model abstention | 2/2 deterministic abstention |
| Wrong-period claims withheld | 1 | No wrong-period proposal generated |
| New model calls / inference reservations | Preserved historical results | 0 / 0 |
| Model selection/abstention accuracy | Historical metrics retained | Unavailable; no model used |

Annual and quarterly values, units, scope and citations are regression-tested together; the four original cases are preserved. `M2-exact-selection-development.json` records the zero-inference replay, repeated-result equality and unchanged reservation accounting. Both 2/2 estimates have Wilson 95% intervals approximately 0.342–1.0. These known developer/parser cases establish narrow software behavior, not independent research accuracy.

Fresh validation: 757 backend/worker tests passed; final combined focused validation 31 passed (21 unit and 10 disposable PostgreSQL), after the two local foreign-key failures described above were corrected. Tests include expected-label tampering, scope/unit/period ambiguity, identical duplicates, source changes, no model calls, no database mutations and concurrent reuse preserving a prior model receipt. Syntax/JSON/whitespace and unchanged-verifier checks passed. Full mandatory exact-commit CI is required for delivery.

## Human gate and fixed roadmap

`M2-exact-human-review-supplement.json` points to the existing source/reviewer worksheet and new results. `M2-UNSEEN-EVALUATION-HANDOFF.md` and `M2-unseen-50-case-reviewer-template.json` prepare the independent process. The template has 50 **blank slots**, zero supplied sources/labels and zero evaluated cases. No reviewer was invented, no labels self-certified, no original experiment altered, and the original ten-case development packet and empty holdout registration remain unchanged.

**M2 quality acceptance: BLOCKED.** Independent source/entity/period/unit/citation review, approval of the existing proposed protocol, 50 unseen human-verified cases, a frozen reference/configuration and held-out evaluation remain unavailable. Real-source rights/PIT qualification is still blocked. The deterministic development criterion passes; AI semantic/interpretive quality is not established by it. No live recommendations, publication, paper admission or trading are activated.

Next: independent review/CI of this exact route, then the human custodian completes source review and supplies the unseen evaluation according to the existing protocol. Quantitative validation, combined AI/technical research, historical replay, complete dashboard and product acceptance remain behind their existing gates. Do not count the blank template as a completed evaluation or reopen a broad prompt-tuning loop.
