"""Persistent bounded-retry jobs for the single worker."""
from alembic import op
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''CREATE TABLE research.jobs (
        job_id text PRIMARY KEY,
        kind text NOT NULL CHECK(kind IN ('ingest','scan','replay')),
        payload jsonb NOT NULL,
        status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','completed','failed')),
        attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
        next_attempt_at timestamptz NOT NULL DEFAULT now(),
        lease_until timestamptz,
        lease_token text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        result jsonb,
        error_code text
    );
    CREATE INDEX jobs_claim ON research.jobs(status,next_attempt_at,lease_until);''')


def downgrade(): op.execute('DROP TABLE research.jobs')
