"""STK-046–051: immutable evidence, chunks, facts, event claims and page manifests."""
from alembic import op
revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''
    CREATE TABLE discovery.evidence_blobs (
        content_hash text PRIMARY KEY, body text NOT NULL
    );
    CREATE TABLE discovery.evidence_documents (
        revision_id text PRIMARY KEY REFERENCES discovery.revisions,
        issuer_id text NOT NULL, content_hash text NOT NULL REFERENCES discovery.evidence_blobs, text_fingerprint text NOT NULL,
        parser_version text NOT NULL, payload jsonb NOT NULL,
        CHECK((payload->'revision'->>'revision_id'=revision_id) IS TRUE)
    );
    CREATE INDEX evidence_dedup ON discovery.evidence_documents(issuer_id,content_hash);
    CREATE INDEX evidence_near_dedup ON discovery.evidence_documents(issuer_id,text_fingerprint);
    CREATE TABLE discovery.evidence_chunks (
        chunk_id text PRIMARY KEY, revision_id text NOT NULL REFERENCES discovery.evidence_documents,
        payload jsonb NOT NULL
    );
    CREATE INDEX evidence_chunks_document ON discovery.evidence_chunks(revision_id);
    CREATE TABLE discovery.financial_facts (
        fact_id text PRIMARY KEY, revision_id text NOT NULL REFERENCES discovery.evidence_documents,
        payload jsonb NOT NULL
    );
    CREATE INDEX financial_facts_document ON discovery.financial_facts(revision_id);
    CREATE TABLE discovery.evidence_claims (
        claim_id text PRIMARY KEY, revision_id text NOT NULL REFERENCES discovery.evidence_documents,
        event_key text NOT NULL, status text NOT NULL CHECK(status IN ('confirmed','unverified')), payload jsonb NOT NULL
    );
    CREATE INDEX evidence_claims_event ON discovery.evidence_claims(event_key);
    CREATE TABLE discovery.evidence_batches (
        stream_id text NOT NULL, cursor_key text NOT NULL, content_hash text NOT NULL,
        processed_at timestamptz NOT NULL, result jsonb NOT NULL,
        PRIMARY KEY(stream_id,cursor_key),
        FOREIGN KEY(stream_id,cursor_key) REFERENCES discovery.pages DEFERRABLE INITIALLY DEFERRED
    );
    CREATE TABLE discovery.evidence_dispatch (
        event_key text PRIMARY KEY, job_id text NOT NULL REFERENCES discovery.schedule_jobs
    );
    ''')
    for table in ('evidence_blobs','evidence_documents','evidence_chunks','financial_facts','evidence_claims','evidence_batches','evidence_dispatch'):
        op.execute(f'CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON discovery.{table} FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()')


def downgrade():
    for table in ('evidence_dispatch','evidence_batches','evidence_claims','financial_facts','evidence_chunks','evidence_documents','evidence_blobs'):
        op.execute(f'DROP TABLE discovery.{table}')
