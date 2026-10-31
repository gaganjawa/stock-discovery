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

After human development review, select and freeze a configuration that passes both positive and negative development checks, then perform the separately approved holdout. Saved v3/v4 model runs each pass negative abstention but miss one of two positives. The exact-route supplement now passes 2/2 positive and 2/2 negative development cases **without model inference**; this does not correct or replace those model measurements. M2 remains blocked; publication, paper admission and trading remain blocked.

## Final development handoff and required return

Review these existing artifacts together; keep your completed review in a separate, versioned file:

- `M2-financial-review-packet.json`: the original ten development cases, never a holdout.
- `M2-hybrid-human-review.json`: the captured excerpt, expected cells and known adversarial cases.
- `M2-abstention-review-supplement.json`: saved model outputs and verifier decisions across prompt versions.
- `M2-exact-human-review-supplement.json` and `M2-exact-selection-development.json`: deterministic results and source locators; **model accuracy unavailable**.

The external reviewer must supply their identity/reference, independence declaration, UTC review time, hashes of reviewed artifacts, independently checked original source identity and availability (or UNRESOLVED), and a per-case signed decision. Each decision must state entity/scope, annual versus quarterly period, currency/unit, independently transcribed value or reason to abstain, exact source location, citation support, numerical/verifier correctness, and disagreement resolution. Confirm that the contradictory row is a developer mutation, not official evidence. Missing original-file/hash/PIT/rights evidence stays UNRESOLVED. A second independent reviewer must resolve disagreements; neither the developer nor another LLM supplies independent human truth.

Separately, the independent custodian must supply the 50 unseen permitted cases and human references described in `M2-UNSEEN-EVALUATION-HANDOFF.md`. Supply only a safe manifest/reference and access instructions initially; keep case contents outside development/tuning access. Exclude all ten development cases, the four familiar examples and their mutations/near duplicates. The blank template has no populated cases or labels.

The owner must explicitly approve the existing proposed thresholds and frozen execution configuration **before** holdout use. No approval, reviewer, label or evaluation has been added by preparing this handoff. Development review, policy approval and unseen-evaluation acceptance are three separate requirements. Non-actionable product development may proceed under the latest roadmap instruction; none of these gates is waived.
