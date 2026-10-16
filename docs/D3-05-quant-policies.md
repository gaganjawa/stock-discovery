# D3-05 — Quantitative investment policies

STK-028–032/054/058/076 · SD ARCH 3.0 §9 · 17 October 2026

## Implemented

`shared/stock_discovery_analysis/quant_policies.py` supplies a deterministic Python policy registry and three technical-only assessment engines. D3-01 Policy, Parameter, Ref, Evidence, Horizon, Conditions and Valuation contracts are reused. Financial calculations use an isolated Decimal context with precision34. No LLM, acquisition, sizing, order execution or publication is performed.

- **Swing, 2–10 sessions:** existing EMA10/EMA30, prior20-session breakout, relative volume1.5 and ATR14 formulas and synthetic price geometry. New configurations explicitly pin holding duration and separate forecast duration. `legacy_swing` dispatches unchanged `ema-breakout-1.0.2` including its historical three-session hold, five-session forecast and legacy sizing. Historical strategy files and fixtures are unchanged. Real swing instrument tick/execution settings remain unavailable; the fictional one-paise geometry cannot activate real mode.
- **Short term, 1–3 months:** registered annual or quarterly year-over-year revenue/earnings growth, price/SMA20 confirmation and annual-EPS valuation scenarios. Quarterly earnings are never multiplied by four or silently treated as annual earnings. Annual valuation inputs have their own freshness check. Entry requires the configured margin of safety against the bear scenario and quantitative thresholds.
- **Long term, 1–5 years:** annual financial momentum, operating-cash-flow margin, earnings/closing-equity proxy, net debt/operating cash flow, free cash flow, FCF yield and a configured2–5-year minimum annual cash-flow-margin consistency proxy. Business/governance coverage is mandatory; cash consistency alone is not proof of business durability. Debt-limit violations disqualify sufficiently evidenced research. Bear/base/bull PE scenarios expose assumptions and calculation references; scenario values are not execution targets.

All numerical thresholds other than the preserved synthetic swing baseline must be supplied in the registered policy. The committed [policies](contracts/quant/policies.synthetic.json) are arbitrary **engineering fixtures**, not approved investment settings or evidence of profitability. No approved policy is bundled. Missing policy, approval, mandatory value, valid denominator, fresh evidence or supported metric produces INSUFFICIENT_EVIDENCE. Zero values remain observed zero; they are never filled from missing inputs. Banks and other sector-specific models fail closed with `unsupported_sector_metrics` until another formula version is implemented and approved.

## Time, identity and compatibility

The registry stores immutable serialized policy versions; changed parameters, approval metadata or effective dates require a new version. Export/restore supports persisted manifests; parameter hashes reuse the shared contract and full manifest hashes include metadata. The engine also records its formula version, input hashes, calculation IDs and assessment ID. The [legacy registration](contracts/quant/legacy-swing.json) describes the preserved baseline separately.

Only eligible publication/availability revisions at the cutoff are selected. Live inputs must have been fetched by the cutoff; historical inputs require verified archival evidence. Future statements, future prices and future calendar knowledge cannot affect research. Equal-clock conflicting statements and incompatible scopes/periods block assessment. Price warmup checks require the last30 known trading sessions, volume, freshness and consistent adjustment basis. Source rights must already have been checked by the D3-03 snapshot boundary; the quantitative engine does not infer permissions.

Month/year endpoints reuse the frozen preceding-valid-session convention, including leap days and holidays. Missing calendar coverage blocks assessment. Review cadence, holding endpoint, forecast endpoint and entry expiry remain distinct. `entry_conditions_met` checks research price/time conditions and rejects expiry; it is not an execution or admission service.

## Research/admission and integration boundary

Action precedence is INSUFFICIENT_EVIDENCE → AVOID → WATCH → conditional BUY. Known adverse facts remain visible even when evidence is insufficient. All outputs are labelled technical-only; no result represents completed AI research. There is no top-N quota, so WATCH/AVOID/insufficient-only batches are valid.

Research assessments always have `paper_admission.status=blocked`, `quantity=null`, `reason=paper_admission_not_evaluated`. No capital or risk limits are invented. D3-10 will evaluate admission independently without changing a sound research thesis solely because capital is unavailable.

The output is a quantitative assessment interface, not a complete published v2 recommendation. D3-06 supplies automatically acquired/extracted financial facts, coverage and verified adverse evidence; D3-09 composes publication/UI; D3-10 supplies portfolio admission and outcomes. The existing scheduler is not silently switched to these policies. Optional RAG/agent work is outside this package. The D3-04 restricted-runtime grant blocker remains unchanged.

Real-market acceptance remains **not complete**: approved policies, source rights/adapters, sector-specific formulas, verified business/governance evidence, instrument settings and later integration packages are still needed. No API key, paid call, purchase, broker transaction or deployment is used.

## Validation

New deterministic cases cover all horizons, immutable policy/configuration versions, missing/unapproved settings, source cutoffs, stale/missing/zero statements, annual/quarterly comparisons, ambiguous revisions, valuation sensitivity, unsupported sectors, Decimal/input-order reproducibility, entry expiry, holiday/leap endpoints and exact legacy compatibility. Generated schemas and fictional results reproduce from source. Final regression totals are recorded on the [board](SIMPLE-BOARD.md).
