-- Run locally in receiver DB; outputs counts/clocks only, no bodies or secrets.
SELECT count(*) AS stored_events, max(sequence) AS remote_high_water,
       max(received_at) AS last_receipt FROM discovery.candidate_events;
SELECT count(*) AS rejected_payloads, max(received_at) AS last_rejection
FROM discovery.candidate_rejections;
-- Run on Mac DB: pending/failed processing and local retrieval cursor.
SELECT status, count(*) FROM discovery.candidate_event_state GROUP BY status;
SELECT min(e.received_at) AS oldest_pending FROM discovery.candidate_events e
JOIN discovery.candidate_event_state s USING(event_id) WHERE s.status='pending';
SELECT receiver_id, cursor FROM discovery.candidate_receivers;
-- Compare remote high-water against the corresponding local cursor; never compare
-- against the Mac's own event sequence. Remote events remain pending by design.
