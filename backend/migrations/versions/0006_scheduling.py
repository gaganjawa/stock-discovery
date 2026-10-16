"""D3-04 durable occurrences, dependency queue, fencing and internal outbox."""
from alembic import op

revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''
    CREATE TABLE discovery.schedule_cursors (
        schedule_hash text PRIMARY KEY, polled_through timestamptz NOT NULL
    );
    CREATE TABLE discovery.occurrences (
        occurrence_id text PRIMARY KEY, payload jsonb NOT NULL,
        CHECK((payload->>'occurrence_id'=occurrence_id) IS TRUE)
    );
    CREATE TABLE discovery.schedule_jobs (
        job_id text PRIMARY KEY, occurrence_id text NOT NULL REFERENCES discovery.occurrences,
        stage text NOT NULL CHECK(stage IN ('ingest','snapshot','screen','event_poll','reassess','outcome','replay')),
        parent_id text REFERENCES discovery.schedule_jobs,
        priority integer NOT NULL, payload jsonb NOT NULL,
        status text NOT NULL CHECK(status IN ('queued','running','retry_wait','completed','partial','blocked','failed','missed')),
        attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
        due_at timestamptz NOT NULL, expires_at timestamptz,
        lease_until timestamptz, token text, result jsonb, error_code text,
        updated_at timestamptz NOT NULL
    );
    CREATE INDEX schedule_claim ON discovery.schedule_jobs(status,priority,due_at);
    CREATE TABLE discovery.schedule_audit (
        audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        job_id text NOT NULL REFERENCES discovery.schedule_jobs,
        at timestamptz NOT NULL, code text NOT NULL
    );
    CREATE TABLE discovery.schedule_outbox (
        event_key text PRIMARY KEY, job_id text NOT NULL REFERENCES discovery.schedule_jobs,
        kind text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL
    );
    CREATE TABLE discovery.material_events (
        event_key text PRIMARY KEY, listing_id text NOT NULL,
        source_revision_id text NOT NULL REFERENCES discovery.revisions,
        event_type text NOT NULL, observed_at timestamptz NOT NULL,
        job_id text NOT NULL REFERENCES discovery.schedule_jobs,
        UNIQUE(listing_id,source_revision_id,event_type)
    );
    CREATE TABLE discovery.admission_pauses (
        event_key text PRIMARY KEY REFERENCES discovery.material_events,
        listing_id text NOT NULL, reason text NOT NULL
    );
    ''')
    for table in ('occurrences','schedule_audit','schedule_outbox','material_events','admission_pauses'):
        op.execute(f'''CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON discovery.{table}
            FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()''')


def downgrade():
    for table in ('admission_pauses','material_events','schedule_outbox','schedule_audit','schedule_jobs','occurrences','schedule_cursors'):
        op.execute(f'DROP TABLE discovery.{table}')
