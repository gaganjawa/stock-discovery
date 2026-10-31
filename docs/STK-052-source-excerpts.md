# STK-052 / M2 — Attributed source excerpts in factual research

This is an incremental extension to the existing fixed-RAG financial report, not a new research framework or completion of M2 quality acceptance.

`historical-factual-1.3.0` gives the configured model a bounded catalogue of exact retrieved excerpts alongside the existing service-calculated financial candidates. The model can select up to three excerpts by immutable candidate and citation IDs. The service recomputes the catalogue, verifies text equality and ordered citation membership, and materializes stored citations itself. Duplicate selections are collapsed. Unknown documents, invented text and borrowed citations fail closed. Overlong excerpts are omitted; no automatic truncation creates a different quotation.

Selected excerpts remain separate from independently validated financial facts and directional arithmetic. They carry `financially_verified=false` and `event_truth_verified=false`, and the UI displays that limitation explicitly. Exact source parity is not proof that a source's figures or statements are true, a sentiment classification, absence of risk or complete news coverage. Missing coverage and existing contradictions remain visible. This slice does not invent management commentary, forecasts or event causes.

No changes to retrieval eligibility, original/current grant checks, read fences, budget reservations, durable model receipts or publication/admission gates. Existing run identity includes the prompt/schema hash; the new version cannot silently reuse an old model result under the same run ID. Historical results remain immutable. Optional response/report fields preserve reading old reports.

## Execution evidence — 31 October 2026

Synthetic fixtures only; no provider or actual model calls.

- Focused financial/RAG/agent/API regressions: 95 passed before the final two unit cases.
- Final full backend/worker suite: 712 passed.
- Fixed-RAG PostgreSQL suite including new excerpt cache/revocation tests: 25 passed, zero skips.
- Frontend production build passed; two synthetic desktop/mobile Playwright cases passed, including source-statement labels and existing cutoff/denial clearing.
- One additional retrieval/read-fence run encountered 13 setup errors because the shared disposable database had no migrated schema (24 isolated cases passed). Existing migrations were then installed on that task-owned database before rerun. This was a validation setup error, not a relaxed production check.

Full PostgreSQL/migration and browser/stack gates remain required on the PR. No synthetic results establish human research-quality accuracy, a real NSE qualification, profitability or AI superiority. Human-reviewed reference labels and a predefined untouched quality holdout remain external acceptance work. M4 combined synthesis and M5 real historical replay remain incomplete.

Follow-up execution: affected retrieval/orchestration/read-fence rerun passed **37 tests** after disposable schema setup. Full PostgreSQL run executed **416 tests: 415 passed, 1 failed, zero skipped**. The failure was unchanged `test_expiry_during_fence_lock_wait_rejects_work[capture]`: a fail-closed `QueryCanceled` at the 12-second statement timeout rather than the expected permission rejection. No grant-fence production/test code or timeout was changed. The validator stopped before downgrade/re-upgrade; lifecycle completion for this revision must not be claimed. Exact failing cases are rerun separately, and required PR CI remains the release gate.

Unchanged expiry-lock rerun: **3 passed, 57 deselected**. This does not erase the failed full run or establish why its timeout occurred. Source review found no new P1/P2 in the excerpt increment; mandatory CI must resolve release readiness.
