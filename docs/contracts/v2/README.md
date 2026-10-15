# D3-01 — version 2 contract amendment

STK-001 / STK-002 / STK-003 · 15 October 2026

[SD ARCH 3.0](../../SD-ARCH-3.0.md) is authoritative. This package defines contracts, not an operational discovery engine. D3-02 and later packages are not implemented here. No source, model, capital allocation or external service is activated.

## Using the contracts

Python types and deterministic validation live in `shared/stock_discovery_contracts/v2.py`. The six checked-in [JSON Schemas](schemas) describe recommendation, horizon, policy, outcome, cohort summary and validation bundle records. Each object rejects unknown fields; required nullable fields must be explicitly present. Python validation rejects coercions, non-finite/non-string decimals, invalid timestamps and unknown enum values. Use `parse_json` at a JSON trust boundary to reject duplicate keys and non-JSON constants.

JSON Schema is the structural layer. It cannot enforce all arithmetic, temporal, reference and cross-record invariants. **Use `validate_bundle` before accepting a v2 bundle**; calling a model or a generic JSON Schema validator alone is not publication approval. Missing reference data is an error, never an invitation to fetch the latest version. D3-03/D3-09 will supply persistent snapshots and publication transactions; this package has no persistence migrations or new application routes.

```python
from stock_discovery_contracts.v2 import parse_json, validate_bundle, read_record

bundle = validate_bundle(parse_json(serialized_bundle))
record = read_record(serialized_record, kind="recommendation",
                     accepted_versions={"2.0.0"})
```

## Recommendation and admission

`Recommendation` is version 2.0.0. Identity, instrument, strategy, provenance clocks, rationale, evidence, versions and append-only revision links remain explicit. New fields include snapshot/baseline, cohort/configuration hash, quant/event origin, research/validation/judge references, eight policy references, evidence quality, conditions and valuation.

The actions are `BUY`, `WATCH`, `AVOID`, `INSUFFICIENT_EVIDENCE`. V2 describes opening/avoiding long exposure. AVOID never means SELL. BUY requires an entry plan, invalidation and expiry, with paper entry strictly after publication. Other actions have no execution plan.

`paper_admission` is independent of the research action. It records `not_requested`, `admitted`, `blocked` or `expired`. Only admitted records contain a positive whole-lot quantity and reservation. Admission requires eligible deterministic risk, known capital, matching risk/reservation quantities and a non-shadow BUY. A research BUY with exhausted capacity or unconfigured capital retains its research action and has no quantity. No contract can issue an order.

Successful AI research requires matching research, validation and judge references belonging to the same snapshot, instrument and assessment. Failure has null references and an explicit unavailable reason; it cannot become a researched BUY. Quant and optional ML cohorts remain distinct from AI success. The contracts do not implement semantic judging or certify calibration; those services are later packages.

## Horizon and time contracts

| Profile | Fixed bounds | Unit | Review cadence |
|---|---|---|---|
| swing | 2–10 | trading sessions | each session |
| short_term | 1–3 | calendar months | weekly |
| long_term | 1–5 | calendar years | monthly |

Every horizon includes a selected duration, decision-availability anchor, exact holding endpoint, entry expiry, next review and pinned calendar reference. Swing counts session closes strictly after the anchor. Calendar month/year endpoints use the anchor date, clamp to the destination month's last date and resolve to the preceding pinned exchange session. The calendar must extend through the target date; incomplete calendars fail. Its SHA-256 hash covers the ordered session-close list. Changed calendars cannot silently move an endpoint. Actual scheduling is D3-04; these contracts do not implement it.

All timestamp strings are valid UTC `YYYY-MM-DDTHH:MM:SSZ`. Live evidence must satisfy publication ≤ availability ≤ fetch ≤ cutoff. Live publication cannot precede actual generation; execution follows publication. Historical reconstruction explicitly marks simulated availability and requires an exact archived revision reference. Synthetic evidence must declare fictional provenance. Bars must be closed; restatements must match the exact snapshot revision. Outcome observations are carried separately from the decision snapshot.

## Policy and outcome contracts

`Policy` 2.0.0 identifies a kind, profile, version, effective time, content hash, typed parameters and status (`unconfigured`, `fixture`, `approved`). Every parameter has a finite decimal string and unit, or null plus an unavailable reason. The content hash covers the ordered parameter list, encoded as sorted-key compact JSON. Approved records require an approval reference. BUY rejects unconfigured/missing parameters and future or mismatched policies. Fixture policies are accepted only for synthetic BUY. These integrity checks do not grant real-world approval or supply strategy formulas; activation and parameter-specific policy semantics belong to later packages.

`Outcome` 2.0.0 pins recommendation, mode, exact horizon, cohort, observation manifest, evaluator and cost policy. States distinguish provisional, matured, no-entry, ambiguous, unavailable and not-applicable. A matured result requires observations through the frozen endpoint. `realized_return` is an optional net paper return ratio (0.01 = 1%); it is never a forecast confidence or annualized result. A scalar return requires paper admission and is unavailable for ambiguous/missing/no-entry cases. A provisional mark is not a completed horizon result. Thesis status is separate. Reassessment appends a later outcome linked by `supersedes_outcome_id`; it preserves old records. Fill simulation, detailed forecast/target metrics and portfolio aggregation remain D3-10/D3-11 work, not claims made by these fixtures.

`CohortSummary` 2.0.0 keeps action counts and research-failure counts separate from disjoint outcome denominators. Eligible BUY outcomes reconcile as resolved + missing + ambiguous + provisional + no-entry. Zero resolved cases require unavailable net expectancy, not zero performance. Each summary explicitly carries horizon, mode and cohort. Calculation of these summaries and statistical comparison are later work.

## Compatibility and fixture evidence

`read_record` requires explicit accepted versions. It validates v2 records with their own model. V1 recommendation 1.0.0 and outcome 1.0.0/1.1.0 reads return the original decoded record without mapping actions or fields. This legacy branch is a lossless reader, not a replacement validator: existing v1 validators and replay tests remain authoritative. WAIT remains WAIT; SELL remains a holding exit. No existing runtime reader or historical fixture is changed.

[Legacy SHA-256 manifest](legacy-fixture-sha256.json) freezes all six existing fixture files at HEAD `9736f40`. Tests check their bytes and run all three legacy validators. Additional tests round-trip actual daily replay 1.1.0 output. The manifest works in a shallow CI checkout.

The three [synthetic bundles](examples) contain 21 recommendations and 21 provisional/not-applicable outcomes: all four experimental arms, every action, capacity-blocked BUY and failed AI for each horizon. Calendars and all evidence/policies are explicitly fictional; weekday calendars are not production exchange calendars. Negative tests cover every nested object's unknown fields, clocks, calendar changes, restatements, unresolved/foreign citations, judge failures, admission, malformed quantities/decimals, immature outcomes, version negotiation and zero-pick denominators. These test contract boundaries for T01/T02/T15; full ingestion and comparative evaluation remain later gates.

## Verification

From the repository, with its existing locked environment:

```sh
PYTHONPATH=backend:shared:worker .venv/bin/python -m pytest backend/tests/test_contracts_v2.py -q
PYTHONPATH=shared .venv/bin/python scripts/export_v2_schemas.py --check
```

To intentionally regenerate schemas after a reviewed contract change, omit `--check`. Schema drift and compatibility tests run automatically in the existing CI application-test step. No new dependency or paid API is required.
