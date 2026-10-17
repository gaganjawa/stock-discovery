"""STK-052/070/071/072: immutable bounded investigation and judge reports."""
from alembic import op
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''CREATE TABLE discovery.agent_results (
        run_id text PRIMARY KEY REFERENCES discovery.rag_reservations,
        baseline_hash text REFERENCES discovery.rag_bundles,
        final_bundle_hash text REFERENCES discovery.rag_bundles,
        payload jsonb NOT NULL,
        CHECK ((payload->>'actionable'='false') IS TRUE)
    );
    CREATE TRIGGER immutable_agent_results BEFORE UPDATE OR DELETE ON discovery.agent_results
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();''')


def downgrade():
    op.execute('DROP TABLE discovery.agent_results')
