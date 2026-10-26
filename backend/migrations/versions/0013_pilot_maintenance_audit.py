"""Allow account quota reservations before a scheduled job exists."""
from alembic import op
revision='0013'
down_revision='real_0012'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("ALTER TABLE discovery.schedule_audit ALTER COLUMN job_id DROP NOT NULL")
    op.execute("ALTER TABLE discovery.schedule_audit ADD CONSTRAINT maintenance_audit_scope CHECK(job_id IS NOT NULL OR code LIKE 'pilot_request:%')")


def downgrade():
    # Refuse destructive rollback when genuine maintenance reservations exist.
    op.execute("ALTER TABLE discovery.schedule_audit ALTER COLUMN job_id SET NOT NULL")
    op.execute("ALTER TABLE discovery.schedule_audit DROP CONSTRAINT maintenance_audit_scope")
