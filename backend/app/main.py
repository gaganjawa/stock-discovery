from fastapi import FastAPI
from contextlib import asynccontextmanager
from stock_discovery_analysis.runtime import validate_private, setting
from .security import LoginLimiter, throttle


@asynccontextmanager
async def lifespan(app):
    validate_private()
    import os
    if os.getenv("DEPLOYMENT_MODE") == "private":
        if not os.getenv("AUTH_TOKEN_FILE") or len(setting("AUTH_TOKEN")) < 32:
            raise ValueError("Private deployment requires a strong owner secret file")
    yield

from stock_discovery_analysis import AnalysisMode, synthetic_recommendation

app = FastAPI(title="Stock Discovery API", version="0.1.0", lifespan=lifespan)
app.state.login_limiter = LoginLimiter()
app.middleware("http")(throttle)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "data_mode": "synthetic"}


@app.get("/api/v1/demo/recommendation")
def demo_recommendation() -> dict[str, object]:
    """A deterministic demo response; it is not investment advice or a live signal."""
    return synthetic_recommendation(AnalysisMode.HISTORICAL)


from .research import router
app.include_router(router)
