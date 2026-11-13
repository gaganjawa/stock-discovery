-- STK-099: cluster owner applies to EXISTING inbox. No new tables or row changes.
\set ON_ERROR_STOP on
SELECT current_database() = 'chartink_inbox' AS correct_database \gset
\if :correct_database
GRANT CONNECT ON DATABASE chartink_inbox TO stk_inbox_reader;
GRANT USAGE ON SCHEMA discovery TO stk_inbox_reader;
GRANT SELECT ON discovery.candidate_events TO stk_inbox_reader;
\else
\echo 'Refusing source grants outside existing inbox'
\quit 1
\endif
