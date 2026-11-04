# STK-084 — Angel One SmartAPI evaluation and provider decision

5 November 2026 IST. D3-02 source feasibility / M1. Documentation-only review.

**Verdict: INSUFFICIENT EVIDENCE. Do not integrate or replace Upstox with SmartAPI.**
Confidence is high that the existing evidence does not qualify a switch; confidence
in Angel One's actual INFY OHLCV accuracy is absent because no authorized sample
was available. Public product capabilities are partly verified; applicable access,
data semantics and persistent-use conditions are not an accepted source packet.
This is not a finding that Angel One's prices are wrong.

Keep Upstox for the already authorized, guarded descriptive workflow. It is the
cheapest demonstrated route for that limited scope, with a free read-only token
and no market-data static-IP requirement [U1]. No candidate is yet established as
the cheapest **fully qualified raw-history/backtesting** provider. Advertised zero
API fees do not settle account, network, permissions or data-quality costs.

## Baseline, inspection and request boundary

Fetched current `origin/main` and branched from
`6a847326167f6e34798da5c55e7a669495cdae80`, the PR #39 merge. STK-083 and its support
wording correction are present. Reviewed [architecture](SD-ARCH-3.0.md),
[current board](SIMPLE-BOARD.md), [D3-02 feasibility](D3-02-source-feasibility.md),
[rights register](source-rights-register.md), [provider matrix](REAL-001-provider-matrix.md),
[later Upstox rights findings](REAL-001-phase4.md), [numerical-data activation](REAL-001-phase5.md),
[Breeze evaluation](STK-004-014-breeze-evaluation.md),
[source decision handoff](PRODUCT-ACCEPTANCE-HANDOFF.md), and
[STK-083 acceptance](STK-083-automated-infy-research.md).
Later scoped activation/acceptance supersedes older blanket availability blockers;
none establishes M1, M2, trading or paper admission.

Bounded inspection of repository references, existing private verification records
and matching environment-variable names found no SmartAPI app/session or explicit
SmartAPI grant. Private `ANGELONE` matches were watchlist symbols, not credentials.
This does not assert the owner has no account elsewhere. No credential values were
printed, no login was attempted, and no private configuration was modified.

| Probe prerequisite | Observed result |
|---|---|
| Pre-existing usable SmartAPI account/session | UNVERIFIED; none identified in inspected locations |
| Applicable static public IP registration | UNVERIFIED; no registration/egress evidence supplied |
| Existing explicit bounded evaluation authorization and source terms | Owner's conditional instruction is present; provider/account-specific evidence is absent |
| Current account quota available | UNVERIFIED without an eligible session and its request accounting |
| Decision | Do not issue the conditional probe |

**Authenticated SmartAPI historical requests: 0. All authenticated provider
requests: 0. Model/inference calls: 0.** Public documentation searches are separate
from historical acquisition. No market-data payload was fetched, no instrument
master was downloaded, no SDK installed/imported, and no database was opened.
No scheduler, subscription, account, OTP automation or order operation was activated.

## Official access, price and authentication findings

| Requirement | Classification and finding | Evidence |
|---|---|---|
| Historical API price | VERIFIED advertised API fee: ₹0, including historical data. This is not zero total ownership cost. | [A1], [A2] |
| Account requirement | VERIFIED documented client-account requirement for API consumption. An older signup guide says client ID is optional for registration; that does not establish account-free historical access. | [A3], [A4], [A5] |
| Account charges | PARTIALLY VERIFIED: published opening fee ₹0; first-year AMC ₹0. Thereafter non-BSDA ₹60 + GST/quarter, described as charged after the first trade in the quarter; qualifying BSDA tiers have nil or ₹100 + GST/year AMC. Owner eligibility and an entirely data-only account's actual charge remain UNVERIFIED. Do not trade to obtain data. | [A6], [A7] |
| Static IP, including data-only | PARTIALLY VERIFIED policy evidence: the official moderator says it applies to **all app types and API access**, including historical-only use. No account-specific exemption verified. | [A8] |
| Read-only exception | UNVERIFIED today. Older API categories and September 2025 guidance distinguished non-order APIs; do not use that to bypass the more recent all-app clarification. | [A2], [A8], [A9] |
| Historical interval/window | VERIFIED documented `ONE_DAY`, at most **2,000 days per request**; that is a request window, not total history or guaranteed candle count. | [A10], [A11] |
| Maximum lookback | PARTIALLY VERIFIED: moderator advertises NSE-equity interday data from 1990-01-01 and intraday from 2016-01-01. This is not an INFY listing-specific coverage guarantee. Actual earliest INFY bar, gaps, delisted instruments and original vintages remain UNVERIFIED. | [A12] |
| Candle quotas | VERIFIED published ceilings: **3/second, 180/minute, 5,000/hour**. Account-specific throttling and any additional daily allocation are UNVERIFIED; 5,000 is not a daily quota here. Limits are cumulative ceilings, not promised throughput. | [A13] |
| Session authentication | VERIFIED official SDK example uses client code, PIN and TOTP; returns JWT/refresh/feed tokens. Documentation also describes browser redirect authentication. No such flow executed. | [A14], [A15] |
| Expiry / daily reauthentication | PARTIALLY VERIFIED: September 2025 admin announcement says daily logout at midnight. Older December 2023 guidance said 24–28 hours and daily login. Plan for daily expiry, not indefinite refresh; exact current account/token reset timezone and lifetime remain UNVERIFIED. | [A9], [A16] |
| Unattended authentication | PARTIALLY VERIFIED technical support: the official SDK demonstrates programmatic TOTP/session creation. This does not prove a currently permitted, reliable unattended daily flow for this account after access-policy changes. No long-lived read-only equivalent to Upstox Analytics was established. | [A14], [A9] |

The official March 2026 announcement says order execution requires a registered
static IP from 1 April, permits primary/secondary IPs, and limits updates to once
per calendar week [A17]. The September 2025 announcement exempted non-order/GTT
APIs [A9]; the recently indexed moderator clarification explicitly applies an
Angel One condition to data-only use too [A8]. These are different scopes and
dates. Do not claim that NSE itself requires a static IP for historical reads.
The prudent current access decision is to require Angel One-compliant static-IP
evidence or an applicable documented exception before probing.

For this Mac, a local reserved LAN address is not a static public egress address.
An ISP static IPv4 service could add a recurring charge; availability, existing
entitlement and exact price are UNVERIFIED. No hosting change, VPN workaround or
new server is justified by this investigation. Cost model: ₹0 API fee + applicable
account charges + incremental static egress + existing compute/network cost.
Even the conditional ₹240/year non-BSDA AMC is not the whole operating cost.

## Candle identity, construction and qualification

| Question | Finding and remaining requirement |
|---|---|
| INFY identity | Target is NSE cash EQ, `INFY-EQ`, ISIN `INE009A01021`, established by the existing NSE reference. `1594` appears as the candidate SmartAPI token in public forum material [A18], not a fresh verified master. Before a future probe, independently corroborate exchange, EQ series and ISIN against the documented scrip-master route [A15]; a token or symbol alone is insufficient. |
| Request/response | Published historical API accepts exchange, symbol token, interval and from/to datetimes. Records are `[timestamp, open, high, low, close, volume]` [A10]. `status=true` and HTTP200 would establish transport success only. |
| Timezone/session | Published examples carry `+05:30`; the official daily index example uses midnight [A11]. That is a date label, not a verified exchange close or publication time. Actual INFY daily labels and inclusion boundaries are UNVERIFIED. Match every date against verified closed sessions. |
| Open/high/low/close | Field names are documented; exact auction inclusion, sampled versus all-trades extrema, close versus LTP/official closing auction methodology and revision rules are UNVERIFIED. Do not import another broker's definitions. |
| Volume | A moderator confirms individual-scrip volume is provided [A19]. Share/lot units, full-session population, auction inclusion and adjustment treatment are UNVERIFIED for NSE EQ. Neither an integer nor lot size 1 proves equivalence to NSE `TtlTradgVol`. |
| Split/bonus/dividend basis | UNVERIFIED. No authoritative raw selector, adjustment formula, dated factors or complete historical-vintage contract established. User reports of unadjusted prices and a moderator's link to docs do not certify raw semantics [A20]. |
| Corporate actions | No complete, documented SmartAPI split/bonus/dividend ledger with effective dates, correction history and coverage assurance was established. Corporate-action coverage remains UNVERIFIED; a chart or company article is not a complete API ledger. |
| Corrections and freshness | UNVERIFIED EOD finalization time, correction SLA and revision identifiers. An old inconsistency thread has moderator investigation responses, not a present-day quality guarantee; user explanations are not provider policy [A21]. No assumption that close +30 minutes means final data. |
| Completeness / expansion | No actual batch tested. Required: exact session membership, uniqueness, finite valid OHLCV, complete pages/window, original/current authorization, retrieval provenance and consistent adjustment vintage. Broader coverage advertising does not qualify additional stocks or survivorship-safe replay. |

SmartAPI cannot currently be described as an **authoritative raw OHLCV source**.
Even three exact matches would only corroborate that sample; they would not prove
raw behavior across corporate actions or complete historical availability.
Do not normalize mismatches, divide volumes by an assumed lot factor, reverse
unknown adjustments or stitch its candles into the Upstox batch.

## Reused same-date reference measurements

The [3 November triangulation receipt](STK-004-014-breeze-evaluation.md#original-eod--mcp--breeze-triangulation--3-november-2026-ist)
corroborated original NSE CM-UDiFF Final against official NSE MCP EOD for the three
requested dates. Original rows uniquely matched INFY/EQ/ISIN, `TradDt=BizDt` and
`SsnId=F1`; numeric mapping was
`OpnPric/HghPric/LwPric/ClsPric/TtlTradgVol`. `LastPric` was not substituted.
Original ZIP hashes and content-free equality evidence remain in that document.
Those checks are reused, not re-executed. Original numeric rows were intentionally
not retained for publication as a reusable dataset; none are reconstructed here.

Angel One versus those same official reference rows:

| Date | Open | High | Low | Close | Volume | Session |
|---|---|---|---|---|---|---|
| 2026-09-01 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NSE reference verified; Angel bar unavailable |
| 2026-10-23 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NSE reference verified; Angel bar unavailable |
| 2026-10-30 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NSE reference verified; Angel bar unavailable |

**Angel One: 0 numeric pairs compared; agreement/disagreement counts N/A;
15 field comparisons untested; 0 of 3 session correspondences tested.** This is
not a zero-error result and not a measured failure.

| Existing comparison only | Open matches | High matches | Low matches | Close matches | Volume matches | Matched session dates |
|---|---|---|---|---|---|---|
| NSE MCP vs original Final, three dates | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Breeze vs original Final, three dates | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 | 3/3 |
| Breeze vs official MCP, existing 41-session sample | 6/41 | 8/41 | 12/41 | 41/41 | 0/41 | 41/41 |

Thus the original three-date reference has **15/15 numeric agreements**; Breeze
has **3/15 agreements and 12/15 disagreements**. The broader Breeze sample has
67/205 agreements and 138/205 disagreements, including all 41 volumes. These are
exact finite-Decimal comparisons without tolerance, from the prior evaluation,
not new Angel One measurements. Breeze's failed sample does not establish which
construction difference caused it, nor prove another broker is accurate.

## Data-use permissions: do not confuse product guidance with a licence

Angel One's general terms refer to separate SmartAPI terms, documentation and
applicable policies [A5]. The reviewed pages did not establish the full applicable
account/data licence. Several SmartAPI docs/FAQ pages returned an authorization
notice on direct opening; official search-index excerpts and accessible official
announcements are identified below. No access-control workaround was attempted.

| Use | Classification / evidence |
|---|---|
| Historical quantitative analysis and strategy backtesting | VERIFIED as explicitly advertised uses in Angel One's official introduction [A2]; also supported by a moderator reply [A22]. Do not claim there is no permission evidence for backtesting. |
| Saving live data locally for later quant analysis | VERIFIED product guidance [A2]. This does not specify indefinite retention of a historical PostgreSQL corpus. |
| Persistent historical storage, retention period, corrections and deletion on closure/revocation | UNVERIFIED applicable obligations. No invented expiry or retention grant. |
| Retained deterministic derived indicators/statistics | PARTIALLY VERIFIED: historical quant analysis is supported; specific persistence, derived-copy and backup obligations remain UNVERIFIED. |
| Local AI inference, embeddings, model training or external AI transfer | UNVERIFIED explicit source permission. A user's AI-backtest question, SDK licence or generic algorithmic-trading marketing does not grant these uses. |
| Historical replay, retained outcomes, prospective paper simulation | Backtesting is supported at product level; complete retained-replay terms and paper-simulation permissions are UNVERIFIED. No admission gate changes. |
| Redistribution, publication and onward data access | Not established for this application; remain disabled. |

Forum statements are attributed provider guidance, not formal licence clauses.
Unknown obligations are a qualification gap, not a legal finding that all private
research is prohibited. Existing Upstox grants cannot be transferred to Angel One.

## Mac automation feasibility using the existing architecture

Inspected existing `worker/worker/providers/upstox.py`,
`worker/worker/stored_research.py`,
`shared/stock_discovery_analysis/{scheduling,swing_qualification}.py` and the
STK-083 operation record. No second scheduler or research engine is needed.

| Requirement | Reuse and SmartAPI-specific feasibility |
|---|---|
| Post-market execution | Existing calendar-aligned close +30 minute schedule is reusable. SmartAPI EOD readiness must be independently established; timing alone cannot qualify a batch. |
| Authentication/recovery | Existing bounded failure reporting is reusable. Daily expiry/static-IP checks need a permitted account flow before acquisition can be unattended. Do not retry login, generate OTPs or assume refresh survives midnight. |
| Sleep/wake catch-up | Existing D3-04 occurrence/lease/catch-up and launchd path can resume at execution time. It cannot make a sleeping Mac available, renew rights or restore an expired session. |
| Calendar validation | Reuse explicit stored calendar coverage and closure checks. SmartAPI daily timestamp labels cannot create the calendar; calendar-source authorization remains independent. |
| Idempotent ingestion | Existing immutable revision/provenance and request-budget contracts are reusable after provider qualification. A future adapter must be source-specific; the current Upstox raw/adjusted handling must not be relabelled. |
| Complete adjustment-safe batches | Existing full-window/page and single-batch checks are reusable, but SmartAPI's price/volume/adjustment semantics are missing inputs, not an implementation defect. |
| Failure monitoring | Existing durable outcomes distinguish denied, unavailable and failed work. A failed fetch must not silently replay a current-looking chart or make unlimited retries. |
| Analysis without acquisition | STK-083's stored-only path already permits guarded analysis of eligible stored evidence. Preserve strict/default and explicit one-session policy; two missing sessions remain unavailable. |
| Monthly operating cost | UNVERIFIED total for SmartAPI: API ₹0 plus conditional account/static-IP costs. Existing Upstox has lower demonstrated incremental integration and auth burden. |

Unattended **stored-evidence analysis** is technically supported by the existing
offline-validated path. Unattended **SmartAPI acquisition** is UNVERIFIED and not
activated. These are separate claims. No backdated availability or reconstructed
point-in-time performance can be inferred from a newly downloaded history.

## Provider comparison

Classifications: **VERIFIED** means the named documented claim or bounded
measurement is supported, not whole-provider qualification. **PARTIALLY VERIFIED**
means some evidence exists with material gaps. **UNVERIFIED** means no sufficient
applicable evidence. **FAILED** means a measured requirement failed, not that every
service offered by that provider fails. Integration effort is an architectural
assessment, not a vendor promise or numerical score.

| Provider | Cost / historical coverage | OHLCV accuracy / volume | Raw versus adjusted / corporate actions |
|---|---|---|---|
| Angel One SmartAPI | PARTIALLY VERIFIED: free API; account/static-IP total unknown. 2,000-day daily window; advertised deep history, actual INFY coverage untested. [A1–A13] | UNVERIFIED: no sample, units/session population unqualified. | UNVERIFIED adjustment basis, factors, complete action ledger and correction vintage. |
| Upstox | VERIFIED free Analytics Token and documented daily history from 2000, ten-year request window [U1–U2]. Existing 43-bar INFY batch verified for descriptive use; not full-history acceptance. | PARTIALLY VERIFIED: actual batch/provenance accepted; authoritative raw OHLCV and volume qualification incomplete. | PARTIALLY VERIFIED: existing provider guidance and adapter use split/bonus-adjusted prices, not dividend-adjusted. No verified raw selector or complete action/volume coverage. [U3], baseline records |
| ICICI Breeze | PARTIALLY VERIFIED: API/backtesting free; account charges not measured [B1]. Existing 41-session history; SDK broader coverage claims are not INFY guarantees. | FAILED for the saved reference sample: 12/15 three-date numeric disagreements; every sampled volume differs. | PARTIALLY VERIFIED: official SDK describes unadjusted history; measured values do not establish official raw OHLCV, complete actions or revision clocks. [B3] |
| Official NSE references | PARTIALLY VERIFIED: MCP free, five-year EOD, three months/call [N1]; licensed products require scope-specific cost. Prior full CM EOD tariff ₹100,000/year is not a one-stock quote [N2]. | VERIFIED for three original Final/MCP rows: 15/15 values match; full operational feed/corrections still unqualified. | PARTIALLY VERIFIED: original Final provides exchange reference fields; prior MCP raw description and corporate-action tool do not prove complete actions or point-in-time history [N2]. |
| TrueData | PARTIALLY VERIFIED: daily bars 10+ years advertised [T1]. Applicable historical-only API total UNVERIFIED; Velocity/Workspace prices exclude API [T2]. | UNVERIFIED: no permitted INFY comparison sample. Exchange-vendor status does not measure this product. | UNVERIFIED raw API/volume basis and complete action vintages for this installation; corporate-data product availability is not included coverage. |
| Global Datafeeds | PARTIALLY VERIFIED: historical API documented; applicable coverage and quote UNVERIFIED. | UNVERIFIED: no INFY reference comparison. | PARTIALLY VERIFIED: `AdjustSplits=false` documented [G1]; that does not settle bonus/dividend/volume semantics or complete actions. |

| Provider | Authentication / unattended acquisition | Storage, analysis and replay rights | Integration effort / present decision |
|---|---|---|---|
| Angel One | PARTIALLY VERIFIED SDK login; daily reset, static-IP and account execution unqualified. | PARTIALLY VERIFIED quant/backtesting guidance; retention/AI/full replay obligations UNVERIFIED. | New source-specific adapter/auth mapping plus qualification required. No integration justified now. |
| Upstox | VERIFIED documented year-long read-only token, no static IP for market data [U1]; recurring owner activation remains separate. | PARTIALLY VERIFIED overall: later provider guidance supports private market-data retention/research/ML/replay; applicable existing grants stay authoritative. Not blanket rights for news, filings or redistribution. [U3] | Existing adapter and guarded research work. Continue within current descriptive scope; cannot fill raw replay gap by relabelling. |
| ICICI Breeze | PARTIALLY VERIFIED: prior authenticated probe worked; documented app/session login and daily-session operation [B2]. No validated unattended recovery here. | PARTIALLY VERIFIED free historical backtesting [B1]; archival retention/revocation/AI terms unresolved. | Existing bounded probe only. Do not promote while measured OHLCV failure is unexplained. |
| Official NSE | PARTIALLY VERIFIED MCP access needs no account/key [N1]; supported application access and licensed-feed delivery need applicable terms. | UNVERIFIED standing stored-corpus/replay entitlement for this installation. A prior one-off informational comparison does not authorize collection. | Best raw-reference clarification target; no scraper or automatic ingestion. |
| TrueData | PARTIALLY VERIFIED credentialed API exists; subscribed auth/session/recovery untested. | PARTIALLY VERIFIED internal analysis advertised; published virtual/paper/simulation exclusions require resolution for intended outcome evaluation. Retention/AI use-specific terms UNVERIFIED. [T3] | New licensed source adapter only after all-in quote, permissions and raw sample. Conditional paid fallback. |
| Global Datafeeds | PARTIALLY VERIFIED access-key API exists; subscription/recovery untested. | PARTIALLY VERIFIED single-subscriber chart/analysis use; simulation restriction requires the stated approvals [G2]. Retention/AI/replay scope unresolved. | Alternative paid candidate, not a ready substitute for a failed rights review. |

The paid-provider comparison reuses existing evaluations, refreshed against the
listed official pages. No quote, subscription or vendor contact occurred. Full
exchange feed prices and desktop plan prices must not be passed off as a personal
historical API quote. No complete feasible raw/backtesting route can be priced
responsibly from this evidence.

## Decision answers and smallest justified next action

1. **Continue Upstox? Yes**, within existing grants and descriptive qualification.
   Preserve freshness warnings, observed availability and all non-actionable gates.
2. **Integrate Angel One now? No.** Free history and an SDK are insufficient reason
   to build an adapter before access and quality blockers are resolved.
3. **Authoritative raw OHLCV? Not established.** Require published construction,
   adjustment and share-volume definitions plus lawful same-date corroboration.
4. **Static-IP obstacle? Yes, potentially material on a Mac/home connection.**
   Current all-app guidance creates an access dependency; actual incremental cost
   is unknown. Do not infer an exemption from the older order-only announcement.
5. **Unattended daily analysis? Stored analysis yes via existing infrastructure;
   SmartAPI refresh unverified.** Official programmatic login is evidence of a
   mechanism, not proof of current compliant daily operation for this account.
6. **Replace or supplement Upstox? Neither is justified now.** No measured quality,
   rights or operational advantage compensates for the new integration burden.
7. **Minimum evidence before integration:** applicable account/static-IP and daily
   auth route; historical storage/derived-copy/retention and intended replay terms;
   official OHLC/volume/auction/adjustment/correction definitions; verified current
   INFY EQ identity; and an authorized bounded sample versus the existing three
   reference dates. A later complete qualifying window and action-spanning evidence
   are needed for promotion; three clean dates alone do not qualify M1 or replay.

The next smallest source decision is to resolve the **existing official NSE
raw-EOD delivery/use-rights question**, retaining Upstox's working components.
Reuse the [already drafted source questions](PRODUCT-ACCEPTANCE-HANDOFF.md), rather
than build another wrapper or rerun unchanged Breeze measurements. If that route
is unavailable, obtain the previously scoped historical-only INFY vendor quote and
explicit replay-use answer. If the owner still prefers Angel One, request only
the missing access/semantics/retention clarifications above before a one-request
evaluation. No message was sent. Do not invent a successor ticket ID or start its
implementation. M1/M2 and trading/paper admission remain blocked.

## Dated source register and limitations

All sources below were reviewed on **2026-11-05 IST**. An absent publication/update
date is explicitly unknown; search crawl times are not publication dates. Official
forum moderator statements are distinguished from user reports. Some forum pages
display a deleted-topic banner while still exposing text publicly; that text is
not treated as a current formal licence. Blocked pages were not bypassed.

| ID | Official source | Publication/update date and review limitation |
|---|---|---|
| A1 | [SmartAPI FAQ](https://smartapi.angelone.in/faq) | Date not shown. Free-history statement available in official indexed text; direct open returned authorization notice. |
| A2 | [Detailed introduction](https://www.angelone.in/knowledge-center/smartapi/detailed-introduction-to-smartapi) | Updated 2026-07-17. Product guidance on free history, quant/backtesting and saving live data; not a full data licence. |
| A3 | [Client ID requirement](https://smartapi.angelone.in/smartapi/forum/topic/4465/do-i-need-angel-one-client-id-to-use-smart-api) | Exact date not exposed; indexed as 2024-era. Moderator_2 says Angel One ID required. |
| A4 | [Signup guide](https://www.angelone.in/news/research/how-to-use-angel-brokings-smartapi) | Updated 2022-08-05. Optional ID at signup does not prove account-free API consumption. |
| A5 | [General terms, Smart API section](https://www.angelone.in/terms-and-conditions) | Date not shown. Refers to separate API terms and account relationship; complete applicable API/data terms not established. |
| A6 | [Account maintenance charges](https://www.angelone.in/support/charges-and-cashbacks/account-maintenance-charges) | Date not shown. Current displayed AMC tiers/conditions; owner tariff not inspected. |
| A7 | [2024–25 annual report](https://www.angelone.in/get-pdf-report-wp/29th-Annual-Report_Angel-One-Limited-2024-25.pdf) | Reporting period 2024–25, publication date not verified. Zero opening/first-year maintenance advertising; not account-specific terms. |
| A8 | [Historical-only static-IP clarification](https://smartapi.angelone.in/smartapi/forum/topic/5671/asking-for-static-ip-for-getting-api-for-historical-data/7) | Exact post timestamp unavailable in opened text; index showed Moderator_3 reply about 28 days old, approximately October 2026. No exact date inferred. All-app condition, not a formal licence clause. |
| A9 | [Static-IP transition/admin announcement](https://smartapi.angelone.in/smartapi/forum/topic/5254/important-updates-to-smartapi-in-compliance-with-sebi-guidelines/35) | Admin 2025-09-26. Non-order exemption, midnight logout and IPv4 support were stated at that time. |
| A10 | [Official indexed API documentation](https://smartapi.angelone.in/docs/ResponseStructure) | Date not shown; official indexed Historical section gives candle schema/window. Direct `/docs/Historical` returned authorization notice. No live semantics test. |
| A11 | [Historical-data release](https://smartapi.angelone.in/smartapi/forum/topic/4012/release-note-free-historical-data-access-for-indices-nse-nfo-bse-bfo-mcx-and-cds-with-smartapi) | Admin 2023-10-09. Daily index timestamp example and 2,000-day limit; old segment scope is not proof of current complete coverage. |
| A12 | [History extent clarification](https://smartapi.angelone.in/smartapi/forum/topic/4393/how-many-years-of-historical-data-we-get-for-nifty-and-stocks/3?lang=en-GB) | Exact date not exposed; indexed as 2024-era. Moderator_1 extent table, not listing-level guarantee. |
| A13 | [Rate-limit table and correction](https://smartapi.angelone.in/smartapi/forum/topic/4387/changes-in-api-rate-limit/1) | March 2024 thread; moderator correction 2024-03-18. Header explicitly says per hour for 5,000. |
| A14 | [Official Python SDK README](https://github.com/angel-one/smartapi-python/blob/main/README.md) | Mutable main viewed on review date; no publication date asserted. Authentication example inspected, never executed. |
| A15 | [Official instrument/auth documentation](https://smartapi.angelone.in/docs/Instruments) | Date not shown; official indexed text includes scrip-master URL and login flow. Current master not downloaded. |
| A18 | [Token/symbol discussion](https://smartapi.angelone.in/smartapi/forum/topic/45/token-with-symbol/4?lang=en-GB) | Exact date unavailable; old forum example only. Candidate `1594` is not current identity qualification. |
| A16 | [Token-expiry clarification](https://smartapi.angelone.in/smartapi/forum/topic/3946/what-is-the-access_token-expiry-time/4) | Moderator_2 2023-12-26. Older 24–28-hour guidance; do not override later daily-reset announcement. |
| A17 | [April 2026 access changes](https://www.angelone.in/news/market-updates/what-s-changing-in-angel-one-s-smartapi-access-from-april-1-2026) | Published 2026-02-25; updated 2026-03-13. Effective date 2026-04-01; order-focused announcement. |
| A19 | [Scrip versus index volume](https://smartapi.angelone.in/smartapi/forum/topic/602/how-do-i-get-historical-index-data-for-nifty-sensex/21?lang=en-GB) | Moderator_1 2024-04-15. Confirms scrip volume availability, not official NSE share-quantity equivalence. |
| A20 | [Adjusted-close question](https://smartapi.angelone.in/smartapi/forum/topic/772/historical-data-not-giving-adjusted-close) | User 2021-05-24; admin 2021-05-25 only links documentation. Does not settle adjustment semantics. |
| A21 | [Historical inconsistency discussion](https://smartapi.angelone.in/smartapi/forum/topic/1265/inconsistent-data-in-historic-data-api/3?lang=en-GB) | Moderator replies August–September 2021. Incident evidence, not current failure measurement or correction SLA. |
| A22 | [Backtesting question](https://smartapi.angelone.in/smartapi/forum/topic/4112/backtesting-historical-data/2) | Moderator_2 2023-12-20. Supports advertised use; no quantified archival/AI obligations. |
| U1 | [Upstox Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/) | Date not shown; current page rechecked. One-year, free, read-only; historical/market categories need no static IP. |
| U2 | [Upstox V3 history](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) | Date not shown; current page rechecked. Daily availability from January 2000, decade request window. |
| U3 | [Upstox permissions/adjustments reply](https://community.upstox.com/t/clarification-on-upstox-historical-candle-v3-data-usage-for-personal-backtesting-and-ml-research/18061/2) | 2026-10-19 per saved Phase 4 record. Direct revisit unavailable; scoped findings reused with that limitation, not freshly authenticated. |
| B1 | [Breeze price/backtesting FAQ](https://www.icicidirect.com/faqs/fno/are-there-any-charges-for-accessing-historical-data-and-using-other-features-of-breeze-api) | Date not shown; official indexed page rechecked. |
| B2 | [Breeze session guide](https://www.icicidirect.com/futures-and-options/api/breeze/article/what-is-a-session-key-and-how-to-generate-it-for-using-breezeapi) and [API reference](https://api.icicidirect.com/breezeapi/documents/index.html) | Dates not shown; official indexed login flow reviewed, no session generated. |
| B3 | [Existing Breeze/NSE qualification record](STK-004-014-breeze-evaluation.md) | 2026-11-03 IST follow-up; primary source links, pinned SDK and content-free exact measurements reused. |
| N1 | [NSE MCP product/FAQ](https://www.nseindia.com/nse-mcp) | Date not shown; current page rechecked for coverage/free access. Prior raw-basis description was not independently recovered in current rendered text; see N2. |
| N2 | [Existing official-source decision](PRODUCT-ACCEPTANCE-HANDOFF.md#raw-price-reconciliation-and-documented-alternatives) | Repository review preceding STK-084; links original NSE tariff effective 2026-04-01 and prior raw/use findings. Tariff not a fresh personalized quote. |
| T1 | [TrueData history coverage](https://feedback.truedata.in/knowledge-base/article/historical-real-time-data-availability-through-market-data-api) | Date not shown; current daily 10+ years claim rechecked. |
| T2 | [TrueData pricing](https://www.truedata.in/information/pricing) | Date not shown; current indexed API-exclusion notice rechecked. No API quote. |
| T3 | [TrueData API uses/restrictions](https://www.truedata.in/market-data-apis) | Date not shown; direct fetch timed out, official indexed text reviewed. Internal analysis and simulation restrictions are vendor statements, not an independent legal opinion. |
| G1 | [Global Datafeeds GetHistory](https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/rest-api-documentation/function-gethistory/) | Date not shown; current `AdjustSplits` documentation rechecked. |
| G2 | [Global Datafeeds API terms](https://globaldatafeeds.in/apis/) | Date not shown; current single-subscriber and simulation restrictions rechecked. |

## Validation and delivery scope

Documentation/source consistency checks passed: 35 source IDs, 14 local links and
anchors, the three exact comparison dates and denominators, baseline ancestry,
Markdown table structure, whitespace and changed-file scope. No new offline technical issue
requires a test or adapter: API shape examples would not establish data accuracy.
No application, PostgreSQL or browser tests are needed for this documentation-only
change; prior acceptance results are historical evidence, not rerun results.
Only this evaluation document is delivered. Unrelated tracked/untracked work,
including `ImportPreview.tsx`, is preserved. No grant, credentials, source payloads,
private screenshots, database/schema, STK-083 code or runtime configuration changed.
