"""STK-004/014 owner-authorized transient SDK diagnostic, never ingestion.

Runs only in a dedicated child, with pinned SDK source, suppressed SDK output,
GET-only transport and durable local request accounting. No Grant is constructed,
no application rights/fence check is overridden, and no retained evidence is read.
The production probe_infy/ingestion path retains its independent Access checks.
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone, date
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.parse import urlsplit
import zipfile

import httpx
from worker.providers.breeze_config import load_manual_session, ConfigurationBlocked
from worker.providers.breeze_probe import resolve_infy

MASTER = 'https://directlink.icicidirect.com/MotherAppMaster/SecurityMaster.zip'
AUTH = 'https://api.icicidirect.com/breezeapi/api/v1/customerdetails'
HISTORY = 'https://breezeapi.icicidirect.com/api/v2/historicalcharts'
PINS = {
    'breeze_connect/__init__.py': '56c808bf033f4056a1a2048a54ff9bdd6cf6910752942aca57158f36800b9ec4',
    'breeze_connect/breeze_connect.py': '08b2e28146a8d4f45b1930ec77a41b26cf6cb7aa9e76adf4680f530fe04b204c',
    'breeze_connect/config.py': 'e445346cad62d4fe420c3cf60bc2c7085137903b0dc070bfdb51d542b7c95e70',
}


class ProbeBlocked(ValueError):
    """Only locally defined, content-free diagnostic codes may be returned."""


def require(ok, code):
    if not ok:
        raise ProbeBlocked(code)


class Quota:
    """Serialize ALL local diagnostic keys; 6/minute and 12/rolling 24h.

    Other devices/clients are outside this ledger; provider account quotas still
    apply. Existing/corrupt/exhausted state is never reset to retry a failed call.
    """
    def __init__(self, path):
        try:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.write(fd, b'[]'); os.fsync(fd)
        except FileExistsError:
            fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        self.file = os.fdopen(fd, 'r+')
        try:
            s = os.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid() and
                    s.st_nlink == 1 and not s.st_mode & 0o077 and s.st_size <= 16384,
                    'private_quota_file_required')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.file.close(); raise ProbeBlocked('quota_unavailable_or_busy') from None

    def reserve(self, now):
        self.file.seek(0)
        try:
            rows = json.load(self.file)
            require(isinstance(rows, list) and len(rows) <= 12 and
                    all(type(t) in (int, float) and t <= now for t in rows), 'invalid_quota')
        except (ValueError, TypeError):
            raise ProbeBlocked('quota_state_invalid_or_clock_regressed') from None
        rows = [t for t in rows if t > now-86400]
        require(len(rows) < 12 and sum(t > now-60 for t in rows) < 6, 'probe_request_budget_exhausted')
        rows.append(now)
        self.file.seek(0); json.dump(rows, self.file); self.file.truncate(); self.file.flush()
        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


class ReadOnlyHTTP:
    def __init__(self, credentials, quota, *, transport=None):
        self.credentials, self.quota = credentials, quota
        self.client = httpx.Client(transport=transport, trust_env=False, follow_redirects=False,
                                  timeout=httpx.Timeout(10, connect=5))
        self.cache, self.requests = {}, []
        self.authentication_ok = False

    def get(self, method, url, **kwargs):
        require(str(method).upper() == 'GET' and url in (MASTER, AUTH, HISTORY), 'non_read_endpoint_denied')
        require(not urlsplit(url).query, 'query_url_denied')
        if url == HISTORY:
            p = kwargs.get('params', {})
            require(self.authentication_ok and set(p) == {'interval', 'from_date', 'to_date',
                    'stock_code', 'exch_code', 'product_type'} and
                    (p['interval'], p['stock_code'], p['exch_code'], p['product_type']) ==
                    ('1day', 'INFTEC', 'NSE', 'cash'), 'historical_scope_denied')
            first, last = date.fromisoformat(p['from_date'][:10]), date.fromisoformat(p['to_date'][:10])
            require(first <= last < datetime.now(timezone.utc).date() and (last-first).days <= 90,
                    'historical_window_denied')
        if url == AUTH:
            body = json.loads(kwargs.get('data', '{}'))
            require(set(body) == {'AppKey', 'SessionToken'} and
                    body['AppKey'] == self.credentials.api_key.get_secret_value() and
                    body['SessionToken'] == self.credentials.api_session.get_secret_value(), 'session_scope_denied')
        if url == MASTER and url in self.cache:
            raw, headers = self.cache[url]
            return httpx.Response(200, content=raw, headers=headers, request=httpx.Request('GET', url))
        self.quota.reserve(time.time())
        require(len(self.requests) < 5, 'probe_request_limit')
        record = dict(resource={MASTER: 'security_master', AUTH: 'manual_session_exchange', HISTORY: 'infy_daily'}[url])
        self.requests.append(record)
        limit = 25_000_000 if url == MASTER else 1_000_000
        started = time.monotonic()
        with self.client.stream('GET', url, headers=kwargs.get('headers'),
                                content=kwargs.get('data'), params=kwargs.get('params')) as response:
            record['http_status'] = response.status_code
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                require(len(raw) <= limit and time.monotonic()-started <= 30, 'response_bound_exceeded')
            record.update(received_at=datetime.now(timezone.utc).isoformat(), bytes=len(raw))
            if url != AUTH:
                record['sha256'] = hashlib.sha256(raw).hexdigest()
            headers = {k:response.headers[k] for k in ('content-type','date','last-modified') if k in response.headers}
            record['response_headers'] = headers
            require(response.status_code == 200, 'upstream_http_'+str(response.status_code))
        if url == MASTER:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                require(sum(x.file_size for x in archive.infolist()) <= 128_000_000 and
                        archive.getinfo('NSEScripMaster.txt').file_size <= 16_000_000, 'master_expansion_limit')
            self.cache[url] = (bytes(raw), headers)
        if url == AUTH:
            body = json.loads(raw)
            self.authentication_ok = (type(body.get('Status')) is int and body['Status'] == 200 and
                'Error' in body and body['Error'] is None and
                isinstance(body.get('Success'), dict) and bool(body['Success'].get('session_token')))
            record['provider_status'] = body.get('Status') if type(body.get('Status')) is int else None
        return httpx.Response(200, content=bytes(raw), headers=headers, request=httpx.Request('GET', url))

    def urlopen(self, url, *args, **kwargs):
        require(url == MASTER, 'unapproved_download_denied')
        return io.BytesIO(self.get('GET', url).content)

    def close(self):
        self.cache.clear(); self.client.close()


def inspect_prices(response, start, end):
    require(isinstance(response, dict), 'historical_response_invalid')
    status = response.get('Status')
    require(type(status) is int and status == 200 and 'Error' in response and
            response['Error'] is None, 'historical_provider_rejected')
    rows = response.get('Success')
    require(isinstance(rows, list) and len(rows) <= 91, 'historical_row_bound')
    labels, invalid = [], 0
    for row in rows:
        require(isinstance(row, dict) and row.get('stock_code') == 'INFTEC' and
                row.get('exchange_code') == 'NSE' and
                row.get('product_type') in (None, 'Cash', 'cash'), 'historical_identity_mismatch')
        try:
            label = datetime.fromisoformat(row['datetime'])
            require(start <= label.date().isoformat() <= end, 'historical_date_outside_window')
            labels.append(label)
            values = [row[k] for k in ('open','high','low','close','volume')]
            require(not any(type(v) is bool for v in values), 'invalid_numeric_type')
            o,h,l,c,v = (Decimal(str(x)) for x in values)
            require(all(x.is_finite() for x in (o,h,l,c,v)) and
                    0 < l <= min(o,c) <= max(o,c) <= h and v >= 0 and v == v.to_integral_value(), 'invalid_ohlcv')
        except (ValueError, TypeError, KeyError, InvalidOperation):
            invalid += 1
    dates = [x.date().isoformat() for x in labels]
    return dict(provider_status=status, candle_count=len(rows), invalid_ohlcv_rows=invalid,
        first_date=min(dates,default=None), last_date=max(dates,default=None),
        duplicate_date_labels=len(dates)-len(set(dates)),
        chronological_order='ascending' if dates == sorted(dates) else 'descending' if dates == sorted(dates,reverse=True) else 'unordered',
        timestamps_timezone_aware=all(x.tzinfo is not None for x in labels) if labels else None,
        missing_sessions='UNAVAILABLE_authoritative_calendar_not_supplied',
        price_basis='unknown', volume_basis='unknown', corporate_actions='unverified',
        published_at=None, first_available_at=None, values_retained=False)


def child(args):
    result = dict(authentication='BLOCKED', historical='NOT_ATTEMPTED', requests=[],
        sdk_version='1.0.68', mode='owner_authorized_transient_read_only_diagnostic',
        M1_status='INSUFFICIENT_EVIDENCE', source_grant_activated=False, database_access=False,
        publication_authorized=False, paper_admission_authorized=False, trading_authorized=False)
    network = quota = None
    try:
        credentials = load_manual_session(args.config)
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
        require(args.start == first.isoformat() and args.end == last.isoformat() and
                first <= last < datetime.now(timezone.utc).date() and (last-first).days <= 90,
                'historical_window_denied')
        args.sdk_root = args.sdk_root.resolve()
        for file, expected in PINS.items():
            require(hashlib.sha256((args.sdk_root/file).read_bytes()).hexdigest() == expected, 'sdk_source_pin_mismatch')
        quota = Quota(args.quota)
        network = ReadOnlyHTTP(credentials, quota); result['requests'] = network.requests
        old_cwd = Path.cwd(); old_disable = logging.root.manager.disable
        # Parent owns this directory, so a timed-out child cannot leave SDK logs.
        with open(os.devnull,'w') as sink:
            try:
                os.chdir(args.runtime_dir); logging.disable(logging.CRITICAL)
                sys.dont_write_bytecode = True
                sys.path.insert(0,str(args.sdk_root))
                with redirect_stdout(sink), redirect_stderr(sink), \
                     patch('urllib.request.urlopen',network.urlopen), \
                     patch('requests.sessions.Session.request',lambda session,method,url,**kw:network.get(method,url,**kw)):
                    from breeze_connect import BreezeConnect
                    sdk = BreezeConnect(api_key=credentials.api_key.get_secret_value())
                    sdk.generate_session(api_secret=credentials.api_secret.get_secret_value(),
                                         session_token=credentials.api_session.get_secret_value())
                    require(network.authentication_ok and sdk.api_handler is not None, 'manual_session_rejected')
                    result['authentication'] = 'SUCCESS'
                    with zipfile.ZipFile(io.BytesIO(network.cache[MASTER][0])) as master:
                        code = resolve_infy(master.read('NSEScripMaster.txt').decode('utf-8-sig'))
                    names = sdk.get_names(exchange_code='NSE',stock_code='INFY')
                    require((names.get('isec_stock_code'),names.get('exchange_stock_code'),code) ==
                            ('INFTEC','INFY','INFTEC'), 'sdk_identity_mismatch')
                    result['identity_verified'] = True
                    raw = sdk.get_historical_data_v2(interval='1day',stock_code=code,exchange_code='NSE',
                        product_type='cash',from_date=args.start+'T00:00:00.000Z',to_date=args.end+'T23:59:59.000Z')
                    result['historical'] = inspect_prices(raw,args.start,args.end)
            finally:
                for name in ('APILogger','WebsocketLogger'):
                    for handler in list(logging.getLogger(name).handlers):
                        handler.close(); logging.getLogger(name).removeHandler(handler)
                logging.disable(old_disable); os.chdir(old_cwd)
    except Exception as exc:
        result['error'] = str(exc) if isinstance(exc,(ProbeBlocked,ConfigurationBlocked)) else 'sanitized_sdk_or_network_failure'
    finally:
        if network: network.close()
        if quota: quota.close()
    print(json.dumps(result))
    return 0 if isinstance(result['historical'],dict) else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True); p.add_argument('--sdk-root',type=Path,required=True)
    p.add_argument('--quota',type=Path,required=True)
    p.add_argument('--start',required=True); p.add_argument('--end',required=True)
    p.add_argument('--owner-authorized-transient-read',action='store_true',required=True)
    p.add_argument('--child',action='store_true')
    p.add_argument('--runtime-dir',type=Path,help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.child: return child(args)
    try:
        with tempfile.TemporaryDirectory(prefix='stk-breeze-private-') as private:
            run = subprocess.run([sys.executable,__file__,*sys.argv[1:],'--child','--runtime-dir',private],
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=120,text=True)
            result = json.loads(run.stdout)
    except Exception:
        print(json.dumps(dict(authentication='BLOCKED',error='isolated_probe_timeout_or_failure'))); return 2
    print(json.dumps(result,indent=2)); return run.returncode


if __name__ == '__main__':
    raise SystemExit(main())
