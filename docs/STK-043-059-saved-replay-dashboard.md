# Saved historical research — STK-043/059

Dashboard and Replay provide **Saved historical research**. Filter by dataset and
instrument, browse older pages, and reopen the exact immutable decision.

## Workflow

1. Load fictional history from Dashboard if necessary.
2. Freeze individual research or choose a saved run.
3. Read frozen financial/AI evidence alongside technical rules. Desktop uses two
   columns; narrow screens stack them.
4. Reopened charts show cutoff-only prices, even when an outcome was recorded.
   Reveal remains explicit; a chart marker identifies the cutoff after reveal.
5. Reveal shows the separate technical baseline outcome and combined abstention.
6. Select a dataset and **Evaluate fictional evidence batch** to queue three pinned
   demonstration dates across its instruments through the existing worker. Refresh
   saved research after completion. Jobs, attempts, failures, immutable decisions
   and outcomes retain existing contracts. Repeating a batch is idempotent.

This workflow requires no script, provider access or model execution.

## API and safety

`GET /api/v1/analysis` extends the existing authenticated resource with optional
dataset/instrument filters, an opaque `before` cursor and bounded 1–50 record pages.
Stable cutoff/ID ordering avoids duplicates across unchanged pages. Each full
snapshot is reauthorized, including final validity after later dependency locks.
Restricted rows expose only an opaque record reference and unavailable status;
other authorized records remain usable.

Frozen detail includes cutoff-only chart bars and never attaches outcomes. Reads
are no-store. Reopening/refreshing creates no analyses or inference receipts.
Denied opens clear old UI evidence; changing history filters or leaving the
component cancels pending requests.

`POST /api/v1/experiments` adds optional `include_financial=true`. Existing payloads
and technical-only job identities are unchanged. Full jobs seed explicitly fictional
filings via existing ingestion, freeze full evidence, and apply the existing daily
evaluator separately to combined and technical baseline records. Malformed flags
fail before decision creation. No publication or admission is performed.

## Evaluation limits

History shows page-scoped coverage counts of technical-only, unqualified combined
and restricted records. These are not performance denominators. Eligible paired
samples remain **zero**, AI-performance metrics **null**, and comparison
**unavailable** while research/policy qualification is blocked. Existing D3-11
governance and immutable forecast/trade contracts remain authoritative; no new
evaluator, threshold or experiment reference is introduced.

All prices and financial fixtures are synthetic software evidence. M1 real NSE
rights/archive/input qualification and M2 independent human/50-case evaluation stay
blocked. Prior experiments and reference packets remain unchanged. No actionable
real recommendations, publication, prospective admission, deployment or trading.

P3: per-record source rechecks can become expensive with large histories; page
limits bound work pending measured query optimization. Browser acceptance uses a
fresh disposable database: repeated discovery tests intentionally consume durable
mock budgets, and exhausted research is correctly withheld rather than reset.
