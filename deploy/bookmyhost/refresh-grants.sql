\set ON_ERROR_STOP on
SELECT current_database() = 'stk_real001_private' AS correct_database \gset
\if :correct_database
BEGIN;
-- STK-099 / STK-014 D3-03/04/12: grants for a separately provisioned refresh login.
-- No migration, receiver/consumer role alteration, DELETE or schema ownership.
GRANT CONNECT ON DATABASE stk_real001_private TO stk_price_refresh;
GRANT USAGE ON SCHEMA discovery TO stk_price_refresh;
GRANT SELECT ON public.alembic_version TO stk_price_refresh;
GRANT SELECT ON discovery.revisions, discovery.streams, discovery.stream_revisions,
 discovery.pages, discovery.grants, discovery.ingestion_grants, discovery.quarantine,
 discovery.candidates, discovery.occurrences, discovery.schedule_jobs,
 discovery.schedule_audit, discovery.schedule_outbox TO stk_price_refresh;
GRANT INSERT ON discovery.streams, discovery.revisions, discovery.stream_revisions,
 discovery.pages, discovery.grants, discovery.ingestion_grants, discovery.quarantine,
 discovery.occurrences, discovery.schedule_jobs, discovery.schedule_audit,
 discovery.schedule_outbox TO stk_price_refresh;
GRANT UPDATE (cursor,complete) ON discovery.streams TO stk_price_refresh;
GRANT UPDATE ON discovery.schedule_jobs TO stk_price_refresh;
GRANT UPDATE (research_status,attempts,retry_at,error_code,result)
 ON discovery.candidates TO stk_price_refresh;
GRANT USAGE ON SEQUENCE discovery.schedule_audit_audit_id_seq TO stk_price_refresh;

COMMIT;
\else
\echo 'Refusing refresh grants outside application database'
\quit 1
\endif
