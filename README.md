# Stock Discovery

Private Indian equity research: discover stocks using news, fundamentals, technical indicators, candles and volume; produce evidence-linked recommendations; compare forecasts and simulated trades with subsequent prices and forward paper results.

Agreed architecture: React + TypeScript + Lightweight Charts, FastAPI, one scheduled Python worker, PostgreSQL, shared Python analysis for historical and live modes, and Docker Compose. An existing LLM supports grounded research; predictive ML experiments come later. No initial microservices, Kubernetes or Redis.

Current ticket: **STK-012 — CI and reproducible builds**, P1, v0.1. In validation. [Build and CI instructions](docs/STK-012.md). STK-013 remains unstarted.

- [Recommendation contract](docs/contracts/recommendation-contract.md)
- [Evaluation contract](docs/contracts/evaluation-contract.md)
- [Capital and risk contract](docs/contracts/capital-risk-contract.md)
- [STK-010 delivery record](docs/STK-010.md)
- [Synthetic JSON examples](docs/contracts/examples/)
- [Working Kanban plan](docs/stock-platform-kanban-plan.md)
- [Original supplied plan](docs/reference/stock-platform-kanban-plan.md)
- [System design](docs/stock-discovery-system-design.docx)
- [Delivery board](https://stock-platform-kanban.jawagag.chatgpt.site)

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

Open the URL printed by Vite (normally http://127.0.0.1:5173). Use the sidebar to explore five sections and toggle fictional examples. No API or database is required for this preview.
