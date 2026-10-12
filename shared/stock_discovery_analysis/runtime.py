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
    if (origin.scheme != "https" or not origin.hostname or
            not origin.hostname.endswith(".ts.net") or origin.username or
            origin.password or origin.path or origin.query or origin.fragment or
            origin.port not in (None, 443)):
        raise ValueError("Private deployment requires the exact Tailscale HTTPS origin")
    if os.getenv("COOKIE_SECURE") != "true":
        raise ValueError("Private deployment requires secure cookies")
    if not os.getenv("DATABASE_URL_FILE"):
        raise ValueError("Private runtime requires a database secret file")
    from psycopg.conninfo import conninfo_to_dict
    db = conninfo_to_dict(setting("DATABASE_URL"))
    if db.get("user") != "stk_runtime" or len(db.get("password", "")) < 32:
        raise ValueError("Private runtime requires strong separate runtime credentials")
    if not os.getenv("CODE_VERSION") or os.getenv("CODE_VERSION") == "local-unversioned":
        raise ValueError("Private deployment requires code provenance")
