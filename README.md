# Stock Discovery

Private Indian equity research: discover stocks using news, fundamentals, technical indicators, candles and volume; produce evidence-linked recommendations; compare forecasts and simulated trades with subsequent prices and forward paper results.

Agreed architecture: React + TypeScript + Lightweight Charts, FastAPI, one scheduled Python worker, PostgreSQL, shared Python analysis for historical and live modes, and Docker Compose. An existing LLM supports grounded research; predictive ML experiments come later. No initial microservices, Kubernetes or Redis.

Current ticket: **STK-001 — Recommendation contract**, P1, v0.1. **Done**: contract, fictional examples and validation are committed and pushed; the hosted board is updated. Delivery evidence is in [the ticket record](docs/STK-001.md). This repository contains documentation and fixture validation only. No application, replay engine, database migrations or deployment is implemented; STK-002 and the rest of the backlog are not started.

- [Recommendation contract](docs/contracts/recommendation-contract.md)
- [Synthetic JSON examples](docs/contracts/examples/)
- [Working Kanban plan](docs/stock-platform-kanban-plan.md)
- [Original supplied plan](docs/reference/stock-platform-kanban-plan.md)
- [System design](docs/stock-discovery-system-design.docx)
- [Delivery board](https://stock-platform-kanban.jawagag.chatgpt.site)

Validate with Python 3.9 or later (standard library only):

```sh
python3 scripts/validate_contract_examples.py
```

All example instruments, market data, holdings and costs are synthetic. The supplied planning documents are preserved as references; their budgets are planning assumptions, not account data or activated settings.
