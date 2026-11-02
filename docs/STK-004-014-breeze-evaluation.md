# STK-004/014 — Breeze read-only INFY evaluation

2 November 2026. D3-02 source feasibility / M1. **M1 BLOCKED; no genuine input
packet qualified.** Existing PR35 was draft/unmerged at `56400781`, with exact
unit/PostgreSQL/UI/aggregate CI successful before this increment. No other
worktree, existing data, source grant or frozen experiment changed.

## Published permissions and unresolved obligations

| Requirement | Verified evidence | Boundary |
|---|---|---|
| SDK code | Official [MIT licence](https://github.com/Idirect-Tech/Breeze-Python-SDK/blob/4125106b48932ff99b45d593749dcec21c552558/LICENSE), SDK source/version 1.0.68 at `4125106b48932ff99b45d593749dcec21c552558` | Software reuse with its notice conditions does not license exchange data. No SDK or reference MCP package installed/imported. |
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

## Configuration and actual public-source result

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

Authenticated Breeze requests: **zero**. Historical `get_names()`/V2 calls: **zero**.
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

## Exact M1 status and next prerequisite

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
