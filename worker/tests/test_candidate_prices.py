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
