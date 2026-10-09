# Recommendation contract 1.0.0

STK-001 · P1 · v0.1. This is a record contract and hand-worked synthetic fixture, not a replay implementation, investment strategy approval, or scoring/promotion policy. The planning baseline and system design are retained in `docs/`. STK-002 owns aggregate metrics and promotion criteria; STK-003 owns capital/risk settings; STK-037–039 own execution implementation and realistic costs.

## Records and field conventions

Each recommendation is one immutable JSON object. The example file is an array of such objects. All listed fields are required; nullable fields use explicit `null`. Unknown values must not be represented by zero. Unknown fields require a schema-version change. IDs are opaque, unique nonempty strings; example IDs begin `SYN-`. Money and prices are positive decimal strings in INR (outcome P&L may be signed). Quantities are positive whole shares. Timestamps are RFC 3339 UTC (`Z`); the display/session timezone is `Asia/Kolkata`. Fixture prices are raw, unadjusted and use a fictional INR 0.01 tick. No corporate action occurs in the fixture.

| Field | Meaning and requirements |
|---|---|
| `recommendation_id`, `schema_version` | Permanent ID; this contract uses `1.0.0`. |
| `synthetic`, `mode`, `run_id` | Fixture flag; mode `synthetic`, `historical_reconstructed`, or `live_paper`; immutable run reference. No real-order mode. |
| `instrument` | `instrument_id`, `symbol`, `exchange`, `series`, `isin`, `currency`, `exchange_timezone`. Stable ID plus symbol mapping as of cutoff; real instruments require a verified ISIN. Synthetic ISIN is null and exchange is `SYNTHETIC_NSE`; never resolve fixture symbols to real securities. |
| `strategy` | `id`, `version`, `config_version`; configuration must be immutable/resolvable. Fixture strategy is illustrative, not an implemented technical indicator. |
| `horizon` | `profile` (`swing`, `intraday`, `long_term`), `forecast_end_at`; this fixed forecast endpoint is independent of trade exit. |
| `information_cutoff_at` | Latest admissible information availability. Candle end must also be at/before cutoff. |
| `generated_at` | Actual record-generation wall time, never backdated in historical reconstruction. |
| `decision_available_at` | Logical signal-ready time including analysis latency; actual availability in live mode, explicitly simulated in replay/fixtures. |
| `earliest_executable_entry_at` | Earliest simulated entry or holding-sale time, strictly after signal availability; null for non-actionable records. Live mode also requires this to follow actual generation. No same-bar close fill based on that bar's close signal. |
| `action`, `position_effect` | See semantics below. |
| `holding` | Null except SELL/HOLD: `holding_ref`, `available_quantity`. Use an internal reference, never broker/account credentials. |
| `execution` | Null for abstentions/HOLD. Otherwise `entry`, `entry_expires_at`, `stop`, `targets`, `max_holding_sessions`, `time_exit`, `quantity`, `assumptions_version`. |
| `forecast` | Null if no directional claim; otherwise `direction` (`up`, `down`, `flat`), `reference_price`, `reference_at`, `end_at`, `definition_version`. No invented confidence probabilities. |
| `evidence` | Array of `evidence_id`, `kind`, `source_ref`, `source_version`, `locator`, `published_at`, `available_at`, `fetched_at`, `availability_basis`, `summary`. Material claims cite these IDs in rationale. |
| `missing_evidence` | Array of `requirement`, `reason`, `blocking`. Empty means no known missing input under this strategy, not universal knowledge. |
| `rationale` | `summary`, `evidence_ids`, `contradictions`, `invalidation`. Separate facts, interpretation and unknowns. |
| `versions` | `dataset`, `code`, `model`, `prompt`. Dataset manifest pins revisions, calendar, universe, adjustment basis and source rights; production code uses a commit identifier. Model/prompt null when unused, otherwise immutable model release and prompt content version. Fixture labels are illustrative identifiers, not claims of executed software. |
| `risk_context` | `status`, `reason`. Fixture is `not_assessed`; quantity is a demonstration input, not approved sizing. Production must reference the later versioned sizing/risk decision. |
| `revises_id`, `revision_reason` | Both null for initial record; otherwise prior same-instrument record and a nonempty reason. New ID and timestamps, no mutation of predecessor. |

Do not attach future candles, fills, forecast correctness or trade P&L to this object. Revisions never retroactively change a simulated trade: replacement/cancellation needs its own time-stamped event in later execution work. Preserve original and revised evaluations separately; prevent cycles and cross-instrument revision links.

## Actions

- **BUY / OPEN_LONG**: conditional proposal to acquire the explicit demonstration quantity. Entry must trigger within its window; it is not a claim that a trade occurred.
- **SELL / CLOSE_LONG or REDUCE_LONG**: dispose of an existing holding. Quantity cannot exceed available holding; CLOSE_LONG equals it, REDUCE_LONG is smaller. No holding means invalid recommendation, not an implicit short. Once filled, there is no new position to stop out or target. Original holding basis/performance belongs to a separate ledger.
- **WAIT / NONE**: sufficient required evidence was inspected but the entry policy is not satisfied. No order or fill; a later actionable decision needs a new recommendation.
- **INSUFFICIENT_EVIDENCE / NONE**: at least one required input is missing, stale, contradictory or ineligible at cutoff. At least one blocking missing-evidence item; no executable conditions and no forecast in this fixture.
- **HOLD / MAINTAIN_LONG**: optional vocabulary retained from the design for an existing holding with no proposed transaction. Distinct from WAIT for a prospective entry; execution is null. No HOLD fixture is needed for this ticket.

Opening a short position is explicitly unsupported in 1.0.0. SELL never means OPEN_SHORT. Neither BUY nor SELL authorizes an actual order.

## Conditions and timing

BUY `entry` has `type: buy_stop`, `trigger_price` and `condition`. It triggers at or above the stated price during `[earliest_executable_entry_at, entry_expires_at)`. At expiry no new fill is eligible. `stop` has `price` and `condition`; `targets` is an array of `{price, exit_fraction}`. Version 1.0.0 examples use exactly one full-position target (`exit_fraction: "1"`), with stop < trigger < target. Multi-target and partial-fill execution are deferred. The stop is active only after entry; rationale also states pre-entry thesis invalidation. If invalidation occurs before entry, record a separate `cancelled` trade outcome.

SELL uses `type: market_at_next_open`, null trigger, a condition to sell at the next eligible open, null stop, empty targets, `max_holding_sessions: 0` and `time_exit: not_applicable`. Its order still expires if it cannot fill. BUY uses a positive session count and `time_exit: close_of_last_holding_session`; the fill session counts as session 1. At the final session, a known stop/target exit takes precedence over the closing time exit. A missing required candle yields `invalid_data` or `pending` while awaiting data, never an assumed no-entry/win. Suspensions/non-trading days do not count as holding sessions; use the pinned calendar.

Live evidence requires `published_at <= available_at <= fetched_at <= cutoff`; availability is when the specific revision became accessible, fetch is when this system received it. Reconstructed history may have `fetched_at > cutoff` only with verified contemporaneous revision availability (`availability_basis: verified_archive`); preserve actual fetch and generation times. A late publication or later restatement is ineligible even if its accounting period predates cutoff. Fixtures use `fictional_fixture`: dates and provenance are explicitly invented, not verified archive claims. Closed-candle features must record bar-end eligibility in their dataset manifest. Historical generation may happen today; historical execution uses the explicit simulated decision-ready time, not today's wall clock.

## Separate outcome envelopes

`forecast-outcomes.synthetic.json` and `trade-outcomes.synthetic.json` contain separate arrays. Each row has `outcome_id`, `recommendation_id`, `schema_version`, `synthetic`, `evaluated_at`, `evaluator_version`, `observation_dataset`, `supersedes_outcome_id`. Corrections append a linked outcome rather than editing the recommendation. Observation dataset here is `SYN-future-v1`. Results cannot be final before their required observations are available.

Forecast rows additionally contain `status` (`matured`, `pending`, `not_applicable`, `invalid_data`), `reference_price`, `observed_price`, `observed_at`, `realized_direction`, `direction_matches`, `price_return_pct`. Null forecast produces not_applicable and null measurements. Fixture definition `SYN-direction-v1` compares the fixed endpoint close with the frozen reference: greater/up, less/down, equal/flat. Price return is `(end/reference - 1) * 100`, rounded to four decimal places; excludes fees. This is an individual example label, not an accuracy denominator or promotion threshold.

Trade rows additionally contain `status` (`closed`, `open`, `no_entry`, `pending`, `ambiguous`, `not_applicable`, `invalid_data`, `cancelled`), `reason`, `assumptions_version`, `fills`, `gross_pnl`, `estimated_costs`, `net_pnl`, `net_proceeds`, `sensitivity_net_pnl`. Fills contain `side`, `at`, `price`, `quantity`, `role`. `at` is exact in these intraday point fixtures; daily OHLC alone must use a time interval/unknown-time representation in a later schema revision, not an invented exact timestamp. Closed long trades have gross `(exit-entry)*quantity`, net gross minus both fill charges. SELL reports net proceeds and leaves trade P&L null because prior holding cost is unknown. Untriggered/abstained cases have no fills, zero costs and null P&L (never score them as a zero-return trade). Open/pending/invalid cases have no final P&L. Ambiguous cases preserve known fills, costs paid so far and alternative net outcomes, with scalar realized P&L null.

## Fictional fill and cost assumptions

`SYN-fill-v1` is deliberately simple and not a brokerage quotation: one share, full fills, unlimited fictional liquidity, no spread/slippage, raw prices, INR 0.10 charge per executed side. These charges stand in for all costs solely for arithmetic examples; realistic date-effective brokerage, taxes, fees, liquidity and adverse slippage belong to STK-039. No real capital/risk configuration is selected.

An opening gap above a BUY stop fills at the open, not the trigger. A gap below an active long stop exits at the open, even at a larger loss. A sell-limit target gapped above fills conservatively at the target. Intraday continuous touches fill at the relevant level in these fixtures. If an opening entry is already at/above its target, cancel the setup as invalidated before entry. A trading halt or absent executable quote is not a fill. At identical event timestamps use known ordering only; otherwise mark ambiguity.

A candle spanning both stop and target with unknown order is **ambiguous**. Do not assume target-first or silently select stop-first. Retain lower/upper outcomes under both feasible paths; obtain permitted finer observations later or leave unresolved. Entry-and-exit ordering within one candle is likewise ambiguous unless the entry at the open or finer data establishes order. A later target does not erase an earlier stop.

## Worked 6 August 2025 example and alternatives

All companies, instrument IDs, evidence, prices and timestamps below are fictional. Each scenario is an independent alternative future for an independent synthetic instrument, not competing claims about one price history. The fixture calendar includes 7, 8 and 11 August 2025 as sessions. 6 August cutoff is 10:05Z (15:35 IST), after the fictional close at 10:00Z. Signal is ready at 10:06Z; earliest entry is 7 August 03:45Z (09:15 IST). Files were actually authored in October 2026; generation timestamps reflect that, while decision times are simulated.

Freeze first: reference close 100.00, prior-window breakout trigger 102.00, stop 98.00, target 110.00. The fictional closed-price/volume evidence is available at 10:01Z and the fictional filing at 08:00Z, both before cutoff. Missing optional news coverage is disclosed. Required-evidence absence blocks the insufficient-evidence case. Then reveal only the separately stored future observations:

| Recommendation suffix | Revealed path (UTC) | Trade outcome | Forecast at 11 Aug 10:00Z |
|---|---|---|---|
| `stop` | 7 Aug open 101; 04:00 reaches 102; 8 Aug 04:00 reaches 98; 11 Aug close 112 | Entry 102, stop 98; gross -4.00, costs .20, net **-4.20**. Later 112 changes nothing. | Up, +12%; up forecast matches despite losing trade. |
| `target` | 7 Aug open 101; 04:00 reaches 102; 8 Aug 04:00 reaches 110; 11 Aug close 108 | Target exit; gross 8.00, net **7.80**. | Up, +8%. |
| `no-entry` | Eligible observations and complete 7–8 Aug bars never reach 102; max high 101.50 | At 8 Aug 10:00Z expiry: no_entry / entry_expired, no fills or costs. A later 112 is outside entry validity. | Up, +12%, independently of no entry. |
| `time-expiry` | 7 Aug fills 102; both complete holding-session bars remain between 98 and 110; 8 Aug close 103 | Two-session time exit at 103; gross 1.00, net **0.80**. Entry expiry does not close a position. | Up, +4% at 104. |
| `ambiguous` | 7 Aug fills 102; 8 Aug bar O=103 H=111 L=97 C=105, no finer order | Known entry only; stop-first net **-4.20**, target-first **7.80**; no scalar realized P&L. | Up, +6% at 106. |
| `gap` | 7 Aug opens 104, filling above 102; 8 Aug opens 95 below stop | Gross -9.00, net **-9.20**. | Down, -4% at 96; up forecast does not match. |
| `sell` | Existing fictional holding of one share; 7 Aug open 100 | CLOSE_LONG at 100; cost .10; net proceeds **99.90**; prior basis unknown, P&L null. No short opened. | Down, -6% at 94; down forecast matches. |
| `wait` | Required evidence present but no qualifying setup | not_applicable; no fill. | No directional forecast. |
| `insufficient` | Required warm-up history unavailable by cutoff | not_applicable; no fill. | No forecast. |

`observations.synthetic.json` includes all event points used for fills and complete bars needed to establish non-events (no-entry and time exit); other paths establish first passage through ordered points plus documented continuous movement between points. Ambiguous OHLC makes no path assertion. Fixture coverage excludes unmentioned outages and corporate actions; production must verify these, not inherit the assumption.

## Verification and limits

Run `python3 scripts/validate_contract_examples.py`. This dependency-free fixture validator checks strict JSON parsing, required top-level fields, IDs, action/position semantics, cutoff eligibility, revision links, observation chronology, outcome references, and hand-worked money arithmetic. Negative self-checks exercise future evidence, invalid SELL, altered outcome arithmetic and duplicate JSON keys. It is intentionally not a general application schema or replay engine. Human review must still check the prose and path assumptions. All tenable outcome paths are illustrative, with no performance inference and no promotion thresholds.
