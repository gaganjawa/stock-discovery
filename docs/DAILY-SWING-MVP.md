# Daily-swing MVP — software handoff

Scope selected by the owner on 14 October 2026: finish the local daily-swing MVP first; defer hosting and broader v1.0 features. This is the synthetic-data edition, not a live-market product.

## Included software

| Workflow | Delivery |
|---|---|
| Local setup | One command starts database, migrations, API, worker and UI; missing owner key generated; existing credentials preserved |
| Access | Owner login, signed session, logout, origin checks and throttling |
| Data | Load fictional history; quality/provenance/version checks |
| Daily signals | Frozen EMA/volume/breakout rules; BUY/WAIT/insufficient evidence; sizing, entry, stop, target, expiry and invalidation |
| Replay | Stock/date/strategy selection; only cutoff-known candles before explicit reveal; costs, fills and ambiguity handling |
| Scorecard | Separate metrics/counts, version-group selection, single-slot portfolio, exclusions and synthetic cash reference |
| Experiments | Persistent batch jobs, retries, failure inspection, versioned reruns and audit JSON export |
| Validation | Grouped samples/descriptive intervals and deterministic chronological assignment audit |
| Explanation | Rule-based explanation always available; optional on-demand OpenAI explanation of frozen synthetic facts |

## Run

1. Start Docker with Compose available.
2. Run `python3 scripts/local.py start` in the repository.
3. Open http://127.0.0.1:5173. Sign in with `AUTH_TOKEN` from `.env`.
4. Load synthetic history from Dashboard; use Replay and Scorecard.

`python3 scripts/local.py stop` preserves existing containers/data. Do not remove the database container/volume if you want to retain local experiments. The launcher is loopback-only local convenience; it is not the private hosting deployment procedure.

## LLM configuration

Both `.env` and `.env.example` exist. Existing `.env` values were preserved, blank LLM fields added only when missing, and file permissions set to owner-only. `.env` is ignored by Git.

- `OPENAI_API_KEY=` — paste your key locally later.
- `LLM_ENABLED=false` — set true only when you want on-demand API calls.
- `LLM_MODEL=gpt-4.1-mini` — configurable.
- `LLM_MAX_OUTPUT_TOKENS=512` — bounded between 64 and 2048.

Restart with the launcher after changing settings. A key is not required for normal signals/replay or rule explanations. No paid provider call was made during development. Provider success/error behavior is tested with mocks; real account/model access remains unverified until you configure it.

LLM text cannot mutate the frozen recommendation. Only frozen synthetic facts/indicators are sent; no future outcomes, credentials or tools. Output is rendered as plain text with an AI-error disclaimer. Requests time out after 20 seconds, have no automatic retry and use `store: false`; this flag is not a claim of zero provider retention. Provider failures fall back to rule text. Explanation history, persistent caching and global AI spending budgets are later enhancements.

Official references: [Responses API migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses) and [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Deferred, not blocking this local edition

Hosting/B2/off-host recovery; permitted real data and broker integrations; real buy-and-hold benchmarks; comprehensive corporate actions; untouched-test/trial-ledger controls; company/news/IPO workflows; live portfolios; intraday; learned models; broad AI budgets and full v1.0 acceptance. Existing source rights and private-release gates remain recorded; they are not marked completed.

## Acceptance

Local checks: 58 application tests, 7 script tests and frontend build passed. Implementation `a9a3eb7` passed [full CI](https://github.com/gaganjawa/stock-discovery/actions/runs/38612490959): 58 application tests, 11 database cases, 7 script tests, build and browser acceptance. The local stack was also started successfully and API/UI/database/worker plus owner login/dashboard/logout smoke checks passed. Local app is left running at http://127.0.0.1:5173. **Local synthetic MVP software acceptance: complete.** Live LLM provider access was mocked, not called. The browser workflow covers login, load, freeze, no-key explanation, reveal, version selection, reports, batch completion and downloaded audit. Secrets stay out of Git and frontend configuration.
