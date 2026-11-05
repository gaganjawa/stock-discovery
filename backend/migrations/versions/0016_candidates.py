"""STK-094 / D3-03 + D3-04 + D3-09: durable discovery, not price evidence."""
from alembic import op

revision = '0016'
down_revision = '0015'
branch_labels = depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE discovery.candidate_events (
      sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
      event_id text PRIMARY KEY,
      received_at timestamptz NOT NULL,
      envelope jsonb NOT NULL CHECK(octet_length(envelope::text)<=65536)
    );
    CREATE TRIGGER immutable_candidate_events BEFORE UPDATE OR DELETE ON discovery.candidate_events
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TABLE discovery.candidate_event_state (
      event_id text PRIMARY KEY REFERENCES discovery.candidate_events,
      status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','failed')),
      error_code text, deliveries integer NOT NULL DEFAULT 1 CHECK(deliveries>0)
    );
    CREATE TABLE discovery.candidate_sessions (
      scanner_key text NOT NULL, session_date date NOT NULL,
      completeness text NOT NULL CHECK(completeness IN ('partial_unverified','verified_fixture_snapshot','verified_complete_snapshot')),
      PRIMARY KEY(scanner_key,session_date)
    );
    CREATE TABLE discovery.candidates (
      candidate_id text PRIMARY KEY, scanner_key text NOT NULL, session_date date NOT NULL,
      symbol text NOT NULL, exchange text NOT NULL CHECK(exchange='NSE'),
      first_observed_at timestamptz NOT NULL, last_observed_at timestamptz NOT NULL,
      status text NOT NULL DEFAULT 'observed_match' CHECK(status='observed_match'),
      research_status text NOT NULL DEFAULT 'pending' CHECK(research_status IN ('pending','completed','blocked','failed')),
      listing_id text, result jsonb, attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
      retry_at timestamptz NOT NULL DEFAULT now(), error_code text,
      UNIQUE(scanner_key,session_date,symbol),
      FOREIGN KEY(scanner_key,session_date) REFERENCES discovery.candidate_sessions,
      CHECK(first_observed_at<=last_observed_at)
    );
    CREATE TABLE discovery.candidate_research_runs (
      run_id text PRIMARY KEY, candidate_id text NOT NULL REFERENCES discovery.candidates,
      recorded_at timestamptz NOT NULL DEFAULT now(), result jsonb NOT NULL
    );
    CREATE TRIGGER immutable_candidate_research_runs BEFORE UPDATE OR DELETE ON discovery.candidate_research_runs
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TABLE discovery.candidate_matches (
      event_id text NOT NULL REFERENCES discovery.candidate_events,
      candidate_id text NOT NULL REFERENCES discovery.candidates,
      PRIMARY KEY(event_id,candidate_id)
    );
    CREATE TRIGGER immutable_candidate_matches BEFORE UPDATE OR DELETE ON discovery.candidate_matches
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE TABLE discovery.candidate_receivers (
      receiver_id text PRIMARY KEY, cursor bigint NOT NULL DEFAULT 0 CHECK(cursor>=0)
    );
    CREATE TABLE discovery.candidate_rate (
      id integer PRIMARY KEY CHECK(id=1), window_at timestamptz NOT NULL, attempts integer NOT NULL
    );
    CREATE TABLE discovery.candidate_rejections (
      payload_hash text PRIMARY KEY, reason text NOT NULL, received_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX candidate_queue ON discovery.candidates(research_status,retry_at);
    CREATE INDEX candidate_lookup ON discovery.candidates(listing_id);
    ''')


def downgrade():
    op.execute('''DROP TABLE discovery.candidate_rejections,discovery.candidate_rate,
      discovery.candidate_receivers,discovery.candidate_matches,discovery.candidate_research_runs,discovery.candidates,
      discovery.candidate_sessions,discovery.candidate_event_state,discovery.candidate_events''')
