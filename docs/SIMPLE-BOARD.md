# Stock Discovery — SD ARCH 3.0 board

Updated: **15 October 2026** · Baseline: [SD ARCH 3.0](SD-ARCH-3.0.md)

**Overall:** architecture integrated; D3-01 contracts implemented at `6b88cf6`. The other 12 packages remain unstarted. This is a package count, not a percentage of effort or application readiness. The existing synthetic MVP works; automatic real-market discovery and grounded AI research are not yet implemented.

## Delivery workflow

- Use existing STK ticket IDs and the architecture's D3 package names in branches, commits and PR titles. D3 labels are delivery packages, not new tracker IDs.
- Work on a ticket-named branch. Push that branch and provide a PR for owner review. Never push directly to `main` or merge a PR.
- Wait for the owner to review, merge and confirm before starting the next package. D3-02 has not been authorized yet.
- Keep one implementation package in progress. Preserve unrelated tracked/untracked WIP; stage only the current ticket's files.

## Package and feature status

| Package / ticket names | Done | Remaining | Status / dependency |
|---|---|---|---|
| **D3-01 Contract amendment** · STK-001/002/003 | Strict v2 recommendations, three horizon profiles, four actions, research/admission separation, policy/outcome contracts, fixtures, compatibility tests | Runtime adoption belongs to later packages | Implemented · `6b88cf6` |
| **D3-02 Rights and source feasibility** · STK-004/005/006/007 | Architecture requirements defined | Source coverage, use/territory/cost matrix, grants and denied-operation cases | Not started · next package, awaiting authorization |
| **D3-03 Revision storage and ingestion** · STK-014/015/019–024 | Existing synthetic data foundation | Automatic adapters, exact revisions, snapshots, corporate actions, quarantine and migrations | Not started · D3-01; mock grants |
| **D3-04 Scheduling and coverage** · STK-017/058/060/073 | Existing synthetic worker foundation | Exchange-calendar occurrences, catch-up, event triggers and full-universe coverage accounting | Not started · D3-03 |
| **D3-05 Quant horizon policies** · STK-028–032/054/058/076 | Existing swing baseline preserved | Configured swing/short/long policies, features and deterministic decision composition | Not started · D3-01/03 |
| **D3-06 Evidence ingestion** · STK-046–051 | Interfaces specified | Automatic permitted filings/news, parsing, financial facts, events and provenance | Not started · D3-02/03 |
| **D3-07 Hybrid RAG** · STK-052/053/074 | Contracts specified | Structured/lexical/semantic retrieval, deterministic calculations, grounded fixed research and budgets | Not started · D3-05/06 |
| **D3-08 Bounded agent and judge** · STK-052/070/071/072 | Contracts specified | Bounded investigation, claim checks, calibrated judge and shadow evaluation | Not started · D3-07 |
| **D3-09 Policy publication and UI** · STK-033/054/058/059 | Existing synthetic UI | Four-action publication, evidence views, horizon/mode controls, event ranking and operational API | Not started · D3-05/07/08 |
| **D3-10 Paper portfolio and outcomes** · STK-037–044/060–063 | Existing synthetic replay | Cross-horizon reservations, ledger, costs/actions, outcome updates and automatic tracking | Not started · D3-03/05/09 |
| **D3-11 Experiment governance** · STK-041/042/044/069/072/076–078 | Existing synthetic audit foundation | Paired/end-to-end cohorts, holdouts, forward evidence, maturity and promotion controls | Not started · D3-10 |
| **D3-12 Private operational pilot** · STK-009/016/017/018/073–075 | Hetzner CX23/Compose/restic/B2 selection approved | Authorized provisioning, security, budgets, monitoring and off-host restore | Deferred · D3-02/04/09/10 + explicit deployment approval |
| **D3-13 Three-horizon release** · STK-079/080/081 | Release criteria specified | Integrated acceptance, coverage evidence, known limits and operational runbook | Not started · D3-11/12 |

## Verification and boundaries

D3-01: **141 application/worker tests passed**, including **83 new contract cases**; 7 script tests, schema consistency, whitespace checks and isolated frontend build passed. Eleven database cases were skipped locally without a test database. All six historical fixture files retain their original hashes. [CI run](https://github.com/gaganjawa/stock-discovery/actions/runs/38758750057) is the source for remote validation status; local results do not imply CI success.

Existing optional LLM explanations summarize synthetic decisions. They are not the planned pre-decision RAG, bounded agent or LLM judge. No paid AI or real-source capability has been activated.

Purchases, paid APIs, deployment and broker orders are outside current authorization. Hosting selection remains fixed; region, final pricing and backup-key custody must be confirmed before provisioning. Optional IPO, intraday, broker reads and predictive ML are not prerequisites for the core three-horizon release.

[Contract details](contracts/v2/README.md) · [Handoff](WORK-HANDOFF.md) · [Historical board](archive/BOARD-before-sd-arch-3.md). Historical synthetic milestones remain valid within their original scope; they do not mark new architecture packages complete.
