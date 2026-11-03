# STK-079 — Steps for your Mac (copy and paste)

This takes about 15 minutes. Nothing here upgrades or changes your original database, and nothing
calls Upstox. It needs your existing checkout of `stock-discovery`, Docker Desktop running, and
the private files you already use: the database URL file and the view config.

## Step 1: Get the new code (keeps your two pending investigation documents)

```sh
cd /path/to/stock-discovery
git status --short            # files marked ?? are untracked and stay in place
git fetch origin
git checkout feat/stk-014-074-079-real-data-recovery
git pull --ff-only
```

If `git checkout` refuses because of modified tracked files, stop and send me the
`git status --short` output. Do not use reset or clean.

## Step 2: Make sure nothing is writing to the database

```sh
launchctl list | grep stock-discovery || echo "no launch agent"
pgrep -fl worker.main || echo "no worker running"
```

If a worker is listed, stop it with `pkill -f worker.main`. If the launch agent is listed, run
`launchctl bootout gui/$(id -u)/local.stock-discovery.research`.

## Step 3: Start the database container

```sh
docker compose up -d database
```

## Step 4: Run the rehearsal (one command)

Replace the two paths with your real private files. `PYTHON` is your project's virtual-environment
Python. Leave it out if it is `.venv/bin/python`.

```sh
DATABASE_URL_FILE=/absolute/private/local-database.url \
REAL_RESEARCH_VIEW_CONFIG=/absolute/private/view.json \
PYTHON=.venv/bin/python \
bash scripts/owner_rehearsal.sh
```

It prints `rehearsal pass: True` and `original unchanged: True`, then lists three JSON
files. **Send me those three files** (or paste their contents). They contain no prices, tokens or
account IDs. Keep the `.dump` backup and `copy-database.url` private.

If it prints `STOP:`, send me the exact line. Nothing has been changed.

## Step 5: See INFY on the upgraded copy (still not your original)

Terminal 1, the API pointed at the copy (use the folder printed in step 4):

```sh
export PYTHONPATH=backend:shared:worker
export AUTH_TOKEN_FILE=/absolute/private/local-owner.key
export DATABASE_URL_FILE=$HOME/stock-discovery-rehearsal-<timestamp>/copy-database.url
export REAL_RESEARCH_VIEW_CONFIG=/absolute/private/view.json
export COOKIE_SECURE=false APP_ORIGIN=http://127.0.0.1:5173
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```sh
cd frontend && node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173/#real-research, sign in with your owner key, and open INFY.

- If the chart shows, Level 1 works on the copy.
- If it says *"Prices come from several downloads; the multi-stream rule is not approved"*, the
  13-download rule is still off. To try it on the copy only, add `"adjusted_multi_stream": "approved_v1"`
  to a **copy** of your view config, point `REAL_RESEARCH_VIEW_CONFIG` at that copy, and restart terminal 1.

Send me a screenshot of the INFY page. After that, I will ask for your approval before anything
touches the original.

## Afterwards (only after you approve)

I will send the single upgrade command for the original. The backup from step 4 stays as your
restore point. The rehearsal copy can be removed later with
`docker compose exec database sh -c 'dropdb -U "$POSTGRES_USER" <copy name from 2-rehearsal.json>'`.
