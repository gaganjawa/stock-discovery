"""STK-095 / D3-03 + D3-04 + D3-09: bounded expanded candidate envelopes.

Transactional constraint replacement only; never rewrite immutable events.
Downgrade fails atomically if larger retained events cannot meet the old bound.
"""
from alembic import op

revision = '0017'
down_revision = '0016'
branch_labels = depends_on = None


def replace_limit(limit):
    # Fail safely under contention rather than blocking receiver/consumer traffic.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute('''ALTER TABLE discovery.candidate_events
      DROP CONSTRAINT candidate_events_envelope_check,
      ADD CONSTRAINT candidate_events_envelope_check
        CHECK (octet_length(envelope::text) <= %d)''' % limit)


def upgrade():
    replace_limit(1048576)


def downgrade():
    replace_limit(65536)
