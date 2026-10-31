# Independent financial review — awaiting reviewer

**Gate: BLOCKED. No reviewer, verified reference labels or untouched holdout are registered.** This packet reviews four known development cases; approving it alone cannot accept M2. The implementation agent has not certified any reference as independent human truth.

Open [the official SEC filing](https://www.sec.gov/Archives/edgar/data/1067491/000106749125000010/exv99w08.htm) independently. The stored fixture is a normalized excerpt, with noncontiguous title/scope context (source lines 4, 21, 3016–3023). It is not the original HTML. Original-file hash and original availability timestamp remain unknown. Verify that the filing is for the intended Infosys entity and that the cited table is consolidated; the developer attribution is not a human confirmation.

Use [the original packet](M2-hybrid-human-review.json) and [the output supplement](M2-abstention-review-supplement.json). Both contain complete captured excerpts; the supplement preserves raw v2/v3/v4 outputs, selected cells and independent verifier decisions. Do not overwrite experiment files. Record your review in a separate file, referencing its packet hash/version, your identity, independence from implementation, source URL and review time.

## Review worksheet

| Case | Developer expectation (unverified by a human) | Checks required |
| --- | --- | --- |
| annual-current | Total revenue from operations 162990 INR crore; year ended March 31, 2025 | Distinguish annual from quarterly 40925; verify consolidated entity, units, exact total row and citation |
| annual-prior | Total revenue from operations 153670 INR crore; year ended March 31, 2024 | Distinguish annual from quarterly 37923; verify same entity, units, row and citation |
| missing-period | Abstain: requested annual March 31, 2027 is absent | Do not substitute 2025 or 2024; confirm no supporting column |
| conflict | Abstain: two contradictory total rows in the supplied case | The appended `1 / 2 / 3 / 4` row is a **synthetic adversarial mutation**, not an official filing statement |

For each case record: official source/entity verified YES/NO/UNRESOLVED; correct row and annual/quarterly period; currency/unit; independently transcribed value or insufficiency reason; source location and excerpt; model output supported YES/NO; verifier decision correct YES/NO; disagreements and a second independent review where needed. Fields in the machine-readable supplement deliberately remain null.

Source quotes and values are supplied by deterministic parsing after model selection. Correct output does not establish LLM financial interpretation. A rejected selection is not a successful model abstention. Confirm the separate metrics in `M2-abstention-development-analysis.json`.

## Separate, unseen holdout

Do not repurpose any development packet, excerpt, mutation or debugging output as an untouched holdout. An independent reviewer must supply separate permitted evidence and labels, kept unavailable to prompt tuning. The existing `M2-heldout-registration.json` remains empty and unevaluated. Before any holdout execution, approve/freeze the existing proposed protocol (`M2-financial-extraction-protocol.json`), including its minimum 50 independently verified cases, thresholds and denominators; register the reference hash, reviewer and time. Review disagreements independently. No developer-generated labels become human labels automatically.

After human development review, select and freeze a configuration that passes both positive and negative development checks, then perform the separately approved holdout. Current v3 and v4 each pass negative abstention but miss one of two positives. M2 remains blocked; publication, paper admission and trading remain blocked.
