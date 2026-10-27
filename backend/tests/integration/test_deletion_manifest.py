"""STK-074: synthetic provenance inspection, never a deletion acceptance claim.

The harness must provide disposable PostgreSQL. Each case creates an isolated
database; teardown is removal of the harness container, not destructive SQL.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb
import pytest

from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis import deletion_manifest as dm
from stock_discovery_analysis.deletion_manifest_contracts import (
    ArtifactRef, ExternalCopy, GrantScope, ManifestRequest,
)
from stock_discovery_analysis.evidence import Document, content_hash
from stock_discovery_analysis.evidence_fixtures import document_fixture, evidence_grant, adapter_fixture
from stock_discovery_analysis.evidence_storage import Access, ingest_next_evidence
from stock_discovery_analysis.revision_fixtures import fixture_records, fixture_request, NOW
from stock_discovery_analysis.revision_storage import Stream, Page, ingest_page

URL = os.getenv('STK_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='requires disposable PostgreSQL')


@pytest.fixture
def case():
    info = psycopg.conninfo.conninfo_to_dict(URL)
    assert info['dbname'] == 'stk013_test'
    name = 'stk074_manifest_' + uuid4().hex[:12]
    with psycopg.connect(psycopg.conninfo.make_conninfo(URL, dbname='postgres'), autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    from sqlalchemy.engine import URL as DatabaseURL
    migration_url = DatabaseURL.create('postgresql', username=info.get('user'), password=info.get('password'),
        host=info.get('host'), port=int(info['port']) if info.get('port') else None, database=name).render_as_string(hide_password=False)
    env = {**os.environ, 'DATABASE_URL': migration_url, 'PYTHONDONTWRITEBYTECODE': '1'}
    env.pop('DATABASE_URL_FILE', None)
    subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
        cwd=Path(__file__).resolve().parents[3], env=env, check=True, capture_output=True)
    with psycopg.connect(psycopg.conninfo.make_conninfo(URL, dbname=name), autocommit=True) as conn:
        def grant(**changes):
            return evidence_grant().model_copy(update=changes)
        grants = {
            'A': grant(grant_id='SYN-grant-A', version='v1', source_id='SYN-provider-A', account_ref='SYN-account-A'),
            'A2': grant(grant_id='SYN-grant-A', version='v2', source_id='SYN-provider-A', account_ref='SYN-account-A'),
            'Aother': grant(grant_id='SYN-other-grant-A', version='v1', source_id='SYN-provider-A', account_ref='SYN-account-A'),
            'Aaccount': grant(grant_id='SYN-other-account', version='v1', source_id='SYN-provider-A', account_ref='SYN-account-other'),
            'B': grant(grant_id='SYN-grant-B', version='v1', source_id='SYN-provider-B', account_ref='SYN-account-B'),
        }
        def seed(label, owner, text):
            grant = grants[owner]
            identity = fixture_records()[0].model_dump(mode='json')
            identity.update(revision_id='SYN-identity-'+label, source_revision='SYN-identity-'+label,
                            source_id=grant.source_id, listing_id='SYN-listing-'+label)
            identity['data']['issuer_id'] = 'SYN-issuer-'+label
            identity['data']['symbol'] = 'SYN-'+label
            stream = Stream(stream_id='SYN-identity-stream-'+label, source_id=grant.source_id,
                            account_ref=grant.account_ref, scope='universe')
            request = fixture_request('universe', source_id=grant.source_id, account_ref=grant.account_ref)
            ingest_page(conn, stream, Page(cursor=None, next_cursor=None, complete=True, records=(identity,)),
                        load_grant=lambda: grant, request=request, audit=lambda d: None)
            raw = document_fixture(rid='SYN-document-'+label).model_dump(mode='json')
            raw['revision'].update(source_id=grant.source_id, instrument_revision_id=identity['revision_id'],
                                   listing_id=identity['listing_id'])
            raw['revision']['data']['document_id'] = 'SYN-filing-'+label
            raw['issuer_id'] = identity['data']['issuer_id']
            body = json.loads(raw['body']); body.update(text=text, events=[dict(
                event_type='earnings', statement=text, status='confirmed', locator='synthetic paragraph')])
            raw['body'] = json.dumps(body)
            raw['revision']['data']['content_hash'] = content_hash(raw['body'])
            doc = Document.model_validate_json(json.dumps(raw))
            access = Access(lambda s: grant, lambda s: fixture_request(s.scope, source_id=s.source_id,
                account_ref=s.account_ref), lambda d: None, lambda: NOW)
            stream = Stream(stream_id='SYN-document-stream-'+label, source_id=grant.source_id,
                            account_ref=grant.account_ref, scope='filings')
            ingest_next_evidence(conn, stream, adapter_fixture(doc), access=access)
            return doc
        docs = {owner: seed(owner, owner, f'Fictional distinct evidence from {owner}: audited earnings grew during this period.') for owner in grants}
        scope = lambda owner: GrantScope(source_id=grants[owner].source_id, account_ref=grants[owner].account_ref,
            grant_id=grants[owner].grant_id, grant_version=grants[owner].version)
        request = ManifestRequest(**scope('A').model_dump(), trigger='expiry', as_of_at='2027-01-01T00:00:00Z')
        yield SimpleNamespace(conn=conn, docs=docs, grants=grants, seed=seed, scope=scope, request=request)


def find(result, table, *key, unresolved=False):
    identifier = dm.artifact_token(table, tuple(str(k) for k in key))
    return next((x for x in (result.unresolved_artifacts if unresolved else result.artifacts)
                 if x.artifact_type == table and x.identifier == identifier), None)


def bundle(conn, label, documents, **extra):
    identifier = digest(label)
    conn.execute('INSERT INTO discovery.rag_bundles VALUES (%s,%s)',
                 (identifier, Jsonb(dict(documents=documents, query={'mode': 'synthetic'}, **extra))))
    return identifier


def result_row(conn, run, base, final=None):
    conn.execute('INSERT INTO discovery.rag_reservations VALUES (%s,%s,%s,%s,%s,%s)',
                 (run, digest(run), 'SYN-model-account', NOW, 100, 0))
    if final:
        conn.execute('INSERT INTO discovery.agent_results VALUES (%s,%s,%s,%s)',
                     (run, base, final, Jsonb({'actionable': False, 'status': 'fixture'})))
    else:
        conn.execute('INSERT INTO discovery.rag_results VALUES (%s,%s,%s)',
                     (run, base, Jsonb({'status': 'fixture'})))


def job(conn, label, payload):
    oid, jid = 'SYN-occurrence-'+label, 'SYN-job-'+label
    conn.execute('INSERT INTO discovery.occurrences VALUES (%s,%s)', (oid, Jsonb({'occurrence_id': oid})))
    conn.execute("""INSERT INTO discovery.schedule_jobs(job_id,occurrence_id,stage,priority,payload,status,due_at,updated_at)
        VALUES(%s,%s,'ingest',2,%s,'completed',%s,%s)""", (jid, oid, Jsonb({'mode': 'synthetic'}), NOW, NOW))
    conn.execute('INSERT INTO discovery.schedule_outbox VALUES (%s,%s,%s,%s,%s)',
                 ('SYN-receipt-'+label, jid, 'pilot_scan', Jsonb(payload), NOW))
    return jid


def snapshot(conn):
    tables = [r[0] for r in conn.execute("""SELECT schemaname||'.'||tablename FROM pg_tables
        WHERE schemaname IN ('discovery','paper','research') ORDER BY 1""")]
    return {t: conn.execute(sql.SQL('SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text')
                           .format(sql.Identifier(*t.split('.')))).fetchall() for t in tables}


def test_provider_account_grant_and_version_isolation(case):
    c = case; m = dm.manifest(c.conn, c.request)
    assert find(m, 'discovery.revisions', c.docs['A'].revision.revision_id)
    for owner in ('B', 'A2', 'Aother', 'Aaccount'):
        assert find(m, 'discovery.revisions', c.docs[owner].revision.revision_id) is None
    root = find(m, 'discovery.grants', 'SYN-grant-A', 'v1')
    assert root.relationship == 'exclusive_in_known_graph'
    assert root.proposed_disposition == 'review_exclusive'
    stream = find(m, 'discovery.streams', 'SYN-document-stream-A')
    assert stream.proposed_disposition == 'resolve_lineage'
    assert 'source_scope_not_grant_pinned' in stream.lineage_issues
    other = ManifestRequest(**c.scope('A2').model_dump(), trigger='revocation', as_of_at=NOW)
    m2 = dm.manifest(c.conn, other)
    assert find(m2, 'discovery.revisions', c.docs['A2'].revision.revision_id)
    assert not find(m2, 'discovery.revisions', c.docs['A'].revision.revision_id)
    assert m2.policy_status == 'UNVERIFIED' and not m2.actionable


def test_evidence_snapshots_and_ingestion_metadata(case):
    c = case; rid = c.docs['A'].revision.revision_id
    c.conn.execute('INSERT INTO discovery.snapshots VALUES (%s,%s)', ('SYN-snapshot', Jsonb({'snapshot_id': 'SYN-snapshot'})))
    c.conn.execute('INSERT INTO discovery.snapshot_items VALUES (%s,%s)', ('SYN-snapshot', rid))
    identity = c.conn.execute('SELECT payload FROM discovery.revisions WHERE revision_id=%s', ('SYN-identity-A',)).fetchone()[0]
    stream = Stream(stream_id='SYN-quarantined-page', source_id=c.grants['A'].source_id,
                    account_ref=c.grants['A'].account_ref, scope='universe')
    ingest_page(c.conn, stream, Page(cursor=None, next_cursor=None, complete=True, records=(identity, {'invalid': 'fixture'})),
        load_grant=lambda: c.grants['A'], request=fixture_request('universe', source_id=stream.source_id,
        account_ref=stream.account_ref), audit=lambda d: None)
    # Snapshot IDs list documents in the real contract; inspect both FK link and JSON.
    bundle_id = bundle(c.conn, 'snapshot-consumer', [rid], snapshot_id='SYN-snapshot')
    m = dm.manifest(c.conn, c.request)
    for table in ('revisions', 'evidence_blobs', 'evidence_documents', 'evidence_chunks',
                  'financial_facts', 'evidence_claims', 'streams', 'stream_revisions', 'pages', 'quarantine',
                  'evidence_batches', 'snapshot_items', 'snapshots'):
        assert any(a.artifact_type == 'discovery.'+table for a in m.artifacts), table
    assert find(m, 'discovery.rag_bundles', bundle_id)


def test_shared_blobs_do_not_make_other_owner_document_deletable(case):
    c = case
    text = 'A deliberately shared fictional disclosure with independently registered provider provenance.'
    a = c.seed('shared-A', 'A', text); b = c.seed('shared-B', 'B', text)
    assert a.revision.data.content_hash == b.revision.data.content_hash
    m = dm.manifest(c.conn, c.request)
    shared = find(m, 'discovery.evidence_blobs', a.revision.data.content_hash)
    assert shared.relationship == 'shared' and shared.proposed_disposition == 'review_shared'
    assert set(shared.source_linkage) == {dm.scope_token(c.scope('A')), dm.scope_token(c.scope('B'))}
    assert not shared.deletion_authorized and not shared.retention_authorized
    assert not find(m, 'discovery.evidence_documents', b.revision.revision_id)


def test_mixed_rag_agent_and_registered_external_copies(case):
    c = case; a, b = (c.docs[k].revision.revision_id for k in ('A', 'B'))
    only_a = bundle(c.conn, 'only-a', [a]); only_b = bundle(c.conn, 'only-b', [b])
    mixed = bundle(c.conn, 'mixed', [a, b], hits=[{'citations': [{'revision_id': a}, {'revision_id': b}]}])
    result_row(c.conn, 'SYN-rag-mixed', mixed)
    result_row(c.conn, 'SYN-agent-mixed', only_a, mixed)
    result_row(c.conn, 'SYN-rag-b', only_b)
    copies = (
        ExternalCopy(copy_id='SYN-export', kind='filesystem', lineage_complete=True,
            dependencies=(ArtifactRef(artifact_type='discovery.rag_bundles', key=(mixed,)),)),
        ExternalCopy(copy_id='SYN-backup', kind='backup', lineage_complete=True, grants=(c.scope('A'), c.scope('B'))),
        ExternalCopy(copy_id='SYN-b-only', kind='backup', lineage_complete=True, grants=(c.scope('B'),)),
    )
    m = dm.manifest(c.conn, c.request, external_copies=copies)
    for table, key in [('discovery.rag_bundles', mixed), ('discovery.rag_results', 'SYN-rag-mixed'),
                       ('discovery.agent_results', 'SYN-agent-mixed'), ('external.filesystem', 'SYN-export'),
                       ('external.backup', 'SYN-backup')]:
        assert find(m, table, key).relationship == 'shared'
    assert not find(m, 'discovery.rag_results', 'SYN-rag-b')
    assert not find(m, 'external.backup', 'SYN-b-only')


def test_copied_citations_excerpts_and_scheduler_references(case):
    c = case; rid = c.docs['A'].revision.revision_id
    text = c.conn.execute('SELECT payload->>\'text\' FROM discovery.evidence_chunks WHERE revision_id=%s LIMIT 1', (rid,)).fetchone()[0]
    jid = job(c.conn, 'copy', {'rows': [{'findings': [{'citations': [{'revision_id': rid, 'excerpt': text}]}]}]})
    job(c.conn, 'unlinked-copy', {'old_assessment': text})
    m = dm.manifest(c.conn, c.request)
    cited = find(m, 'discovery.schedule_outbox', 'SYN-receipt-copy')
    orphan_copy = find(m, 'discovery.schedule_outbox', 'SYN-receipt-unlinked-copy')
    assert cited and orphan_copy
    assert 'text_match_is_not_proven_lineage' in orphan_copy.lineage_issues
    assert orphan_copy.proposed_disposition == 'resolve_lineage'
    wire = m.model_dump_json()
    assert text not in wire and rid not in wire and jid not in wire
    assert any(d.reason == 'json_reference' for d in cited.dependency_reasons)
    assert find(m, 'discovery.schedule_jobs', jid)
    assert find(m, 'discovery.occurrences', 'SYN-occurrence-copy')


def test_source_only_receipts_and_incomplete_parent_are_not_grant_pinned(case):
    c = case
    job(c.conn, 'source-only', {'source_id': c.grants['A'].source_id})
    rid = c.docs['A'].revision.revision_id
    parent = bundle(c.conn, 'unknown-parent', ['SYN-nonexistent'])
    mixed = bundle(c.conn, 'known-and-unknown', [rid], baseline_hash=parent)
    hinted = bundle(c.conn, 'known-and-other-source', [rid], attribution={'source_id': c.grants['B'].source_id})
    m = dm.manifest(c.conn, c.request)
    receipt = find(m, 'discovery.schedule_outbox', 'SYN-receipt-source-only')
    assert receipt and 'source_scope_not_grant_pinned' in receipt.lineage_issues
    assert receipt.proposed_disposition == 'resolve_lineage'
    row = find(m, 'discovery.rag_bundles', mixed)
    assert row.relationship == 'unknown' and 'missing_json_dependency' in row.lineage_issues
    assert row.proposed_disposition == 'resolve_lineage'
    other = find(m, 'discovery.rag_bundles', hinted)
    assert other.relationship == 'shared' and other.proposed_disposition == 'resolve_lineage'
    assert dm.scope_token(c.scope('B')) in other.source_linkage


def test_missing_lineage_is_explicit_never_safe(case):
    c = case
    unknown = bundle(c.conn, 'broken', ['SYN-missing-revision'], observations={'unknown': 'not attributable'})
    copies = (ExternalCopy(copy_id='SYN-unknown-backup', kind='backup'),
              ExternalCopy(copy_id='SYN-broken-export', kind='filesystem', lineage_complete=True,
                  dependencies=(ArtifactRef(artifact_type='discovery.rag_bundles', key=('SYN-missing',)),)),)
    m = dm.manifest(c.conn, c.request, external_copies=copies)
    row = find(m, 'discovery.rag_bundles', unknown, unresolved=True)
    assert row.relationship == 'unknown' and 'missing_json_dependency' in row.lineage_issues
    for kind, key in [('backup', 'SYN-unknown-backup'), ('filesystem', 'SYN-broken-export')]:
        assert find(m, 'external.'+kind, key, unresolved=True).proposed_disposition == 'resolve_lineage'
    assert not m.complete and all(not a.deletion_authorized and not a.retention_authorized
                                 for a in (*m.artifacts, *m.unresolved_artifacts))


def test_deterministic_duplicate_read_only_requests(case, monkeypatch):
    c = case; before = snapshot(c.conn)
    original = dm._read
    reads = []
    def checked(conn):
        assert conn.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        assert conn.execute('SHOW transaction_isolation').fetchone()[0] == 'repeatable read'
        data, keys, foreign, unsupported = original(conn)
        reads.append(True)
        if len(reads) == 2:
            data = {t: list(reversed(rows)) for t, rows in reversed(list(data.items()))}
            foreign.reverse()
        return data, keys, foreign, unsupported
    monkeypatch.setattr(dm, '_read', checked)
    copies = (ExternalCopy(copy_id='SYN-one', kind='backup', grants=(c.scope('A'),)),
              ExternalCopy(copy_id='SYN-two', kind='filesystem', grants=(c.scope('B'),)))
    first = dm.manifest(c.conn, c.request, external_copies=copies)
    second = dm.manifest(c.conn, c.request, external_copies=tuple(reversed(copies)))
    assert first.model_dump_json() == second.model_dump_json()
    assert snapshot(c.conn) == before
    for table in ('publication_runs', 'recommendations', 'experiment_trials'):
        assert c.conn.execute(sql.SQL('SELECT count(*) FROM discovery.{}').format(sql.Identifier(table))).fetchone()[0] == 0
    assert c.conn.execute('SELECT count(*) FROM paper.portfolios').fetchone()[0] == 0


def test_missing_target_and_wrong_account_fail_closed(case):
    c = case
    for changes in ({'account_ref': 'SYN-unknown'}, {'grant_version': 'missing'}, {'source_id': 'SYN-wrong'}):
        with pytest.raises(ValueError, match='^manifest_target_grant_unavailable$'):
            dm.manifest(c.conn, c.request.model_copy(update=changes))


def test_non_synthetic_database_content_is_rejected(case):
    c = case
    grant = c.grants['A'].model_dump(mode='json')
    grant.update(grant_id='private-marker-do-not-print', synthetic=False, source_id='private-provider')
    c.conn.execute('INSERT INTO discovery.grants VALUES (%s,%s,%s)', (grant['grant_id'], grant['version'], Jsonb(grant)))
    before = snapshot(c.conn)
    with pytest.raises(ValueError, match='^manifest_non_synthetic_data$') as caught:
        dm.manifest(c.conn, c.request)
    assert 'private-marker' not in str(caught.value)
    assert snapshot(c.conn) == before


def test_bounds_and_duplicate_external_registrations(case, monkeypatch):
    c = case
    copy = ExternalCopy(copy_id='SYN-duplicate', kind='backup')
    with pytest.raises(ValueError, match='^manifest_duplicate_copy_registration$'):
        dm.manifest(c.conn, c.request, external_copies=(copy, copy))
    with monkeypatch.context() as patch:
        patch.setattr(dm, 'MAX_EDGES', 1)
        with pytest.raises(ValueError, match='^manifest_graph_limit$'):
            dm.manifest(c.conn, c.request)
    with monkeypatch.context() as patch:
        patch.setattr(dm, 'MAX_BYTES', 1)
        with pytest.raises(ValueError, match='^manifest_inventory_limit$'):
            dm.manifest(c.conn, c.request)
    monkeypatch.setattr(dm, 'MAX_ROWS', 1)
    with pytest.raises(ValueError, match='^manifest_inventory_limit$'):
        dm.manifest(c.conn, c.request)


def test_external_copy_dependencies_are_registration_order_independent(case):
    c = case
    original = ExternalCopy(copy_id='SYN-original', kind='filesystem',
        lineage_complete=True, grants=(c.scope('A'),))
    backup = ExternalCopy(copy_id='SYN-dependent-backup', kind='backup',
        lineage_complete=True, dependencies=(ArtifactRef(
            artifact_type='external.filesystem', key=(original.copy_id,)),))
    before = snapshot(c.conn)
    forward = dm.manifest(c.conn, c.request, external_copies=(backup, original))
    reverse = dm.manifest(c.conn, c.request, external_copies=(original, backup))
    assert snapshot(c.conn) == before
    assert forward.model_dump_json() == reverse.model_dump_json()


@pytest.mark.parametrize('other_scope', ['unknown-provider', 'A2', 'Aaccount'])
def test_known_citation_does_not_hide_additional_json_source_scope(case, other_scope):
    c = case
    attribution = (dict(source_id='SYN-unregistered-provider', account_ref='SYN-unregistered-account',
                        grant_id='SYN-unregistered-grant', grant_version='v1')
                   if other_scope == 'unknown-provider' else c.scope(other_scope).model_dump())
    identifier = bundle(c.conn, 'additional-scope-'+other_scope,
        [c.docs['A'].revision.revision_id], attribution=attribution)
    before = snapshot(c.conn)
    m = dm.manifest(c.conn, c.request)
    row = find(m, 'discovery.rag_bundles', identifier)
    assert snapshot(c.conn) == before
    # A pinned citation cannot prove that a separate attribution is the same grant.
    assert row.relationship != 'exclusive_in_known_graph'
    if other_scope == 'unknown-provider':
        assert row.proposed_disposition == 'resolve_lineage' and row.lineage_issues
    else:
        request = ManifestRequest(**c.scope(other_scope).model_dump(), trigger='revocation', as_of_at=NOW)
        other = dm.manifest(c.conn, request)
        assert (find(other, 'discovery.rag_bundles', identifier)
                or find(other, 'discovery.rag_bundles', identifier, unresolved=True))


def test_multiple_json_scopes_preserve_unknown_conflicting_and_invalid_attribution(case):
    c = case; rid = c.docs['A'].revision.revision_id
    scopes = [
        c.scope('A2').model_dump(), c.scope('Aaccount').model_dump(), c.scope('B').model_dump(),
        {'source_id': 'SYN-unknown-provider'},
        {**c.scope('B').model_dump(), 'revision_id': rid},
        {'source_ref': c.grants['A'].source_id, 'account_ref': ['SYN-invalid-account']},
        {**c.scope('A').model_dump(), 'grant_version': 'SYN-missing-version'},
    ]
    identifier = bundle(c.conn, 'multiple-attributions', [rid], attributions=scopes)
    m = dm.manifest(c.conn, c.request)
    row = find(m, 'discovery.rag_bundles', identifier)
    assert set(row.source_linkage) == {dm.scope_token(c.scope(k)) for k in ('A', 'A2', 'Aaccount', 'B')}
    assert row.relationship == 'shared' and row.proposed_disposition == 'resolve_lineage'
    assert {'source_scope_not_grant_pinned', 'source_scope_unavailable',
            'conflicting_source_attribution', 'invalid_source_attribution'} <= set(row.lineage_issues)
    assert 'SYN-unknown-provider' not in m.model_dump_json()
    assert not row.deletion_authorized and not row.retention_authorized


def test_untrusted_json_scope_is_a_candidate_and_free_text_is_not_provenance(case):
    c = case
    claimed = bundle(c.conn, 'untrusted-scope', [], attribution=c.scope('A2').model_dump())
    text_only = bundle(c.conn, 'untrusted-text', [], commentary=json.dumps(c.scope('A').model_dump()))
    request = ManifestRequest(**c.scope('A2').model_dump(), trigger='revocation', as_of_at=NOW)
    m = dm.manifest(c.conn, request)
    row = find(m, 'discovery.rag_bundles', claimed)
    assert row.source_linkage == (dm.scope_token(c.scope('A2')),)
    assert row.relationship == 'unknown' and row.proposed_disposition == 'resolve_lineage'
    text = find(m, 'discovery.rag_bundles', text_only, unresolved=True)
    assert text and not text.source_linkage and text.proposed_disposition == 'resolve_lineage'


@pytest.mark.parametrize('anchored', [False, True])
@pytest.mark.parametrize('dangling', [False, True])
def test_external_cycles_and_dangling_references_are_deterministic(case, anchored, dangling):
    c = case
    copies = (
        ExternalCopy(copy_id='SYN-cycle-one', kind='filesystem', lineage_complete=True,
            grants=(c.scope('A'),) if anchored else (), dependencies=(
                ArtifactRef(artifact_type='external.backup', key=('SYN-cycle-two',)),)),
        ExternalCopy(copy_id='SYN-cycle-two', kind='backup', lineage_complete=True, dependencies=(
            ArtifactRef(artifact_type='external.filesystem', key=('SYN-cycle-one',)),) + ((
            ArtifactRef(artifact_type='external.filesystem', key=('SYN-dangling',)),
            ArtifactRef(artifact_type='external.unsupported', key=('SYN-invalid',)),
            ArtifactRef(artifact_type='external.filesystem', key=('SYN-cycle-one', 'SYN-invalid-key')),)
            if dangling else ())),
    )
    before = snapshot(c.conn)
    one = dm.manifest(c.conn, c.request, external_copies=copies)
    two = dm.manifest(c.conn, c.request, external_copies=tuple(reversed(copies)))
    assert one.model_dump_json() == two.model_dump_json()
    assert snapshot(c.conn) == before
    for kind, name in [('filesystem', 'SYN-cycle-one'), ('backup', 'SYN-cycle-two')]:
        row = find(one, 'external.'+kind, name, unresolved=not anchored)
        assert row
        if dangling or not anchored:
            assert row.relationship == 'unknown' and row.proposed_disposition == 'resolve_lineage'
        if dangling:
            assert 'missing_dependency' in row.lineage_issues
        else:
            assert 'missing_dependency' not in row.lineage_issues
        assert not row.deletion_authorized and not row.retention_authorized
    assert not one.complete and not one.actionable


def test_database_failure_mid_inventory_is_sanitized_and_connection_recovers(case):
    c = case; before = snapshot(c.conn)
    original_settings = tuple(c.conn.execute('SHOW '+setting).fetchone()[0]
                              for setting in ('transaction_read_only', 'transaction_isolation', 'statement_timeout'))

    class FailDuringRead:
        calls = 0

        def __getattr__(self, name):
            return getattr(c.conn, name)

        def execute(self, query, *args, **kwargs):
            self.calls += 1
            if self.calls == 10:
                assert c.conn.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
                assert c.conn.execute('SHOW transaction_isolation').fetchone()[0] == 'repeatable read'
                return c.conn.execute('SELECT %s::integer', ('SYN-private-error-marker',))
            return c.conn.execute(query, *args, **kwargs)

    with pytest.raises(ValueError, match='^manifest_inspection_failed$') as caught:
        dm.manifest(FailDuringRead(), c.request)
    assert 'SYN-private-error-marker' not in str(caught.value)
    assert caught.value.__suppress_context__
    assert c.conn.info.transaction_status == TransactionStatus.IDLE
    assert snapshot(c.conn) == before
    assert tuple(c.conn.execute('SHOW '+setting).fetchone()[0]
                 for setting in ('transaction_read_only', 'transaction_isolation', 'statement_timeout')) == original_settings
    recovered = dm.manifest(c.conn, c.request)
    assert recovered == dm.manifest(c.conn, c.request)
    assert snapshot(c.conn) == before


@pytest.mark.parametrize('shape', ['numeric', 'object', 'malformed-list', 'mixed-list'])
def test_malformed_json_references_preserve_valid_lineage_without_exclusivity(case, shape):
    c = case; a, b = (c.docs[k].revision.revision_id for k in ('A', 'B'))
    value = {'numeric': 123, 'object': {'id': b}, 'malformed-list': [123, {}],
             'mixed-list': [b, 123, {'id': 'SYN-untrusted'}]}[shape]
    key = 'revision_ids' if shape.endswith('list') else 'revision_id'
    parent = bundle(c.conn, 'malformed-'+shape, [a], citations=[{key: value}])
    child = bundle(c.conn, 'dependent-'+shape, [], baseline_hash=parent)
    before = snapshot(c.conn)
    first = dm.manifest(c.conn, c.request)
    assert first == dm.manifest(c.conn, c.request)
    assert snapshot(c.conn) == before
    expected = {dm.scope_token(c.scope('A'))}
    if shape == 'mixed-list':
        expected.add(dm.scope_token(c.scope('B')))
    for identifier in (parent, child):
        row = find(first, 'discovery.rag_bundles', identifier)
        assert set(row.source_linkage) == expected
        assert row.relationship != 'exclusive_in_known_graph'
        assert row.proposed_disposition == 'resolve_lineage'
        assert 'malformed_json_dependency' in row.lineage_issues
        assert not row.deletion_authorized and not row.retention_authorized
