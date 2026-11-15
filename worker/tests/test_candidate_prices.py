import pytest
from worker.candidate_prices import RefreshConfig,retry_reason
from worker.providers.upstox import UpstreamAccessRejected


def config(**updates):
    return dict(market=dict(account_ref='test',grant_file='/test/grants',token_file='/test/token',
        symbols=('INFY',),retention_days=365,lookback_days=40,**updates),scanner_keys=('scanner',))


def test_bounds_and_price_only_mode():
    assert RefreshConfig(**config()).max_symbols==20
    with pytest.raises(ValueError):RefreshConfig(**config(financial_statements=True))
    with pytest.raises(ValueError):RefreshConfig(**config(corporate_actions=True))
    with pytest.raises(ValueError):RefreshConfig(**{**config(),'max_symbols':101})
    with pytest.raises(ValueError):RefreshConfig(**{**config(),'candidate_days':8})


@pytest.mark.parametrize('error,reason',[(TimeoutError(),'transient'),(PermissionError(),'rights'),
    (FileNotFoundError(),'credentials'),(UpstreamAccessRejected(401),'credentials'),
    (UpstreamAccessRejected(403),'rights'),(ValueError('source_rate_limited'),'transient'),
    (ValueError('instrument_missing_or_ambiguous:TEST'),'readiness'),(RuntimeError('secret'),'permanent')])
def test_sanitized_retry_classification(error,reason):assert retry_reason(error)==reason


def test_hosted_heartbeat_advances_only_after_a_completed_cycle(tmp_path,monkeypatch):
    import json
    from contextlib import nullcontext
    from worker import candidate_prices as worker
    health=tmp_path/'health.json'
    monkeypatch.setenv('CANDIDATE_PRICE_HEALTH_FILE',str(health))
    monkeypatch.setattr(worker,'setting',lambda _: 'synthetic-only')
    monkeypatch.setattr(worker.psycopg,'connect',lambda *a,**k:nullcontext(object()))
    monkeypatch.setattr(worker,'cycle',lambda *a,**k:dict(status='idle',provider_requests=0))
    worker.serve(RefreshConfig(**config()),True)
    old=health.read_bytes();assert json.loads(old)['result_status']=='idle'
    def failed(*a,**k):raise ConnectionError('synthetic database outage')
    monkeypatch.setattr(worker,'cycle',failed)
    with pytest.raises(ConnectionError):worker.serve(RefreshConfig(**config()),True)
    assert health.read_bytes()==old
