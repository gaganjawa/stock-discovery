# REAL-001 Phase 4 — permission findings and stop condition

20 October 2026 (IST). **PARTIAL / genuine INFY acceptance BLOCKED.**
STK-004/005/006/007, D3-02 source feasibility. No infrastructure changes.

## Meaningful new evidence

The previous blanket description of Upstox storage/replay rights as unresolved
is superseded for **private, single-owner, non-redistributed market data**.
Public replies on Upstox's developer community establish the narrower uses below.
This is not an operational grant for every endpoint, corpus or processing use.

Sources reviewed:

- **U1:** [1 September reply by Anand_Sajankar](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3).
  His public profile identifies him as “Software Engineer, Upstox”. The reply
  permits local historical data, private research/backtests, features, ML and
  retention of derived statistics/model artifacts, subject to API terms/limits.
  Exact clause: “No separate data licence is required for this private, non-commercial use case.”
- **U2:** [19 October reply by Ketan](https://community.upstox.com/t/clarification-on-upstox-historical-candle-v3-data-usage-for-personal-backtesting-and-ml-research/18061/2).
  Posted with title “Developer @ Upstox”. Numbered answers 1/3/7 permit historical
  OHLCV retention, statistical/ML/strategy work and this private use without an
  additional licence. Exact clause: “Yes, statistical analysis, machine learning and strategy development are permitted.”
  Answer 6 says splits/bonuses are back-adjusted; dividends are not.
- **U3:** [19 October reply by Ketan](https://community.upstox.com/t/clarification-on-storing-upstox-nse-market-data-locally-for-private-research-backtesting/18112/2).
  Answers 1–4 allow local API/WebSocket market-data storage, long-term retention,
  research and internal replay. Exact clause: “We don’t impose a retention limit.”
  Answers 5–6 exclude redistribution from this permission and require an account.
  These are attributed provider-community statements, not a separately executed
  licence. Public JSON confirmed post authors/titles; forum staff flags are false,
  which is not being represented as administrator verification.
- **U4:** [Analytics Token documentation](https://upstox.com/developer/api-documentation/analytics-token/)
  and [Historical Candle V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
  establish authenticated read-only data access and candle retrieval.
- **U5:** [Upstox terms, Intellectual Property Rights](https://upstox.com/terms-of-use-and-privacy-policy/)
  reserve proprietary rights and restrict commercial/public reuse without consent.
  Exact limiting phrase: “for commercial or public purposes”. These restrictions
  do not negate U1–U3's express private API-data guidance. The personal-data privacy
  section is not a market-data licence.

Web extraction could not retrieve U2/U3 topic bodies; their public Discourse JSON
endpoints `/t/18061.json` and `/t/18112.json` returned HTTP 200 and the actual replies.
No login, bypass, posted message, market-data request or token use occurred.

## Nine requested operations

| Operation | Finding | Scope and evidence |
|---|---|---|
| Historical OHLCV retrieval | **PERMITTED** | Authenticated documented endpoints, rate limits; U2 answer 1 and U4. |
| Local PostgreSQL storage | **PERMITTED** | U1 and U3 answers 1–2 allow local raw/normalized market data and long-term retention. PostgreSQL is a local storage implementation, not a new distribution use. |
| Quantitative indicators | **PERMITTED** | U1 feature/statistical derivation and U2 answer 3. |
| Historical replay/backtesting | **PERMITTED** | U1; U3 answers 3–4 explicitly permit backtesting/internal replay. Data-quality and look-ahead checks remain separate. |
| Local financial analysis | **PERMITTED for historical market-data analysis; UNCLEAR for fundamentals/news/filings** | U1/U2 cover market-data research. Their answers do not establish rights in third-party financial/news bodies or issuer documents. |
| Local Ollama inference | **PERMITTED within private market-data ML/AI research (inference from U1/U2); UNCLEAR for the financial corpus** | Model brand is immaterial to private processing, but corpus permissions are not transferable. No external processor, publication or redistribution. |
| Embedding generation | **PERMITTED for the same private market-data features (inference from U1/U2); UNCLEAR for filing/news text** | Broad private ML/feature permission supports that use; it does not license another source's documents. |
| Derived recommendation storage | **PERMITTED for private market-data research outputs (inference from U1/U2)** | U1 answers a private research question explicitly excluding signal redistribution; U2 allows strategy development and own-account use of findings. Private retained analytical outputs fit that scope. No financial/news corpus rights or public signal service inferred. |
| Prospective paper-performance evaluation | **PERMITTED as private market-data research (inference from U1/U2/U3)** | Evaluating private strategy findings against subsequently retrieved observations fits the confirmed research/analysis scope. This does not qualify inputs, authorize orders or admit paper positions. |

No reviewed clause expressly prohibits these nine private operations as a whole.
Commercial/public redistribution is outside the confirmed scope; news/filing
corpus rights stay blocked. No active grant was
created with invented expiry, attribution or deletion conditions.

## Minimum financial-source requirement and decisive blocker

One complete run needs permission to acquire a genuine document, temporarily parse
it, store its revision/text and extracted facts, compute ratios, retain local
embeddings, run local inference, and retain cited private research. Permission
for transient viewing alone cannot satisfy A5–A9/A11.

**Infosys:** [Terms of Use, LIMITED LICENSE](https://www.infosys.com/terms-of-use.html)
allows access/display but says “You shall not modify, copy” and restricts
reproduction/derivative uses. The opening terms give specific-area terms priority;
the limited-license section also recognizes materials with their own licences.
No applicable report-specific exception was established. Persistent report copies
are prohibited under the general licence absent an exception/permission. Automated
retrieval, temporary parsing, extracted-fact retention, embeddings and AI analysis
remain **UNCLEAR / NEEDS CONFIRMATION** for the requested pipeline. This is not a
legal conclusion that ordinary personal reading or all uses of facts are forbidden.

Best official candidates remain:

- [Integrated Annual Report 2025–26](https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-26.pdf),
  from the [annual index](https://www.infosys.com/investors/reports-filings/annual-report/annual-reports.html).
  Candidate for annual income, balance sheet and cash flows; no tables/values or
  exact publication timestamp were verified by extraction.
- [Quarterly-report index](https://www.infosys.com/investors/reports-filings/quarterly-results.html),
  for quarterly financial statements; ingestion rights remain unqualified.
- [Q1 FY27 results advertisement](https://www.infosys.com/investors/documents/exchange-filings/2026/advertisement-pertaining-financial-results-q1fy27.pdf)
  and [23 April board-outcome candidate](https://www.infosys.com/investors/documents/exchange-filings/2026/outcome-board-meeting-23apr2026.pdf),
  for results/announcements, not assumed to contain every requested statement.

Legitimate alternatives: SEC public EDGAR reuse was established previously, but
runtime access was denied and was **not retried**. Owner-provided lawfully obtained
full EDGAR document plus original URL/availability metadata is a possible input
for review, not a fabricated excerpt or accepted automatic retrieval. NSE's
[website terms](https://www.nseindia.com/static/nse-terms-of-use) and
[data policy](https://www.nseindia.com/static/market-data/nse-data-policy) do not
license a scraping fallback. BSE's [corporate-data service](https://marketdata.bseindia.com/)
needs applicable usage terms; no subscribed rights were established.

**Stop condition reached:** no usable permitted financial corpus established.
No additional adapters, schemas, mock pipelines, tests or handlers were added.

## Precise owner actions — drafts, not sent

### One consolidated Upstox clarification

To Upstox Support / Developer API team:

I use an authenticated Analytics Token for a private, single-owner application on
my Mac, with no redistribution, public display, cloud AI or broker orders. Your
community replies in topics 17302, 18061 and 18112 confirm local market-data
retention, private ML/AI research and replay. Please confirm the remaining corpus scope:
(1) do the same permissions cover your income-statement, balance-sheet, cash-flow and news APIs, including
local fact extraction, document/text retention, embeddings and Ollama inference;
(2) what attribution, deletion-on-revocation/account-closure or third-party-content
conditions apply? Please link the applicable clauses and distinguish any excluded
content. Separately, can Historical Candle V3 supply original unadjusted prices or
point-in-time adjustment factors/effective dates? The current guidance says splits
and bonuses are back-adjusted, which matters for historically accurate replay.
No additional token or paid service is requested.

### Infosys IR permission request

To Infosys Investor Relations:

May I automatically retrieve your 2025–26 annual report and subsequent quarterly
results/announcements for my own private, non-commercial research, retain the
original documents and source-labelled extracted financial facts locally, compute
ratios, create local embeddings, and use local Ollama inference to retain cited
research notes? Nothing will be redistributed, sold, sent to cloud AI or used to
place orders. Your website's LIMITED LICENSE restricts copying and derivatives;
please identify an applicable investor-report exception or provide permission,
including attribution, retention/deletion and automated-access conditions. I need
full source-document provenance, not permission merely to view the website.

Owner may send these drafts or explicitly authorize sending through an available
channel. Owner approval alone cannot replace provider rights. A full lawfully
obtained EDGAR filing with provenance is another reviewable alternative.

## Actual execution and acceptance

A1 **BLOCKED** (financial-source rights/access). A2–A9 **BLOCKED by A1**: no genuine
filing parsed, figures verified, persisted facts/citations, embeddings, retrieval,
local research or claim validation. A10 **BLOCKED technically**: no operational
market-data grant/configuration activated; calendar/completeness/action coverage
and approved policies remain missing. Newly confirmed back-adjustment semantics
also conflict with the adapter's current `raw` representation; do not relabel or
use these candles as raw. No data ingestion was attempted under that mismatch.
A11–A13 **BLOCKED by upstream acceptance**: no INFY publication, dashboard record
or prospective reference. A14 **NOT STARTED**; no actual future outcome exists.

Ollama's Phase 3 verified models remain historical readiness evidence, not Phase 4
financial execution or qualification. No AI call was justified without eligible
financial evidence. No financial figures/corpus or tokens are in this report.

Code baseline remains Phase 3 `5b1a055`: 606 tests, 164 DB cases (zero skips), five
browser workflows and CI passed. Phase 4 changes only permission/acceptance
records. New CI is reported on PR #12; prior results are not presented as a new
real-data run. No local regression rerun was needed for document-only changes;
the PR CI executes the full requested regression, DB/migration/build/browser suite.
Costs: **₹0**. No external deployment, purchase, provider message or broker order.
