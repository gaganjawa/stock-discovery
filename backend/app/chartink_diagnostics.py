"""Opt-in, bounded private rejection evidence. HTTP exposes structure only."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time

from stock_discovery_analysis.chartink_columns import COLUMNS
from stock_discovery_analysis.chartink_diagnostics import KNOWN_FIELDS, kind, payload_shape
from stock_discovery_analysis.runtime import setting

FILE = Path('/tmp/chartink-rejections/rejections.json')
MAX_RECORDS = 20
MAX_RECORD_BYTES = 128 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024
MAX_AGE_SECONDS = 24 * 60 * 60
REDACTED = '[REDACTED]'
_last_write_failed = False
SENSITIVE = re.compile(r'webhook|credential|password|passwd|secret|token|authorization|cookie|api.?key|capability|private.?key', re.I)
URL = re.compile(r'(?:[a-z][a-z0-9+.-]*://|/hooks/chartink/)[^\s"<>]+', re.I)
ASSIGNMENT = re.compile(r'(?:password|passwd|secret|token|api.?key|credential|authorization|capability)\s*[:=]\s*[^\s,;]+', re.I)
AUTH = re.compile(r'\b(?:bearer|basic)\s+\S+', re.I)
TOKEN = re.compile(r'(?<![\w])[A-Za-z0-9_=-]{32,}(?![\w])')


def enabled():
    return os.getenv('CHARTINK_REJECTION_DIAGNOSTICS') == 'true'


def _path():
    return Path(os.getenv('CHARTINK_REJECTION_FILE', str(FILE)))


def _redactor():
    # Load secret-file settings without logging values or exception details.
    secrets = [setting(name) for name in ('CHARTINK_WEBHOOK_SECRET', 'CHARTINK_PULL_SECRET', 'DATABASE_URL')]
    def clean(text):
        for secret in secrets:
            if secret:
                text = text.replace(secret, REDACTED)
        return TOKEN.sub(REDACTED, ASSIGNMENT.sub(REDACTED, AUTH.sub(REDACTED, URL.sub(REDACTED, text))))
    return clean


def _private(payload):
    clean = _redactor()
    remaining = 4096
    def redact(value, depth=0):
        nonlocal remaining
        remaining -= 1
        if depth > 12 or remaining < 0:
            return '[TRUNCATED]'
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if remaining < 0:
                    result['[TRUNCATED]'] = True
                    break
                # Unknown values are unnecessary for diagnosing column-set differences.
                # Keep their names/types in column_contract, never arbitrary credentials.
                safe_key = clean(key)
                result[safe_key] = REDACTED if SENSITIVE.search(key) or key not in KNOWN_FIELDS else redact(item, depth + 1)
            return result
        if isinstance(value, list):
            result = []
            for item in value:
                if remaining < 0:
                    result.append('[TRUNCATED]')
                    break
                result.append(redact(item, depth + 1))
            return result
        if isinstance(value, float) and not math.isfinite(value):
            return '[NON_FINITE]'
        return clean(value) if isinstance(value, str) else value

    columns = payload.get('columns') if isinstance(payload, dict) else None
    report = {'type': kind(columns), 'expected': list(COLUMNS), 'rows': []}
    if isinstance(columns, list):
        report['count'] = len(columns)
        for index, row in enumerate(columns[:200]):
            detail = {'index': index, 'type': kind(row)}
            if isinstance(row, dict):
                detail.update(missing=sorted(set(COLUMNS) - row.keys()),
                              extra=[clean(key) for key in sorted(row.keys() - set(COLUMNS))],
                              types={clean(key): kind(value) for key, value in row.items()})
            report['rows'].append(detail)
        report['truncated'] = len(columns) > 200
    return {'payload': redact(payload), 'column_contract': report}


def _check_file(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
        raise ValueError('unsafe_diagnostic_file')
    os.fchmod(fd, 0o600)


@contextmanager
def _locked():
    path = _path()
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('unsafe_diagnostic_directory')
        lock = os.open(path.name + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
        try:
            _check_file(lock)
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield directory, path.name
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def _load(directory, name):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return []
    with os.fdopen(fd, 'rb') as stream:
        _check_file(stream.fileno())
        raw = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError('oversize_archive')
    records = json.loads(raw)
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('invalid_archive')
    return records


def _encoded(records):
    return json.dumps(records, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def _bounded(records, now):
    records = [r for r in records if 0 <= now - r['recorded_epoch'] < MAX_AGE_SECONDS][-MAX_RECORDS:]
    while len(_encoded(records)) > MAX_ARCHIVE_BYTES:
        records.pop(0)
    return records


def _save(directory, name, records):
    # Single bounded archive; atomic replacement never exposes a partial record.
    # A fixed temporary name is safe under the exclusive lock and bounds crash debris.
    temp = name + '.tmp'
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
    try:
        _check_file(fd)
        os.ftruncate(fd, 0)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(_encoded(records))
            stream.flush()
            os.fsync(fd)
        os.replace(temp, name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(fd)
        try:
            os.unlink(temp, dir_fd=directory)
        except FileNotFoundError:
            pass


def record(payload, reason, body=None):
    global _last_write_failed
    if not enabled():
        return
    now = time.time()
    try:
        entry = {'recorded_epoch': now,
                 'summary': {'reason': reason, 'received_at': datetime.fromtimestamp(now, timezone.utc).isoformat(),
                             **payload_shape(payload)},
                 **_private(payload)}
        if body is not None:
            entry.update(body_sha256=hashlib.sha256(body).hexdigest(), body_bytes=len(body))
        if len(_encoded(entry)) > MAX_RECORD_BYTES:
            entry.pop('payload')
            entry.pop('column_contract')
            entry['capture_omitted'] = 'record_size_limit'
        with _locked() as (directory, name):
            records = _bounded(_load(directory, name) + [entry], time.time())
            _save(directory, name, records)
        _last_write_failed = False
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # Do not log payloads, secrets, paths, SQL or exception text. Rejection stays rejected.
        _last_write_failed = True


def read():
    """Safe HTTP summary; also prunes expiry during the existing 30s health check."""
    if not enabled():
        return {'enabled': False}
    try:
        with _locked() as (directory, name):
            records = _load(directory, name)
            retained = _bounded(records, time.time())
            # Remove an interrupted write (never used as accepted diagnostic evidence).
            try:
                os.unlink(name + '.tmp', dir_fd=directory)
            except FileNotFoundError:
                pass
            if retained != records:
                _save(directory, name, retained)
        return {'enabled': True, 'available': not _last_write_failed,
                'records': [r['summary'] for r in retained]}
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return {'enabled': True, 'available': False}
