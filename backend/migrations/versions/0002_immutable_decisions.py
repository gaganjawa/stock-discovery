"""STK-015: freeze decisions, outcomes and run provenance; append corrections."""
from alembic import op
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE FUNCTION research.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'Immutable research record: append a linked correction' USING ERRCODE='23514';
    END; $$;
    CREATE FUNCTION research.freeze_run_provenance() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Run audit records cannot be deleted' USING ERRCODE='23514';
        END IF;
        IF (to_jsonb(NEW) - 'status' - 'completed_at') IS DISTINCT FROM
           (to_jsonb(OLD) - 'status' - 'completed_at') THEN
            RAISE EXCEPTION 'Run provenance is immutable' USING ERRCODE='23514';
        END IF;
        IF OLD.status IN ('completed','failed') AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'Terminal runs are immutable; retry in a new run' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END; $$;
    CREATE TRIGGER immutable_run BEFORE UPDATE OR DELETE ON research.runs
        FOR EACH ROW EXECUTE FUNCTION research.freeze_run_provenance();
    ''')
    for table in ('decisions', 'forecast_outcomes', 'trade_outcomes'):
        op.execute(f'''CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON research.{table}
            FOR EACH ROW EXECUTE FUNCTION research.reject_mutation()''')
        op.execute(f'''CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON research.{table}
            FOR EACH STATEMENT EXECUTE FUNCTION research.reject_mutation()''')
    op.execute('''CREATE FUNCTION research.validate_decision_provenance() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE run research.runs;
    BEGIN
        SELECT * INTO run FROM research.runs WHERE run_id=NEW.run_id;
        IF NOT FOUND THEN RETURN NEW; END IF;
        IF (NEW.payload->'versions'->>'dataset' = run.dataset_version
            AND NEW.payload->'versions'->>'code' = run.code_version
            AND NEW.payload->'strategy'->>'version' = run.strategy_version
            AND NEW.information_cutoff_at = run.information_cutoff_at
            AND (NEW.payload->>'information_cutoff_at')::timestamptz = NEW.information_cutoff_at
            AND (NEW.payload->>'generated_at')::timestamptz = NEW.generated_at
            AND (NEW.payload->>'decision_available_at')::timestamptz = NEW.decision_available_at
            AND jsonb_typeof(NEW.payload->'evidence') = 'array') IS NOT TRUE
            OR (NEW.payload->'versions'->>'model') IS DISTINCT FROM run.model_version
            OR (NEW.payload->'versions'->>'prompt') IS DISTINCT FROM run.prompt_version
            OR (NEW.payload->>'revises_id') IS DISTINCT FROM NEW.revises_id
            OR (NEW.payload->>'revision_reason') IS DISTINCT FROM NEW.revision_reason THEN
            RAISE EXCEPTION 'Decision provenance does not match frozen run' USING ERRCODE='23514';
        END IF;
        IF NEW.revises_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM research.decisions WHERE recommendation_id=NEW.revises_id
            AND (generated_at > NEW.generated_at OR information_cutoff_at > NEW.information_cutoff_at)
        ) THEN
            RAISE EXCEPTION 'Correction predates original' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END; $$;
    CREATE TRIGGER decision_provenance BEFORE INSERT ON research.decisions
        FOR EACH ROW EXECUTE FUNCTION research.validate_decision_provenance();
    ''')


def downgrade():
    op.execute('DROP TRIGGER decision_provenance ON research.decisions')
    op.execute('DROP FUNCTION research.validate_decision_provenance()')
    op.execute('DROP TRIGGER immutable_run ON research.runs')
    op.execute('DROP FUNCTION research.freeze_run_provenance()')
    for table in ('decisions', 'forecast_outcomes', 'trade_outcomes'):
        op.execute(f'DROP TRIGGER immutable_record ON research.{table}')
        op.execute(f'DROP TRIGGER immutable_truncate ON research.{table}')
    op.execute('DROP FUNCTION research.reject_mutation()')
