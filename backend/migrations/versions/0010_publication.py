"""STK-033/054/058/059: fenced publication queue and immutable v2 artifacts."""
from alembic import op
revision = '0010'
down_revision = '0009'
branch_labels = depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE discovery.publication_runs (
      run_id text PRIMARY KEY, request_key text UNIQUE NOT NULL, request_hash text NOT NULL,
      request jsonb NOT NULL, status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','running','completed','failed')),
      stage text NOT NULL DEFAULT 'queued', token text, error_code text,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE discovery.publication_batches (
      run_id text PRIMARY KEY REFERENCES discovery.publication_runs,
      horizon text NOT NULL, mode text NOT NULL CHECK(mode='synthetic'),
      published_at timestamptz NOT NULL DEFAULT now(), payload jsonb NOT NULL
    );
    CREATE INDEX publication_latest ON discovery.publication_batches(horizon,published_at DESC,run_id);
    CREATE TABLE discovery.recommendations (
      recommendation_id text PRIMARY KEY, run_id text NOT NULL REFERENCES discovery.publication_batches,
      listing_id text NOT NULL, horizon text NOT NULL, cohort text NOT NULL,
      payload jsonb NOT NULL, artifact jsonb NOT NULL, sort_key text NOT NULL,
      UNIQUE(run_id,listing_id,horizon,cohort),
      CHECK ((payload->>'schema_version'='2.0.0') IS TRUE),
      CHECK ((payload->'cohort'->>'shadow'='true') IS TRUE),
      CHECK ((payload->'paper_admission'->>'status'='blocked') IS TRUE)
    );
    CREATE TABLE discovery.publication_outbox (
      run_id text PRIMARY KEY REFERENCES discovery.publication_batches, payload jsonb NOT NULL
    );
    CREATE TABLE discovery.publication_source_controls (
      source_id text PRIMARY KEY, revoked boolean NOT NULL DEFAULT false
    );
    CREATE FUNCTION discovery.protect_publication_request() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.run_id IS DISTINCT FROM OLD.run_id OR NEW.request IS DISTINCT FROM OLD.request
         OR NEW.request_hash IS DISTINCT FROM OLD.request_hash OR NEW.request_key IS DISTINCT FROM OLD.request_key
      THEN RAISE EXCEPTION 'immutable publication request'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER immutable_publication_request BEFORE UPDATE ON discovery.publication_runs
      FOR EACH ROW EXECUTE FUNCTION discovery.protect_publication_request();
    CREATE TRIGGER immutable_publication_batches BEFORE UPDATE OR DELETE ON discovery.publication_batches
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_recommendations BEFORE UPDATE OR DELETE ON discovery.recommendations
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TRIGGER immutable_publication_outbox BEFORE UPDATE OR DELETE ON discovery.publication_outbox
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    ''')


def downgrade():
    op.execute('''DROP TABLE discovery.publication_outbox, discovery.recommendations,
      discovery.publication_batches, discovery.publication_runs, discovery.publication_source_controls;
      DROP FUNCTION discovery.protect_publication_request();''')
