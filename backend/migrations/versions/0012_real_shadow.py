"""STK-059/060: real shadow publication and separate prospective references."""
from alembic import op
revision='real_0012'
down_revision='0011'
branch_labels=depends_on=None

def upgrade():
    op.execute('''
    ALTER TABLE discovery.publication_batches DROP CONSTRAINT publication_batches_mode_check;
    ALTER TABLE discovery.publication_batches ADD CONSTRAINT publication_batches_mode_check CHECK(mode IN ('synthetic','live_paper'));
    CREATE TABLE paper.shadow_references (
      reference_id text PRIMARY KEY,
      recommendation_id text UNIQUE NOT NULL REFERENCES discovery.recommendations,
      payload jsonb NOT NULL,
      CHECK ((payload->>'mode'='live_paper') IS TRUE),
      CHECK ((payload->>'actionable'='false') IS TRUE)
    );
    CREATE TABLE paper.shadow_outcomes (
      outcome_id text PRIMARY KEY,
      reference_id text NOT NULL REFERENCES paper.shadow_references,
      sequence integer NOT NULL CHECK(sequence>0),
      input_hash text NOT NULL,
      evaluated_at timestamptz NOT NULL,
      payload jsonb NOT NULL,
      UNIQUE(reference_id,sequence), UNIQUE(reference_id,input_hash)
    );
    CREATE TRIGGER immutable_shadow_references BEFORE UPDATE OR DELETE ON paper.shadow_references
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_shadow_outcomes BEFORE UPDATE OR DELETE ON paper.shadow_outcomes
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    ''')

def downgrade():
    op.execute('''DROP TABLE paper.shadow_outcomes, paper.shadow_references;
      ALTER TABLE discovery.publication_batches DROP CONSTRAINT publication_batches_mode_check;
      ALTER TABLE discovery.publication_batches ADD CONSTRAINT publication_batches_mode_check CHECK(mode='synthetic');''')
