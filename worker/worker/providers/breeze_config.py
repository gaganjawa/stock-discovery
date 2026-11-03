"""STK-004/014: private manual-session preflight; no SDK, login or network.

Only the explicitly selected file is read. No environment/cache/history fallback
and no shell evaluation. Readiness is not authentication or a source-data grant.
"""
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import stat
from zoneinfo import ZoneInfo

from pydantic import SecretStr

FIELDS = ('ICICI_API_KEY', 'ICICI_API_SECRET', 'ICICI_API_SESSION',
          'ICICI_SESSION_CREATED_AT_UTC', 'ICICI_FRESH_SESSION_CONFIRMED')


class ConfigurationBlocked(ValueError):
    """Codes contain no private file content, supplied values or unknown keys."""


@dataclass(frozen=True)
class ManualSession:
    api_key: SecretStr = field(repr=False)
    api_secret: SecretStr = field(repr=False)
    api_session: SecretStr = field(repr=False)
    created_at: datetime


def _require(condition, code):
    if not condition:
        raise ConfigurationBlocked(code)


def load_manual_session(path, *, now=None):
    """Require an owner-only regular file and explicitly confirmed new session.

    Same Indian calendar date / under 24 hours is a conservative LOCAL preflight,
    not a claim about the broker's exact expiry. Only the broker authenticates it.
    """
    try:
        fd = os.open(Path(path), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise ConfigurationBlocked('private_config_unavailable') from None
    with os.fdopen(fd, 'r', encoding='utf-8') as handle:
        metadata = os.fstat(handle.fileno())
        _require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
                 and metadata.st_nlink == 1 and not metadata.st_mode & 0o077,
                 'owner_only_regular_config_required')
        _require(metadata.st_size <= 16_384, 'private_config_size_limit')
        try:
            text = handle.read(16_385)
        except (OSError, UnicodeError):
            raise ConfigurationBlocked('private_config_unreadable') from None
    _require(len(text) <= 16_384, 'private_config_size_limit')
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        _require(separator and key in FIELDS, 'unknown_or_malformed_config_field')
        _require(key not in values, 'duplicate_config_field')
        if value.startswith(('"', "'")):
            _require(len(value) >= 2 and value[-1] == value[0], 'invalid_config_quoting')
            value = value[1:-1]
        _require(len(value) <= 4096 and all(ord(c) >= 32 for c in value),
                 'invalid_config_value')
        values[key] = value
    missing = [key for key in FIELDS if not values.get(key)]
    _require(not missing, 'missing_config_fields:'+','.join(missing))
    _require(values['ICICI_FRESH_SESSION_CONFIRMED'] == 'true',
             'fresh_unexposed_manual_session_confirmation_required')
    try:
        created = datetime.fromisoformat(values['ICICI_SESSION_CREATED_AT_UTC'].replace('Z', '+00:00'))
    except ValueError:
        raise ConfigurationBlocked('manual_session_utc_time_required') from None
    _require(created.tzinfo is not None and created.utcoffset() == timedelta(0),
             'manual_session_utc_time_required')
    now = now or datetime.now(timezone.utc)
    _require(now.tzinfo is not None, 'aware_preflight_clock_required')
    ist = ZoneInfo('Asia/Kolkata')
    _require(created <= now and now - created < timedelta(hours=24) and
             created.astimezone(ist).date() == now.astimezone(ist).date(),
             'manual_session_stale_or_future')
    return ManualSession(*(SecretStr(values[key]) for key in FIELDS[:3]), created_at=created)


def main():
    parser = argparse.ArgumentParser(description='Private Breeze configuration check; never authenticates.')
    parser.add_argument('--config', type=Path, default=Path('.env.breeze.local'))
    args = parser.parse_args()
    try:
        load_manual_session(args.config)
    except ConfigurationBlocked as exc:
        print(json.dumps(dict(configuration='BLOCKED', authentication='NOT_ATTEMPTED',
                              reason=str(exc), sdk_imported=False)))
        return 2
    print(json.dumps(dict(configuration='READY', authentication='NOT_ATTEMPTED',
                          sdk_imported=False, source_rights_verified=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
