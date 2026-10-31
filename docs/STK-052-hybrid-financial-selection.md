# STK-052 / D3-07 M2 — Hybrid financial selection

PR24 merged under protected main at `e7523bb70cd7ce8766b0e4808f69748dc36d51d1`. Exact `999a9cc` CI passed unit, PostgreSQL, UI and aggregate checks. Review found no substantiated P1/P2 blocker in its development-only scope. Raw failure accounting and unavailable zero denominators remain preserved.

## Diagnosis and correction

The original experiment established incorrect abstention and invalid abstention metadata from the coding model, and JSON/empty-final-response failure from VL. It did not isolate table comprehension from row selection. There is no evidence of the verifier rejecting an otherwise fully correct financial claim. The underlying VL runtime/model cause remains unresolved; changing response shape did not fix it.

The hybrid parses the pinned table with the existing financial-number and span verifier, supplies candidate cells to the model, then verifies its selection against the requested row/period. Values, units, source identity and quotes come from the source cell, never model-generated numbers. Source snapshot/profile/cutoff and durable reservations remain mandatory. This is a development route, not trusted production loading or independent entity verification.

Version 1 produced one correct coding-model positive, a valid ID pointing to the wrong period on the other positive, one valid negative abstention and one wrong-row selection on the conflicting case. These IDs were NOT corrupted. VL failed JSON parsing on all four cases. The final reservation-summary export encountered a Decimal serialization error; all eight case results had already been saved. No inference was repeated to repair that export.

Version 2 uses short IDs and an explicit grammar enumeration while preserving the same cases, model digests, temperature 0, seed 0, context 16384, output limit 1800 and independent verifier. This isolates a presentation/grammar change, not model superiority. Both negative coding-model selections remained invalid and were rejected. A presentation helper produces explicit INSUFFICIENT_EVIDENCE with no findings after rejection; it does not call that successful model abstention.

| Version 2 result | qwen2.5-coder:7b | qwen3-vl:8b |
| --- | --- | --- |
| Supported hybrid cells | 2/2 | 0/2 |
| Response contract validity | 4/4 | 0/4 |
| Model abstention on negative cases | 0/2 | 0/2 |
| Application negative cases with no findings | 2/2 | 2/2 |
| Accepted numeric/citation support | 2/2 | Unavailable (0 accepted) |

Two successes have a Wilson 95% interval approximately 0.342–1.0; this sample cannot establish general accuracy. Numeric and citation correctness here measure deterministic materialization after model selection, not independent generation or comprehension of figures. No financial interpretation or broad company research has been validated.

## Evidence, human review and limits

`research-quality/M2-hybrid-human-review.json` contains the captured excerpt, developer expected cells (162990 and 153670 INR crore for annual March 31 2025 and 2024), source locations, actual outputs, decisions and reviewer instructions. Reviewer identity, labels and decisions remain null. The conflicting-row case is explicitly synthetic. Original ten development cases and independent holdout remain untouched. Original HTML/PIT availability, entity mapping and provider rights for genuine NSE activation remain unqualified.

Original span results, hybrid version 1, version 2 and protocols are separate immutable files. The v1 source snapshot supports reproduction. Two explicitly bounded eight-call hybrid comparisons used an additional 320000 conservative units; all prior 200000 units were reconstructed and preserved in the disposable ledger. Final total 26 reservations / 520000 units, no refunds. API cost USD0; electricity and peak resource usage unmeasured. No additional inference beyond these comparisons.

Focused tests reject fabricated figures, citations, wrong periods, wrong-row IDs and invalid schemas; cover temporal denial, durable failure/cache accounting and report abstention. 745 backend/worker tests passed before the final presentation helper; final focused suite 10 passed; 7 isolated PostgreSQL tests passed. Full mandatory exact-commit CI is required for delivery.

**M2 remains PARTIAL.** Positive extraction is now demonstrated for one model on two development cells. Model negative abstention, VL output compatibility, independent human references/held-out evaluation and production/source qualification remain blockers. Next: independently review the packet; diagnose negative selection on development evidence in a separately bounded run, with no verifier relaxation. Combined AI/technical recommendations and historical replay remain gated.
