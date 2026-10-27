"""STK-074 bounded read-only provenance inspection for disposable synthetic DBs.

There is no cleanup executor, grant amendment, filesystem access or inference.
Membership in this manifest is a review dependency, never permission to delete.
"""
import json
from collections import defaultdict, deque
from itertools import islice

from psycopg import sql
from psycopg.pq import TransactionStatus

from stock_discovery_contracts.rights import Grant
from stock_discovery_contracts.v2 import check, digest
from .deletion_manifest_contracts import (DeletionManifest, Dependency,
    ExternalCopy, GrantScope, ManifestArtifact, ManifestRequest)

TABLES = tuple('discovery.' + t for t in (
    'grants', 'streams', 'revisions', 'stream_revisions', 'pages', 'quarantine',
    'snapshots', 'snapshot_items', 'evidence_blobs', 'evidence_documents',
    'evidence_chunks', 'financial_facts', 'evidence_claims', 'evidence_batches',
    'evidence_dispatch', 'rag_bundles', 'rag_reservations', 'rag_results',
    'agent_results', 'schedule_cursors', 'occurrences', 'schedule_jobs',
    'schedule_audit', 'schedule_outbox', 'material_events', 'admission_pauses',
    'publication_runs', 'publication_batches', 'recommendations',
    'publication_outbox', 'publication_source_controls', 'experiments',
    'experiment_trials', 'experiment_events', 'experiment_results',
)) + tuple('paper.' + t for t in (
    'portfolios', 'ledger', 'observations', 'processed', 'shadow_references', 'shadow_outcomes',
))
MAX_ROWS = 10000
MAX_BYTES = 16 * 1024 * 1024
MAX_TEXT_ANCHORS = 500
MAX_TEXT_COMPARISONS = 1000000
MAX_EDGES = 50000
MAX_GRANTS = 100

# Versioned JSON contracts supplement relational FKs. Unrecognised relationships
# remain unresolved, rather than treating arbitrary equal numbers as provenance.
JSON_REFS = {
    'revision_id': ('discovery.revisions',), 'revision_ids': ('discovery.revisions',),
    'source_revision_id': ('discovery.revisions',), 'source_revision_ids': ('discovery.revisions',),
    'source_revisions': ('discovery.revisions',), 'input_revision_ids': ('discovery.revisions',),
    'instrument_revision_id': ('discovery.revisions',), 'supersedes_id': ('discovery.revisions',),
    'documents': ('discovery.evidence_documents',), 'document_revision_ids': ('discovery.evidence_documents',),
    'chunk_id': ('discovery.evidence_chunks',), 'fact_id': ('discovery.financial_facts',),
    'input_fact_ids': ('discovery.financial_facts',), 'claim_id': ('discovery.evidence_claims',),
    'bundle_hash': ('discovery.rag_bundles',), 'baseline_hash': ('discovery.rag_bundles',),
    'final_bundle_hash': ('discovery.rag_bundles',), 'snapshot_id': ('discovery.snapshots',),
    'run_id': ('discovery.rag_results', 'discovery.agent_results', 'discovery.publication_runs'),
    'parent_run_id': ('discovery.rag_results', 'discovery.agent_results'),
    'recommendation_id': ('discovery.recommendations',), 'recommendation_ids': ('discovery.recommendations',),
    'portfolio_id': ('paper.portfolios',), 'job_id': ('discovery.schedule_jobs',),
    'occurrence_id': ('discovery.occurrences',), 'trial_id': ('discovery.experiment_trials',),
    'experiment_id': ('discovery.experiments',), 'stream_ids': ('discovery.streams',),
    'source_observations': ('discovery.revisions',),
}
# JSON forms of the existing revision, snapshot, research and governance contracts.
LIST_REFS = frozenset(('revision_ids', 'source_revision_ids', 'source_revisions',
    'input_revision_ids', 'documents', 'document_revision_ids', 'input_fact_ids',
    'recommendation_ids', 'stream_ids'))
NULLABLE_REFS = frozenset(('instrument_revision_id', 'supersedes_id', 'fact_id',
    'bundle_hash', 'baseline_hash', 'final_bundle_hash', 'portfolio_id'))
LIMITATIONS = (
    'provider_policy_and_trigger_authority_unverified',
    'exclusive_means_only_known_dependencies_not_legal_ownership',
    'unregistered_files_backups_exports_logs_and_model_caches_not_discoverable',
    'external_registry_completeness_not_independently_verified',
    'json_without_provenance_or_exact_text_matches_cannot_be_attributed',
    'legacy_research_schema_has_no_uniform_grant_lineage',
    'physical_storage_wal_snapshots_and_erasure_not_assessed',
)


def scope_token(scope):
    return digest({k: getattr(scope, k) for k in GrantScope.model_fields})


def artifact_token(table, key):
    return digest([table, list(key)])


def _walk(value, depth=0):
    check(depth <= 40, 'manifest_json_depth_limit')
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, depth + 1)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _references(key, value):
    """Retain identifiable candidates, but never hide an invalid reference shape."""
    def identifier(item):
        return isinstance(item, str) and bool(item.strip())
    if value is None and key in NULLABLE_REFS:
        return (), False
    if key == 'source_observations' and isinstance(value, dict):
        return (tuple(k for k in value if identifier(k)),
                any(not identifier(k) or not isinstance(v, dict) for k, v in value.items()))
    if key in LIST_REFS:
        valid = isinstance(value, list) and all(identifier(v) for v in value)
    else:
        valid = key != 'source_observations' and identifier(value)
    # Flattening salvages strings from malformed lists, with uncertainty retained.
    # Arbitrary object values are not interpreted as identifiers.
    return tuple(v for v in _strings(value) if identifier(v)), not valid


def _objects(value, depth=0):
    check(depth <= 40, 'manifest_json_depth_limit')
    if isinstance(value, dict):
        yield value
        children = value.values()
    else:
        children = value if isinstance(value, list) else ()
    for child in children:
        yield from _objects(child, depth + 1)


def _synthetic(rows):
    for row in rows:
        for key, value in _walk(row):
            check(not (key == 'synthetic' and value is False), 'manifest_non_synthetic_data')
            check(not (key == 'mode' and value in ('live_paper', 'historical_reconstructed')), 'manifest_non_synthetic_data')
            check(not (key == 'availability_basis' and value in ('observed', 'observed_live', 'verified_archive')), 'manifest_non_synthetic_data')


def _read(conn):
    # Read metadata only before inspecting row payloads. Future tables are reported,
    # not silently considered covered or read through caller-controlled SQL.
    tables = {r[0] for r in conn.execute("""SELECT schemaname||'.'||tablename FROM pg_tables
        WHERE schemaname IN ('discovery','paper','research')""")}
    check(set(TABLES) <= tables, 'manifest_schema_incomplete')
    keys = {}
    foreign = []
    for table, parent, kind, columns, parent_columns in conn.execute("""
        SELECT c.conrelid::regclass::text, c.confrelid::regclass::text, c.contype,
          ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(n,o)
                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.n ORDER BY k.o),
          ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(n,o)
                JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.n ORDER BY k.o)
        FROM pg_constraint c WHERE c.contype IN ('p','f')
          AND c.connamespace IN ('discovery'::regnamespace,'paper'::regnamespace)
        ORDER BY c.conrelid::regclass::text,c.conname"""):
        if table not in TABLES:
            continue
        if kind == 'p':
            keys[table] = tuple(columns)
        else:
            foreign.append((table, parent, tuple(columns), tuple(parent_columns)))
    check(set(keys) == set(TABLES), 'manifest_primary_key_unavailable')
    data = {}
    total_rows = total_bytes = 0
    for table in sorted(TABLES, key=lambda t: (t != 'discovery.grants', t)):
        name = sql.Identifier(*table.split('.'))
        count, size = conn.execute(sql.SQL('SELECT count(*),coalesce(sum(octet_length(to_jsonb(t)::text)),0) FROM {} t').format(name)).fetchone()
        total_rows += count
        total_bytes += size
        check(total_rows <= MAX_ROWS and total_bytes <= MAX_BYTES, 'manifest_inventory_limit')
        data[table] = [r[0] for r in conn.execute(sql.SQL('SELECT to_jsonb(t) FROM {} t').format(name))]
        _synthetic(data[table])
    return data, keys, foreign, tables - set(TABLES)


def _build(data, keys, foreign, request, copies, unsupported):
    rows = {}
    parents = defaultdict(set)
    issues = defaultdict(set)
    grants = {}
    scope_nodes = {}
    for table, items in data.items():
        for row in items:
            node = (table, tuple(str(row[k]) for k in keys[table]))
            rows[node] = row
    for node, row in rows.items():
        if node[0] != 'discovery.grants':
            continue
        grant = Grant.model_validate_json(json.dumps(row['payload']))
        check(grant.synthetic and grant.source_id.startswith('SYN-') and grant.account_ref.startswith('SYN-'), 'manifest_non_synthetic_grant')
        check((grant.grant_id, grant.version) == node[1], 'manifest_grant_identity_mismatch')
        scope = GrantScope(source_id=grant.source_id, account_ref=grant.account_ref,
                           grant_id=grant.grant_id, grant_version=grant.version)
        grants[node] = scope_token(scope)
        scope_nodes[scope_token(scope)] = node
    target = scope_token(request)
    check(target in scope_nodes, 'manifest_target_grant_unavailable')
    check(len(grants) <= MAX_GRANTS, 'manifest_graph_limit')
    edge_count = 0

    def edge(child, parent, reason):
        nonlocal edge_count
        if parent not in rows:
            issues[child].add('missing_dependency')
        elif child != parent and (parent, reason) not in parents[child]:
            edge_count += 1
            check(edge_count <= MAX_EDGES, 'manifest_graph_limit')
            parents[child].add((parent, reason))

    # Ownership flows from revisions to stream metadata and blobs, not back to
    # every revision/document sharing the container. This avoids deleting B's
    # document merely because it references the same blob as A's document.
    for table, parent, columns, parent_columns in foreign:
        if table == 'discovery.revisions' and parent == 'discovery.streams':
            continue
        if table == 'discovery.evidence_documents' and parent == 'discovery.evidence_blobs':
            continue
        if parent not in keys or parent_columns != keys[parent]:
            for node in rows:
                if node[0] == table:
                    issues[node].add('unsupported_foreign_key')
            continue
        for node, row in rows.items():
            if node[0] == table and all(row.get(k) is not None for k in columns):
                parent_node = (parent, tuple(str(row[k]) for k in columns))
                edge(node, parent_node, 'foreign_key')
                # These aggregate records own their child content. Reverse only
                # ownership links, never grant, identity or shared-blob references.
                containers = {
                    ('discovery.snapshot_items', 'discovery.snapshots'),
                    ('discovery.schedule_outbox', 'discovery.schedule_jobs'),
                    ('discovery.schedule_jobs', 'discovery.occurrences'),
                    ('discovery.rag_results', 'discovery.rag_reservations'),
                    ('discovery.agent_results', 'discovery.rag_reservations'),
                    ('discovery.recommendations', 'discovery.publication_batches'),
                    ('discovery.publication_batches', 'discovery.publication_runs'),
                    ('discovery.experiment_trials', 'discovery.experiments'),
                    ('discovery.experiment_results', 'discovery.experiment_trials'),
                    ('paper.ledger', 'paper.portfolios'), ('paper.observations', 'paper.portfolios'),
                }
                if (table, parent) in containers:
                    edge(parent_node, node, 'container_member')
    for node, row in rows.items():
        if node[0] == 'discovery.revisions':
            check(row['payload'].get('availability_basis') == 'fictional_fixture', 'manifest_non_synthetic_data')
            grant_node = ('discovery.grants', (row['grant_id'], row['grant_version']))
            check(grant_node in grants, 'manifest_revision_grant_unavailable')
            grant = rows[grant_node]['payload']
            check(row['source_id'] == grant['source_id'], 'manifest_revision_source_mismatch')
            stream = ('discovery.streams', (row['stream_id'],))
            check(stream in rows and rows[stream]['account_ref'] == grant['account_ref'], 'manifest_revision_account_mismatch')
            edge(stream, node, 'stream_member')
        if node[0] == 'discovery.stream_revisions':
            edge(('discovery.streams', (row['stream_id'],)), ('discovery.revisions', (row['revision_id'],)), 'stream_member')
        if node[0] == 'discovery.evidence_documents':
            edge(('discovery.evidence_blobs', (row['content_hash'],)), node, 'blob_owner')

    # JSON fields are inspected only for relationships, never returned verbatim.
    for node, row in list(rows.items()):
        for column, value in row.items():
            if not isinstance(value, (dict, list)):
                continue
            for key, child in _walk(value):
                targets = JSON_REFS.get(key, ())
                if not targets:
                    continue
                identifiers, malformed = _references(key, child)
                if malformed:
                    issues[node].add('malformed_json_dependency')
                for identifier in identifiers:
                    matches = [(table, (identifier,)) for table in targets if (table, (identifier,)) in rows]
                    if not matches:
                        issues[node].add('missing_json_dependency')
                    for parent in matches:
                        edge(node, parent, 'json_reference')
        # Resolve each attribution in its own object. A citation elsewhere in the
        # artifact cannot corroborate this object's account/grant/version claim.
        if node[0] != 'discovery.grants':
            for attribution in _objects(row):
                for source_key in ('source_id', 'source_ref'):
                    if source_key not in attribution:
                        continue
                    scope = {'source_id': attribution[source_key]}
                    scope.update({k: attribution[k] for k in ('account_ref', 'grant_id', 'grant_version')
                                  if k in attribution})
                    if 'grant_id' in scope and 'version' in attribution:
                        if 'grant_version' in scope and scope['grant_version'] != attribution['version']:
                            issues[node].add('conflicting_source_attribution')
                        scope.setdefault('grant_version', attribution['version'])
                    if any(not isinstance(v, str) or not v for v in scope.values()):
                        issues[node].add('invalid_source_attribution')
                        continue
                    hints = {g for g in grants if all(rows[g]['payload'].get('version' if k == 'grant_version' else k) == v
                                                     for k, v in scope.items())}
                    rid = attribution.get('revision_id')
                    revision = rows.get(('discovery.revisions', (rid,))) if isinstance(rid, str) else None
                    if revision is not None:
                        pinned = ('discovery.grants', (revision['grant_id'], revision['grant_version']))
                        if pinned in hints:
                            # Only a co-located revision corroborates these fields;
                            # do not fan its source-only metadata out to other grants.
                            continue
                        issues[node].add('conflicting_source_attribution')
                    # Even a full matching JSON scope is an attribution candidate,
                    # not authoritative ownership without corroborating lineage.
                    issues[node].add('source_scope_not_grant_pinned' if hints else 'source_scope_unavailable')
                    for parent in hints:
                        edge(node, parent, 'source_scope_only')

    # Detect exact copied excerpts in otherwise unlinked JSON. These are
    # candidates, not proof of provenance; paraphrases/short values stay unknown.
    anchors = defaultdict(set)
    for node, row in rows.items():
        if node[0] == 'discovery.evidence_chunks':
            text = row['payload'].get('text')
            if isinstance(text, str) and len(text) >= 24:
                anchors[text].add(('discovery.evidence_documents', (row['revision_id'],)))
    check(len(anchors) <= MAX_TEXT_ANCHORS, 'manifest_text_limit')
    comparisons = 0
    core = {'discovery.' + t for t in ('grants', 'streams', 'revisions', 'stream_revisions',
        'evidence_blobs', 'evidence_documents', 'evidence_chunks', 'financial_facts', 'evidence_claims')}
    for node, row in rows.items():
        if node[0] in core:
            continue
        for _, value in _walk(row):
            for text in _strings(value):
                if len(text) < 24:
                    continue
                comparisons += len(anchors)
                check(comparisons <= MAX_TEXT_COMPARISONS, 'manifest_text_limit')
                for excerpt, owners in anchors.items():
                    if excerpt in text or text in excerpt:
                        issues[node].add('text_match_is_not_proven_lineage')
                        for parent in owners:
                            edge(node, parent, 'copied_text_candidate')

    seen_copies = set()
    for copy in copies:
        check(copy.copy_id not in seen_copies, 'manifest_duplicate_copy_registration')
        seen_copies.add(copy.copy_id)
        node = ('external.' + copy.kind, (copy.copy_id,))
        rows[node] = {}
        if not copy.lineage_complete:
            issues[node].add('external_lineage_incomplete')
    # Register the complete inventory before resolving forward/cyclic references.
    for copy in copies:
        node = ('external.' + copy.kind, (copy.copy_id,))
        for ref in copy.dependencies:
            edge(node, (ref.artifact_type, ref.key), 'registered_copy')
        for scope in copy.grants:
            parent = scope_nodes.get(scope_token(scope))
            if parent is None:
                issues[node].add('external_grant_unavailable')
            else:
                edge(node, parent, 'registered_copy')

    # Monotone worklist handles cycles without recursion or ordering effects.
    lineage = {node: ({grants[node]} if node in grants else set()) for node in rows}
    def propagate():
        children = defaultdict(set)
        for node in rows:
            for parent, _ in parents[node]:
                children[parent].add(node)
        pending = deque(sorted(rows))
        queued = set(rows)
        while pending:
            parent = pending.popleft()
            queued.remove(parent)
            for node in sorted(children[parent]):
                before = len(lineage[node]), len(issues[node])
                lineage[node].update(lineage[parent])
                issues[node].update(issues[parent])
                if before != (len(lineage[node]), len(issues[node])) and node not in queued:
                    pending.append(node)
                    queued.add(node)
    propagate()
    for node in rows:
        if not lineage[node]:
            issues[node].add('unattributed_dependency')
    propagate()
    # Unsupported/missing lineage is never evidence of provider independence.
    def artifact(node):
        known = lineage[node]
        problems = set(issues[node])
        if not known:
            problems.add('unattributed_artifact')
        relationship = 'shared' if len(known) > 1 else 'unknown' if problems else 'exclusive_in_known_graph'
        disposition = 'resolve_lineage' if problems else 'review_shared' if len(known) > 1 else 'review_exclusive'
        return ManifestArtifact(artifact_type=node[0], identifier=artifact_token(*node),
            source_linkage=tuple(sorted(known)), relationship=relationship,
            dependency_reasons=tuple(Dependency(artifact_type=parent[0], identifier=artifact_token(*parent), reason=reason)
                for parent, reason in sorted(parents[node])), lineage_issues=tuple(sorted(problems)),
            proposed_disposition=disposition)
    affected = tuple(artifact(n) for n in sorted(rows) if target in lineage[n])
    unresolved = tuple(artifact(n) for n in sorted(rows) if target not in lineage[n] and (not lineage[n] or issues[n]))
    limitations = tuple(sorted((*LIMITATIONS, *('uninspected_table:' + digest(t) for t in sorted(unsupported)))))
    body = dict(schema_version='1.0.0', synthetic=True, target=target, trigger=request.trigger,
        as_of_at=request.as_of_at, artifacts=affected, unresolved_artifacts=unresolved,
        inspected_tables=tuple(sorted(TABLES)), limitations=limitations,
        policy_status='UNVERIFIED', complete=False, actionable=False)
    wire = {**body, 'artifacts': [x.model_dump(mode='json') for x in affected],
            'unresolved_artifacts': [x.model_dump(mode='json') for x in unresolved]}
    return DeletionManifest(**body, manifest_hash=digest(wire))


def manifest(conn, request, *, external_copies=()):
    """Inspect an idle autocommit connection to a disposable, synthetic database.

    Output intentionally omits source text, raw IDs, grant documents and paths.
    All failures use fixed codes; database/Pydantic errors must not disclose rows.
    """
    try:
        def validate(cls, value):
            # Revalidate even model_copy(update=...) instances, which Pydantic
            # otherwise trusts without checking their updated fields.
            wire = value.model_dump_json() if isinstance(value, cls) else json.dumps(value)
            return cls.model_validate_json(wire)
        request = validate(ManifestRequest, request)
        copies = tuple(validate(ExternalCopy, c) for c in islice(external_copies, 501))
        check(len(copies) <= 500, 'manifest_registry_limit')
        check(conn.autocommit and conn.info.transaction_status == TransactionStatus.IDLE,
              'manifest_idle_autocommit_required')
        database = conn.info.dbname
        check(database == 'stk013_test' or database.startswith(('stk013_test_', 'stk074_manifest_')),
              'manifest_disposable_database_required')
        with conn.transaction():
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            conn.execute("SET LOCAL statement_timeout = '5s'")
            data, keys, foreign, unsupported = _read(conn)
            return _build(data, keys, foreign, request, copies, unsupported)
    except Exception as exc:
        # Only our own fixed codes are safe diagnostics. Validation/DB exceptions
        # can contain arbitrary input, SQL row contents or connection information.
        code = str(exc) if type(exc) is ValueError else ''
        if not code.startswith('manifest_') or not code.replace('_', '').isalnum():
            code = 'manifest_inspection_failed'
        raise ValueError(code) from None
