# Stock Discovery

## Authoritative architecture

[SD ARCH 3.0](docs/SD-ARCH-3.0.md) is the frozen design baseline for three-horizon automated NSE discovery and grounded AI research. Repository integration and [D3-01 contracts](docs/contracts/v2/README.md) are implemented following the subsequent owner authorization on 15 October 2026. [D3-02 source rights and feasibility](docs/D3-02-source-feasibility.md) is merged; real-source activation remains blocked. [D3-03 revision ingestion](docs/D3-03-revision-ingestion.md) is merged with fictional adapter acceptance. [D3-04 scheduling](docs/D3-04-scheduling.md) is ready for review; restricted-runtime permissions remain an explicit blocker. D3-05 through D3-13 remain unstarted. Existing synthetic MVP behavior is unchanged. External deployment remains unauthorized.

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
