# Non-actionable company research — STK-052/054

The existing company API now accepts `analysis=combined` and optional `cutoff_at`.
The company Swing tab has a **Compare stored research** control. It performs no
acquisition, model inference, publication or portfolio writes.

The flow is stored evidence → STK-014/STK-079 technical qualification and strategy
→ existing immutable fixed-RAG factual report → current deterministic catalogue
validation → one grant-fenced API response → company UI. It presents technical
conditions, financial trends/earnings changes, supported model-selected claims,
directional interpretations, exact quotations, conflicts and source gaps together.
No technical BUY is promoted: the combined action is always
`INSUFFICIENT_EVIDENCE`, with no execution levels or sizing.

## Evidence boundaries

- Original acquisition grants, current permissions and provider/account/grant
  fences are rechecked under one existing `guarded_read` transaction. Denial of
  either component withholds both. No cached composite is trusted.
- Only observed-mode stored bundles at/before the requested cutoff participate.
  Eligible new filings or corrected revisions require financial research refresh.
  Earlier reports are retained immutably and can still be inspected at their
  earlier cutoff when current access remains permitted.
- The unchanged financial verifier recomputes the report catalogue. Report
  version, entity, listing, horizon, cutoff and citation membership must match.
  Raw/rejected model output and pending semantic prose are not exposed here.
- Stored model identity/prompt/verifier versions and citations are visible.
  Comparable-period arithmetic is explicitly deterministic, not model accuracy.
  Only deterministically supported directional interpretations enter this view;
  uncalibrated free-form judge interpretations remain unaccepted.
- Quotes are attributed source statements, not independently verified figures,
  established events or evidence of complete announcement coverage. Uncertainties
  are not rewritten into claims of investment quality or absence of risk.
- Different financial/technical cutoffs are disclosed. Current access/freshness
  gates are never revived by requesting an old cutoff. The view is a reconstruction,
  not a prospective prediction or immutable recommendation publication.

## Replay wiring, not AI-performance acceptance

Existing synthetic freeze/read API responses include a `research_context` projected
from the already-frozen decision. The Replay UI shows that context before explicit
future-price reveal. The context does not read outcomes, change frozen storage or
attach later research. Restart and reveal leave its identity unchanged.

The existing synthetic Dataset has **no frozen financial evidence**. This gap is
explicit. Its technical outcomes cannot be reported as AI/combined performance.
Freezing a complete historical financial/technical bundle and running the existing
governed paired evaluation remain next product work, not an accepted capability of
this increment. No historical contracts, migrations or frozen examples changed.

## Validation and limitations

Local software validation uses fabricated observed-mode evidence, scripted model
selection and disposable PostgreSQL. No new actual model/provider calls or inference
reservations were made on the four familiar development cases. The prior experiments
and proposed human thresholds remain unchanged.

Focused checks cover the full filing → scripted selection → verifier → combined API
flow, technical BUY/WAIT with no promotion, repeated-read accounting, source removal
and mixed-source revocation, both read/restriction orderings, stale/new filings,
point-in-time exclusion, replay restart/reveal, and desktop/mobile stale-result
clearing. Final exact counts are recorded in the progress checkpoint and PR.

M1 real rights/input qualification, M2 independent human/50-case evaluation, historical
evaluation and policy approval remain BLOCKED. No genuine NSE recommendation,
semantic-quality acceptance or production-readiness claim is made. Latest-document
enumeration and per-revision authorization remain a P3 scalability concern; no new
cache was introduced to trade correctness for speed.
