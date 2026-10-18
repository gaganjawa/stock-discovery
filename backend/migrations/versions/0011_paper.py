"""STK-037–044/060–063: immutable paper ledger and observation inbox."""
from alembic import op
revision = '0011'
down_revision = '0010'
branch_labels = depends_on = None


def upgrade():
    op.execute('''
    CREATE SCHEMA paper;
    CREATE TABLE paper.portfolios (
      portfolio_id text PRIMARY KEY, request_key text UNIQUE NOT NULL,
      config jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE paper.ledger (
      portfolio_id text NOT NULL REFERENCES paper.portfolios,
      sequence bigint NOT NULL, event_key text NOT NULL, event_at timestamptz NOT NULL,
      kind text NOT NULL, payload jsonb NOT NULL, state jsonb NOT NULL,
      previous_hash text NOT NULL, event_hash text NOT NULL,
      PRIMARY KEY(portfolio_id,sequence), UNIQUE(portfolio_id,event_key),
      CHECK ((state->>'cash')::numeric >= 0),
      CHECK ((state->>'reserved')::numeric >= 0),
      CHECK ((state->>'reserved')::numeric <= (state->>'cash')::numeric)
    );
    CREATE TABLE paper.observations (
      observation_id text PRIMARY KEY, portfolio_id text NOT NULL REFERENCES paper.portfolios,
      request_key text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(portfolio_id,request_key)
    );
    CREATE UNIQUE INDEX paper_session ON paper.observations(portfolio_id,(payload->>'session_close_at'));
    CREATE TABLE paper.processed (
      observation_id text PRIMARY KEY REFERENCES paper.observations,
      portfolio_id text NOT NULL, sequence bigint NOT NULL,
      FOREIGN KEY(portfolio_id,sequence) REFERENCES paper.ledger
    );
    CREATE INDEX paper_due ON paper.observations(created_at,observation_id);
    CREATE TRIGGER immutable_portfolios BEFORE UPDATE OR DELETE ON paper.portfolios
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_ledger BEFORE UPDATE OR DELETE ON paper.ledger
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_observations BEFORE UPDATE OR DELETE ON paper.observations
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_processed BEFORE UPDATE OR DELETE ON paper.processed
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    ''')


def downgrade():
    op.execute('DROP SCHEMA paper CASCADE')
