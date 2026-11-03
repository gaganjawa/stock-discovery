# STK-004/014 — Breeze read-only INFY evaluation

2 November 2026 initial evaluation; authenticated follow-up on **3 November IST**
(2 November UTC), below. D3-02 source feasibility / M1. **M1 BLOCKED; no genuine
input packet qualified.** PR35 remains draft/unmerged; its `db441127` head passed
exact unit/PostgreSQL/UI/aggregate CI in run `41488880956` before this follow-up.
No other worktree, existing data, source grant or frozen experiment changed.

## Published permissions and unresolved obligations

| Requirement | Verified evidence | Boundary |
|---|---|---|
| SDK code | Official [MIT licence](https://github.com/Idirect-Tech/Breeze-Python-SDK/blob/4125106b48932ff99b45d593749dcec21c552558/LICENSE), SDK source/version 1.0.68 at `4125106b48932ff99b45d593749dcec21c552558` | Software reuse with its notice conditions does not license exchange data. Initial evaluation imported no SDK; isolated official-SDK execution is documented below. Reference MCP never installed/executed. |
| Access and historical backtests | Official [Breeze FAQ](https://www.icicidirect.com/faqs/fno/are-there-any-charges-for-accessing-historical-data-and-using-other-features-of-breeze-api) expressly includes historical backtesting among free features | Covered private historical testing does not need a new individual permission reply. An eligible ICICIdirect account/app/session is still necessary. Account charges are not measured; no account opened or purchase made. |
| Quotas | [Official API reference](https://api.icicidirect.com/breezeapi/documents/index.html) and [rate-limit FAQ](https://www.icicidirect.com/faqs/fno/what-is-the-rate-limit-for-breeze-api): 100 calls/minute, 5,000/day across endpoints | The account must share this allocation across clients. No rate-limit retries or trading calls. Order/static-IP rules do not establish a static-IP requirement for this read-only historical probe. |
| Persistence / revocation | No applicable clause found in reviewed public Breeze resources defining indefinite PostgreSQL storage, derived copies, expiry/revocation purge, backups/restore or minimal audit retention | **UNVERIFIED**, not permission and not an assertion that storage is prohibited. The backtesting statement is not an unlimited archival licence. WhatsApp-specific conditions and the Breeze Zero brokerage offer are not substituted for data terms. |
| Data scope and AI | [Official product information](https://www.icicidirect.com/futures-and-options/api/breeze) describes market data and strategy testing | Redistribution, third-party AI transfer/training and a complete filings/news corpus are not inferred. No such use performed. |
| History and price basis | SDK advertises 10 years; product page describes three years of second-level history. API accepts `1day`, NSE cash | Neither statement verifies current INFY coverage, unadjusted OHLC/share volume, dividend/split/bonus treatment, archived corrections or original availability. Keep these **UNVERIFIED**. |

## Reference implementation review — not installed or executed

Reviewed `aranjan/icici-mcp` at `bc8c96e834b8c21322e799d1eba56da02aaf707a`,
including server, auth, CLI, configuration and all three test modules.

- [server.py:199](https://github.com/aranjan/icici-mcp/blob/bc8c96e834b8c21322e799d1eba56da02aaf707a/src/icici_mcp/server.py#L199) forwards the supplied stock code to V2 without an ISIN-backed security-master check. The advertised NSE `INFY` example must not be assumed to be the ICICI request code. Its date helper uses a fixed 06:00 UTC string, which is not evidence of session closure.
- The same server registers placement/modification/cancellation/square-off tools. Read-only annotations on other tools do not disable them or establish a safety boundary. None are exposed here.
- [auth.py:109](https://github.com/aranjan/icici-mcp/blob/bc8c96e834b8c21322e799d1eba56da02aaf707a/src/icici_mcp/auth.py#L109) implements Playwright/TOTP login; [line 268](https://github.com/aranjan/icici-mcp/blob/bc8c96e834b8c21322e799d1eba56da02aaf707a/src/icici_mcp/auth.py#L268) falls back through cached/manual sessions to automatic login. It also logs user identity and may include an API-key login URL in failure diagnostics. These behaviors are not reused.
- Tests exercise registration, basic order validation, environment/cache handling and CLI absence paths. The [string-conversion test](https://github.com/aranjan/icici-mcp/blob/bc8c96e834b8c21322e799d1eba56da02aaf707a/tests/test_server.py#L107) and [Playwright import test](https://github.com/aranjan/icici-mcp/blob/bc8c96e834b8c21322e799d1eba56da02aaf707a/tests/test_auth.py#L109) are placeholders. They do not verify INFY identity, candle semantics, session coverage or absence of trading side effects. Tests were read, not run.

The official SDK also needs care before any future live setup: importing
`breeze_connect.py` downloads a master and creates `logs/`; debug logging is enabled.
`generate_session()` exchanges the supplied manual API session and loads scripts.
`get_names()` reads the master but returns no ISIN. V2 uses `requests.get` without
an explicit timeout. A live client needs bounded transport and controlled logging
before initialization; this offline contract does not certify that runtime setup.

## Initial configuration and actual public-source result — 2 November

Bounded inspection covered project/workspace environment references, existing
REAL-001 source/config/grant references, process environment names, standard Claude/
Codex MCP references and the conventional ICICI token-cache location. **No usable
Breeze configuration or session was found in these locations.** This does not
assert that the owner has no ICICIdirect account elsewhere. Values were never
printed. Neither the project environment nor its virtual environment has
`breeze_connect` installed.

The [official instrument documentation](https://api.icicidirect.com/breezeapi/documents/index.html#instruments)
links the public [security master](https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip).
Two bounded GETs returned HTTP200; archive/member data was inspected in memory,
not extracted to the repository or retained as a source dataset. The second
request exercised the new resolver against the actual file:

| Metadata | Observed value |
|---|---|
| Fetched | `2026-11-02T17:02:03.145803+00:00` |
| Response Last-Modified | `Mon, 02 Nov 2026 02:32:59 GMT` — not a historical first-availability claim |
| Archive SHA-256 | `ffa9cd9822932700287d519a27fa61411bf006fb8f8f79432d88db2a72becf17` |
| Member | `NSEScripMaster.txt` |
| ISIN / exchange symbol / ICICI short code | `INE009A01021` / `INFY` / **`INFTEC`** |
| Retained artifact | Content-free retrieval metadata only, in the private temporary test packet; no ZIP, prices, volumes or account details |

At this initial checkpoint: authenticated Breeze requests **zero**; historical `get_names()`/V2 calls **zero**.
No original historical response exists to preserve; none was manufactured from
SDK samples. SDK-shape tests are not an actual SDK or provider integration result.

## Small demonstrated integration gap and contract tests

`worker/providers/breeze_probe.py` supplies an **unregistered probe contract**,
not a production source adapter. It reuses existing `Stream`, rights/fence `Access`
and validation conventions, without changing STK-014/079 or importing the SDK.

- Handles the official CSV's whitespace-before-quoted-header shape; resolves exact ISIN + NSE symbol and rejects missing, conflicting or duplicate identities. The optional future SDK call must corroborate the returned ICICI code.
- Has only fixed `get_names()` and `get_historical_data_v2()` reads. Uses the resolved code, `NSE`, `cash`, `1day`, a bounded past window of at most 90 days, no auth/order/holdings endpoint and no generic method forwarding.
- Rechecks source/account/scope and current rights/fences through `Access` before/after reads and for both dependencies before returning. SDK failures and 401/403 classifications are sanitized; no automatic retry or session refresh.
- Retains only provider-status/count/date-label metadata in its result; no raw payload, credentials, prices or volume. Thirty distinct labels are **not** proof of 30 closed sessions. Values, actions, timezone, adjustment, volume basis and original availability remain explicitly unverified.
- Always returns `INSUFFICIENT_EVIDENCE`; cannot emit `CandleData`/`raw-v1`, immutable revisions, publication or admission. No runtime registry/API/UI/worker is connected. The caller still owns SDK lifecycle, safe transport/logging and account-wide quotas; this is not a security sandbox around the general SDK.

Fresh focused run: **246 passed, zero failures/skips**, including **40 new Breeze
cases** plus existing qualification, rights, swing-research, Upstox and filing
regressions. Initial fixture failures used invalid zero-day synthetic grant/request
limits; fixtures were corrected to the existing positive-limit contract, without
changing production rights. Synthetic fixture limits are not provider terms.

Command:
```sh
PYTHONPATH=backend:shared:worker .venv/bin/python -m pytest worker/tests/test_breeze_probe.py backend/tests/test_swing_qualification.py backend/tests/test_source_rights.py backend/tests/test_swing_research.py worker/tests/test_real_upstox.py worker/tests/test_real_documents.py worker/tests/test_real_filings.py -q
```

## Initial M1 status and next prerequisite — superseded by follow-up below

**BLOCKED / INSUFFICIENT_EVIDENCE.** Identity mapping is corroborated by the public
master; no actual daily candles were retrieved. A 30-closed-session sample,
OHLC/share-volume comparison, corporate-action treatment, source timestamps and
freshness are **NOT TESTED**. Existing Upstox samples are adjusted/unqualified;
there is no accepted raw baseline against which to claim numerical agreement.
Master bonus/dividend flags cannot establish a complete dated action archive.

Next account prerequisite: an eligible existing ICICIdirect account with a
registered Breeze app and a current **manually generated API session**, referenced
through private local configuration alongside the app key/secret. No password,
TOTP seed, account number or secret belongs in chat, logs, tests or commits. A path
to an already configured setup suffices; no new account purchase is requested.
The [official daily-session FAQ](https://www.icicidirect.com/faqs/fno/do-i-have-to-generate-a-session-key-everyday)
documents daily renewal. No automatic TOTP or browser login is implemented.

After that prerequisite, review safe official-SDK initialization and use the
bounded read-only sample under account quotas. Compare at least 30 real complete
sessions with permitted calendar/action evidence, preserving actual response/
retrieval metadata in the allowed scope. Verify raw/volume semantics instead of
relabeling. Applicable persistent storage/retention and original/current grant/
fence/coverage reviews remain necessary before any ingestion. Filings/material
events and M2 independent human/50-case, genuine strategy, operational, publication,
paper-admission and trading gates remain separately blocked.

## Authenticated SDK follow-up — 3 November 2026 IST

**Authentication SUCCESS; real historical retrieval SUCCESS; M1 still BLOCKED.**
This supersedes the initial missing-configuration observation, not the prior
immutable test/probe results. Owner supplied app credentials and a fresh manually
generated, unexposed API session through an ignored owner-only local file. Local
preflight rejected an initially future-dated UTC creation time without calling
Breeze; the owner corrected it. No session timestamp or credential was invented.

### Runtime and security boundary

`scripts/verify_breeze_access.py` is an explicit owner-authorized **transient SDK
diagnostic**, following the existing Upstox diagnostic convention. It never reads
retained evidence, accesses PostgreSQL, constructs a Grant, supplies a fake/no-op
Access, registers a source or changes an existing permission. Production
`probe_infy()` retains all independent Access/grant/fence checks. Successful
authentication is not proof of permission for permanent storage or AI processing.

- Executed the official `breeze-connect` **1.0.68** source from its PyPI sdist,
  SHA-256 `8d6e3ef353fe119047e53ab11413b8686903afa195b51a962e378e20914de0c3`.
  Three exact package-file hashes are checked before import; source matches the
  reviewed official GitHub module after newline normalization. No SDK code is
  vendored, setup script executed, or project dependency/lockfile changed.
  Dependencies were isolated in a temporary directory. Reference MCP not installed.
- SDK import/session initialization ran in a dedicated child. SDK stdout/stderr
  and logging were suppressed before import. Its empty log directory was private
  and removed by the parent, including on child timeout; no source/account logs
  were retained. No session/profile body or hash of that body appears in receipts.
- Only GET to the three exact resources below is permitted. Other verbs, order
  URLs, redirects, alternate downloads, other symbols/products/intervals and
  windows over 90 days are denied. No automatic login, refresh or retry. The
  SDK's redundant public-master downloads reuse the same bytes in memory.
- Transport bounds: 5 possible network requests per invocation, 10-second read /
  5-second connection timeouts, 30-second response-stream and 120-second child
  bounds; master 25 MB compressed / 128 MB total expanded, NSE member 16 MB,
  other bodies 1 MB. These are diagnostic safety bounds, not provider entitlements.
- A private locked/fsynced ledger reserves attempts before requests, survives
  restart and denies corrupt/clock-regressed/exhausted state: at most 6/minute
  and 12/rolling 24 hours across clients sharing that ledger. **Other processes,
  devices or alternate ledgers are not accounted for.** Provider account-wide
  100/minute and 5,000/day quotas still apply; no global account usage was measured.

Private setup (never paste values in chat or commits): ignored `.env.breeze.local`,
owner-only permissions `0600`, contains `ICICI_API_KEY`, `ICICI_API_SECRET`,
`ICICI_API_SESSION`, `ICICI_SESSION_CREATED_AT_UTC` (actual UTC ISO timestamp) and
`ICICI_FRESH_SESSION_CONFIRMED=true`. No password/TOTP/customer ID is requested.
The loader reads only this selected file, with no environment/cache/history
fallback or shell evaluation. It conservatively requires a non-future creation
time, under 24 hours old and the same Indian calendar date; the broker alone
determines actual session validity. An old screenshot session is not reused.

Preflight, which does not import the SDK or authenticate:
```sh
PYTHONPATH=backend:shared:worker .venv/bin/python -m worker.providers.breeze_config --config .env.breeze.local
```
The diagnostic additionally requires an explicitly supplied pinned SDK root,
isolated SDK dependencies on `PYTHONPATH`, a persistent private `--quota` file,
past `--start` / `--end`, and `--owner-authorized-transient-read`. It is not a
production ingestion command. Never reset the quota file to bypass its limits.

### Actual requests and observations

Exactly **three HTTP GETs**, no retry, all HTTP200; two authenticated API calls.
`get_names()` was an SDK-local master lookup, not another HTTP request. These
results are genuine SDK execution, separate from all synthetic fixture tests.

| Resource | Endpoint / actual receipt |
|---|---|
| SDK public master | `https://directlink.icicidirect.com/MotherAppMaster/SecurityMaster.zip`; received `2026-11-02T18:38:54.098089+00:00`; 2,859,542 bytes; SHA-256 `c10096eaedec256bdce5cfefe3c3086df4a2e58cd830dd1bb621bf2ad3c6a175`; Last-Modified `Mon, 02 Nov 2026 02:34:02 GMT` |
| Manual API-session exchange | `https://api.icicidirect.com/breezeapi/api/v1/customerdetails`; received `2026-11-02T18:38:54.304197+00:00`; provider Status200. Account/session response discarded, not logged or hashed. |
| INFY daily history | `https://breezeapi.icicidirect.com/api/v2/historicalcharts`; received `2026-11-02T18:38:54.925386+00:00`; 6,300 bytes; SHA-256 `656f41d1036565e5295651acee6938bf866998b2959f4e97b45f6900741dbc98`; provider Status200, original Error null |

Master ISIN `INE009A01021` + NSE symbol `INFY` + EQ series resolved to **INFTEC**;
official `get_names(NSE, INFY)` corroborated that mapping before history.
V2 request: `INFTEC`, `NSE`, `cash`, `1day`,
`2026-09-01T00:00:00.000Z` through `2026-10-30T23:59:59.000Z`.

| Check | Actual result / limitation |
|---|---|
| Candles | **41**, dated **1 September–30 October 2026**, ascending, zero duplicate date labels |
| Basic OHLCV | Zero invalid rows: finite positive OHLC, low <= open/close <= high; nonnegative integral volume. Numerical values discarded. This does not establish raw-price or share-volume semantics. |
| Closed/missing sessions | **UNAVAILABLE**: no authoritative full NSE calendar was supplied. 41 labels are not proof of 41 complete closed sessions or absence of missing sessions. |
| Timestamps | Provider candle labels are timezone-naive. UTC request strings do not establish the timezone/close/publication of returned labels. |
| Adjustments and actions | **UNVERIFIED**: no split/bonus/dividend or volume convention established; no dated action archive obtained. No `raw-v1` conversion. |
| Reference comparison | **UNAVAILABLE**: no qualified raw baseline; prior Upstox samples remain adjusted/unqualified. No fabricated agreement. |
| Provenance | Response hashes and true retrieval metadata retained privately; original publication/first-availability remain null. HTTP Date/Last-Modified are not original historical availability. |
| Persistence | No prices, volumes, ZIP/CSV, account/profile/session response or original response body retained. No database accessed. Only sanitized metadata and quota timestamps remain in ignored owner-only files. |

### Fresh validation and remaining blocker

Fresh focused validation: **300 passed, 0 failed, 0 skipped**, including **94**
Breeze cases (40 existing probe, 24 private configuration, 30 transport/summary
guards) and existing qualification/source-rights/swing-research/Upstox/document/
filing regressions. An initial transport fixture exposed `httpx.Response` treating
`bytearray` content as a stream; converting to immutable bytes fixed buffered
SDK `.json()` compatibility before the live run. It was not a provider failure.

Exact-commit CI at `9149d859` (run `41503304845`) then found a concrete Linux
portability defect: hard-coded `/private/tmp` prevented creation of the child's
private working directory, so the timeout-cleanup test never reached its mocked
child. CI recorded **1 failed, 887 passed** in the unit job; not called flaky.
An explicit system-temp-directory regression failed locally before correction.
Using `TemporaryDirectory`'s operating-system default fixes that path while
preserving private permissions and cleanup. The test also restores bytecode
settings after simulating a child in-process. After correction: **300 focused
and 888 complete backend/worker unit tests passed**, zero failures/skips (one
existing Starlette/AnyIO deprecation warning). Database/browser coverage remains
the mandatory separate CI gate; no additional live Breeze call was made.

No further authenticated probe is needed to prove basic access. The next genuine
qualification blockers are documented raw OHLC/share-volume/action semantics,
complete authoritative closed-session/action and filing/material-event coverage,
effective instrument settings, truthful original availability, and applicable
storage/retention/revocation/backup obligations. Published free historical testing
remains acknowledged; no blanket request for new permission letters. These inputs
must satisfy existing STK-014 and original/current grant/fence contracts before
ingestion or a qualified real instrument. M2 human/50-case, genuine evaluation,
operational, publication, paper-admission and trading approvals remain blocked.

## Official-source qualification follow-up — 3 November 2026 IST

**Exact calendar membership VERIFIED; Breeze OHLCV qualification BLOCKED by
observed source discrepancies.** No production code, strategy, source grant or
stored dataset changed. Prior observations above remain historical records.

### Exact CI at the starting commit

Commit `bda66eb7124774854c5b69ecc2838dac68dc74f8`,
[run 41503723202](https://github.com/gaganjawa/stock-discovery/actions/runs/41503723202):
**unit PASS, postgres PASS, ui PASS, checks PASS**. PR35 remained draft/unmerged.
Any subsequent documentation commit requires its own exact-commit CI.

### Calendar and permitted comparison procedure

The official [CM trading-holiday circular NSE/CMTR/71775](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf),
dated 12 December 2025, and the current [2026 equity holiday page](https://www.nseindia.com/resources/exchange-communication-holidays?apiversion=v2)
confirm 14 September, 2 October and 20 October as holidays. The bounded window
1 September–30 October contains **41 expected regular sessions**, excluding
weekends and those three holidays. This reviewed expected set is not a new
production calendar, evidence of unscheduled closures, or an invented historical
availability timestamp. Circular receipt: HTTP200 at
`2026-11-02T18:56:24.309272+00:00`, 176,256 decoded bytes, SHA-256
`aa97e0afc0ce394097f2fc62631c68e3c2e4c7c23541ed35f21d9fc06b0dcacb`.

The earlier receipt retained no full date-label set or numerical values. Exactly
one fresh guarded SDK sample was therefore necessary. Private manual-session
preflight passed; the existing pinned SDK, GET-only transport, quota ledger and
private child/cleanup controls were reused. No fallback login or extra historical
retry. This increment used three Breeze HTTP GETs; the durable ledger now
preserves six reservations across both genuine probes, without reset.

The fresh sample's **actual labels** were compared in memory with that expected
set: **41 observed, zero missing, zero unexpected, zero duplicates**. Sorted-label
SHA-256: `1b06dae1421b5e90416b379c96b4dfdc4bd1b57e17cb7086492751db3bd67002`.
History receipt: `2026-11-02T19:01:23.513557+00:00`, SHA-256
`656f41d1036565e5295651acee6938bf866998b2959f4e97b45f6900741dbc98`.
That is **identical to the original sample's response hash**, linking the exact
membership check to the existing sample rather than merely comparing counts.

The [official NSE MCP interface](https://www.nseindia.com/nse-mcp) now worked through
its documented streamable-HTTP endpoint. Schema discovery used initialize 200,
initialized notification 202 and tools/list 200 (SSE). A separate query session
used initialize 200, notification 202, `get_corporate_actions` 200 and then
`get_stock_history` 200, without retries. Queries were fixed to INFY; actions
1 September–3 November, history two months ending 30 October. No pagination/bulk
scraping, website-API fallback or stored NSE data corpus. MCP informational access
does not establish storage, simulation or recommendation rights.

### Documented adjustments versus measured agreement

The official SDK's [pinned README](https://github.com/Idirect-Tech/Breeze-Python-SDK/blob/4125106b48932ff99b45d593749dcec21c552558/README.md)
explicitly states that historical data does not account for corporate adjustments.
The pinned original returned HTTP200 at `2026-11-02T18:56:24.737700+00:00`, SHA-256
`a62a6d1acb3b115fec161c52fadf9b78c1b4ee10ff0ab806291ed55b2f1d0b88`;
the note occurs six times. **This is provider documentation**, not independent
verification of every candle or of volume adjustment semantics. Existing
`price_basis='unknown'` diagnostic output was not silently promoted to `raw-v1`.

NSE's official `get_stock_history` tool describes its reference as unadjusted
bhavcopy OHLCV. The query returned 41 rows inside the target window at
`2026-11-02T19:00:53.306180+00:00`; parsed JSON-RPC message SHA-256
`89a792b14e63351ae82d9faea530ce0d8bbe326d47a059a287014b3eebd055c7`.
Comparison used the same dates and explicit open/high/low/close/volume fields,
finite Decimal equality, no rounding/tolerance, adjustment or unit conversion.
All values existed transiently in RAM/child stdin only; receipts retain field
agreement results, not prices, share counts or raw tool messages.

| Field | Exact matches / 41 | Mismatches / 41 |
|---|---:|---:|
| Open | 6 | 35 |
| High | 8 | 33 |
| Low | 12 | 29 |
| Close | 41 | 0 |
| Volume | 0 | 41 |

On **1 September, 23 October and 30 October**, each representative row matches
**close only**; **open, high, low and volume all differ**. A private receipt also
records the exact mismatching fields for every compared date. No numerical
agreement, acceptable error tolerance or explanation for these differences was
invented. The comparison identifies a qualification blocker, not a proved defect
in either provider or in existing strategy code.

NSE's [price/volume reference](https://www.nseindia.com/historical/price-and-volume-data-per-security)
identifies cash-equity traded quantity, and its [MCP volume documentation](https://www.nseindia.com/nse-mcp)
describes shares separately from turnover. Breeze's API labels its field traded
volume but the reviewed reference does not establish its exact NSE-share,
sampling/session or adjustment convention. **The Breeze field is not verified
as exchange-total traded shares:** integral values plus 41/41 quantity mismatches
cannot establish units or a conversion factor. No lots/shares multiplier inferred.

### Original disclosures and separate clocks

- The [official Q2 results index](https://www.infosys.com/investors/reports-filings/quarterly-results/2026-2027/q2.html)
  and issuer events page identify **23 October 2026** results for the quarter and
  half-year ended **30 September 2026**. The listed 16:30 IST press conference and
  18:00 IST earnings call are **event times**, not document-publication clocks.
- The original [IFRS INR statements](https://www.infosys.com/investors/reports-filings/quarterly-results/2026-2027/q2/documents/consolifrsinr-fy27-q2-and-h1-finstatement.pdf)
  returned HTTP200; the decoded PDF was acquired transiently at
  `2026-11-02T19:02:44.849453+00:00`, 1,030,221 bytes, SHA-256
  `d47fe57f3907f8b99996b5000037aac3f2a42f11059a4a1d0e28b726f9f70ca3`.
  Its Last-Modified header is `Fri, 23 Oct 2026 10:51:39 GMT`; that header is
  **not** verified first-public availability. No PDF or financial table retained.
- The issuer's [board-outcome disclosure](https://www.infosys.com/investors/documents/exchange-filings/2026/outcome-board-meeting23oct2026.pdf)
  supports **₹26 per equity share interim dividend**, **3 November 2026 record
  date**, and **11 November payment date** in the official indexed passage. The
  full original-body download exceeded the diagnostic's 25 MB decoded bound and
  was discarded; no full-body hash or parser success is claimed. The smaller
  original quarterly statements above were retrieved instead. Record date is not
  silently treated as ex-date or an action inside the sampled price window.
- The bounded NSE action lookup returned without an error/warning. Only lookup
  status/schema was retained, so it does **not** establish an event count, an
  independently preserved action list or exhaustive filing/material-event
  coverage. No empty-list/action-free attestation is created.

**Verified original publication/dissemination timestamps: unavailable.** Filing/
announcement dates, scheduled event times, server Last-Modified and present-day
retrieval timestamps remain separate. No third-party timestamp, PDF filename or
search-engine crawl date fills that gap. Observed-now evidence cannot become
historically available evidence at an October cutoff through backdating.

### Existing STK-014 criteria — precise disposition

| Criterion | Status | Remaining qualification boundary |
|---|---|---|
| Authorized source / intended use | **PARTIAL** | Account read access and published free historical testing established; no original/current stored grant or additional use activated. Informational MCP access is not storage/replay authority. |
| Retention / revocation / deletion / backups | **BLOCKED** | Applicable persistent and derived-copy obligations not established; persistent provider ingestion remains disabled. |
| Price and volume basis | **BLOCKED** | Provider documents unadjusted history, but measured OHL/volume disagree; Breeze share-volume and correction/session conventions unresolved. |
| Regular session membership | **VERIFIED for this sample** | Actual labels equal the 41-session expected set; full point-in-time session records, clocks and original acquisition lineage remain unqualified. |
| Corporate-action coverage | **PARTIAL** | Specific dividend disclosed; no complete dated permitted action evidence or validated action-free-window attestation. |
| History / freshness | **PARTIAL** | 41 matching regular date labels, but OHLCV quality unresolved. Sample ends 30 October, not the later 2 November session; no current signal freshness or historical availability certified. |
| Tick / lot / eligibility / risk | **PARTIAL** | Exact ISIN/symbol mapping verified; effective settings/eligibility/risk packet not established. No defaults introduced. |
| Filings / material events | **PARTIAL** | Original quarterly PDF and specific indexed dividend disclosure found; original availability and complete event coverage missing. |
| Provenance / deterministic failures | **PARTIAL** | Retrieval hashes, source URLs and exact comparison receipts exist; no qualified immutable revisions, original/current grants or historical availability invented. |
| Overall instrument | **BLOCKED / INSUFFICIENT_EVIDENCE** | No `SwingInputs` qualification, real recommendation, publication, admission or trade authorized. |

No production defect was demonstrated, so this increment changes documentation
only. A private one-shot validation reused the existing guarded child and passed
six synthetic comparison checks, including identical counts with the wrong
holiday/session, duplicates, missing dates, absent reference and changed volume.
These are diagnostic checks, not new platform functionality or real-data
acceptance. Source values, credentials and the one-shot script are excluded from
Git. Existing grants, fences, qualification and synthetic fixtures are unchanged.
Fresh relevant regression run: **300 passed, 0 failed, 0 skipped** across Breeze,
qualification, source rights, swing research, Upstox and document/filing tests.
The three existing contract validators, JSON/local-link, syntax and whitespace
checks passed. No full local database/browser suite was rerun for documentation.

**Next prerequisite:** resolve the measured Breeze-versus-NSE OHL/share-quantity
differences using permitted original EOD evidence and/or an applicable published
candle-construction explanation; do not adjust one series to force agreement.
Establish applicable persistent storage obligations and the missing coverage,
settings and original clocks before ingestion. No provider contact or purchase
was made; no individual permission reply is demanded for already covered uses.

## Original EOD / MCP / Breeze triangulation — 3 November 2026 IST

Starting commit `26ed3213b2e50042a6745c94af3814ea9a897aa3` passed **unit,
postgres, ui and checks** in [run 41507391584](https://github.com/gaganjawa/stock-discovery/actions/runs/41507391584).
PR35 remains draft/unmerged. This increment changes documentation only.

### Original reference acquisition and identity

The [official report catalogue](https://www.nseindia.com/all-reports) provides
CM-UDiFF Common Bhavcopy Final. Three owner-specified, one-off original report
downloads were read in memory, not collected into an archive or automated market
dataset. The downloadable-content exception in the [website terms](https://www.nseindia.com/static/nse-terms-of-use)
is treated narrowly for this informational inspection; no standing collector,
redistribution, simulation or permanent provider-storage right is inferred.

All three originals returned HTTP200 from
`https://nsearchives.nseindia.com/content/cm/`. Each ZIP contained the expected
same-named CSV. Each selected row had unique `TckrSymb=INFY`, `SctySrs=EQ`,
`ISIN=INE009A01021`, matching `TradDt` and `BizDt`, and `SsnId=F1`. No ambiguous
row, alternate series or another provider's field was substituted.

| Date | Original ZIP filename | ZIP SHA-256 |
|---|---|---|
| 2026-09-01 | `BhavCopy_NSE_CM_0_0_0_20260901_F_0000.csv.zip` | `c5a3ac986df7627ad79897a0d67f069b53361c1e92801cb4699932509453c919` |
| 2026-10-23 | `BhavCopy_NSE_CM_0_0_0_20261023_F_0000.csv.zip` | `009b57f15cb36e14fa956b2e585b69b23f279eb8532c2c63c0adf0aa2ed77689` |
| 2026-10-30 | `BhavCopy_NSE_CM_0_0_0_20261030_F_0000.csv.zip` | `ce2b0e6615bbc48990bb32ab081f85568451bb6f16fc54bff7d786faa7d2ca44` |

Original receipts: `2026-11-02T19:22:19.772877+00:00`,
`19:22:19.923064+00:00`, `19:22:20.012892+00:00`, respectively. CSV hashes and
HTTP Last-Modified headers are preserved as metadata, not original publication
proof. The column mapping was exactly `OpnPric/HghPric/LwPric/ClsPric/TtlTradgVol`;
`LastPric` was separately inspected, never substituted for `ClsPric`.

### Three-source numeric comparison

**A:** original NSE CM-UDiFF Final row. **B:** official NSE MCP history.
**C:** pinned official Breeze SDK V2, NSE/cash/1day. One MCP query session and
one guarded Breeze cycle were used; no retries. Existing private configuration,
timeouts, GET allowlist and durable ledger were reused. Total Breeze reservations
across the three genuine cycles are now **nine**, without reset. The latest
history hash still equals the original 41-candle sample's hash.

Every numeric comparison used finite Decimal values without tolerance or
normalization. Absolute difference is `abs(value-reference)`; percentage difference
is that difference divided by `abs(reference)`, times 100. A zero denominator is
unavailable, not zero. Volume ratios use the unconverted source quantities.

| Date | B versus A | C versus A | C versus B | Volume-ratio conclusion |
|---|---|---|---|---|
| 2026-09-01 | All five fields equal; absolute/percentage differences zero | Close equal; open/high/low/volume differ | Same result | Below one |
| 2026-10-23 | All five fields equal; absolute/percentage differences zero | Close equal; open/high/low/volume differ | Same result | Below one; different from other dates |
| 2026-10-30 | All five fields equal; absolute/percentage differences zero | Close equal; open/high/low/volume differ | Same result | Below one; different from other dates |

The exact numerical three-date table, absolute/percentage differences and both
Breeze/NSE ratios were returned to the owner for this private informational
inspection. They are not published as provider rows or a reusable derived
dataset in Git. The durable receipt retains source hashes, identity, equality
flags and procedure hash only. Original reports, MCP payloads, source values,
ratio tables and SDK/account bodies were not written to a data store.

### Definitions and what the measurements do / do not establish

- **Open:** NSE's [pre-open rules](https://www.nseindia.com/static/products-services/equity-market-pre-open)
  use the auction equilibrium as the daily open, or the first normal-market trade
  if no equilibrium is discovered. A broker's first sampled regular-session print
  is not automatically that official open. We have not established that Breeze
  uses that alternative calculation.
- **High/low:** The official [CM protocol](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/TP_CM_Trimmed_NNF_PROTOCOL_6.1.pdf)
  identifies highest/lowest trade prices, distinct from indicative opening
  information. Broker sampling can differ from the full executed-trade universe;
  the precise Breeze sampling/correction/auction policy is not established.
- **Close versus LTP:** NSE's [2026 CAS SOP, section 5](https://nsearchives.nseindia.com/content/circulars/CMTR73362.pdf)
  defines auction equilibrium with specified fallbacks for CAS-eligible equities;
  the [CAS description](https://www.nseindia.com/static/products-services/closing-auction-session)
  distinguishes the auction and continuous sessions. Do not apply a historical
  last-half-hour VWAP description indiscriminately to all 2026 stocks. In these
  three original rows, **LastPric equals ClsPric**. Thus the matching Breeze close
  cannot distinguish an LTP calculation from an official-close calculation.
- **Quantity:** Original `TtlTradgVol` is the cash-equity traded quantity, separate
  from trade count and turnover. Breeze's [API reference](https://api.icicidirect.com/breezeapi/documents/index.html)
  names traded volume but does not establish an identical full-exchange/session
  universe or a corrective multiplier. Its [product page](https://api.icicidirect.com/)
  advertises second-level LTP history; that is not proof of a daily construction
  formula. No shares/lots conversion is justified by the measured variable ratios.

**Confirmed:** MCP agrees with the original Final reports on all 15 inspected
fields. The same request/source-identity/date mapping passes, and provider JSON
values were compared before any strategy, candle adjustment, aggregation or
rounding by this application. This eliminates this diagnostic's transformation
and a bad MCP reference as explanations for these specific observations.

**Not a constant unit difference:** volume ratios vary across the dates, with
unequal deficits. Closes agree while other price fields do not; one price-scale
factor cannot fix that. Several differences materially exceed tick rounding.

**Auction/sampling is a hypothesis, not a proved root cause:** Breeze high is
above the original full-day high on 1 September and 30 October; on 23 October
its low misses the exchange's extreme and its high is below the official high.
Simply omitting a subset of the same final executed trades cannot generate a
high above their maximum. Different trade/quote universes, cancellation or
correction treatment, session construction or a provider data-quality defect
remain possible. No published Breeze formula was found that proves which cause
applies. No price or volume was corrected to make the feeds agree.

### Source decision and next prerequisite

**Formal STK-014/M1 classification: UNQUALIFIED SOURCE.** It fails full-OHLCV
verification. Its closes remain a **provisional closing-price-only research
candidate** supported by these three original rows and the earlier 41-date MCP
comparison. That narrow agreement is not a general closing-price contract,
original availability evidence, retention licence or approval to ingest/reuse
the source in a recommendation. No hybrid candle is assembled from A/B/C.

Resolve the provider's documented candle/trade-universe/correction semantics or
obtain an independently permitted full-OHLCV source before swing qualification.
Applicable storage/retention/revocation/backup terms, complete actions/filings/
material events, effective settings and truthful availability remain necessary.
No production code defect was demonstrated; no strategy or source grant changed.
M1, real recommendations, publication, paper admission and trading remain blocked.
Fresh validation: **300 relevant regressions passed, zero failures/skips**; four
private diagnostic Decimal/percentage checks, three contract validators, syntax,
JSON/local-link, whitespace and credential-exclusion checks passed. No full local
database/browser rerun or new application regression was needed for documentation.
