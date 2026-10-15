"""T03: deterministic permission failures before any processing/transfer."""
import json
from pathlib import Path

import pytest

from stock_discovery_contracts.rights import (
    Grant, UseRequest, authorize, cleanup_plan, guarded_use,
)

ROOT = Path(__file__).resolve().parents[2]


def grant(**changes):
    data = json.loads((ROOT / 'docs/contracts/rights/grants.synthetic.json').read_text())[0]
    data.update(changes)
    return Grant.model_validate_json(json.dumps(data))


def request(**changes):
    data = dict(
        source_id='SYN-source', account_ref='SYN-account', scope='prices',
        uses=['acquire'], region='IN', destination_region=None, processor_ref=None,
        requested_at='2026-10-15T12:00:00Z', synthetic=True, units=1,
        retention_days=30, attribution_present=True,
    )
    data.update(changes)
    return UseRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('use', ['acquire', 'store', 'extract', 'derive', 'historical_replay', 'paper_evaluation'])
def test_explicit_local_uses(use):
    assert authorize(grant(), request(uses=[use])).allowed


@pytest.mark.parametrize('changes,code', [
    ({'uses':['embed']}, 'use_denied'),
    ({'uses':['external_ai']}, 'use_denied'),
    ({'uses':['train']}, 'use_denied'),
    ({'uses':['export']}, 'use_denied'),
    ({'uses':['backup']}, 'use_denied'),
    ({'uses':['store','embed']}, 'use_denied'),
    ({'uses':['unknown']}, 'use_denied'),
    ({'region':'DE'}, 'region_denied'),
    ({'scope':'news'}, 'scope_denied'),
    ({'source_id':'other'}, 'source_account_mismatch'),
    ({'account_ref':'other'}, 'source_account_mismatch'),
    ({'synthetic':False}, 'synthetic_mismatch'),
    ({'requested_at':'2025-12-31T23:59:59Z'}, 'grant_not_yet_valid'),
    ({'requested_at':'2027-01-01T00:00:00Z'}, 'grant_expired'),
    ({'retention_days':31}, 'retention_exceeded'),
    ({'attribution_present':False}, 'attribution_missing'),
    ({'units':101}, 'operation_limit_exceeded'),
    ({'processor_ref':'remote'}, 'use_denied'),
    ({'destination_region':'US'}, 'destination_denied'),
])
def test_denial_prevents_callback(changes, code):
    calls, events = [], []
    with pytest.raises(PermissionError, match=code):
        guarded_use(lambda: grant(), request(**changes), events.append, lambda: calls.append('transferred'))
    assert calls == [] and len(events) == 1
    assert events[0].code == code and events[0].allowed is False


@pytest.mark.parametrize('status', ['pending', 'denied', 'revoked'])
def test_inactive_grants(status):
    g = grant(status=status, revoked_at='2026-10-14T00:00:00Z' if status=='revoked' else None)
    assert authorize(g, request()).code == 'grant_not_active'


def test_unknown_grant_and_revocation_between_calls():
    calls, events = [], []
    current = [grant()]
    run = lambda: guarded_use(lambda: current[0], request(), events.append, lambda: calls.append('read'))
    run()
    current[0] = grant(status='revoked', revoked_at='2026-10-15T11:00:00Z')
    with pytest.raises(PermissionError): run()
    current[0] = None
    with pytest.raises(PermissionError, match='grant_missing'): run()
    assert calls == ['read'] and len(events) == 3


def test_external_embedding_needs_both_permissions_and_destination():
    g = grant(allowed_uses=['embed','external_ai'], external_processors=['SYN-model'], regions=['IN','US'])
    r = request(uses=['embed','external_ai'], destination_region='US', processor_ref='SYN-model')
    assert authorize(g, r).allowed
    assert authorize(g, request(uses=['embed','external_ai'], processor_ref='SYN-model')).code == 'destination_required'
    assert authorize(g, request(uses=['embed','external_ai'], destination_region='US', processor_ref='other')).code == 'processor_denied'
    assert authorize(grant(allowed_uses=['embed']), r).code == 'use_denied'
    assert authorize(g, request(uses=['embed'], processor_ref='SYN-model')).code == 'use_denied'


@pytest.mark.parametrize('use', ['backup','export'])
def test_backup_and_export_require_destination_permission(use):
    g = grant(allowed_uses=[use])
    assert authorize(g, request(uses=[use])).code == 'destination_required'
    assert authorize(g, request(uses=[use], destination_region='DE')).code == 'destination_denied'
    assert authorize(g, request(uses=[use], destination_region='IN')).allowed


def test_audit_failure_prevents_use():
    calls=[]
    def broken_audit(decision): raise RuntimeError('audit unavailable')
    with pytest.raises(RuntimeError):
        guarded_use(lambda: grant(), request(), broken_audit, lambda: calls.append('read'))
    assert calls == []


def test_cleanup_is_explicit_and_permission_limited():
    assert cleanup_plan(grant(), '2026-10-15T12:00:00Z') is None
    plan=cleanup_plan(grant(), '2027-01-01T00:00:00Z')
    assert plan.reason=='expired' and not plan.keep_metadata_tombstone
    assert plan.include_derived_and_backups and plan.delete_content
    g=grant(status='revoked', revoked_at='2026-10-15T00:00:00Z', audit_tombstones_permitted=True)
    assert cleanup_plan(g, '2026-10-15T12:00:00Z').keep_metadata_tombstone
    assert cleanup_plan(None, '2026-10-15T12:00:00Z').deadline_days == 0


@pytest.mark.parametrize('changes', [
    {'allowed_uses':['magic']}, {'approval_evidence_ref':None},
    {'retention_days':None}, {'deletion_deadline_days':None},
    {'max_units_per_operation':None}, {'attribution':None},
    {'retention_days':True}, {'regions':['*']}, {'regions':[]},
    {'allowed_uses':['acquire','acquire']}, {'unexpected':True},
    {'expires_at':'2026-02-30T00:00:00Z'}, {'revoked_at':'2026-10-15T00:00:00Z'},
])
def test_invalid_grants(changes):
    with pytest.raises(ValueError): grant(**changes)


def test_records_cannot_be_mutated_and_no_real_grants_ship():
    g=grant()
    with pytest.raises(ValueError): g.status='active'
    assert isinstance(g.allowed_uses, tuple)
    records=json.loads((ROOT/'docs/contracts/rights/grants.synthetic.json').read_text())
    assert all(row['synthetic'] and row['source_id'].startswith('SYN-') for row in records)


def test_cleanup_deadline_does_not_move_on_retry():
    g=grant(status='revoked', revoked_at='2026-10-14T00:00:00Z', deletion_deadline_days=2)
    first=cleanup_plan(g, '2026-10-15T00:00:00Z')
    late=cleanup_plan(g, '2026-10-20T00:00:00Z')
    assert first.delete_by_at == late.delete_by_at == '2026-10-16T00:00:00Z'


def test_real_register_empty_and_schemas_current():
    import subprocess
    import sys
    assert json.loads((ROOT/'docs/contracts/rights/grants.real.json').read_text()) == []
    subprocess.run([sys.executable, str(ROOT/'scripts/export_rights_schemas.py'), '--check'], check=True)


def test_unknown_cleanup_terms_never_preserve_metadata_or_delay():
    g=grant(status='pending', approval_evidence_ref=None, deletion_deadline_days=30, audit_tombstones_permitted=True)
    plan=cleanup_plan(g, '2026-10-15T12:00:00Z')
    assert plan.deadline_days == 0 and not plan.keep_metadata_tombstone
    assert plan.delete_by_at == '2026-10-15T12:00:00Z'


def test_expiration_boundary_and_invalid_request():
    assert authorize(grant(), request(requested_at='2026-01-01T00:00:00Z')).allowed
    for changes in ({'uses':[]}, {'units':True}, {'units':0}, {'retention_days':0}, {'uses':['acquire','acquire']}):
        with pytest.raises(ValueError): request(**changes)
