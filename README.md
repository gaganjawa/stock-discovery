# Stock Discovery

## Authoritative architecture

[SD ARCH 3.0](docs/SD-ARCH-3.0.md) is the frozen design baseline for three-horizon automated NSE discovery and grounded AI research. Repository integration and [D3-01 contracts](docs/contracts/v2/README.md) are implemented following the subsequent owner authorization on 15 October 2026. [D3-02 source rights and feasibility](docs/D3-02-source-feasibility.md) is merged; real-source activation remains blocked. [D3-03 revision ingestion](docs/D3-03-revision-ingestion.md) is merged with fictional adapter acceptance. [D3-04 scheduling](docs/D3-04-scheduling.md) is merged; restricted-runtime permissions remain an explicit blocker. [D3-05 quantitative policies](docs/D3-05-quant-policies.md) are merged. [D3-06 evidence ingestion](docs/D3-06-evidence-ingestion.md) is merged (PR #6). [D3-07 hybrid RAG](docs/D3-07-hybrid-rag.md) is merged (PR #7). [D3-08 bounded research and semantic judge](docs/D3-08-bounded-research.md) and the CI setup fix are merged. [D3-09 three-horizon publication and UI](docs/D3-09-publication-ui.md) integrates the quantitative engines, fictional evidence ingestion, fixed RAG, bounded agent, separate judge and deterministic decision gates. Human calibration and real activation remain unapproved. D3-10 paper portfolio and outcomes are merged (PR #11); D3-11 through D3-13 remain unstarted. Existing synthetic MVP behavior is unchanged. External deployment remains unauthorized.

## REAL-001 — actual-source integration (PARTIAL)

Phase 9 verifies a **limited research-only local beta**: genuine INFY charts, 24 financial facts, cited historical findings and explicit missing-session/qualification labels. Open `/#real-research` using the [local runbook](docs/REAL-001-runbook.md). The prospective Swing pilot remains **BLOCKED**: the final October 23 check lacks that session’s candle, and policy/action/volume/risk/research gates are unresolved. No real recommendation or prospective reference exists. [Phase 9 execution and launch checklist](docs/REAL-001-phase9.md) · [Policy review](docs/REAL-001-phase8-policy-decision.md). Provider values remain private.

The existing app now has a distinct **Real research** view with explicit blocked coverage and three horizons. Operational adapters are opt-in; no synthetic fallback or paper-admission bypass is added. See the [acceptance record](docs/REAL-001-acceptance.md), [provider/permission matrix](docs/REAL-001-provider-matrix.md) and [local runbook](docs/REAL-001-runbook.md). Keep tokens outside Git and never put values in `.env.example`.

## Three-horizon discovery

Start the existing local stack, sign in, and use **Dashboard → Three-horizon discovery → Run fictional discovery**. Choose Swing, Short-term or Long-term, then compare Quantitative only, Quantitative + RAG and Quantitative + agent. Inspect decisions, risk constraints, missing/conflicting evidence, citations, provenance and coverage. The worker automatically ingests the pinned fictional source feed for each requested run; no uploads or paid models are needed. All publications remain **MOCK / SHADOW / NON-ACTIONABLE**, with blocked admission and no quantity. The observation cutoff and actual publication time are displayed separately.

See [D3-09 API, validation, reproduction and activation boundaries](docs/D3-09-publication-ui.md). Existing synthetic workflows remain available.

## Local daily-swing MVP

Start Docker, then from this repository run:

```sh
python3 scripts/local.py start
```

Open http://127.0.0.1:5173 and sign in using `AUTH_TOKEN` in `.env`. The launcher creates a missing owner key without printing it or replacing existing credentials. Choose **Load synthetic history**, then **Replay → Freeze recommendation → Reveal**. Scorecard supports version groups, batches and export. Use `python3 scripts/local.py stop` to stop services while retaining their containers/data; `status` shows services.

The application currently uses fictional daily history. Real-market feeds, hosting, IPO/news, intraday and model training are deferred. See [MVP scope and acceptance](docs/DAILY-SWING-MVP.md).

### Optional AI explanation

`.env` and `.env.example` contain these fields. Add your key only to `.env`:

```dotenv
LLM_ENABLED=false
OPENAI_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_MAX_OUTPUT_TOKENS=512
```

After adding the key, set `LLM_ENABLED=true` and rerun the local launcher. **Explain recommendation** then makes an on-demand API request using frozen synthetic facts. It does not calculate or change the signal. With AI disabled, missing credentials or provider failure, the existing rule explanation remains available. No external API calls are needed for normal MVP operation. Never commit `.env`.

AI calls can incur provider charges when you enable them. Requests have a 20-second timeout and bounded output, no tools and no automatic retries. Broader AI budgets and persistent explanation history are deferred. The current integration is for the local Compose stack; private-host configuration remains separate.

---

Private Indian equity research: discover stocks using news, fundamentals, technical indicators, candles and volume; produce evidence-linked recommendations; compare forecasts and simulated trades with subsequent prices and forward paper results.

Existing MVP stack: React + TypeScript + Lightweight Charts, FastAPI, one scheduled Python worker, PostgreSQL, shared Python analysis for historical and live modes, and Docker Compose. Its optional LLM explanation summarizes frozen synthetic recommendations. The approved target adds grounded research, bounded investigation and ranking influence under deterministic risk controls; see SD ARCH 3.0 above. Predictive ML remains optional. No initial microservices, Kubernetes or Redis.

Current checkpoint: synthetic preview, hardened private configuration and encrypted local recovery/rollback verification pass; private release readiness is **PARTIAL**. **v0.1/v0.2 have not been tagged or privately deployed.** See [STK-018 release acceptance and recovery runbook](docs/STK-018.md) for gates, risks and release notes, and [work handoff](docs/WORK-HANDOFF.md) for local preview instructions.

- [Recommendation contract](docs/contracts/recommendation-contract.md)
- [Evaluation contract](docs/contracts/evaluation-contract.md)
- [Capital and risk contract](docs/contracts/capital-risk-contract.md)
- [STK-010 delivery record](docs/STK-010.md)
- [Synthetic JSON examples](docs/contracts/examples/)
- [Working Kanban plan](docs/stock-platform-kanban-plan.md)
- [Original supplied plan](docs/reference/stock-platform-kanban-plan.md)
- [System design](docs/stock-discovery-system-design.docx)
- [Lightweight progress board](docs/SIMPLE-BOARD.md)

Validate with Python 3.9 or later (standard library only):

```sh
python3 scripts/validate_contract_examples.py
python3 scripts/validate_evaluation_examples.py
python3 scripts/validate_capital_risk_examples.py
```

All example instruments, market data, holdings and costs are synthetic. The supplied planning documents are preserved as references; their budgets are planning assumptions, not account data or activated settings.

Run the UI locally (Node 20.19+ or 22.12+):

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the URL printed by Vite (normally http://127.0.0.1:5173). Use the sidebar to explore five sections and toggle fictional examples. The functional preview now requires the API, PostgreSQL, migrations and owner authentication; use the Compose instructions in the work handoff.

### Paper portfolios and outcome tracking (D3-10)

The authenticated dashboard now includes **Paper portfolio & outcomes**. Create a
separately labelled fictional simulation with virtual starting capital, run
D3-09 discovery, track published decisions, and advance a fictional session.
The local worker records reservations, fills, fees, immutable transactions and
outcomes. Cash is shared across horizons; risk limits govern every admission.
View holdings, outcome details, horizon/cohort comparisons and explicit data
limitations alongside the existing discovery and synthetic replay workflows.

MOCK/SHADOW recommendations remain blocked from forward-paper portfolios. The
fictional simulation contract never changes their original admission status.
Forward source/model/policy approvals and observation adapters remain
unconfigured; no broker orders or real-market activation are included.
See [D3-10 contracts, execution assumptions and API](docs/D3-10-paper-portfolio.md).

REAL-001 Phase 2 remains **PARTIAL**: configured official-document ingestion now
connects D3-06 to local D3-07/08 research, with rights-aware company views and
three-horizon input mapping. Real INFY filing access returned 403; publication
and prospective integration are unfinished. [Phase 2 details](docs/REAL-001-phase2.md).

### REAL-001 Phase 3 — PARTIAL

The existing publication engine now supports explicitly configured, permitted real
shadow research, with immutable prospective references and a rights-aware history
view. No genuine INFY publication or outcome has passed acceptance. Source rights,
calendar/action coverage, real policies and grounded model qualification remain
blocked. The T9 model folder and Ollama inventory passed the final recheck. See
[Phase 3 acceptance](docs/REAL-001-phase3.md) for commands, validation and A1–A14.

### REAL-001 Phase 4 — permission review, PARTIAL

[Phase 4 findings](docs/REAL-001-phase4.md) establish private Upstox market-data retention/research/replay rights from provider-community replies. Genuine filing-corpus rights remain unresolved; no actual INFY research was produced. The stop condition was followed: no additional conditional infrastructure. Consolidated Upstox and Infosys permission drafts are prepared, not sent.
