# REAL-001 Phase 9 — limited local beta, prospective pilot blocked

23 October 2026 · STK-014/028/046/052/054/058/059/060 · **PARTIAL**.
Existing feature branch and draft PR #12; no merge or new architecture package.

**RESEARCH-ONLY LOCAL BETA: READY**, for authenticated, manually refreshed local historical research within current source permissions.
**PROSPECTIVE SWING PILOT: BLOCKED. FULL THREE-HORIZON GO-LIVE: NOT YET ACCEPTED.**

## Baseline and implemented changes

Phase 8 commit `1c4ce3053d1137f6229cbfeece659de8965a5f31` matched the feature ref and PR head. Its [CI run](https://github.com/gaganjawa/stock-discovery/actions/runs/39830721794) passed. The older synchronization blocker is resolved; earlier reports are historical.

The existing view now distinguishes latest verified closed-session coverage from elapsed clock age. Weekend, declared-holiday, pre-close and exact-close tests cover this distinction. Calendar-list membership does not attest calendar completeness. The direct `/#real-research` link opens the real view after authentication. No D3-05 policy parameter, source grant, database schema, model or publication gate changed.

## Actual INFY market check

The initial bounded refresh returned 34 genuine candles through 22 October, with no missing closed session at its pre-close cutoff. Direct same-day and wider-window provider probes agreed. The [official V3 contract](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) defines an inclusive end date. Midnight-IST labels map to verified exchange-session timestamps. The previously absent 22 October candle is now available; the evidence supports earlier provider availability lag, not a cursor or timezone correction. Its exact release time is unknown.

A final bounded refresh at **16:10 IST (10:40 UTC), 23 October** requested 3 September–23 October and returned **33 candles through 22 October**, missing the newly closed 23 October session. The window moved forward one day when the latest closed session changed, so 2 September is outside this latest coherent adjustment batch; its older immutable record was not deleted. This is an exact current-data blocker, not a synthetic replacement. The dashboard correctly shows the missing session and preserves historical descriptive charts.

Existing D3-05 functions calculate SMA20, EMA10, EMA30, ATR14, prior-20 high and support on genuine data. Exact values, latest-close comparisons, provenance IDs and actual timestamps remain in the private owner report. They are descriptive adjusted-price calculations, not raw execution inputs. Relative volume is unavailable because adjustment semantics are unverified. No fictional eligibility or instrument-risk profile is substituted.

## Permissions, policy and research

Corporate-action access still fails **scope_denied before network**. No grant changed. The [official endpoint](https://upstox.com/developer/api-documentation/get-corporate-actions/) documents fields, not blanket usage rights or complete action coverage. The relevant [official community clarification request](https://community.upstox.com/t/clarification-on-upstox-historical-candle-v3-private-research-data-retention-and-corporate-actions/18014) has a staff acknowledgment, not an affirmative completeness/permission answer. No email was requested or sent. Split/bonus factors and effective-date completeness, dividend effects, volume semantics and historical raw/PIT execution remain unqualified; no double adjustment occurs.

[Policy review](REAL-001-phase8-policy-decision.md): proposed version 2.0.0 is unchanged, unapproved and unactivated. A one-elapsed-day limit is unsuitable as the sole weekend/holiday freshness rule. Existing calendar data supports the descriptive comparison; changing the strategy contract's elapsed-day semantics requires a separately versioned change. The engine was not relaxed. No owner activation decision is requested while action, risk, execution-settings and research prerequisites remain missing.

The 24 genuine consolidated numeric financial facts across four periods remain in D3-06. These are permitted secondary numerical snapshots, not an original issuer filing/PDF corpus. Six actual model-selected factual claims and one mathematical Swing relationship revalidate against saved genuine evidence; all five previously rejected model claims/relations remain rejected. Cash-flow conflict and abstention remain explicit. Phase 7 Qwen 7B/Nomic executions are reused; Phase 9 verifies installed model availability without new inference. Prior 14B judge false positives still prevent broad semantic qualification. Current financial/event coverage, original publication times, EPS/shares, debt/equity and valuation remain incomplete.

## Assessment and publication

The actual D3-05 Swing result is **INSUFFICIENT_EVIDENCE**, with `policy_not_configured` and `eligibility_or_instrument_risk_unavailable`. Adjusted descriptive indicators remain separate from excluded raw-price strategy inputs; no entry/exit prices or purchasable quantity are issued.

The genuine D3-09 attempt stops at **factual_research_not_recommendation**. This first encountered gate does not replace the other readiness blockers. D3-10 has **zero real references, outcomes, positions or ledger entries** and no pending eligible outcome work. No recommendation was backdated or future performance manufactured. P9-09 is blocked, not passed. Short- and long-term historical reports remain useful but unqualified for publication.

## Executed local launch checklist

| Check | Result | Actual evidence |
|---|---|---|
| 1. Application start | PASS | Existing loopback API and frontend start with private file settings. |
| 2. Authentication | PASS | Real browser login succeeds; logout makes the protected endpoint return 401. |
| 3. PostgreSQL | PASS | SELECT 1 succeeds against the genuine database. |
| 4. Provider availability | PASS | Actual permitted Upstox calendar/identity/prices calls succeed; today’s candle remains absent. |
| 5. Ollama availability | PASS | Native service lists installed Qwen 7B/14B and Nomic digests. No new inference/download. |
| 6. Actual data | PASS | Genuine chart and 24 financial facts visible; final coherent window has 33 candles. |
| 7. Research and citations | PASS | All three actual historical reports visible; six facts and one relationship revalidated against immutable bundles. |
| 8. Stale/missing data | PASS | Before-close current-session match changes to missing October 23 after close; genuine browser verifies it. |
| 9. Exact blockers | PASS | Policy, risk, source/basis and research limitations remain visible; no publication is implied. |
| 10. Refresh without duplicates | PASS | Real refresh/recovery succeeds; duplicate logical revision sequences remain zero; UI read refresh preserves chart rows. |
| 11. Interrupted run | PASS | SIGKILL after genuine fetch but before price commit leaves data unchanged and releases lock; recovery succeeds. No mid-transaction kill claim. |
| 12. Private data | PASS | Token, owner key, database setting, grant, reports and screenshot stay outside Git with owner-only file permissions; grants unchanged. |
| 13. History and corrections | PASS | Existing append-only revisions and research retained; interruption/recovery checks preserve original research hashes. |
| 14. Start/stop safety | PASS | Task-owned API/frontend stopped and restarted; research/fact/revision counts and hashes unchanged before subsequent authorized refresh. |

This readiness is limited to the tested local manual beta, not cloud/public deployment, unattended scheduling, complete provider coverage, profitable strategy calibration or paper admission. Use the [runbook](REAL-001-runbook.md). Source expiry/revocation remains enforced. The actual interrupted process stopped after fetch and before commit; migration tests separately verify atomic rollback.

## Acceptance and validation

| Criterion | Result |
|---|---|
| P9-01 | PASS: exact Phase 8 head CI verified successful. |
| P9-02 | PASS diagnostic: October 22 lag resolved; October 23 absence recorded at final actual cutoff. Current signal freshness remains blocked. |
| P9-03 | Explicit unqualified action/volume status; no invented grant/factor. |
| P9-04 | Actual descriptive indicators checked; risk/eligibility and raw execution inputs missing. |
| P9-05 | Review completed; policy unchanged and unapproved. |
| P9-06 | Actual saved financial/model citations and rejections revalidated. |
| P9-07 | Genuine engine execution abstains with exact reasons. |
| P9-08 | PASS safeguard: mandatory publication gate rejects actual attempt. |
| P9-09 | BLOCKED: no qualified publication/reference exists. |
| P9-10 | PASS: genuine authenticated dashboard, all horizons and missing-session state checked without HTTP mocks. |
| P9-11 | PASS within limited local beta scope: all 14 operational checks executed above. |
| P9-12 | PASS: rights, research-only restrictions and ₹0 scope preserved. |

Full backend/worker: **662 passed**. PostgreSQL: **168 passed, zero skips**. Migration upgrade/repeat/downgrade/re-upgrade/atomic rollback passed. Three contract/evaluation/risk validators and ten script tests passed. Production frontend build passed. All **five browser fixture workflows passed** (38.6 seconds) after correcting the fixture key. Final-commit CI is reported at delivery; actual before/restart/after-close browser checks are separate from fixtures. One existing Python deprecation warning remains. An initial local fixture browser attempt used an undersized test-only access key and failed authentication; this was an environment setup error, not bypassed authentication.

[Redacted execution metadata](../evidence/real-001/phase9-execution.json) contains counts/statuses only. Private `phase9-owner-report.md` and JSON records retain actual values, source lineage and cutoffs outside this public repository. No new models, paid services, provider messages, deployment, broker orders, merge or D3-11–13. **Stop after Phase 9; REAL-001 remains PARTIAL.**
