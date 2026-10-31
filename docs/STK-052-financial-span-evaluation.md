# STK-052 / M2 — Representative table-span development evaluation

## PR23 release

PR23 merged at `103f5ffb6c05ea80a516ecc37f5385b837307b68` after exact-commit checks passed for `9eeb2cb`: 421 PostgreSQL tests, zero skips, migration lifecycle and other mandatory gates. Focused adapter/output/provenance review found no substantiated P1/P2 blocker; actual llama.cpp operation and hard-crash cleanup remain unverified/deferred.

## Evidence and boundary

A real Infosys 2025 IFRS INR revenue table is publicly readable in [SEC Exhibit 99.8](https://www.sec.gov/Archives/edgar/data/1067491/000106749125000010/exv99w08.htm). SEC's [FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) permits reuse of public EDGAR filing content. The one identified raw-document request returned HTTP 403 and was stopped, with no retries, proxy or identity rotation.

The fixture is a selected, whitespace-normalized public web-tool excerpt with exact source lines, URL and local capture timestamp. Scope/title context comes from separate disclosed source lines. It is **not the original HTML**, and its original-file SHA and first-public availability are unknown. The rupee glyph is an image; currency context comes from the explicit INR title and crore unit text. No production grant, corpus acceptance or genuine NSE recommendation was activated.

The span checker supports this pinned two-level pipe-table layout only. It separately maps quarterly and annual columns, validates snapshot/hash/header/context, parses numbers using the existing filing parser, and rejects missing periods, duplicate/conflicting rows, changed profiles, numbers, periods, units and quoted spans. It does not infer fiscal starts, add a speculative PDF parser or promote copied text to original-source evidence. Production FinancialRow verification and the real-data acceptance gate are unchanged.

## Predeclared actual benchmark

The fixed protocol selected two installed models before inference: qwen2.5-coder:7b baseline and qwen3-vl:8b general-instruction candidate. No dedicated finance-specialist instruction model was identified; the VL model is not assumed finance-optimal. Larger installed models were outside this run's resource cap. No model was downloaded.

Each received four development tasks with equal settings: annual current, annual prior, missing period and an explicitly generated conflicting-row mutation. Positive reference cells came from the deterministic table checker. The mutation is not an actual filing. The original ten development cases were preserved unchanged, with their hash recorded. No holdout was opened and no developer label became human verified.

The harness reuses existing provider, durable reservations/results, budget checks, fraction and Wilson statistics. Cached cases do not repeat inference; ambiguous receipts cannot retry; failures remain in denominators. Source capture/cutoff checks run before inference. It cannot promote a strategy or authorize publication/trading.

## Observed results — not research-quality acceptance

| Original four-case run, per model | qwen2.5-coder:7b | qwen3-vl:8b |
| --- | --- | --- |
| Positive field success: number/unit/period/citation/quote | 0/2 each | 0/2 each |
| Accepted supported cells | 0/2 | 0/2 |
| Negative status-only abstention | 2/2 | 0/2 |
| Strict contract-valid negative abstention | 0/2 | 0/2 |
| Response/contract failures | 4/4 | 4/4 |
| Unsupported acceptance rate | Unavailable: no accepted claims | Unavailable: no accepted claims |

The coding model abstained even on valid rows and retained a non-null evidence ID despite the null-field abstention contract. These are contract failures, not server outages or four incorrect numeric predictions. The VL responses could not be parsed as JSON.

A separate two-call diagnostic added decoded header labels and bounded raw-output capture. It did not replace the original results or change the verifier. The coding model returned one valid abstention on the positive case (still 0/1 extraction); the VL model returned an empty final response, causing JSONDecodeError (0/1 extraction). The underlying VL empty-output cause is not established. No response repair, verifier weakening or model-superiority claim was made.

Raw immutable run reports, model/prompt hashes, native usage and reference provenance are retained. Supplemental analysis separates citation support, contradiction abstention, status-only abstention and strict contract validity. Zero denominators are unavailable. Unit/scope context was supplied by the pinned profile; these metrics do not prove independent unit interpretation. Current-model knowledge contamination is not excluded. One company/table and two positives per model cannot support general accuracy or ranking claims.

Ten total actual calls consumed ten conservative reservations (200,000 units), without refunds or resets. API cost USD 0; electricity unmeasured. The original benchmark used eight calls; the diagnostic used only the remaining two reservations. No further inference was performed.

**M2 development readiness: NOT PASSED. Human-verified quality acceptance: UNAVAILABLE.** The code correctly rejects the failures; software tests passing do not qualify financial research. Independent human references/holdout, stronger source/layout handling and usable structured extraction remain required. Do not advance M3–M7 as though this gate passed.

## Running and validation

`evaluate_financial_spans.py` requires explicit `--execute-local-development`, registered model/protocol hashes, a new output path and migrated disposable `stk013_test`. It preserves budgets and stores immutable receipts in that disposable environment; it is not a production ingestion route. The v1 protocol and result remain historical; the current serializer requires a matching new protocol and cannot silently overwrite/reuse v1 results.

Fresh local tests: 740 backend/worker passed; 10 isolated PostgreSQL harness/financial integration cases passed. Reference/profile tampering, future sources, duplicate IDs, zero denominators, budgets, cache, ambiguous crashes, caller-transaction rejection and negative spans are covered. The evaluation requires idle autocommit so reservations survive inference failures; its validator version participates in cache identity. Canonical model-number formatting is enforced consistently with metric scoring. Historical actual run reports are not rewritten by these final hardening checks. Exact-commit full CI/lifecycle remains required for this increment. Real-source qualification, independent human review and app integration are not completed by this benchmark.
