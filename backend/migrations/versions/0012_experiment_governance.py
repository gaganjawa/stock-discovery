"""D3-11 immutable experiment manifests, trial history and holdout access."""
from alembic import op
revision='0012'
down_revision='0011'
branch_labels=depends_on=None


def upgrade():
    op.execute('''
    CREATE TABLE discovery.experiments (
      experiment_id text PRIMARY KEY, manifest_hash text UNIQUE NOT NULL,
      manifest jsonb NOT NULL, split_audit jsonb NOT NULL, registered_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE discovery.experiment_trials (
      trial_id text PRIMARY KEY, experiment_id text NOT NULL REFERENCES discovery.experiments,
      request_hash text NOT NULL, request jsonb NOT NULL, registered_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE discovery.experiment_events (
      sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      experiment_id text NOT NULL REFERENCES discovery.experiments,
      trial_id text REFERENCES discovery.experiment_trials,
      kind text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE discovery.experiment_results (
      trial_id text PRIMARY KEY REFERENCES discovery.experiment_trials,
      result_hash text NOT NULL, payload jsonb NOT NULL, evaluated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX experiment_history ON discovery.experiment_events(experiment_id,sequence);
    ''')
    for table in ('experiments','experiment_trials','experiment_events','experiment_results'):
        op.execute(f'CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON discovery.{table} FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()')
        op.execute(f'CREATE TRIGGER immutable_truncate_{table} BEFORE TRUNCATE ON discovery.{table} FOR EACH STATEMENT EXECUTE FUNCTION research.reject_mutation()')


def downgrade():
    op.execute('DROP TABLE discovery.experiment_results, discovery.experiment_events, discovery.experiment_trials, discovery.experiments')
