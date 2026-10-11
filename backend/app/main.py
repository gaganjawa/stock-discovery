from fastapi import FastAPI

from stock_discovery_analysis import AnalysisMode, synthetic_recommendation

app = FastAPI(title="Stock Discovery API", version="0.1.0")


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "data_mode": "synthetic"}


@app.get("/api/v1/demo/recommendation")
def demo_recommendation() -> dict[str, object]:
    """A deterministic demo response; it is not investment advice or a live signal."""
    return synthetic_recommendation(AnalysisMode.HISTORICAL)


from .research import router
app.include_router(router)
