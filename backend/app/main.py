from fastapi import FastAPI
from contextlib import asynccontextmanager
from stock_discovery_analysis.runtime import validate_private, setting
from .security import LoginLimiter, throttle
from stock_discovery_analysis.operations import event
from fastapi.responses import JSONResponse
import logging
import time


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


@app.middleware("http")
async def safe_request_log(request, call_next):
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        # Do not pass exception strings/tracebacks to the server logger.
        logging.getLogger("uvicorn.error").error(event("request_failed", status=500))
        return JSONResponse({"detail": "Internal request failure"}, status_code=500)
    if response.status_code >= 400:
        logging.getLogger("uvicorn.error").warning(event(
            "request_rejected", status=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000)))
    return response


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "data_mode": "synthetic"}


@app.get("/api/v1/demo/recommendation")
def demo_recommendation() -> dict[str, object]:
    """A deterministic demo response; it is not investment advice or a live signal."""
    return synthetic_recommendation(AnalysisMode.HISTORICAL)


from .research import router
app.include_router(router)

from .discovery import router as discovery_router
app.include_router(discovery_router)

from .paper import router as paper_router
app.include_router(paper_router)

from .real_research import router as real_research_router
app.include_router(real_research_router)
