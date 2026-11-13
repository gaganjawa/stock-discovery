# STK-095 / D3-03 + D3-04 + D3-09 — customized webhook rejection

## Cause and provider evidence

Owner reports an authenticated production rejection at **12 November 2026,
17:00:04 IST**, reason `invalid_payload_fields`, with zero accepted events.
The historical rejection retained a hash/reason only, so its original fields
cannot be recovered. This change has not read or changed the production database.

The old adapter requires stocks, trigger_prices, triggered_at, scan_name,
scan_url and alert_name, with only optional webhook_url. Any other top-level key
fails before identity/value validation. STK-095's original synthetic_enrichment_v1
was deliberately invented for synthetic scanners; it was not a provider contract.

Provider evidence:

- [Original documented JSON](https://chartink.com/articles/alerts/webhook-support-for-alerts/)
  defines the six string fields plus optional webhook_url.
- [Current alert guide](https://chartink.com/articles/alerts/alerts-guide/)
  documents customizable Payload Columns, distinct from result columns.
- Read-only inspection of the owner's View JSON preview on 12 November showed
  an extra `columns` array, but accessibility exposed a truncated preview. No
  Test webhook or Update alert action was performed by the agent.
- On **13 November**, the owner supplied the complete response captured by testing
  Chartink against an external webhook inspection service. This verifies the
  container and 14 exact row keys: symbol, close, %_change, volume, marketcapname,
  sector, industry, EMA10, ema30, sma50, rsi14, AVG_VOLUME20, avg_true_range,
  PREV20_HIGH. There are three objects aligned with three placeholder stocks.
  The new fixture preserves that observed test structure and placeholder values,
  replacing the destination URL and scanner identity. No private capability URL
  is committed, printed, retained in diagnostics or included in accepted envelopes.

**The supplied message is a provider Test webhook, not a genuine market alert.**
It uses SYMBOL 1–3, numeric placeholders in symbol/text fields, and RSI above 100.
Previously `columns` caused the first rejection; merely permitting that key would
still fail symbol, type and range checks. Those gates must not be weakened for
actual candidates. Live-market column types/null behavior have not yet been
observed; the adapter applies the existing strict domain contract and will reject
incompatible live rows with safe diagnostics rather than guess/coerce them.

## Versioned adapter and test-delivery isolation

`chartink-columns-v1` accepts the observed row-array container with exactly the
14 verified keys. Actual alerts still require configured scanner identity and
finite authorization, valid unique NSE-style symbols, matched prices/counts,
valid trigger time, matching row symbol at every position, bounded types/ranges,
and no unknown fields or mixed synthetic/provider enrichment. Text snapshot fields
must be strings or explicitly missing; numeric fields use the existing finite
bounded-number rules. ATR period remains unverified: avg_true_range is preserved
as provenance but cannot silently become ATR14. Output stays descriptive and
unverified, never actionable or point-in-time qualified.

Actual alerts emit `chartink-event-columns-v1`, with typed enrichment and retained
original column provenance. Event hashes include the columns, exclude webhook_url,
and preserve existing same-session replay deduplication. The original six-field
`chartink-event-v1` and synthetic fixture extension remain compatible.

Only the **exact observed provider test template**, after scanner identity and
expiry checks, emits `chartink-provider-test-v1` with delivery_kind=provider_test,
empty symbols and provider_test_not_market_delivery completeness. The immutable
receipt uses the existing inbox and authenticated feed. Materialization marks it
completed without inserting any session, candidate, match or research row.
Near-matches cannot bypass normal validation. HTTP 202 reports delivery_kind;
health separately counts provider_test_events and candidate_delivery_events.
Stored event/high-water counts include test receipts for correct cursor recovery;
they do not prove genuine market delivery.

## Privacy-safe diagnostics

Opt-in `CHARTINK_REJECTION_DIAGNOSTICS=true` retains at most 20 structure summaries
in `/tmp/chartink-rejection-shapes.json`, mode 0600, using a process-shared file
lock and atomic replacement. The existing authenticated `/candidate-health` route
returns summaries; unauthenticated access remains denied. Disabled by default,
with no database migration or permission expansion. Existing container tmpfs is
used, so records disappear on container replacement.

Schema `chartink-rejection-shape-v1` retains recognized field names, JSON types,
object/array counts and bounded sampled structures. It never copies scalar values,
stock symbols, request bodies, exception messages, headers or URLs. Arbitrary key
names can carry secrets too: unknown names are redacted and counted by type.
Four nesting levels, 16 entries per object/array sample and 160 visited nodes bound
work/output. Counts describe structure, never scanner completeness. Duplicate JSON
keys and nonstandard NaN/Infinity constants fail closed. Diagnostic write failure
cannot turn a rejection into acceptance or prevent normal rejection handling.

## Verification and limits

Tests cover the supplied provider test structure, URL exclusion, identity and
expiry, exact-test near-matches, original documented format, versioned columns,
row alignment/counts, unknown/missing keys, malformed values, numeric text fields,
RSI/finite-number bounds, replay hashes, ambiguous JSON and diagnostic privacy,
retention/mode/work limits. Invented valid candidate values exercise the observed
wire structure; they are explicitly not claimed as a genuine market receipt.

Isolated PostgreSQL acceptance covers HTTP 202, durable insertion, authenticated
feed retrieval, replay deduplication and envelope revalidation. Provider test
materialization must create zero sessions/candidates/matches/research; a valid
invented candidate alert must create exactly one candidate/session with typed
snapshot values. Production delivery and live type compatibility remain deployment
acceptance gates. Exact-head CI evidence is recorded in PR #49.

## Deployment — explicit approval required

No live service, URL, credential, alert setting, volume or database has changed.
This PR is separate from STK-099 PR #48, based on main. It changes shared
normalization/materialization, so **all feed-consuming workers must receive the
compatible code before the receiver emits new envelope versions**. If PR #48 is
selected for hosting, its release must incorporate this shared-code change after
owner review; no STK-099 hosting files are bundled here. Old consumers fail closed
on new envelopes and can stall their cursor; do not silently skip those receipts.

After owner review and explicit deployment approval:

1. Record current receiver/consumer image IDs, reviewed commits, effective Compose
   files and config hashes privately. Preserve the exact receiver project, database,
   volumes, credentials, webhook URL, hostname and scanner identity. Build immutable
   reviewed images on an isolated builder, not the live VPS.
2. Deploy compatible consumer code first using its established launcher and cursor,
   then verify it reads old v1 events. Do not activate new workers or duplicate a
   running consumer. The existing schema and least-privilege grants are sufficient.
3. In an approved maintenance window, replace **only the receiver image** in its
   existing Compose project. Optionally enable CHARTINK_REJECTION_DIAGNOSTICS=true.
   Render/review Compose first; use receiver-only `up -d --no-deps receiver`. No
   migration, database/proxy recreation, volume deletion or credential rotation.
   Delivery during restart has no assumed retry guarantee.
4. If separately approved, trigger Chartink's Test webhook against the unchanged
   app URL. Require HTTP 202, delivery_kind=provider_test, one durable test receipt,
   deduplicated retry, authenticated feed and no candidate/research/session rows.
   Do not count this as a genuine market event or Mac-off acceptance.
5. Observe an ordinary genuine alert. Require scanner identity, exact field/type
   and symbol alignment checks, durable candidate receipt, one worker result and
   correct UI source labels. If rejected, inspect only the authenticated bounded
   shape diagnostics; do not dump values or widen the adapter speculatively.
6. Disable diagnostics after verification. Keep only sanitized evidence and retain
   the independently approved backup/monitoring controls. No model/provider-source
   acquisition or broker operations are introduced.

## Rollback

Restore the recorded receiver image and disable diagnostics using the same
receiver-only Compose operation. Keep the **compatible consumer** until every new
version already stored has been consumed: an old consumer cannot validate those
immutable envelopes. Do not delete events, reset cursors, rewrite the database or
resume a stale copy to make an old worker appear healthy. If consumer code itself
must be rolled back, stop it and report the blocked cursor; preserve the backlog
until a compatible consumer is restored. There is no database/schema rollback.
Production volumes, credentials and exact webhook URL stay unchanged.


### PR #49 P2 follow-up — bounded envelopes and decimal arithmetic

The HTTP body remains limited to 65,536 bytes. Expanded normalized envelopes
have a separate 1,048,576-byte serialized JSON limit, checked before database
writes; the inbox still holds at most 10,000 events. This bounds serialized
envelope retention to approximately 9.77 GiB (database/index overhead additional).
Storage overflow returns HTTP 413; a full inbox returns HTTP 503. Duplicates at
inbox capacity remain replayable. Neither failure inserts partial event/state rows.

Enrichment numbers allow at most 28 coefficient digits and decimal exponents
from -28 through 12, in addition to existing per-field value ranges. Excess
precision/exponents and any DecimalException during conversion, comparison or
derived arithmetic become `invalid_enrichment_number` (HTTP 422 with a durable
hash/reason rejection and opt-in structure-only diagnostics). All four derived
metrics share this boundary, including CSV and synthetic enrichment callers.
No raw value is included in the error. Trigger prices have no derived arithmetic.

Regression coverage includes real PostgreSQL/HTTP batches of 35, 40, 50 and
150 candidates, oversized 500-row transport, bounded storage/full-inbox failures,
replay at capacity, authenticated feed, materialization and decimal rejection
privacy. Batch values remain invented software fixtures, not live-market evidence.
The existing deployment/rollback procedure applies; no migration or grant change.
