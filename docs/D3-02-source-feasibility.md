# D3-02 — Rights and source feasibility

STK-004 / STK-005 / STK-006 / STK-007 · Reviewed **15 October 2026**

**Delivery:** public-source feasibility review plus tested use-specific permission contracts. **Activation: blocked for all real sources.** No account-specific written grant or quote was supplied, no provider contacted, and no account/API subscription activated. Public pages establish candidate routes and restrictions, not project permissions. The empty [real grant register](contracts/rights/grants.real.json) is intentional. This satisfies D3-02's “grants recorded or explicit blockers” delivery boundary; it does not close the underlying real-use approvals.

## STK-004/005 — Source, coverage and cost matrix

“Unverified” means no permitted sample or account-specific coverage confirmation was obtained. A documented endpoint is not proof of complete NSE membership or survivorship-safe history.

| Candidate / primary evidence | Documented route and useful scope | Material coverage gaps to verify | Cost evidence and rights disposition |
|---|---|---|---|
| [Kite Connect terms](https://kite.trade/terms/) | Broker API route | Delisted listings, historical universe, original revisions, adjustment provenance, actions and benchmark coverage unverified | Terms §2(a) prohibit virtual/mock trading and limit use to India; §4(b) restricts permanent API-content copies absent permission. **Blocked** for the proposed replay/paper/archive workflow. Charges communicated separately; no written project quote. Obtain an applicable written exception before reconsidering. |
| [Upstox historical V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) | OHLCV; daily bars documented from Jan 2000 with a decade per retrieval request | Instrument-by-instrument availability, delisted equities, point-in-time membership, actions, benchmark licensing and exact historical revisions unverified | Documentation does not establish this project's storage, replay, paper or AI-transfer rights. No all-in project quote or account terms recorded; pricing **unknown**, not assumed free. |
| [NSE EOD/history](https://www.nseindia.com/static/market-data/eod-historical-data-subscription), [data policy](https://www.nseindia.com/static/market-data/nse-data-policy) | Direct EOD files and historical trade products; contractual licensing route | Required daily OHLCV granularity, dated security master, delistings, original action revisions, financial-document rights and benchmark coverage need explicit product selection | [2026 tariff page](https://www.nseindia.com/static/market-data/products-tariff) links domestic/international schedules. [Domestic tariff §4](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) lists Capital Market historical trade data at ₹110,000/year/site, excluding applicable taxes. This is a different product from a negotiated daily-bar feed and **not a quote for this platform**. Territory, product suitability and fees remain unresolved. |
| [BSE data portal](https://marketdata.bseindia.com/), [information-product tariff](https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf) | BSE history/corporate-data candidate; secondary evidence reconciliation | Does not establish NSE universe coverage; issuer linkage, point-in-time documents/actions and revision archives unverified | Tariff PDF fetch returned HTTP 403 in this review; no current price is asserted. Written product/use/territory quote required. No access restriction bypass attempted. |
| [TrueData](https://www.truedata.in/) | Vendor advertises market-data, corporate announcement, corporate-data and news APIs and exchange authorization | Verify authorization for the exact product, full eligible NSE/delisted coverage, original revisions, financial scope and document delivery | Displayed desktop-plugin pricing is not a server/API licence quote. API/retention/paper/embedding/AI-transfer/backup rights and total costs unknown. |
| [Global Datafeeds](https://globaldatafeeds.in/) | Vendor lists market-data, fundamental and news APIs | Exact exchange entitlements, complete history/universe/actions, issuer mapping and revision availability unverified | Written server/API product quote and use-specific licence required. No entitlement is inferred from its product listing. |

No provider is selected. The useful next procurement artifact is a written daily-NSE-history + dated-universe + actions offer with explicit replay/paper and storage rights. Vendor/exchange authorization must be confirmed for that exact offer, not inferred from a marketing claim. No sales messages have been sent.

## STK-007 — Documents, facts and news

| Route | Feasibility evidence | Permission / coverage blocker |
|---|---|---|
| NSE announcements/RSS | [NSE RSS](https://www.nseindia.com/static/rss-feed) documents corporate-information feeds; [website terms](https://www.nseindia.com/static/nse-terms-of-use) remain applicable | Feed availability does not grant permanent PDF/text storage, extraction, embeddings, external-AI transfer or distribution. Confirm supported automated retrieval, revisions and retention. |
| BSE corporate filings | [SEBI's corporate-filings directory](https://www.sebi.gov.in/curation/corporate_filings.html) points to exchange disclosure routes | Automated delivery rights, original publication/revision clocks and duplicate exchange filings need verification. |
| Issuer investor-relations sites | Candidate per-issuer source for reports and results; no blanket issuer grant claimed | Each domain's terms, stable retrieval route, authenticity, dated revisions and permitted derived/AI uses must be recorded before enabling it. |
| Licensed news / vendor corporate APIs | TrueData and Global Datafeeds list relevant API products above | Headlines/metadata permission is not full-text permission. Confirm retention, syndicated-source rights, derived facts, model transfer, embeddings and backup deletion separately. |
| SEBI circulars/disclosures | Official regulatory context and primary-source documents | Not a market-price feed or complete issuer financial archive. Automated content uses remain subject to applicable terms and exact-source review. |

Price availability cannot substitute for long-horizon financial history. Missing document/news coverage must produce explicit missing evidence; manual uploading does not replace the automatic route. No scraper, source adapter or RAG pipeline is delivered in this package.

## Use and territory decision register

For **every real candidate above**, acquisition for this application, storage, extraction, derived indicators/facts, embeddings, external AI, historical replay, paper evaluation, export, backup and optional training are **unapproved until evidence is recorded**. Kite has the additional explicit restrictions described above. Absence of an express prohibition is not an allow decision.

Each approval must bind source, account, product scope, permitted uses, processing and destination countries, exact external processor(s), validity/expiry, attribution, retention/deletion including backups/derived artifacts, request quotas and approval evidence. Rights are rechecked on each use; a previously downloaded document is not permanently cleared for new uses. Unknown source/use, expired/revoked grants and region mismatch deny processing before transfer.

Hetzner CX23/Linux/Compose and restic/B2 remain the approved hosting design. The server, backup and AI-processing regions are **unset**. Any India-only term is an unresolved compatibility constraint; do not silently select a region, transfer data abroad, or reopen the host decision. The ₹3,000/month envelope remains a planning target; no compatible complete stack has been quoted. Record setup fees, ongoing data/API fees, usage/egress, taxes, currency and quote validity before any purchase. Paid calls and activation still need separate owner authorization.

## STK-006 — Exact scope and regulatory boundary

Current scope is one owner's private research software and virtual paper outcomes, with no clients, public recommendations, distribution, fees for advice or broker orders. This describes the product boundary; it is **not a determination of exemption or legal compliance**.

The [SEBI Research Analysts Regulations page](https://www.sebi.gov.in/legal/regulations/aug-2025/securities-and-exchange-board-of-india-research-analysts-regulations-2014-last-amended-on-august-6-2025-_96110.html) and [2026 SEBI research-analyst material](https://www.sebi.gov.in/sebi_data/attachdocs/feb-2026/1770375507051.pdf) are review references. No account-specific legal opinion is available. Before real integration, the owner must resolve broker/exchange obligations and any applicable registration or specialist-review requirements for the exact use. Public distribution, clients/advice, monetization or order execution requires a fresh scoped review; D3-02 authorizes none of these. Provider licensing remains an independent gate even for private use.

## Review checklist for written replies — prepared, not sent

1. Confirm product, account, eligible NSE series, history start per listing, delisted coverage, dated membership, calendars, symbol/ISIN revisions, raw/adjusted prices, corporate actions and benchmark rights. Identify unavailable fields explicitly.
2. Confirm private automated acquisition, exact-revision retention, historical replay and simulated paper evaluation; distinguish these from live brokerage orders.
3. Confirm extraction, derived facts/indicators, embeddings, specific external model processors and optional model training separately. State whether only metadata, excerpts or full text may be transferred.
4. List processing/backup/processor regions, attribution, redistribution/export limits, quota windows, deletion on expiry/revocation (including derived data and backups), and whether content-free audit tombstones may remain.
5. Supply account-specific approval evidence and tax-inclusive setup/monthly/usage quotes, currency, validity and termination terms. Owner separately authorizes activation after review.

## Software boundary and acceptance

`shared/stock_discovery_contracts/rights.py` supplies strict versioned grant/request/decision/cleanup contracts and `authorize` / `guarded_use`. Grants are immutable with tuple scopes. Combined operations need all listed permissions; external embeddings need both `embed` and `external_ai`, a permitted processor and destination. The trusted adapter must enumerate every actual use, supply current UTC time and load the current approved grant; payload text cannot authorize itself.

`guarded_use` reloads the grant, writes a content-free decision through the caller's audit function and calls the operation only when allowed. Audit failure stops the operation. Tests use callbacks with fictional data; there is no production provider adapter or credential access. This is a synchronous boundary, not a concurrency-safe grant store, aggregate quota counter or spend reservation system. Those transactional/runtime integrations belong to D3-03/04/06/074 work. Per-operation unit limits are enforced here; aggregate quotas and budgets are not claimed complete.

Cleanup returns an explicit plan for source content, derived artifacts and backups. Deletion deadlines are anchored to expiry/revocation and never extended by retries. Unknown terms request immediate cleanup; metadata tombstones require explicit permission. Actual storage deletion and backup expiry are later packages, not simulated successes.

Schemas and fixtures live under [contracts/rights](contracts/rights). Real grants are empty. Synthetic grants cannot authorize real requests. `backend/tests/test_source_rights.py` covers T03 denials before callbacks, revocation, expiry, region and processor mismatch, missing grants, retention, attribution, malformed contracts and cleanup. Existing v1/v2 historical fixtures and application behavior are unchanged.
