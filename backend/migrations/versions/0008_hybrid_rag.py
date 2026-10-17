"""STK-052/053/074: lexical index, immutable RAG manifests and budget reservations."""
from alembic import op
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE INDEX evidence_chunks_fts ON discovery.evidence_chunks
        USING gin(to_tsvector('english'::regconfig, payload->>'text'));
    CREATE TABLE discovery.rag_bundles (
        bundle_hash text PRIMARY KEY, payload jsonb NOT NULL
    );
    CREATE TABLE discovery.rag_reservations (
        run_id text PRIMARY KEY, request_hash text NOT NULL, account text NOT NULL,
        reserved_at timestamptz NOT NULL, units bigint NOT NULL CHECK(units>0),
        cost numeric NOT NULL CHECK(cost>=0)
    );
    CREATE INDEX rag_budget_window ON discovery.rag_reservations(account,reserved_at);
    CREATE TABLE discovery.rag_results (
        run_id text PRIMARY KEY REFERENCES discovery.rag_reservations,
        bundle_hash text REFERENCES discovery.rag_bundles,
        payload jsonb NOT NULL
    );
    ''')
    for table in ('rag_bundles', 'rag_reservations', 'rag_results'):
        op.execute(f'CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON discovery.{table} FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()')


def downgrade():
    for table in ('rag_results', 'rag_reservations', 'rag_bundles'):
        op.execute(f'DROP TABLE discovery.{table}')
    op.execute('DROP INDEX discovery.evidence_chunks_fts')
