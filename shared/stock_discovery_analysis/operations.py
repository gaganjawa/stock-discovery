"""Allowlisted operational events; no request/exception/credential strings."""
import json
import time
from pathlib import Path


def event(name, **fields):
    allowed = {key: value for key, value in fields.items()
               if key in {"status", "duration_ms", "failed_jobs", "stale_jobs"}
               and isinstance(value, (int, float, bool))}
    return json.dumps({"event": name, **allowed}, sort_keys=True)


def heartbeat(ok, path="/tmp/worker-health.json"):
    destination = Path(path)
    staging = destination.with_suffix(".tmp")
    staging.write_text(json.dumps({"at": time.time(), "ok": bool(ok)}))
    staging.replace(destination)


def healthy(path="/tmp/worker-health.json", now=None):
    try:
        data = json.loads(Path(path).read_text())
        age = (time.time() if now is None else now) - data["at"]
        return data["ok"] is True and 0 <= age <= 120
    except (OSError, ValueError, KeyError, TypeError):
        return False
