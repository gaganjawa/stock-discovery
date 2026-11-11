-- STK-097: run as chartink_owner ONLY in the dedicated chartink_inbox database.
-- Create chartink_receiver LOGIN with a generated password separately via psql \password.
\set ON_ERROR_STOP on
SELECT current_database() = 'chartink_inbox' AS correct_database \gset
\if :correct_database
REVOKE ALL ON DATABASE chartink_inbox FROM PUBLIC;
GRANT CONNECT ON DATABASE chartink_inbox TO chartink_receiver;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA discovery TO chartink_receiver;
GRANT SELECT, INSERT ON discovery.candidate_events TO chartink_receiver;
GRANT USAGE, SELECT ON SEQUENCE discovery.candidate_events_sequence_seq TO chartink_receiver;
GRANT SELECT, INSERT, UPDATE ON discovery.candidate_event_state, discovery.candidate_rate TO chartink_receiver;
GRANT SELECT, INSERT, DELETE ON discovery.candidate_rejections TO chartink_receiver;
\else
\echo 'Refusing grants outside dedicated chartink_inbox'
\quit 1
\endif
