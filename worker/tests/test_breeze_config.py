"""Fake private-file values only. No credential, SDK or network requirement."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

from worker.providers.breeze_config import ConfigurationBlocked, FIELDS, load_manual_session, main

NOW = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
VALUES = dict(zip(FIELDS, ('FAKE-KEY-NOT-A-CREDENTIAL', 'FAKE-SECRET-NOT-A-CREDENTIAL',
    'FAKE-NEW-MANUAL-SESSION', '2026-11-02T11:00:00Z', 'true')))


def config(tmp_path, **updates):
    values = {**VALUES, **updates}
    path = tmp_path/'private.env'
    path.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n')
    path.chmod(0o600)
    return path


def test_private_fresh_manual_session_and_secret_safe_representations(tmp_path):
    result = load_manual_session(config(tmp_path), now=NOW)
    assert result.api_session.get_secret_value() == VALUES['ICICI_API_SESSION']
    assert result.created_at.hour == 11
    assert all(value not in repr(result) for value in list(VALUES.values())[:3])
    assert all(value not in str(asdict(result)) for value in list(VALUES.values())[:3])


@pytest.mark.parametrize('missing', FIELDS)
def test_missing_required_fields_do_not_read_environment_or_cached_session(tmp_path, monkeypatch, missing):
    monkeypatch.setenv('ICICI_API_SESSION', 'FAKE-OLD-EXPOSED-TOKEN')
    path = config(tmp_path, **{missing: ''})
    with pytest.raises(ConfigurationBlocked, match='missing_config_fields') as err:
        load_manual_session(path, now=NOW)
    assert 'FAKE' not in str(err.value)


@pytest.mark.parametrize('confirmation', ['false', 'TRUE', 'yes'])
def test_explicit_freshness_confirmation_required(tmp_path, confirmation):
    with pytest.raises(ConfigurationBlocked, match='fresh_unexposed_manual_session'):
        load_manual_session(config(tmp_path, ICICI_FRESH_SESSION_CONFIRMED=confirmation), now=NOW)


@pytest.mark.parametrize('created', ['FAKE-PRIVATE-VALUE', '2026-11-02T11:00:00',
    '2026-11-02T11:00:00+05:30'])
def test_timestamp_errors_are_sanitized(tmp_path, created):
    with pytest.raises(ConfigurationBlocked, match='manual_session_utc_time_required') as err:
        load_manual_session(config(tmp_path, ICICI_SESSION_CREATED_AT_UTC=created), now=NOW)
    assert created not in str(err.value)


@pytest.mark.parametrize('created', ['2026-11-02T13:00:00Z', '2026-11-01T12:00:00Z',
    '2026-11-01T17:00:00Z'])
def test_future_old_and_previous_indian_date_sessions_rejected(tmp_path, created):
    with pytest.raises(ConfigurationBlocked, match='manual_session_stale_or_future'):
        load_manual_session(config(tmp_path, ICICI_SESSION_CREATED_AT_UTC=created), now=NOW)


@pytest.mark.parametrize('mode', [0o644, 0o640, 0o666])
def test_nonprivate_file_is_rejected(tmp_path, mode):
    path = config(tmp_path); path.chmod(mode)
    with pytest.raises(ConfigurationBlocked, match='owner_only_regular_config'):
        load_manual_session(path, now=NOW)


def test_symlink_and_missing_file_rejected(tmp_path):
    target = config(tmp_path); link = tmp_path/'link.env'; link.symlink_to(target)
    for path in (link, tmp_path/'missing.env'):
        with pytest.raises(ConfigurationBlocked, match='private_config_unavailable'):
            load_manual_session(path, now=NOW)


@pytest.mark.parametrize('extra', ['ICICI_API_KEY=FAKE-SECOND-KEY\n',
    'UNKNOWN-PRIVATE-KEY=PRIVATE-SECRET\n', 'PRIVATE-SECRET-WITHOUT-EQUALS\n'])
def test_duplicate_unknown_and_malformed_lines_do_not_echo_input(tmp_path, extra):
    path = config(tmp_path)
    with path.open('a') as out: out.write(extra)
    with pytest.raises(ConfigurationBlocked) as err:
        load_manual_session(path, now=NOW)
    assert not any(word in str(err.value) for word in ('PRIVATE', 'FAKE', 'SECRET'))


def test_dotenv_values_are_literal_not_shell_commands(tmp_path):
    value = 'FAKE#=+!$(must-not-execute)'
    result = load_manual_session(config(tmp_path, ICICI_API_KEY=value), now=NOW)
    assert result.api_key.get_secret_value() == value


def test_preflight_does_not_claim_authentication_or_print_secrets(tmp_path, monkeypatch, capsys):
    path = config(tmp_path, ICICI_API_SESSION='')
    monkeypatch.setattr(sys, 'argv', ['preflight', '--config', str(path)])
    assert main() == 2
    output = capsys.readouterr().out
    assert 'NOT_ATTEMPTED' in output and 'BLOCKED' in output
    assert all(value not in output for value in list(VALUES.values())[:3])
