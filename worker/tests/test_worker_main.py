from worker.main import run_once


def test_worker_cycle_is_synthetic_and_non_actionable() -> None:
    result = run_once()
    assert result["job"] == "synthetic-heartbeat"
    assert result["recommendation"]["mode"] == "live"
    assert result["recommendation"]["is_synthetic"] is True
    assert result["recommendation"]["is_actionable"] is False
