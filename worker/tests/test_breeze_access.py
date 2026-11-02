"""Synthetic transport/session tests; never import or contact the real SDK."""
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import httpx
from pydantic import SecretStr
import pytest

from worker.providers.breeze_config import ManualSession

SPEC = importlib.util.spec_from_file_location('verify_breeze_access',
    Path(__file__).resolve().parents[2]/'scripts'/'verify_breeze_access.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


@pytest.fixture
def credentials():
    return ManualSession(SecretStr('FAKE-KEY'), SecretStr('FAKE-SECRET'),
                         SecretStr('FAKE-SESSION'), datetime.now(timezone.utc))


def master():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('NSEScripMaster.txt',
            'ShortName,ExchangeCode,ISINCode,Series\nINFTEC,INFY,INE009A01021,EQ\n')
    return out.getvalue()


def history_params():
    return dict(interval='1day', from_date='2020-01-01T00:00:00.000Z',
        to_date='2020-01-30T23:59:59.000Z', stock_code='INFTEC', exch_code='NSE', product_type='cash')


def transport(tmp_path, credentials, handler):
    quota = probe.Quota(tmp_path/'quota.json')
    network = probe.ReadOnlyHTTP(credentials, quota, transport=httpx.MockTransport(handler))
    return network, quota


@pytest.mark.parametrize('method,url', [('POST', probe.AUTH), ('PUT', probe.HISTORY),
    ('DELETE', probe.MASTER), ('GET', 'https://api.icicidirect.com/breezeapi/api/v1/order'),
    ('GET', probe.MASTER+'?session=FAKE-SECRET')])
def test_nonread_and_unknown_endpoints_never_reach_transport(tmp_path, credentials, method, url):
    network, quota = transport(tmp_path, credentials, lambda r: pytest.fail('network used'))
    try:
        with pytest.raises(probe.ProbeBlocked): network.get(method, url)
        assert network.requests == []
    finally:
        network.close(); quota.close()


def test_master_is_memory_only_cached_and_unapproved_download_is_denied(tmp_path, credentials):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=master())
    network, quota = transport(tmp_path, credentials, handler)
    try:
        assert network.urlopen(probe.MASTER).read() == network.get('GET', probe.MASTER).content
        assert len(seen) == 1
        with pytest.raises(probe.ProbeBlocked): network.urlopen('https://unapproved.invalid')
        assert len(list(tmp_path.iterdir())) == 1  # accounting only, no response files
    finally:
        network.close(); quota.close()
    assert network.cache == {}


@pytest.mark.parametrize('status', [301, 401, 403, 429, 500])
def test_http_rejection_has_no_retry_redirect_or_private_body_in_diagnostics(tmp_path, credentials, status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text='FAKE-SECRET FAKE-SESSION',
                              headers={'Location': 'https://unapproved.invalid'})
    network, quota = transport(tmp_path, credentials, handler)
    try:
        with pytest.raises(probe.ProbeBlocked, match='upstream_http_'+str(status)) as err:
            network.get('GET', probe.AUTH, data=json.dumps(dict(AppKey='FAKE-KEY', SessionToken='FAKE-SESSION')))
        assert len(calls) == 1 and not network.authentication_ok
        assert 'FAKE' not in str(err.value)+json.dumps(network.requests)
        assert 'sha256' not in network.requests[0]  # no hash of account/session response
    finally:
        network.close(); quota.close()


def test_authentication_is_exact_and_history_requires_success(tmp_path, credentials):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=dict(Status=200, Error=None, Success=dict(session_token='FAKE-EXCHANGED')))
    network, quota = transport(tmp_path, credentials, handler)
    try:
        with pytest.raises(probe.ProbeBlocked): network.get('GET', probe.HISTORY, params=history_params())
        with pytest.raises(probe.ProbeBlocked): network.get('GET', probe.AUTH, data='{"AppKey":"WRONG"}')
        assert calls == []
        response = network.get('GET', probe.AUTH, data=json.dumps(dict(AppKey='FAKE-KEY', SessionToken='FAKE-SESSION')))
        assert response.json()['Status'] == 200  # requests-compatible buffered response for SDK
        assert network.authentication_ok
        network.get('GET', probe.HISTORY, params=history_params())
        assert len(calls) == 2
        assert 'FAKE' not in json.dumps(network.requests)
    finally:
        network.close(); quota.close()


@pytest.mark.parametrize('change', [dict(stock_code='INFY'), dict(exch_code='BSE'),
    dict(product_type='futures'), dict(interval='1minute'), dict(expiry_date='2020-01-01'),
    dict(from_date='2019-01-01T00:00:00Z'), dict(to_date='2999-01-01T00:00:00Z')])
def test_history_scope_and_window_are_bounded_before_network(tmp_path, credentials, change):
    network, quota = transport(tmp_path, credentials, lambda r: pytest.fail('network used'))
    network.authentication_ok = True
    try:
        with pytest.raises(probe.ProbeBlocked):
            network.get('GET', probe.HISTORY, params={**history_params(), **change})
        assert network.requests == []
    finally:
        network.close(); quota.close()


def test_quota_survives_restart_and_serializes_concurrent_clients(tmp_path):
    path = tmp_path/'quota.json'
    quota = probe.Quota(path)
    try:
        for _ in range(6): quota.reserve(1000)
        with pytest.raises(probe.ProbeBlocked, match='exhausted'): quota.reserve(1000)
        with pytest.raises(probe.ProbeBlocked, match='busy'): probe.Quota(path)
    finally: quota.close()
    quota = probe.Quota(path)
    try:
        for _ in range(6): quota.reserve(1061)
        with pytest.raises(probe.ProbeBlocked, match='exhausted'): quota.reserve(1122)
        with pytest.raises(probe.ProbeBlocked, match='clock_regressed'): quota.reserve(999)
        assert len(json.loads(path.read_text())) == 12
    finally: quota.close()


def test_corrupt_quota_is_not_reset(tmp_path):
    path = tmp_path/'quota.json'; path.write_text('broken'); path.chmod(0o600)
    quota = probe.Quota(path)
    try:
        with pytest.raises(probe.ProbeBlocked, match='quota_state_invalid'): quota.reserve(1000)
    finally: quota.close()
    assert path.read_text() == 'broken'


def candles():
    return dict(Status=200, Error=None, Success=[dict(stock_code='INFTEC', exchange_code='NSE',
        datetime=(datetime(2020,1,1)+timedelta(days=i)).isoformat(),
        open='100', high='102', low='99', close='101', volume='1000') for i in range(30)])


def test_ohlcv_summary_never_qualifies_sessions_prices_or_availability():
    result = probe.inspect_prices(candles(), '2020-01-01', '2020-01-30')
    assert result['candle_count'] == 30 and result['invalid_ohlcv_rows'] == 0
    assert result['chronological_order'] == 'ascending' and result['duplicate_date_labels'] == 0
    assert result['timestamps_timezone_aware'] is False
    assert result['price_basis'] == result['volume_basis'] == 'unknown'
    assert result['published_at'] is result['first_available_at'] is None
    assert result['missing_sessions'].startswith('UNAVAILABLE') and not result['values_retained']
    assert 'open' not in result and 'volume' not in result


@pytest.mark.parametrize('change', [dict(high='90'), dict(volume='0.5'), dict(close='NaN'), dict(low=True)])
def test_invalid_ohlcv_is_counted_not_hidden(change):
    response = candles(); response['Success'][0].update(change)
    assert probe.inspect_prices(response, '2020-01-01', '2020-01-30')['invalid_ohlcv_rows'] == 1


def test_duplicate_dates_and_mixed_timezone_labels_do_not_crash_or_imply_coverage():
    response = candles(); response['Success'][1]['datetime'] = '2020-01-01T00:00:00+05:30'
    result = probe.inspect_prices(response, '2020-01-01', '2020-01-30')
    assert result['duplicate_date_labels'] == 1 and result['timestamps_timezone_aware'] is False


def test_missing_error_or_wrong_identity_is_rejected():
    response = candles(); response.pop('Error')
    with pytest.raises(probe.ProbeBlocked, match='provider_rejected'):
        probe.inspect_prices(response, '2020-01-01', '2020-01-30')
    response = candles(); response['Success'][0]['stock_code'] = 'OTHER'
    with pytest.raises(probe.ProbeBlocked, match='identity_mismatch'):
        probe.inspect_prices(response, '2020-01-01', '2020-01-30')


def test_child_sanitizes_sdk_exceptions_and_cleans_connections(tmp_path, credentials, monkeypatch, capsys):
    monkeypatch.setattr(probe, 'load_manual_session', lambda path: credentials)
    monkeypatch.setattr(probe, 'PINS', {})
    class BrokenSDK:
        def __init__(self, **kwargs): raise ValueError('sdk_FAKE-SECRET FAKE-SESSION')
    monkeypatch.setitem(sys.modules, 'breeze_connect', SimpleNamespace(BreezeConnect=BrokenSDK))
    old_cwd, old_path = Path.cwd(), list(sys.path)
    args = SimpleNamespace(config=tmp_path/'unused', sdk_root=tmp_path, quota=tmp_path/'quota',
                           runtime_dir=tmp_path, start='2020-01-01', end='2020-01-30')
    try:
        assert probe.child(args) == 2
        result = json.loads(capsys.readouterr().out)
        assert result['authentication'] == 'BLOCKED'
        assert result['error'] == 'sanitized_sdk_or_network_failure' and 'FAKE' not in json.dumps(result)
        assert not any(result[k] for k in ('database_access','publication_authorized',
            'source_grant_activated','paper_admission_authorized','trading_authorized'))
        assert Path.cwd() == old_cwd
        other = probe.Quota(args.quota); other.close()  # previous connection released
    finally: sys.path[:] = old_path


def test_parent_timeout_removes_private_sdk_working_directory(tmp_path, monkeypatch, capsys):
    private = []
    def timeout(command, **kwargs):
        directory = Path(command[-1]); private.append(directory)
        (directory/'logs').mkdir(); (directory/'logs'/'apiLogs.log').write_text('')
        raise subprocess.TimeoutExpired(command, 120)
    monkeypatch.setattr(probe.subprocess, 'run', timeout)
    monkeypatch.setattr(sys, 'argv', ['probe', '--config', str(tmp_path/'config'), '--sdk-root',
        str(tmp_path), '--quota', str(tmp_path/'quota'), '--start','2020-01-01','--end','2020-01-30',
        '--owner-authorized-transient-read'])
    assert probe.main() == 2
    assert not private[0].exists()
    assert json.loads(capsys.readouterr().out)['error'] == 'isolated_probe_timeout_or_failure'
