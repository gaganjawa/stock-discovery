# STK-097 — D3-03/04/09 receiver deployment readiness

Prerequisite: STK-096 PR #45 merged as aa65cc6. Reuses the STK-094 receiver,
immutable inbox, bounded feed, worker cursor and research/UI pipeline. STK-095
synthetic enrichment remains synthetic-only; live enriched JSON is unverified.
No public deployment, paid call, alert change or private-database migration occurs.

## Deployment inventory and operator preparation

`deploy/chartink/compose.yaml` is a separate Compose project, not an overlay on the
private research stack. Only the proxy publishes ports 80/443. The database has a
named durable volume and no published port. Receiver/database share an internal
network; the proxy alone has external networking for TLS certificate renewal.
No research API, local source grants or private market evidence is mounted.

Create private secret files outside Git: db_password, owner_url, receiver_url,
webhook, pull, scanner.json. Use independent random passwords/capabilities of at
least 32 characters, directory mode 0700, and files readable only by the intended
container UID (receiver 10001). Compose file secrets are bind-mounted, not an
encrypted secret vault; verify host ownership/readability before activation.
URLs target database:5432/chartink_inbox; owner is chartink_owner, runtime role is
chartink_receiver. Never pass owner credentials to the receiver. Scanner config
must pin the exact approved identity/version, rights and finite expiry.

Set CHARTINK_SECRETS_DIR and RECEIVER_DOMAIN. Validate with:

```sh
docker compose -f deploy/chartink/compose.yaml config --quiet
```

After explicit provisioning/activation approval, start database, run the setup
profile's migrate service, then create the runtime role as owner using psql
(`CREATE ROLE chartink_receiver LOGIN;` and interactive `\password
chartink_receiver`). Apply `grants.sql` with psql ON_ERROR_STOP; it refuses any
database other than chartink_inbox. Runtime grants cover only intake/feed/control
tables and sequence. No access is granted to market evidence or research tables.
The owner must verify password-file ownership, role privileges and restore before
starting the receiver profile. Set CHARTINK_RECEIVER_ENABLED=true only after
approval. Default false returns 503 for intake/feed even if services are started.

Caddy automatically issues/renews HTTPS certificates for the approved DNS name.
The proxy forwards only intake/feed/authenticated monitoring routes; all other
paths return 404, including internal health and private research routes. Receiver
access logs, proxy request/error logs and container receiver logs are disabled to
avoid capability URL disclosure. Health and aggregate metrics replace raw request
logging. The Caddy image is pinned to the digest validated locally. Keep host firewall ingress limited to 80/443 and approved
administration access; no Mac incoming port or tunnel is required.

## Monitoring

Internal `/healthz` checks actual candidate-table connectivity (container health).
`/candidate-health?after=<Mac cursor>` requires the independent pull bearer token
and shares the bounded request budget. It returns only counts, capacity, high-water,
last receipt, oldest unpulled receipt, lag and rejection count. Poll once per minute
using a protected header file/client, never a URL query secret. Alert on failed
health, any new rejections, capacity >=80%, increasing lag or cursor_ahead. Store
previous samples externally to detect increases. Alert routing/scheduling must be
configured by the owner; no paid monitoring dependency is introduced.

Use `monitor.sql` locally for Mac pending/failed processing and persisted cursor.
Compare the remote sequence with the matching receiver cursor, not local event
sequences. Receiver states stay pending because materialization runs on the Mac.
A successful feed response is not a Mac acknowledgement; only the local committed
cursor proves durable receipt. The receiver does not infer completed delivery.
Unknown coverage/no alert is never zero eligible candidates. Network failures
before arrival are unobservable here; check Chartink's alert history separately.
No documented retry guarantee is assumed. Monitor backup age, host disk/quota and
certificate expiry separately. Retention requires approved archival, not deleting
immutable events to clear capacity.

## Backup and restore rehearsal

On the approved receiver host, use a restrictive umask and a private backup path:

```sh
umask 077
docker compose -f deploy/chartink/compose.yaml exec -T database \
  pg_dump -U chartink_owner -d chartink_inbox -Fc > /private/backup/inbox.dump
restic backup /private/backup/inbox.dump
restic check
```

Configure RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE and restricted B2 credentials
outside Git, with the encryption key stored separately. Never back up by copying
live PostgreSQL files. Verify dump exit status before upload and alert on failures.
Apply approved retention only after restore rehearsal; do not delete volumes.

Restore a selected restic snapshot to a new private directory and a **new isolated
PostgreSQL container/volume**, with no public receiver attached. Create the target
empty database and owner role; run `pg_restore --exit-on-error --no-owner` into it.
Reapply least-privilege grants, verify schema 0016, event count/hashes, high-water,
immutable triggers and feed replay. Never use `--clean` against a live database.
Record recovery duration and last backed-up receipt. Restore rehearsals must not
reuse the production volume. Rotate credentials if restoring after compromise.

## Mac and Chartink activation

Use the existing worker with CHARTINK_RECEIVER_URL=https://approved-host,
CHARTINK_PULL_SECRET_FILE and the locally approved matching scanner configuration.
Run `python -m worker.main --candidate-intake` with existing private DB/source grants.
TLS verification and redirect rejection remain enabled; event/cursor commits remain
atomic. Receipt times are retained through downtime and replay.

After owner approval, open Modify Alert for the existing scanner, preserve filters
and email settings, configure Payload Columns separately from Result Columns, and
enter the private HTTPS webhook capability URL. Begin with the documented basic
payload. Inspect the first real delivery privately; compare types, column alignment,
time/date semantics, partial matches and duplicate behavior. Unknown enrichment
must be rejected until an isolated adapter is verified against an actual sample.
Do not claim delivery or live enrichment compatibility from synthetic tests.

## Costs and acceptance

Retain the approved Hetzner CX23 selection. Existing-host incremental compute can
be zero if capacity permits. Prior STK-095 planning allowance is EUR 8/month for
compute/networking plus taxes/domain, and about USD 0.14/month for 20 GB B2 storage
before free allowance. These are planning estimates, not purchase quotations;
recheck stock, regional price and taxes before authorization. See STK-095's pricing
sources. No new infrastructure layer or service purchase is required for tests.

Local focused acceptance uses two separate disposable databases, a generated
one-day localhost TLS certificate and invented symbols. It posts documented JSON
over real HTTPS, verifies persistence before ack, pulls through the real outbound
worker, reconnects, checks cursor recovery and duplicate delivery, and verifies
Candidates API output plus monitoring authentication. Ten PostgreSQL tests and
30 parser/receiver tests passed at the initial checkpoint. Final focused checks,
UI acceptance and exact-head full CI must be recorded on the PR; public deployment,
backup restore rehearsal and actual provider delivery remain owner-gated.

Final local checkpoint: 30 parser/receiver tests passed; ten combined existing
candidate/new delivery database tests passed before the additional role assertion;
final two deployment-specific PostgreSQL tests passed. The optional real browser
path passed with no API mocks: HTTPS POST → remote commit → outbound HTTPS pull →
local reconnect/materialization → actual Candidates UI and watchlist save. The
initial browser save correctly failed CSRF because its generated origin was not
configured; the test now supplies its actual origin, with production protection
unchanged. Least-privilege checks deny market-revision reads and inbox deletion.
Compose configuration and pinned Caddy configuration validate. CI also runs the
new real HTTPS browser flow; full database suite is deferred to exact-head CI,
not repeatedly rerun locally. Backup/restore commands are documented; an actual
host-specific backup/restore rehearsal remains mandatory before public activation.
