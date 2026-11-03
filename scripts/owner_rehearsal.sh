#!/usr/bin/env bash
# STK-079: one-command owner rehearsal on the Mac. Read-only on the original database.
# Usage (from the repository root, PostgreSQL container running, worker stopped):
#   DATABASE_URL_FILE=/absolute/private/local-database.url \
#   REAL_RESEARCH_VIEW_CONFIG=/absolute/private/view.json \
#   bash scripts/owner_rehearsal.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
fail() { echo "STOP: $*" >&2; exit 1; }

[ -x "$PYTHON" ] || fail "Python not found at $PYTHON. Re-run with PYTHON=/path/to/your/venv/bin/python"
[ -n "${DATABASE_URL_FILE:-}" ] && [ -r "$DATABASE_URL_FILE" ] || fail "Set DATABASE_URL_FILE to your private database URL file"
VIEW="${REAL_RESEARCH_VIEW_CONFIG:-}"
[ -z "$VIEW" ] || [ -r "$VIEW" ] || fail "REAL_RESEARCH_VIEW_CONFIG is set but not readable"
if pgrep -f "worker.main" >/dev/null; then fail "The research worker is running. Stop it first (see docs/STK-079-mac-steps.md step 2)"; fi
[ -n "${STK_COMPOSE_COMMAND:-}" ] || docker compose ps database >/dev/null 2>&1 || docker-compose ps database >/dev/null 2>&1 || fail "Start the database container first: docker compose up -d database"

OUT="$HOME/stock-discovery-rehearsal-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$OUT"
export PYTHONPATH=backend:shared:worker
VIEW_ARGS=(); [ -n "$VIEW" ] && VIEW_ARGS=(--view-config "$VIEW")

echo "1/3 Read-only audit of the original database..."
"$PYTHON" scripts/audit_retained_database.py --listing NSE:INE009A01021 ${VIEW_ARGS[@]+"${VIEW_ARGS[@]}"} > "$OUT/1-audit-original.json"

echo "2/3 Backup, restore to a separate copy, upgrade the copy only..."
"$PYTHON" scripts/rehearse_migration.py "$OUT/pre-0015-backup.dump" --keep-copy > "$OUT/2-rehearsal.json" \
  || { cat "$OUT/2-rehearsal.json" 2>/dev/null; fail "Rehearsal did not pass. Send $OUT/2-rehearsal.json; do NOT upgrade the original"; }

COPY=$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1]))['copy'])" "$OUT/2-rehearsal.json")
( umask 077; "$PYTHON" -c "import sys,psycopg;print(psycopg.conninfo.make_conninfo(open(sys.argv[1]).read().strip(),dbname=sys.argv[2]))" \
  "$DATABASE_URL_FILE" "$COPY" > "$OUT/copy-database.url" )

echo "3/3 Read-only audit of the upgraded copy..."
DATABASE_URL_FILE="$OUT/copy-database.url" "$PYTHON" scripts/audit_retained_database.py --listing NSE:INE009A01021 ${VIEW_ARGS[@]+"${VIEW_ARGS[@]}"} > "$OUT/3-audit-copy.json"

"$PYTHON" - "$OUT" <<'EOF'
import json, sys
out = sys.argv[1]
r = json.load(open(out + '/2-rehearsal.json')); a = json.load(open(out + '/3-audit-copy.json'))
print('\nRESULT')
print(' rehearsal pass       :', r.get('pass'))
print(' original unchanged   :', r.get('original_unchanged'))
print(' copy schema          :', r['upgrade']['version'])
print(' rows checked         :', r['original']['rows'], 'in', r['original']['tables'], 'tables')
print('\nSend these three files (no prices, tokens or account IDs inside):')
for f in ('1-audit-original.json', '2-rehearsal.json', '3-audit-copy.json'):print(' ', out + '/' + f)
print('\nKeep private, never send:', out + '/pre-0015-backup.dump', 'and', out + '/copy-database.url')
EOF
