# Full historical evidence replay — STK-037/043/059

In Replay, select **Include fictional financial evidence** before freezing.
The existing authenticated analysis endpoint then stores an additive full snapshot
in the existing immutable run manifest, linked to the unchanged technical baseline.
No new schema, outcome engine, model runtime or provider interface is introduced.

The UI separates **evidence known at the historical cutoff** from **what became
known afterward**. It displays financial statements/facts, exact periods/units,
calculations, citations, upstream and stored revisions, hashes, availability clocks,
uncertainties, and a combined abstention. An explicit reveal shows subsequent
fictional prices and the original technical baseline's fill/stop/target/expiry/fees/
slippage result. Combined performance is unavailable with paired sample size zero.

## Frozen content and compatibility

- Technical indicators and as-of bars, instrument, mapping, membership, corporate
  actions and closed-session calendar inputs; original Dataset version retained.
- Stored, immutable financial document bodies and normalized facts, retrieval
  bundle, source revision/content hashes and original acquisition grant identities.
- Contradictions, coverage gaps and deterministic comparable-period calculations.
- Exact cutoff, publication/availability/acquisition clocks and strategy, code,
  snapshot and verifier versions. Model/prompt/findings/citations only when verified
  contemporary evidence exists; absent versions are null.
- Combined decision/reasons and the existing technical baseline recommendation ID.

Full snapshots have new content-based run IDs and configuration
`SYN-COMBINED-ABSTAIN-1`, keeping them out of the technical baseline's version cohort.
Legacy technical freeze/read/reveal behavior and old identifiers stay intact.
Historical recommendation/evaluation examples and the M2 reference packets are
unchanged. Full snapshots are never retroactively attached to old decisions.

The old synthetic candle fixture deliberately distinguishes fictional availability
from its later fixture fetch time. Its original provenance is preserved, not
backdated. New fictional filing clocks are explicitly hypothetical development
inputs; they are not assertions about original NSE filing availability.

## Time and authorization boundaries

The existing as-of retriever selects eligible statement revisions. Every document
and identity pin is checked against stored payload/hash, source/account/original
grant, fictional mode, and publication/availability/acquisition at or before cutoff.
Missing clocks or lineage fail closed. Later corrections appear only in later
snapshots. Duplicate ingestion remains idempotent. Conflicting facts stay visible
and do not support comparable-period calculations.

All original grant fence identities are locked in deterministic order, then current
store/derive/historical-replay rights are checked using fresh database time. Locks
remain through the atomic full-snapshot commit. Restriction before authorization
rolls back the new run; restriction after authorization waits for commit. Historical
records remain immutable. Read/reveal/scorecard/export reauthorize source dependencies;
revocation hides copied content rather than rewriting history. Protected replay
responses use `Cache-Control: no-store`.

AI attachment uses the optional stored `historical_ai_run_id` in the existing
analysis request (or the Replay UI's optional run-ID field), never caller-supplied
claim text. It requires the exact same historical evidence bundle,
reservation before completion, and verifiable completion at/before cutoff. Today's
cached reports are never selected. Existing reports without completion timestamps
remain unavailable. The default run-ID is empty; this view never runs inference.
Synthetic tests exercise contemporary/late/unknown completion with scripted results;
they are not model-quality measurements. Historical model-knowledge contamination
remains unqualified.

## Acceptance and limitations

All new financial sources are labelled fictional development evidence. Seeding is
explicit opt-in and uses existing rights-gated revision/evidence ingestion. No
source permissions are granted for real providers. No inferred availability, real
filings, model output or unknown instrument setting is substituted.

M1 source qualification, M2 independent human review/50-case holdout, historical
quality acceptance and policy approval remain blocked. `financial_qualified=false`;
the combined decision always abstains and cannot publish or admit a position.
Technical baseline outcomes cannot establish AI/combined accuracy or profitability.
Actual NSE archive integration and valid paired AI/quantitative metrics remain
dependent on those gates. The existing evaluation engine is reused; no new
performance thresholds are invented.

P3 follow-up: copied snapshot size and per-source authorization cost grow with
evidence volume. Current retrieval caps remain enforced. General real reader/cache,
deletion and backup/restore work is not expanded by this slice.
