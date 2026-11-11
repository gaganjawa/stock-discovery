"""Secret-file configuration and fail-closed private runtime checks."""
import os
from pathlib import Path
from urllib.parse import urlsplit


def setting(name, default=""):
    filename = os.getenv(name + "_FILE")
    return Path(filename).read_text().strip() if filename else os.getenv(name, default)


def validate_private():
    mode = os.getenv("DEPLOYMENT_MODE", "local")
    if mode not in ("local", "private"):
        raise ValueError("Unknown deployment mode")
    if mode == "local":
        return
    origin = urlsplit(os.getenv("APP_ORIGIN", ""))
    access = os.getenv("PRIVATE_ACCESS_MODE", "tailscale")
    if access not in ("tailscale", "authenticated_proxy"):
        raise ValueError("Unknown private access mode")
    if (origin.scheme != "https" or not origin.hostname or
            (access == "tailscale" and not origin.hostname.endswith(".ts.net")) or origin.username or
            origin.password or origin.path or origin.query or origin.fragment or
            (access == "tailscale" and origin.port not in (None, 443))):
        raise ValueError("Private deployment requires an exact HTTPS origin for its access mode")
    if os.getenv("COOKIE_SECURE") != "true":
        raise ValueError("Private deployment requires secure cookies")
    if not os.getenv("DATABASE_URL_FILE"):
        raise ValueError("Private runtime requires a database secret file")
    from psycopg.conninfo import conninfo_to_dict
    db = conninfo_to_dict(setting("DATABASE_URL"))
    roles = ("stk_runtime",) if access == "tailscale" else ("stk_runtime", "stk_candidate_worker")
    if db.get("user") not in roles or len(db.get("password", "")) < 32:
        raise ValueError("Private runtime requires strong separate runtime credentials")
    if not os.getenv("CODE_VERSION") or os.getenv("CODE_VERSION") == "local-unversioned":
        raise ValueError("Private deployment requires code provenance")
