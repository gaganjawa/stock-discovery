"""Immutable synthetic dataset manifests and resumable ingestion checkpoints."""
from alembic import op
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''CREATE TABLE research.datasets (
        dataset_version text PRIMARY KEY,
        manifest jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        CHECK (manifest->>'version'=dataset_version),
        CHECK ((manifest->>'synthetic')::boolean IS TRUE)
    );
    CREATE TRIGGER immutable_dataset BEFORE UPDATE OR DELETE ON research.datasets
        FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TABLE research.ingestion_pages (
        dataset_version text NOT NULL,
        page_number integer NOT NULL CHECK (page_number>=0),
        digest text NOT NULL,
        completed_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(dataset_version,page_number)
    );''')


def downgrade():
    op.execute('DROP TABLE research.ingestion_pages')
    op.execute('DROP TABLE research.datasets')
