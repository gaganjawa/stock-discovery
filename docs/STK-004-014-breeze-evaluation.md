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
