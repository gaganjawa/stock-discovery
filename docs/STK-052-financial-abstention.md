# STK-052 / D3-07 M2 — Explicit financial abstention

PR25 passed exact-commit mandatory unit, PostgreSQL, UI and aggregate CI at `c50e3da3ee459c0957824f4495603faab24526c3`; protected-main enforcement was verified active (strict aggregate `checks`, administrators included). Independent code/source/result review found no substantiated P1/P2 blocker in the development-only scope. It merged at `2607e091e9002e4c68aa2321ae76c8edd0286922`.

## Measured diagnosis

V2 discarded conflicting rows from selectable cells without exposing row multiplicity to the model. Missing-period and conflict cases still offered unrelated candidates; the empty-string abstention option was not used. The source-level missing-context problem and observable wrong selections are confirmed. The model's internal reasoning and individual causal contributions of the prompt changes are unknown. Original financial verification correctly withheld unsupported outputs.

V3 adds an explicit `ABSTAIN` grammar option, exact row/period matching instructions, and source-derived available periods and row counts. It retains unrelated cell choices, so neither the grammar nor a reference label forces abstention. Reference answers are not included in the prompt. Compact candidate context in V3 recovered both negative abstentions but selected the prior-year quarterly cell instead of its annual cell.

V4 retains those instructions and restores full original cell context (quotes, locators and source hashes) as the only context change. It still misses one positive. The configuration is **development-only and NOT promoted/accepted**. Existing production research, source-rights checks and numeric/citation verifier remain unchanged. Historical empty-string abstention remains readable; new requests explicitly offer `ABSTAIN`.

| Coding model, four fixed development cases | V2 baseline | V3 compact context | V4 full context |
| --- | --- | --- | --- |
| Correct positive model selections | 2/2 | 1/2 | 1/2 |
| Explicit contract-valid model negative abstention | 0/2 | 2/2 | 2/2 |
| Response contract validity | 4/4 | 4/4 | 4/4 |
| Deterministic verifier rejections | 2 | 1 | 1 |
| Negative application results without findings | 2/2 | 2/2 | 2/2 |
| Accepted numeric/citation correctness | 2/2 | 1/1 | 1/1 |

A rejection is never counted as model abstention. Numeric/citation correctness describes deterministic cell materialization after selection, not LLM-generated numbers or independent financial interpretation. Wilson 95% interval for 2/2 is approximately 0.342–1.0, and for 1/2 approximately 0.095–0.905. These repeatedly tuned development cases cannot establish general quality.

Both protocols were recorded before their four calls; v3 and v4 results and v3 source context are separate artifacts. No prior result was modified. Only qwen2.5-coder:7b ran (installed digest recorded in each result); no additional VL calls. Eight new local calls reserved 160000 units. All 26 prior reservations were reconstructed conservatively from preserved artifacts in the disposable ledger: final 34 reservations / 680000 units, zero refunds/resets and USD0 provider API cost. Reconstruction uses recorded source cutoffs for conservative historical accounting; it does not certify original wall-clock reservation timestamps. No electricity or peak-resource estimate is claimed.

## Independent review and release gate

[Reviewer worksheet](research-quality/M2-INDEPENDENT-REVIEW.md) and [supplement](research-quality/M2-abstention-review-supplement.json) retain source identity/locations, original captured excerpts, developer expectations, actual outputs, verifier decisions and blank human fields. The existing review packet had no reviewer or approved labels. The existing unseen holdout remains empty and unevaluated. Its proposed minimum is 50 independently verified cases; protocol approval and reference freeze must precede holdout execution. No implementation-agent labels are independent human truth.

**M2 acceptance: BLOCKED.** Negative behavior improved, but no tested configuration passes both positive and negative development criteria, and independent human/holdout evidence is missing. M1 rights/PIT/raw-data qualification also remains blocked. Do not advance to combined AI/technical recommendations, historical replay, complete dashboard/ranking or end-to-end acceptance before their existing gates.

## Validation

748 backend/worker tests passed after the initial correction. Final combined focused validation passed 20 tests (12 unit and 8 disposable PostgreSQL). That combined command exposed duplicate unit/integration test module basenames; the unit file was renamed to `test_financial_selection_unit.py`, then the same command passed. New coverage verifies visible conflict multiplicity, missing-period metadata, non-forced abstention, unchanged positive provenance, and durable separation of rejection versus model abstention. Syntax/JSON/whitespace passed; full exact-commit CI remains the delivery gate. No actual operational database, provider grant, frozen holdout or trading gate was changed.

Next: independent human source/case review, then a separately bounded development investigation of annual/quarterly selection stability before any holdout or milestone promotion. Do not retry the preserved runs or claim this increment completed M2.
