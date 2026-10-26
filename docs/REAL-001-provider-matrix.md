# REAL-001 — provider verification and activation matrix

**Current Phase 5:** [Narrow numerical-data activation](REAL-001-phase5.md#source-rights-decision) supersedes earlier blanket financial-corpus blockers for private structured Upstox numerical API facts. This is explicitly an inference from the broad private API market-data guidance and documented fundamentals scope. Issuer PDF and article-body rights are not activated. Provider conflicts, corporate-action/volume semantics and original publication dates remain unqualified. The historical rows below are preserved as prior findings, not current activation status.
Phase 5 final checks: 617 backend/worker tests and 164 PostgreSQL tests (zero skips) passed; actual fact-only Ollama parity passed, broader research failed citation validation; all three actual publication attempts remain blocked by `real_policies_required`. See [Phase 5 evidence](REAL-001-phase5.md).

**Phase 4 supersedes the earlier Upstox market-data uncertainty:** [Nine-operation matrix, exact clauses and owner drafts](REAL-001-phase4.md). Provider developer replies permit private local market-data retention, ML/AI research and replay. This does not establish filing/news corpus rights or every output/evaluation use. Historical-candle adjustment semantics require technical correction before raw-data ingestion. No active grant created.

Verified **19 October 2026**. STK-004/005/006/007, D3-02. API reachability,
provider permissions, software acceptance and investment qualification are separate.
This record grants no rights. No paid subscription was activated.

| Source | Availability, authentication, price | History, identity, rate limits | Storage, replay, AI, attribution | Decision |
|---|---|---|---|---|
| Upstox | [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/) is free, read-only, lasts one year; market APIs need no static IP. Owner supplied a token. | [V3 daily history](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) documents daily history from 2000 and a decade per request. Adapter deliberately caps requests at 366 days. [JSON instrument master](https://upstox.com/developer/api-documentation/instruments/) supplies NSE EQ identity. [Standard limits](https://upstox.com/developer/api-documentation/rate-limiting/) are 50/second, 500/minute, 2,000/30 minutes, per user/API. | [General terms](https://upstox.com/terms-of-use-and-privacy-policy/) restrict commercial/public reuse and retain proprietary rights. These do **not establish a specific retention period, archival replay, local embedding/inference, paper-evaluation or attribution licence** for this installation. Unknown uses remain denied by D3-02. Read-only API diagnostics are owner-authorized and do not create a storage grant. | Preferred ₹0 candidate. Actual identity, candles, calendar, fundamentals and news access verified. Operational persistence remains unactivated. |
| NSE direct | [EOD/historical subscription](https://www.nse.in/static/market-data/eod-historical-data-subscription) offers official paid data; agreement and commercial terms needed. No subscribed credentials. | Official data products exist; approved machine feed, instrument/calendar coverage and feed-specific limits must be confirmed. | [Website terms](https://www.nseindia.com/static/nse-terms-of-use) prohibit systematic automated collection. [Data policy](https://www.nseindia.com/static/market-data/nse-data-policy) requires an agreement describing intended uses. No website scraping fallback. | Blocked; no feed purchase. |
| BSE direct | [Information-products tariff](https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf) describes licensed real-time, EOD, historical and corporate data. [Corporate-data service](https://marketdata.bseindia.com/) exists. | Product-specific delivery, identity/history coverage, authentication and quotas not qualified here. BSE identity alone does not prove an NSE listing. | Retention, replay, automated processing, AI and attribution require the applicable licence; not inferred from website access. | Blocked; no subscribed feed. |
| Zerodha Kite | [Official pricing](https://www.zerodha.com/products/api/) lists market-data/history at ₹500/month. No paid app activated. | [Daily history](https://kite.trade/docs/connect/v3/historical/) and [instrument master](https://kite.trade/docs/connect/v3/market-quotes/) documented; access token required. Account-specific quota allocation not verified. | [API terms](https://www.kite.trade/terms/) restrict public redistribution; do not presume storage/replay/AI rights from a subscription. | Outside initial ₹0 target; no purchase. |
| Infosys investor relations | [Reports and filings](https://www.infosys.com/investors/reports-filings/) and [2026 20-F](https://www.infosys.com/investors/documents/exchange-filings/2026/form20f-2026.pdf) are discoverable. | HTML/PDF disclosures; no verified automatic feed/parser coverage in this delivery. | [Terms](https://www.infosys.com/terms-of-use.html) offer limited access/display rights; automated retention/extraction/embedding qualification remains unresolved. | Candidate primary source; no document ingested. |
| SEC EDGAR / Infosys | [Public data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces/) need no API key. [Fair access](https://www.sec.gov/about/developer-resources) requires identified, efficient requests and caps aggregate traffic at 10/second. | Infosys CIK 1067491; one identified companyfacts request returned **HTTP 403** from this runtime. No retry using changed identities, proxy or access-control workaround. | API availability is documented; runtime access is blocked. No grant or retained financial corpus created. | Alternative investigated; blocked in this environment. |

## Verified Upstox ancillary APIs

- [Market timings](https://upstox.com/developer/api-documentation/get-market-timings/): authenticated NSE session response verified for 16 October 2026. The current ingestion adapter consumes already persisted, permitted observed sessions; automatic calendar acquisition is **not wired**. No calendar is fabricated from weekdays or daily-bar midnight labels.
- [Income statement](https://upstox.com/developer/api-documentation/get-income-statement/), [balance sheet](https://upstox.com/developer/api-documentation/get-balance-sheet/), [cash flow](https://upstox.com/developer/api-documentation/get-cash-flow/): actual Infosys responses returned consolidated, crore-denominated data. Only response-field/availability metadata retained. Original filing publication dates and source documents are not established by these responses. They are not yet D3-06 filing evidence.
- [News](https://upstox.com/developer/api-documentation/get-news/): instrument-key query returned 10 Infosys items on its first page. Documentation limits this feed to the preceding seven days, at most 30 instrument keys per request. This is **provider news**, not official exchange announcements or comprehensive news. No article text retained or ingested.
- [Corporate actions](https://upstox.com/developer/api-documentation/get-corporate-actions/): documented candidate; actual endpoint/normalization not qualified. Existing D3-03 split/bonus/dividend logic is unchanged; action coverage remains missing.

## Minimum remaining source action

The token is configured privately; no further token is needed. Obtain the applicable
Upstox/account permission evidence for private historical retention, automated
financial derivation, local embedding/inference, prospective paper evaluation,
retention/deletion and attribution. Record only the allowed uses in the existing
D3-02 `Grant` contract. Written provider clarification is an option when published
terms do not answer these points; no message has been sent on the owner's behalf.

Keep external AI, training, redistribution/export, backups and reconstructed replay
disabled unless separately supported. A working token must never auto-create an
active grant. A provider permission blocker is not a claim that private use is
prohibited; it means the required use-specific evidence has not been established.

## Phase 2 SEC clarification

SEC's [webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
expressly permits reuse of public EDGAR filing content. The genuine 2026 INFY
20-F direct request still returned HTTP 403 in this runtime. This distinguishes
reuse permission from technical access; no access-control workaround or active
grant was created. Upstox retention/AI evidence remains unresolved; the owner
confirmed no additional evidence is available. See [Phase 2](REAL-001-phase2.md).

## Phase 3 use-specific review — 20 October 2026

No new grant, purchase or provider communication. The following are permission
findings, not legal conclusions that every unconfirmed private use is prohibited.

| Candidate | Retrieval | Retention/extraction | Quant/replay | Embeddings/local AI | Prospective evaluation | Exact missing evidence |
|---|---|---|---|---|---|---|
| Upstox Analytics | Read-only API access documented and previously probed | Unresolved use-specific retention/deletion and derived-data rights | Unresolved for retained/replayed installation data | Unresolved | Unresolved | Applicable account/data-provider terms or written authorization covering each intended use, attribution and retention duration. Token success is insufficient. |
| Infosys IR annual/quarterly disclosures | Public document links found; automated pipeline grant not established | Site terms restrict reproduction; no report-specific exception verified | Not established | Not established | Not established | Permission for automated document retrieval, private document/fact storage, deterministic derivation, local embeddings/inference and subsequent research evaluation, with attribution/retention conditions. |
| NSE official website/data service | Website automation restricted; permitted feed requires applicable agreement | No applicable agreement | No applicable agreement | No applicable agreement | No applicable agreement | Official feed licence scoped to this installation; do not substitute website scraping. |
| BSE corporate-data service | Official service identified, access not activated | Licence not supplied | Not established | Not established | Not established | Applicable corporate-data delivery/usage licence and NSE identity mapping; public links are not an authorization. |
| SEC EDGAR | Prior identified filing request blocked, no retry in Phase 3 | Public EDGAR reuse documented by SEC FAQ | Runtime corpus unavailable | Runtime corpus unavailable | Runtime corpus unavailable | Legitimate authorized access; no bypass or alternative request identity attempted. |

Official primary candidates identified (not ingested):

- [Infosys integrated annual report 2025–26, PDF](https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-26.pdf).
  Reporting-year label 2025–26; exact publication timestamp and table periods not
  verified by ingestion. Discovered through the official annual-report index.
- [Infosys Q1 FY27 financial-results advertisement, PDF](https://www.infosys.com/investors/documents/exchange-filings/2026/advertisement-pertaining-financial-results-q1fy27.pdf).
  Candidate quarterly disclosure; exact publication timestamp, statements/scope,
  completeness and units remain unverified. Not substituted for a full filing.
- [Infosys board-meeting outcome, PDF](https://www.infosys.com/investors/documents/exchange-filings/2026/outcome-board-meeting-23apr2026.pdf).
  Candidate announcement; filename date is not a verified publication timestamp.

Supporting terms/product URLs: [Infosys terms](https://www.infosys.com/terms-of-use.html),
[annual index](https://www.infosys.com/investors/reports-filings/annual-report/annual-reports.html),
[Upstox Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/),
[NSE terms](https://www.nseindia.com/static/nse-terms-of-use),
[NSE data policy](https://www.nseindia.com/static/market-data/nse-data-policy),
[NSE copyright](https://www.nseindia.com/static/nse-copyright),
[BSE official corporate-data service](https://marketdata.bseindia.com/).
No raw report, restricted financial table or API content was retained for this review.
