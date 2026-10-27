"""STK-074 input/privacy guards; no database, files or providers touched."""
from types import SimpleNamespace

import pytest
from psycopg.pq import TransactionStatus

from stock_discovery_analysis.deletion_manifest import artifact_token, manifest, scope_token
from stock_discovery_analysis.deletion_manifest_contracts import ExternalCopy, ManifestRequest


def request():
    return ManifestRequest(source_id='SYN-provider', account_ref='SYN-account', grant_id='SYN-grant',
                           grant_version='v1', trigger='revocation', as_of_at='2026-10-27T00:00:00Z')


class NoDatabase:
    autocommit = True
    info = SimpleNamespace(dbname='production', transaction_status=TransactionStatus.IDLE)

    def transaction(self):
        raise AssertionError('must reject before opening database transaction')


def test_production_database_rejected_before_queries():
    with pytest.raises(ValueError, match='^manifest_disposable_database_required$'):
        manifest(NoDatabase(), request())


@pytest.mark.parametrize('changes', [
    {'source_id': 'real-provider'}, {'account_ref': 'real-account'}, {'synthetic': False},
    {'trigger': 'delete'}, {'as_of_at': '2026-02-30T00:00:00Z'}, {'grant_id': 'private source text / secret'},
])
def test_invalid_and_model_copy_inputs_are_sanitized(changes):
    with pytest.raises(ValueError, match='^manifest_inspection_failed$') as caught:
        manifest(NoDatabase(), request().model_copy(update=changes))
    assert 'secret' not in str(caught.value)


def test_registry_cannot_supply_paths_or_non_synthetic_copies():
    for copy in ({'copy_id': 'SYN-file', 'kind': 'filesystem', 'path': '/private/secret'},
                 ExternalCopy(copy_id='SYN-file', kind='backup').model_copy(update={'synthetic': False})):
        with pytest.raises(ValueError, match='^manifest_inspection_failed$'):
            manifest(NoDatabase(), request(), external_copies=(copy,))


def test_caller_transaction_is_not_changed():
    connection = NoDatabase()
    connection.autocommit = False
    with pytest.raises(ValueError, match='^manifest_idle_autocommit_required$'):
        manifest(connection, request())


def test_tokens_are_stable_and_scope_specific():
    r = request()
    assert scope_token(r) == scope_token(r.model_copy(update={'trigger': 'expiry'}))
    assert scope_token(r) != scope_token(r.model_copy(update={'grant_version': 'v2'}))
    assert artifact_token('discovery.revisions', ('SYN-one',)) == artifact_token('discovery.revisions', ['SYN-one'])
    assert artifact_token('discovery.revisions', ('SYN-one',)) != artifact_token('discovery.revisions', ('SYN-two',))


@pytest.mark.parametrize('key,value,expected,malformed', [
    ('revision_id', 'SYN-one', ('SYN-one',), False),
    ('revision_id', 123, (), True),
    ('revision_id', {'id': 'SYN-one'}, (), True),
    ('revision_id', None, (), True),
    ('revision_id', '   ', (), True),
    ('revision_id', ['SYN-one'], ('SYN-one',), True),
    ('revision_ids', [], (), False),
    ('revision_ids', ['SYN-one', 'SYN-two'], ('SYN-one', 'SYN-two'), False),
    ('revision_ids', 'SYN-one', ('SYN-one',), True),
    ('revision_ids', [123, None, {}], (), True),
    ('revision_ids', ['SYN-one', 123, {'id': 'SYN-two'}], ('SYN-one',), True),
    ('revision_ids', [['SYN-one'], 'SYN-two'], ('SYN-one', 'SYN-two'), True),
    ('source_observations', {'SYN-one': {}}, ('SYN-one',), False),
    ('source_observations', {'SYN-one': 123}, ('SYN-one',), True),
    ('source_observations', ['SYN-one'], ('SYN-one',), True),
    ('source_observations', None, (), True),
])
def test_reference_shapes_preserve_candidates_and_report_malformed_values(key, value, expected, malformed):
    from stock_discovery_analysis.deletion_manifest import _references
    assert _references(key, value) == (expected, malformed)


@pytest.mark.parametrize('key', ['instrument_revision_id', 'supersedes_id', 'fact_id',
                                'bundle_hash', 'baseline_hash', 'final_bundle_hash', 'portfolio_id'])
def test_contractual_nullable_references_are_not_malformed(key):
    from stock_discovery_analysis.deletion_manifest import _references
    assert _references(key, None) == ((), False)


@pytest.mark.parametrize('malformed', [123, {'id': 'SYN-untrusted'}, [123], ['SYN-valid', 123]])
def test_malformed_reference_prevents_exclusivity_and_propagates_without_database(malformed):
    from stock_discovery_analysis import deletion_manifest as dm
    from stock_discovery_analysis.revision_fixtures import fixture_grant, fixture_records
    from stock_discovery_contracts.v2 import digest
    grant = fixture_grant()
    raw = fixture_records()[0].model_dump(mode='json')
    raw['revision_id'] = 'SYN-valid'
    data = {
        'discovery.grants': [dict(grant_id=grant.grant_id, version=grant.version, payload=grant.model_dump(mode='json'))],
        'discovery.streams': [dict(stream_id='SYN-stream', source_id=grant.source_id, account_ref=grant.account_ref)],
        'discovery.revisions': [dict(revision_id='SYN-valid', source_id=grant.source_id, stream_id='SYN-stream',
                                    grant_id=grant.grant_id, grant_version=grant.version, payload=raw)],
        'discovery.rag_bundles': [dict(bundle_hash=digest('parent'), payload={
            'revision_ids': ['SYN-valid'], 'citations': [{'revision_id': malformed}]}),
            dict(bundle_hash=digest('child'), payload={'baseline_hash': digest('parent')})],
    }
    keys = {'discovery.grants': ('grant_id', 'version'), 'discovery.streams': ('stream_id',),
            'discovery.revisions': ('revision_id',), 'discovery.rag_bundles': ('bundle_hash',)}
    foreign = [('discovery.revisions', 'discovery.grants', ('grant_id', 'grant_version'), ('grant_id', 'version'))]
    target = ManifestRequest(source_id=grant.source_id, account_ref=grant.account_ref,
        grant_id=grant.grant_id, grant_version=grant.version, trigger='revocation', as_of_at='2026-10-27T00:00:00Z')
    result = dm._build(data, keys, foreign, target, (), set())
    bundles = [a for a in result.artifacts if a.artifact_type == 'discovery.rag_bundles']
    assert len(bundles) == 2
    for row in bundles:
        assert row.source_linkage == (dm.scope_token(target),)
        assert row.relationship == 'unknown' and row.proposed_disposition == 'resolve_lineage'
        assert 'malformed_json_dependency' in row.lineage_issues
        assert not row.deletion_authorized and not row.retention_authorized
    reversed_data = {k: list(reversed(v)) for k, v in reversed(list(data.items()))}
    assert result == dm._build(reversed_data, keys, foreign, target, (), set())
