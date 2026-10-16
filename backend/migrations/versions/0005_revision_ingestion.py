"""D3-03 additive revision ingestion namespace; legacy research tables untouched."""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE SCHEMA discovery;
    CREATE TABLE discovery.grants (
        grant_id text NOT NULL, version text NOT NULL, payload jsonb NOT NULL,
        PRIMARY KEY(grant_id, version)
    );
    CREATE TABLE discovery.streams (
        stream_id text PRIMARY KEY, source_id text NOT NULL, account_ref text NOT NULL,
        scope text NOT NULL, cursor text, complete boolean NOT NULL DEFAULT false
    );
    CREATE TABLE discovery.revisions (
        revision_id text PRIMARY KEY, stream_id text NOT NULL REFERENCES discovery.streams,
        source_id text NOT NULL, source_revision text NOT NULL, logical_key text NOT NULL, sequence integer NOT NULL CHECK(sequence>0),
        kind text NOT NULL CHECK(kind IN ('instrument','membership','candle','action','document','session')),
        listing_id text NOT NULL, available_at timestamptz NOT NULL,
        grant_id text NOT NULL, grant_version text NOT NULL,
        instrument_revision_id text REFERENCES discovery.revisions,
        supersedes_id text REFERENCES discovery.revisions,
        content_hash text NOT NULL CHECK(length(content_hash)=64), payload jsonb NOT NULL,
        FOREIGN KEY(grant_id, grant_version) REFERENCES discovery.grants,
        UNIQUE(source_id, logical_key, sequence),
        UNIQUE(source_id, logical_key, source_revision),
        CHECK((payload->>'revision_id'=revision_id) IS TRUE),
        CHECK((payload->>'source_id'=source_id) IS TRUE),
        CHECK((payload->>'listing_id'=listing_id) IS TRUE),
        CHECK((payload->'data'->>'kind'=kind) IS TRUE),
        CHECK(((payload->>'available_at')::timestamptz=available_at) IS TRUE),
        CHECK(((payload->>'sequence')::integer=sequence) IS TRUE),
        CHECK((payload->>'source_revision'=source_revision) IS TRUE)
    );
    CREATE INDEX revision_asof ON discovery.revisions(stream_id,available_at,logical_key);
    CREATE INDEX revision_listing ON discovery.revisions(listing_id,kind,available_at);
    CREATE TABLE discovery.stream_revisions (
        stream_id text NOT NULL REFERENCES discovery.streams,
        revision_id text NOT NULL REFERENCES discovery.revisions,
        PRIMARY KEY(stream_id,revision_id)
    );
    CREATE TABLE discovery.pages (
        stream_id text NOT NULL REFERENCES discovery.streams, cursor_key text NOT NULL,
        content_hash text NOT NULL, next_cursor text, complete boolean NOT NULL,
        accepted integer NOT NULL CHECK(accepted>=0), quarantined integer NOT NULL CHECK(quarantined>=0),
        PRIMARY KEY(stream_id,cursor_key)
    );
    CREATE TABLE discovery.quarantine (
        stream_id text NOT NULL, cursor_key text NOT NULL, position integer NOT NULL,
        content_hash text NOT NULL, reason text NOT NULL,
        PRIMARY KEY(stream_id,cursor_key,position),
        FOREIGN KEY(stream_id,cursor_key) REFERENCES discovery.pages DEFERRABLE INITIALLY DEFERRED
    );
    CREATE TABLE discovery.snapshots (
        snapshot_id text PRIMARY KEY, payload jsonb NOT NULL,
        CHECK((payload->>'snapshot_id'=snapshot_id) IS TRUE)
    );
    CREATE TABLE discovery.snapshot_items (
        snapshot_id text NOT NULL REFERENCES discovery.snapshots,
        revision_id text NOT NULL REFERENCES discovery.revisions,
        PRIMARY KEY(snapshot_id, revision_id)
    );
    ''')
    for table in ('grants','revisions','stream_revisions','pages','quarantine','snapshots','snapshot_items'):
        op.execute(f'''CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON discovery.{table}
            FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()''')


def downgrade():
    for table in ('snapshot_items','snapshots','quarantine','pages','stream_revisions','revisions','streams','grants'):
        op.execute(f'DROP TABLE discovery.{table}')
    op.execute('DROP SCHEMA discovery')
