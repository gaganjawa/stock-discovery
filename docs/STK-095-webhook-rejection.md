# STK-095 / D3-03 + D3-04 + D3-09 — customized webhook rejection

## Evidence and scope

Owner reports an authenticated production rejection at **12 November 2026,
17:00:04 IST**, reason `invalid_payload_fields`, with zero accepted events.
This change has not inspected or modified the production database or receiver.

`normalize()` requires stocks, trigger_prices, triggered_at, scan_name, scan_url
and alert_name; only webhook_url is additionally permitted. Every other top-level
key fails before identity/value validation. The optional synthetic_enrichment_v1
transport is expressly invented and restricted to synthetic scanners. STK-095's
CSV column aliases do not establish a production webhook JSON contract.

Provider evidence checked 12 November:

- [Documented original JSON](https://chartink.com/articles/alerts/webhook-support-for-alerts/)
  has six string fields and optional webhook_url.
- [Current provider alert guide](https://chartink.com/articles/alerts/alerts-guide/)
  confirms customizable Payload Columns, distinct from result columns, but does
  not document the wire types, alignment or empty-value behavior.
- Read-only inspection of the owner's existing alert **View JSON** confirms the
  extra top-level `columns` array and an object beginning with symbol and close.
  Accessibility exposes only a truncated preview. It is a provider-generated
  example, not the rejected delivery. No values, screenshot or capability URL
  were retained in repository evidence. No Test webhook or Update alert action
  was performed; the dialog was cancelled unchanged.
- Trigger history exposed no delivered JSON. The owner has no payload structure
  sample. Existing rejection records contain a hash and reason only, which cannot
  reconstruct the original body. A public-page source request was denied.

**Conclusion:** `columns` is a demonstrated incompatibility in the provider
preview. The exact fields/types of the historical failed delivery are still
unknown. A complete observed-payload regression fixture and production columns
adapter remain BLOCKED. Do not claim that this diagnostic increment fixes real
customized delivery or accept arbitrary extra keys to suppress the error.

## Prepared diagnostic implementation

Opt-in `CHARTINK_REJECTION_DIAGNOSTICS=true` stores at most 20 structure summaries
in `/tmp/chartink-rejection-shapes.json`, mode 0600, using a process-shared file
lock and atomic replacement. No database migration or privilege expansion.
The existing authenticated `/candidate-health` response exposes the summaries;
unauthenticated access remains denied. Feature is disabled by default. The file
is in the existing container tmpfs and disappears on container replacement.

Schema `chartink-rejection-shape-v1` records only recognized field names, JSON
value types, object/array counts and bounded sampled structures. It never copies
scalar values, string contents, stock symbols, request bodies, exception messages,
headers or URLs. Arbitrary field names could themselves carry secrets or stock
symbols: unrecognized names are redacted and only their number/type histogram is
retained. Known labels are limited to the documented base fields, observed columns
container and existing STK-095 column vocabulary. Four nesting levels, 16 entries
per object/array sample and 160 visited nodes bound work/output. Counts describe
structure, never completeness of a trading session.

JSON duplicate keys and nonstandard NaN/Infinity constants now fail closed.
Diagnostic write failure cannot cause acceptance or change the 422 rejection.
The normal six-field adapter, scanner identity, decimal checks, authorization,
capability stripping, hash/idempotency and commit-before-202 behavior stay intact.
There is no permissive enriched adapter or invented enriched JSON fixture.

## Acceptance

Tests cover structural privacy with adversarial key names and secret markers,
scalars/types, nesting/width bounds, disabled behavior, file modes/retention,
write failure, duplicate keys and malformed JSON. PostgreSQL integration checks
rejected columns do not create events, diagnostics require feed authentication,
and the original documented format returns HTTP 202, commits one durable event,
deduplicates replay and is retrievable from the authenticated feed. Invented
values exercise observed *partial* preview structure; they are not represented
as the real failed delivery. CI evidence belongs in the focused PR.

## Deployment and rollback — approval required

This PR is diagnostic preparation only and must remain draft until the provider
structure has been verified and a strict versioned adapter is reviewed. Do not
merge/deploy it as a claim of restored delivery. It is separate from STK-099 PR #48
and introduces no migration or shared worker change requiring a dependency on it.

If the owner explicitly approves a **diagnostics-only receiver deployment**:

1. Record the existing receiver image ID, reviewed commit, effective Compose files
   and config hashes privately. Keep the existing project, volumes, credentials,
   source grants, hostname and exact webhook URL. Build the reviewed API image on
   an isolated builder, not the running VPS.
2. Use an approved maintenance window to replace **only the receiver image** and
   set `CHARTINK_REJECTION_DIAGNOSTICS=true`. Render/review Compose first. Use the
   existing receiver project with `up -d --no-deps receiver`; do not run migrations,
   recreate the database/proxy, delete volumes or change alert settings. Delivery
   during the brief restart has no assumed retry guarantee.
3. Read `/candidate-health` using the existing private pull authentication mechanism
   (never put secrets into command arguments or logs). Wait for an ordinary genuine
   provider delivery. Do not press Test webhook against production without separate
   authorization. Export only the bounded structure summary privately.
4. Verify complete field names/types/nesting, per-stock alignment, null/empty
   semantics and column aliases against provider configuration. Redacted unknown
   names need private provider confirmation; do not loosen the logger to dump
   keys/values. Implement an explicitly versioned columns adapter only from that
   evidence, with exact allowlists, identity/type/size checks and capability
   exclusion, then add representative value-redacted tests and run isolated
   HTTP 202 → PostgreSQL → authenticated feed acceptance before release.
5. Roll back by restoring the recorded receiver image and disabling the diagnostic
   option with the same receiver-only Compose operation. No database rollback is
   necessary; accepted events, existing volumes and credential files remain intact.
   Disable diagnostics after evidence collection. Retain only sanitized structure
   evidence; tmpfs diagnostics are not a backup or audit of historical bodies.

Alternative: a complete provider-generated example or privately obtained schema
can unblock adapter implementation without any production deployment. Neither a
truncated preview nor green tests of the original format proves customized support.
