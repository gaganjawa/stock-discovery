# PRD — Stock Discovery takeover (STK-014/074/079)

## Original problem
Take over the private NSE three-horizon research platform (github gaganjawa/stock-discovery). Audit it read-only, find what actually blocks it, and deliver a critical-path plan without rewriting the architecture. The specific blocker was the retained database at migration 0013 causing INFY to return HTTP 403, plus three-level completion planning.

## Architecture (unchanged)
FastAPI, worker, PostgreSQL, React/TS and local Ollama, in the owner's repo. The work is in `/app/stock-discovery`, branch `feat/stk-014-074-079-real-data-recovery`, commit f94e885 on top of PR #35 head 8611904. The preview `/app/frontend` is a static handoff page with the patch and audit available for download.

## Implemented (3 Nov 2026)
- Verified: PR #35 is open with 4/4 CI green on its exact head and 0 reviews. `main` has migrations 0001–0015.
- Root cause reproduced on invented data: a 0013 schema lacks the 0015 fences, so reads fail closed. Upgrading 0013 → 0015 preserves every row and restores reads.
- The API now returns 503 "Database migration required" instead of 403 when the schema is behind. Status includes `database` and a `readiness` level, and the UI shows a readiness banner.
- An owner-gated multi-stream rule (`adjusted_multi_stream: approved_v1`, off by default). Streams are verified one by one, must overlap and must agree; anything else fails closed.
- `scripts/audit_retained_database.py` (read-only, sanitized) and `scripts/rehearse_migration.py` (works only on a restored copy).
- Tests: 937 unit, 536 integration/migration and the script tests pass, plus Playwright at 1280 and 390.

## Backlog
- P0: the owner runs the audit and rehearsal on the Mac, then approves migrating the original and decides on rule v1 and retention.
- P0: review and merge PR #35, then open this branch as a PR (needs GitHub access).
- P1: extend real descriptive research to the 12-stock pilot. Wire in Upstox corporate actions and the calendar. Activate launchd.
- P2 (external): an original-price source, filing rights, the 50-case review, policy approval and forward paper tracking.
