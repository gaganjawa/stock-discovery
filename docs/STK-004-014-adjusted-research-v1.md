# STK-004/014 — Adjusted research contract V1

Present-day descriptive research only. M1 remains BLOCKED. No historical
strategy evaluation, qualified execution, publication or paper admission.

The existing company view now returns typed `adjusted_research` alongside the
compatible `price_features` field. Existing Decimal indicator functions are
reused without formula changes. Relative volume always remains null.

## Identity and provenance

`adjusted-research-v1` records the instrument/provider, immutable price and parent
instrument revisions, upstream source versions, original acquisition grant
IDs/versions, publication/availability clocks, acquisition/observation clocks,
calendar revisions, session coverage, basis, methodology uncertainty and reasons.
Acquisition/observation clocks explicitly use the stored revision's `fetched_at`:
these are observation receipt clocks, never claimed exchange publication times.

Batch identity is the digest of the original ingestion stream, verified immutable
page hashes and ordered revision IDs. Verification reconstructs the complete
paged content using the existing Upstox adapter's ordered numeric-cursor protocol.
Every selected revision must belong to that original complete stream, with the
exact stored payload and complete page coverage, no quarantine, and one observed
fetch time. Equal timestamps alone cannot pass. Missing receipts, partial/mixed
revision sets, changed payloads, ambiguous streams and unsupported page layouts
fail closed. Reads are bounded to 5,000 revisions/pages.

This proves an ingestion batch, not a single authenticated HTTP response or a
provider-certified adjustment ledger. `response_hash` is null because the existing
revision ingestion does not persist original HTTP response hashes. No new storage,
provider requests or inference pipeline is introduced.

## Read and temporal boundary

The company view retains its existing grant checks and transaction-scoped read
fences, including original acquisition dependencies, current grants and parent
revisions. Restrictions are revalidated before content leaves the guarded read.
No cached result or independent endpoint is added.

Only the ordinary present-day company view can produce descriptive metrics.
Any explicit historical cutoff request returns unavailable adjusted research,
even when the cutoff equals the current clock. Later fetched/available evidence
is ineligible. Today's adjusted history is never reconstructed as information
known before an adjustment. Price/volume adjustment factors and rounding remain
unverified; volume basis remains unknown.

At least 30 observed bars, membership in verified closed sessions, no missing or
duplicate sessions, and the latest known closed session are required. Session-list
completeness is explicitly not attested. No new elapsed-age threshold is invented.
Adjusted charts are withheld when this verification fails; non-Upstox behavior is
preserved. Gaps cannot be hidden by dropping old batches before qualification.

All five permissions are literal false: actionable, execution qualification,
historical PIT qualification, publication authorization and paper admission.
The result cannot validate as an execution recommendation. Raw-v1/STK-014
qualification, frozen strategies, datasets, replay, paper engine and evaluation
artifacts remain unchanged.

## Validation and remaining limits

Synthetic unit cases cover missing/mixed page evidence, invalid provenance,
future observations, historical requests, pagination order, unknown volume,
false-permission invariants and rejection as a recommendation. Disposable
PostgreSQL cases cover the full company view, complete batches, same-clock mixed
streams, missing sessions, historical requests, durable restriction after a
successful read, revoked/missing grants, idempotent reads and unchanged storage.
Existing read-fence concurrency and research/ingestion regressions remain required.

No genuine NSE input is qualified by these tests. Original execution prices,
complete actions/filings/events/settings, historical source availability, and
unresolved backup/revocation/deletion/correction obligations remain separate gates.
The two pending source-investigation documents are preserved outside this commit.

Available results independently validate session counts and coverage flags on
deserialization, and require all seven indicator keys (nullable values remain
supported). Calendar completeness is still not inferred from session rows.

Operational limitation: rolling daily updates in separate streams cannot satisfy
the full-window single-batch proof and remain unavailable. Multi-batch merging is
not supported; batch identity is not relaxed.

Daily boundary validation uses the actual candle and calendar revisions, not
readiness flags alone. Each candle must exactly match one known closed session's
open and close, with at least 30 distinct daily intervals and no missing, extra,
duplicate or ambiguous intervals in the observed window. Failure returns
`session_boundaries_unverified`, with metrics and adjusted charts withheld.
No timestamps are normalized and calendar exhaustiveness remains unattested.
