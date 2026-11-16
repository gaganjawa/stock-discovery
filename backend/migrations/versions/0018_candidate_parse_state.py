"""STK-095 / D3-03: durable asynchronous parsing beside immutable inbox receipts."""
from alembic import op
revision='0018'
down_revision='0017'
branch_labels=depends_on=None


def upgrade():
    op.execute('''ALTER TABLE discovery.candidate_event_state
      ADD COLUMN parsed_envelope jsonb CHECK(octet_length(parsed_envelope::text)<=1048576),
      ADD COLUMN diagnostics jsonb CHECK(octet_length(diagnostics::text)<=32768)''')


def downgrade():
    # Never discard parsed evidence or quarantine details during rollback.
    op.execute('''DO $$ BEGIN
      IF EXISTS (SELECT FROM discovery.candidate_event_state
        WHERE parsed_envelope IS NOT NULL OR diagnostics IS NOT NULL) THEN
        RAISE EXCEPTION 'candidate_parse_evidence_present';
      END IF;
    END $$''')
    op.execute('ALTER TABLE discovery.candidate_event_state DROP COLUMN diagnostics, DROP COLUMN parsed_envelope')
