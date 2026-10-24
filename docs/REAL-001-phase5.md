# REAL-001 Phase 5 — actual numerical evidence, PARTIAL

21 October 2026 (IST). STK-014/015/046/048/052/059/060; existing D3-02–10.
Continue draft PR #12; no merge, deployment, purchase, order or D3-11–13 work.

## Actual sources and private execution

The existing Upstox Analytics Token retrieved the NSE instrument master, dated
NSE sessions, V3 daily candles and consolidated yearly income, balance-sheet and
cash-flow API responses. These are genuine authenticated observations, not test
responses or issuer PDFs. The private PostgreSQL database contains 31 observed
sessions, one INFY identity, 27 candles, three numerical evidence snapshots and
24 financial facts (20 reported facts and four calculated net margins), covering
four annual reporting periods. Original filing publication times are unavailable;
availability/publication fields conservatively use observation clocks. Period
boundaries use Indian financial-year dates, separately from those clocks.

The API reports business revenue separately from total revenue including other
income. Extraction uses the precise Revenue line, verifies the income addition
and profit-before-tax minus tax, and verifies asset and liability components.
The summary's operating-profit label is not used to invent an operating margin.
Cash-balance movements do not reconcile to the supplied total cash-flow lines;
that discrepancy remains in retrieved evidence. Debt, EPS units, total equity,
capex, valuation inputs and official event coverage remain unverified or missing.
No cash-flow reconciliation items or shares outstanding are invented. An actual
key-ratios response was also inspected, but lacks a verified reporting/valuation
as-of basis and does not resolve EPS, operating margin or debt; it is not joined
into period-aligned facts.

Exact source figures, source response hashes, model diagnostics, source grants,
UI screenshot and run results remain in the owner's private local evidence folder
and database. This repository is public: no provider dataset, generated research,
credential, private grant or actual-data screenshot is committed or redistributed.
The final owner report can reference the private evidence. Public execution
metadata is in `evidence/real-001/phase5-execution.json`.

## Source-rights decision

Phase 4 U1–U3 establish private API market-data retention and research. The
[Analytics Token documentation](https://upstox.com/developer/api-documentation/analytics-token/)
explicitly includes fundamentals; the documented
[income statement](https://upstox.com/developer/api-documentation/get-income-statement/),
[balance sheet](https://upstox.com/developer/api-documentation/get-balance-sheet/)
and [cash flow](https://upstox.com/developer/api-documentation/get-cash-flow/)
are structured numerical Market Data APIs. Applying that broad private API-data
research guidance to these numerical observations is an **explicit scope
inference**, not a new signed licence or permission to copy third-party text.
Full issuer PDFs, news/article bodies, external AI, redistribution, export,
training and historical reconstructed replay remain excluded.

The private D3-02 configuration allows acquire/store/extract/derive/embed and
private shadow evaluation for the numerical source. The existing `filings`
storage scope is used only as the D3-06 container for numerical API snapshots;
it does not activate an issuer-document crawler. Thirty-day retention/review,
immediate deletion and attribution are conservative **local operational limits**,
not invented provider-imposed terms. No permission email or manual upload is
required. The grant is reloaded before use and is not shipped as an active default.

## Corrected price semantics

V3 observations are explicitly `split_bonus_adjusted`, never `raw`. The revision
fetch clock anchors the observed adjustment basis. Refreshes append revisions,
including unchanged adjusted prices, and refresh the entire bounded window;
a seven-day overlap cannot detect older back-adjustments. The chart and
descriptive indicators use only the latest coherent observation batch. Older
stored raw labels are neither rewritten nor admitted as verified raw inputs.

D3-03 rejects double adjustment and reconstructed-PIT use of this series. The
raw execution/strategy input path excludes it pending action qualification.
D3-05's existing indicator functions calculate descriptive price-only features;
relative volume is unavailable because provider volume-adjustment semantics are
unverified. Dividends are not represented as total returns. D3-10 may retain
later observation receipts but cannot compute a qualified return from an
unverified adjustment basis or unsupported action. No outcome is fabricated.

## Research, UI and publication

Genuine D3-07 PostgreSQL fact retrieval, full-text lookup and Nomic semantic
retrieval executed. Local qwen2.5-coder:7b generated actual financial responses.
Early runs exposed native Ollama JSON-grammar incompatibilities. Generation now
uses a structural schema projection, while the original full contract and exact
citation/fact validators remain authoritative. Numeric assertions cannot hide
inside free-form inference claims. The issuer-document adapter explicitly rejects
reuse of the Upstox numerical-source grant for PDF/HTML retrieval. Model digests, prompt hashes, conservative
budget reservations and actual latency remain recorded; unsuccessful runs stay
immutable rather than being overwritten or silently retried.

Three fact-only v1.2 runs passed exact fact/citation parity using actual Nomic
embeddings and qwen generation (46.5–47.9 seconds each). A discovered validator
bug that promoted a model abstention to WATCH was corrected and regression
tested: the new runs retain INSUFFICIENT_EVIDENCE. Earlier records are preserved.
The subsequent v1.3 broader-research request failed citation membership/locator
validation for all three horizons (47.3–51.1 seconds per generation). Those
outputs were rejected. The current prompt has **not** passed broad financial
research acceptance; successful fact copying is not financial-reasoning
qualification. No independent semantic judge or bounded investigation acceptance
is claimed. No generated BUY proposal is a published recommendation.

All three D3-05 assessment entry points execute with actual observed evidence,
and abstain because real strategy policies and eligibility/risk coverage are not
configured. This is not a calibrated financial-engine pass. D3-09 requires an
explicit real strategy/horizon configuration; none is manufactured. Actual publication attempts for all three horizons returned
`real_policies_required`; an actual subsequent-observation pass found no eligible
references. No real recommendation or D3-10 prospective reference is claimed. No paper admission is
bypassed. The actual browser workflow displays INFY prices, financial facts,
source locations, descriptive indicators, model-run history and the three
insufficient-evidence states. Original publication dates are labelled unknown.

D3-04 ingestion can opt into dated calendar refresh and numerical financial
statements through the existing handler (`refresh_calendar` and
`financial_statements`). Calendar refresh is deliberately bounded to a 40–44-day
configured price window plus a closure buffer. Research/publication/observation
scheduling is not activated; unattended end-to-end operation is not claimed.

## Acceptance status

| Item | Actual result |
|---|---|
| A1 | PASS for retrieved observations and explicit basis; action/volume/PIT qualification remains incomplete. |
| A2 | PASS: three genuine numerical financial endpoints, four annual periods. |
| A3 | PARTIAL: units/periods and available arithmetic reconciled; provider conflicts and missing line items remain explicit; no independent issuer corroboration. |
| A4 | PASS within the documented private numerical-data scope inference and local limits. |
| A5 | PARTIAL: real descriptive price indicators; three policy-gated assessments abstain. |
| A6 | PASS for actual retrieval, embeddings and local generation; financial qualification is not established. |
| A7 | PARTIAL: three fact-only runs passed; all three broader-research runs failed exact citation validation and abstained. Financial reasoning is not qualified. |
| A8 | BLOCKED: no explicit real strategy/horizon configuration and no qualified complete research. |
| A9 | PARTIAL: actual evidence dashboard verified; no publication exists to display. |
| A10 | BLOCKED by A8; no prospective reference fabricated. |
| A11 | NOT ACCEPTED: no published reference or mature eligible future outcome; adjustment safeguards preserved. |
| A12 | PASS: private processing only; no unauthorized admission, redistribution, purchase, deployment or order. |

Local validation: 617 backend/worker tests; all 164 PostgreSQL integration tests
with zero skips; complete migration lifecycle including atomic rollback; three
contract validators; 10 script unit tests; production frontend build; five browser
E2E workflows. A fresh prompt/model targeted suite passed 38 tests. Genuine
no-mock browser checks separately verified prices, facts, citations, unqualified
model history and absent publications across all three horizons. CI is reported by the GitHub checks on draft PR #12; prior Phase 4 CI is not
counted as current validation.

Remaining blockers are the broad model output/citation failure, absent semantic
qualification, missing/ambiguous financial and event inputs, unqualified action
and volume/PIT coverage, absent approved real policies/risk inputs, and therefore
publication, prospective references and unattended end-to-end acceptance.
Historical synthetic acceptance remains separate. REAL-001 is **PARTIAL**, not
complete. No paid use, deployment, broker order, merge or later-package work.
