-- STK-099: app owner applies to restored app DB only. Roles created separately.
\set ON_ERROR_STOP on
SELECT current_database() = 'stk_real001_private' AS correct_database \gset
\if :correct_database
BEGIN;
REVOKE ALL ON DATABASE stk_real001_private FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE stk_real001_private TO stk_runtime, stk_candidate_worker;
GRANT USAGE ON SCHEMA research, discovery, paper TO stk_runtime, stk_candidate_worker;
GRANT SELECT ON ALL TABLES IN SCHEMA research, discovery, paper TO stk_runtime, stk_candidate_worker;
GRANT SELECT ON public.alembic_version TO stk_runtime, stk_candidate_worker;
GRANT UPDATE ON discovery.candidates, discovery.candidate_event_state TO stk_runtime;
GRANT SELECT, INSERT, UPDATE ON discovery.candidate_receivers, discovery.candidate_event_state,
 discovery.candidate_sessions, discovery.candidates TO stk_candidate_worker;
GRANT INSERT ON discovery.candidate_events, discovery.candidate_matches,
 discovery.candidate_research_runs TO stk_candidate_worker;
GRANT USAGE, SELECT ON SEQUENCE discovery.candidate_events_sequence_seq TO stk_candidate_worker;
-- Existing legacy owner analysis writes immutable records; no provider credentials.
GRANT INSERT ON ALL TABLES IN SCHEMA research TO stk_runtime;
GRANT UPDATE ON research.jobs TO stk_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA research TO stk_runtime;
-- API paper routes append portfolios, admissions and queued observations only.
-- No paper sequences exist; processed receipts belong to the execution worker.
GRANT INSERT ON paper.portfolios, paper.ledger, paper.observations TO stk_runtime;
-- FOR UPDATE portfolio serialization needs UPDATE on one column. Immutable
-- portfolio trigger still rejects every actual mutation.
GRANT UPDATE (portfolio_id) ON paper.portfolios TO stk_runtime;
-- FOR SHARE source locks need UPDATE privilege. Deny actual API mutations,
-- including source renaming that could bypass revocation, via a role guard.
CREATE OR REPLACE FUNCTION discovery.hosted_source_control_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
  IF current_user = 'stk_runtime' THEN
    RAISE EXCEPTION 'hosted_api_source_control_mutation_denied' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION discovery.hosted_source_control_guard() FROM PUBLIC;
CREATE OR REPLACE TRIGGER hosted_source_control_guard BEFORE UPDATE
ON discovery.publication_source_controls FOR EACH ROW
EXECUTE FUNCTION discovery.hosted_source_control_guard();
GRANT UPDATE (source_id) ON discovery.publication_source_controls TO stk_runtime;
-- Other existing authenticated write routes: enqueue and append-only governance.
GRANT INSERT ON discovery.publication_runs, discovery.experiments,
 discovery.experiment_trials, discovery.experiment_events, discovery.experiment_results TO stk_runtime;
GRANT USAGE ON SEQUENCE discovery.experiment_events_sequence_seq TO stk_runtime;
COMMIT;
\else
\echo 'Refusing grants outside restored private application database'
\quit 1
\endif
