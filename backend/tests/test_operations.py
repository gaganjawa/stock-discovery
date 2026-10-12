import json
from stock_discovery_analysis.operations import event, heartbeat, healthy


def test_operational_logs_drop_sensitive_fields():
    raw = event("request_rejected", status=401, token="SECRET_CANARY",
                cookie="SECRET_CANARY", query="SECRET_CANARY", exception="SECRET_CANARY")
    assert "SECRET_CANARY" not in raw
    assert json.loads(raw) == {"event": "request_rejected", "status": 401}


def test_worker_health_fails_closed(tmp_path):
    path = tmp_path / "heartbeat"
    assert not healthy(path)
    heartbeat(True, path)
    data = json.loads(path.read_text())
    assert healthy(path, now=data["at"]+30)
    assert not healthy(path, now=data["at"]+121)
    heartbeat(False, path)
    assert not healthy(path)
