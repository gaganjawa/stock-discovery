# REAL-001 — provider verification and activation matrix

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
