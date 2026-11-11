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
COMMIT;
\else
\echo 'Refusing grants outside restored private application database'
\quit 1
\endif
