from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck_identifies_synthetic_mode() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_mode": "synthetic"}


def test_demo_recommendation_is_non_actionable() -> None:
    response = client.get("/api/v1/demo/recommendation")
    assert response.status_code == 200
    assert response.json() == {
        "recommendation_id": "SYN-STK010-HISTORICAL-001",
        "instrument": "SYNTHETIC-EQUITY",
        "decision": "wait",
        "mode": "historical",
        "is_synthetic": True,
        "is_actionable": False,
    }
