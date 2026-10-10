CREATE SCHEMA research;

CREATE TABLE research.instruments (
    instrument_id text PRIMARY KEY CHECK (btrim(instrument_id) <> ''),
    isin text,
    exchange text NOT NULL,
    series text NOT NULL,
    currency text NOT NULL DEFAULT 'INR' CHECK (currency = 'INR'),
    exchange_timezone text NOT NULL DEFAULT 'Asia/Kolkata',
    synthetic boolean NOT NULL,
    CHECK (synthetic OR isin IS NOT NULL),
    UNIQUE (exchange, series, isin)
);
CREATE TABLE research.instrument_symbols (
    instrument_id text NOT NULL REFERENCES research.instruments,
    symbol text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    source_ref text NOT NULL,
    available_at timestamptz NOT NULL,
    PRIMARY KEY (instrument_id, valid_from),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX symbols_lookup ON research.instrument_symbols(symbol, valid_from);

CREATE TABLE research.candles (
    candle_id text PRIMARY KEY,
    instrument_id text NOT NULL REFERENCES research.instruments,
    source_ref text NOT NULL,
    source_version text NOT NULL,
    interval text NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    available_at timestamptz NOT NULL,
    fetched_at timestamptz NOT NULL,
    availability_basis text NOT NULL CHECK (availability_basis IN ('observed_live','verified_archive','fictional_fixture')),
    adjustment_basis text NOT NULL CHECK (adjustment_basis IN ('raw','adjusted')),
    adjustment_version text NOT NULL,
    open numeric(24,8) NOT NULL CHECK (open > 0),
    high numeric(24,8) NOT NULL CHECK (high > 0),
    low numeric(24,8) NOT NULL CHECK (low > 0),
    close numeric(24,8) NOT NULL CHECK (close > 0),
    volume bigint NOT NULL CHECK (volume >= 0),
    CHECK (starts_at < ends_at AND ends_at <= available_at AND available_at <= fetched_at),
    CHECK (low <= open AND low <= close AND high >= open AND high >= close AND low <= high),
    UNIQUE (instrument_id, source_ref, source_version, interval, starts_at, adjustment_basis, adjustment_version)
);
CREATE INDEX candles_asof ON research.candles(instrument_id, interval, starts_at, available_at);

CREATE TABLE research.documents (
    document_id text PRIMARY KEY,
    instrument_id text REFERENCES research.instruments,
    source_ref text NOT NULL,
    source_version text NOT NULL,
    locator text NOT NULL,
    document_type text NOT NULL,
    published_at timestamptz NOT NULL,
    available_at timestamptz NOT NULL,
    fetched_at timestamptz NOT NULL,
    availability_basis text NOT NULL CHECK (availability_basis IN ('observed_live','verified_archive','fictional_fixture')),
    rights_ref text NOT NULL,
    content_sha256 text CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    storage_ref text,
    CHECK (published_at <= available_at AND available_at <= fetched_at),
    UNIQUE (source_ref, locator, source_version)
);
CREATE INDEX documents_asof ON research.documents(instrument_id, available_at);
CREATE TABLE research.facts (
    fact_id text PRIMARY KEY,
    instrument_id text NOT NULL REFERENCES research.instruments,
    document_id text NOT NULL REFERENCES research.documents,
    name text NOT NULL,
    value jsonb NOT NULL,
    unit text,
    period_start date,
    period_end date,
    available_at timestamptz NOT NULL,
    extraction_version text NOT NULL,
    source_locator text NOT NULL,
    supersedes_id text REFERENCES research.facts,
    CHECK (supersedes_id IS NULL OR supersedes_id <> fact_id),
    CHECK (period_start IS NULL OR period_end IS NULL OR period_start <= period_end)
);
CREATE INDEX facts_asof ON research.facts(instrument_id, name, available_at);

CREATE TABLE research.runs (
    run_id text PRIMARY KEY,
    mode text NOT NULL CHECK (mode IN ('synthetic','historical_reconstructed','live_paper')),
    information_cutoff_at timestamptz NOT NULL,
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    status text NOT NULL CHECK (status IN ('pending','running','completed','failed')),
    dataset_version text NOT NULL,
    code_version text NOT NULL,
    strategy_version text NOT NULL,
    model_version text,
    prompt_version text,
    manifest jsonb NOT NULL CHECK (jsonb_typeof(manifest) = 'object'),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);
CREATE TABLE research.accounts (
    account_ref text PRIMARY KEY,
    synthetic boolean NOT NULL,
    currency text NOT NULL DEFAULT 'INR' CHECK (currency = 'INR')
);
CREATE TABLE research.capital_buckets (
    bucket_id text PRIMARY KEY,
    account_ref text NOT NULL REFERENCES research.accounts,
    kind text NOT NULL CHECK (kind IN ('unallocated','active_trading','long_term')),
    UNIQUE (account_ref, kind),
    UNIQUE (bucket_id, account_ref)
);
CREATE TABLE research.holdings (
    holding_id text PRIMARY KEY,
    account_ref text NOT NULL REFERENCES research.accounts,
    bucket_id text NOT NULL,
    instrument_id text NOT NULL REFERENCES research.instruments,
    observed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL,
    quantity bigint NOT NULL CHECK (quantity >= 0),
    unavailable_quantity bigint NOT NULL DEFAULT 0 CHECK (unavailable_quantity >= 0),
    reserved_sell_quantity bigint NOT NULL DEFAULT 0 CHECK (reserved_sell_quantity >= 0),
    cost_basis numeric(24,8) CHECK (cost_basis >= 0),
    source_ref text NOT NULL,
    source_version text NOT NULL,
    FOREIGN KEY (bucket_id, account_ref) REFERENCES research.capital_buckets(bucket_id, account_ref),
    CHECK (unavailable_quantity + reserved_sell_quantity <= quantity),
    CHECK (observed_at <= recorded_at),
    UNIQUE (holding_id, instrument_id),
    UNIQUE (account_ref, bucket_id, instrument_id, observed_at, source_ref, source_version)
);
CREATE INDEX holdings_asof ON research.holdings(account_ref, instrument_id, observed_at);
-- One event stores both legs of a transfer: it cannot leave an unpaired cash leg.
-- No row is created for a skipped contribution. Amounts are flows, never returns.
CREATE TABLE research.contribution_ledger (
    event_id text PRIMARY KEY,
    account_ref text NOT NULL REFERENCES research.accounts,
    kind text NOT NULL CHECK (kind IN ('deposit','withdrawal','transfer')),
    from_bucket_id text,
    to_bucket_id text,
    amount numeric(24,8) NOT NULL CHECK (amount >= 0),
    effective_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('pending','posted','failed')),
    source_ref text NOT NULL,
    source_event_id text NOT NULL,
    reverses_id text UNIQUE REFERENCES research.contribution_ledger,
    correction_reason text,
    FOREIGN KEY (from_bucket_id, account_ref) REFERENCES research.capital_buckets(bucket_id, account_ref),
    FOREIGN KEY (to_bucket_id, account_ref) REFERENCES research.capital_buckets(bucket_id, account_ref),
    UNIQUE (account_ref, source_ref, source_event_id),
    CHECK ((kind = 'deposit' AND from_bucket_id IS NULL AND to_bucket_id IS NOT NULL)
        OR (kind = 'withdrawal' AND from_bucket_id IS NOT NULL AND to_bucket_id IS NULL AND amount > 0)
        OR (kind = 'transfer' AND from_bucket_id IS NOT NULL AND to_bucket_id IS NOT NULL
            AND from_bucket_id <> to_bucket_id AND amount > 0)),
    CHECK (reverses_id IS NULL OR (reverses_id <> event_id AND correction_reason IS NOT NULL AND btrim(correction_reason) <> ''))
);
CREATE INDEX ledger_asof ON research.contribution_ledger(account_ref, effective_at, status);

CREATE TABLE research.decisions (
    recommendation_id text PRIMARY KEY,
    instrument_id text NOT NULL REFERENCES research.instruments,
    run_id text NOT NULL REFERENCES research.runs,
    schema_version text NOT NULL,
    information_cutoff_at timestamptz NOT NULL,
    generated_at timestamptz NOT NULL,
    decision_available_at timestamptz NOT NULL,
    action text NOT NULL CHECK (action IN ('BUY','SELL','WAIT','HOLD','INSUFFICIENT_EVIDENCE')),
    position_effect text NOT NULL,
    holding_id text,
    revises_id text,
    revision_reason text,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    UNIQUE (recommendation_id, instrument_id),
    FOREIGN KEY (holding_id, instrument_id) REFERENCES research.holdings(holding_id, instrument_id),
    FOREIGN KEY (revises_id, instrument_id) REFERENCES research.decisions(recommendation_id, instrument_id),
    CHECK (information_cutoff_at <= decision_available_at),
    CHECK ((action = 'BUY' AND position_effect = 'OPEN_LONG' AND holding_id IS NULL)
        OR (action = 'SELL' AND position_effect IN ('CLOSE_LONG','REDUCE_LONG') AND holding_id IS NOT NULL)
        OR (action = 'HOLD' AND position_effect = 'MAINTAIN_LONG' AND holding_id IS NOT NULL)
        OR (action IN ('WAIT','INSUFFICIENT_EVIDENCE') AND position_effect = 'NONE' AND holding_id IS NULL)),
    CHECK ((revises_id IS NULL AND revision_reason IS NULL)
        OR (revises_id IS NOT NULL AND revises_id <> recommendation_id AND revision_reason IS NOT NULL AND btrim(revision_reason) <> '')),
    CHECK (payload ?& ARRAY['recommendation_id','instrument','run_id','schema_version','action','position_effect']),
    CHECK ((payload->>'recommendation_id' = recommendation_id AND payload->>'run_id' = run_id
        AND payload->>'schema_version' = schema_version AND payload->>'action' = action
        AND payload->>'position_effect' = position_effect
        AND payload->'instrument'->>'instrument_id' = instrument_id) IS TRUE)
);
CREATE INDEX decisions_asof ON research.decisions(instrument_id, information_cutoff_at);
CREATE TABLE research.forecast_outcomes (
    outcome_id text PRIMARY KEY,
    recommendation_id text NOT NULL REFERENCES research.decisions,
    evaluated_at timestamptz NOT NULL,
    evaluator_version text NOT NULL,
    observation_dataset text NOT NULL,
    status text NOT NULL CHECK (status IN ('matured','pending','not_applicable','invalid_data')),
    supersedes_outcome_id text,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    UNIQUE (outcome_id, recommendation_id),
    FOREIGN KEY (supersedes_outcome_id, recommendation_id) REFERENCES research.forecast_outcomes(outcome_id, recommendation_id),
    CHECK (supersedes_outcome_id IS NULL OR supersedes_outcome_id <> outcome_id)
);
CREATE TABLE research.trade_outcomes (
    outcome_id text PRIMARY KEY,
    recommendation_id text NOT NULL REFERENCES research.decisions,
    evaluated_at timestamptz NOT NULL,
    evaluator_version text NOT NULL,
    observation_dataset text NOT NULL,
    status text NOT NULL CHECK (status IN ('closed','open','no_entry','pending','ambiguous','not_applicable','invalid_data','cancelled')),
    supersedes_outcome_id text,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    UNIQUE (outcome_id, recommendation_id),
    FOREIGN KEY (supersedes_outcome_id, recommendation_id) REFERENCES research.trade_outcomes(outcome_id, recommendation_id),
    CHECK (supersedes_outcome_id IS NULL OR supersedes_outcome_id <> outcome_id)
);
-- PostgreSQL NUMERIC accepts NaN; explicitly reject non-finite financial values.
ALTER TABLE research.candles ADD CHECK (high < 'Infinity'::numeric);
ALTER TABLE research.holdings ADD CHECK (cost_basis IS NULL OR cost_basis < 'Infinity'::numeric);
ALTER TABLE research.contribution_ledger ADD CHECK (amount < 'Infinity'::numeric);

-- A reversal negates exactly one posted event; it is not an arbitrary new flow.
CREATE FUNCTION research.validate_ledger_reversal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE original research.contribution_ledger;
BEGIN
    IF NEW.reverses_id IS NOT NULL THEN
        SELECT * INTO original FROM research.contribution_ledger WHERE event_id = NEW.reverses_id;
        IF NOT FOUND OR original.status <> 'posted' OR original.reverses_id IS NOT NULL
           OR NEW.account_ref <> original.account_ref OR NEW.kind <> original.kind
           OR NEW.amount <> original.amount
           OR NEW.from_bucket_id IS DISTINCT FROM original.from_bucket_id
           OR NEW.to_bucket_id IS DISTINCT FROM original.to_bucket_id THEN
            RAISE EXCEPTION 'Reversal must match a posted original event' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER ledger_reversal_check BEFORE INSERT OR UPDATE ON research.contribution_ledger
FOR EACH ROW EXECUTE FUNCTION research.validate_ledger_reversal();
