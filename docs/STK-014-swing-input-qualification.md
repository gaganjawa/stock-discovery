# STK-014 — single-instrument real swing input qualification

This pure, read-only contract is an input-readiness check, not strategy approval,
provider authorization, publication or portfolio admission. It makes no network,
database, model or filesystem calls. No existing engine or synthetic path changes.

`SwingInputs` and `qualify()` live in
`shared/stock_discovery_analysis/swing_qualification.py`. Existing `Grant`,
`UseRequest`, `Candle`, `Calendar`, provenance and indicator calculations are reused.

## Contract and trust boundary

The caller supplies one NSE instrument, a cutoff, observed candles/calendar,
explicit instrument settings and evidence for prices, calendar, corporate actions,
instrument metadata, filings and material events. Each evidence dependency records
its revision, source/account request, original acquisition grant ID/version,
current grant, observed timestamp, coverage interval and freshness deadline.
Every dependency is checked, including additional providers and grant versions.
Missing evidence, denied rights, mismatched grants, future observations, stale or
incomplete coverage and unknown settings produce deterministic reason codes.

A trusted integration must resolve immutable acquisition linkage and current grants
and fences; verify policy references, retention compliance, deletion capability,
coverage completeness, adjustment semantics and eligibility against actual evidence.
Caller-supplied assertions are not independent verification. This function is not a
replacement for PostgreSQL enforcement, read-side authorization or final transaction
checks. Its result is a cutoff-specific assessment, never a reusable access token.
No production loader or UI is wired to these assertions by this ticket.

Requirements:

- Every source permits acquire/store/derive in the requested territory, quantity and
  retention interval under the exact original grant version. Renewal cannot bless
  an old acquisition. Restriction state and retention/deletion support must be
  explicitly verified for every dependency; unknown means insufficient.
- Price and calendar provenance must link to the exact evidence revision and be
  observed and available by cutoff. Coverage attestations must cover the complete
  input window through cutoff and remain fresh at cutoff.
- At least 30 closed sessions, exact calendar/bar alignment, no duplicates or gaps,
  positive volume and available existing indicator values are required.
- This deliberately limited implementation accepts raw prices/raw volume and a
  verified action-free window only. Adjusted history or windows with actions need
  later validated handling; they are not relabeled raw or guessed.
- Positive finite tick size, positive integer lot size, affirmative eligibility,
  absence of an instrument risk prohibition and complete filings/event coverage
  are required. Settings must come from the attested instrument source.

`INPUTS_QUALIFIED` means these supplied inputs pass this contract.
`INSUFFICIENT_EVIDENCE` identifies unmet requirements. Output includes sorted checks
and original source/account/grant/version/revision linkage, not source text, prices
or credentials. Linkage identifiers are internal metadata, not public diagnostics.
All results have actionable, publication_authorized and paper_admission_authorized
set to false. BUY, entry levels and quantity are not produced. The existing
`real_swing_instrument_settings_unavailable` gate is unchanged.

## Real evidence status, not synthetic acceptance

No current provider or private-data verification was performed. For INFY, the prior
Phase 9 record demonstrates historical descriptive indicators but does not qualify
execution inputs. Current source/grant and retention/deletion compliance remain
unverified; adjusted price/volume semantics and corporate-action coverage remain
unqualified; latest history/calendar freshness needs a new permitted observation;
current tick/lot/eligibility and filing/material-event coverage need evidence.
No real instrument is declared qualified. No policy approval is created.

A real instrument can satisfy this contract only after all required evidence is
supplied through a trusted resolver. Read-fence integration, policy approval,
action-aware normalization, executable strategy settings, UI integration, sizing
and live acceptance are separate work. Complete this review before starting them.

## Validation

Deterministic invented fixtures exercise qualification, missing/denied scopes,
retention/deletion uncertainty, grant renewal, mixed-source restrictions, unknown
instrument settings, unsupported adjustment bases, gaps/duplicates/provider lag,
future/synthetic/unattributed observations, missing coverage and deterministic
provenance. These tests grant no actual provider permission. Related rights,
quantitative-policy, real-readiness, API/scan and mocked-provider regressions are
run alongside them. No PostgreSQL changes or persistent operations are introduced.

## P2 corrections — acquisition authorization and immutable linkage

Evidence now carries an immutable `acquisition_grant` snapshot, explicit
`acquired_at`, and `revision_provenance`, separately from the current `grant` and
attestation `observed_at`. For this observed-data slice, acquisition must equal the
revision's fetched timestamp, with availability <= acquisition <= observation <=
qualification cutoff. Missing timestamps/provenance produce reason codes; malformed
values are rejected by the existing timestamp/provenance schemas. No cutoff is
substituted for acquisition time.

The original grant snapshot must authorize `acquire` at acquisition time. The
current exact grant ID/version must independently authorize `store`/`derive` and
any additional requested uses at cutoff. Revoked/expired current permissions fail
even when acquisition was lawful. Continued use does not require permission for a
new acquisition. Both snapshots must retain original grant identity. Resolution
of these snapshots against immutable storage remains the trusted caller's duty.

`bar_revision_ids` explicitly links each candle (in input order) to its stored
revision; `calendar_revision_id` links the calendar. Evidence retains the stored
ID separately from the upstream version in `revision_provenance.source_version`.
Matching includes the complete provenance and provider identity, not an assumed
identity between upstream versions and database IDs. Existing Candle/Provenance
contracts are unchanged. Missing or incorrect links fail closed.

Each stored revision must have one consistent original provider/account,
instrument, acquisition grant ID/version/snapshot, acquisition time and immutable
provenance. Contradictory rows are rejected in any order. Identical repeated
references are idempotent. Sorted `provenance` retains acquisition identifiers;
`revision_lineage` additionally preserves upstream versions and immutable clocks,
including conflicting candidates, without market values or source text.

Regression coverage includes all three reproduced review findings, grant validity
boundaries, revoked/expired current grants, distinct stored/upstream identifiers,
missing and contradictory timestamps, explicit links, conflicting ownership and
provenance, duplicate references and order-independent diagnostics. These remain
synthetic tests, not external permission or real-instrument acceptance evidence.

## Immutable candle consistency correction

Each supplied stored candle revision ID must resolve to exactly one canonical
Candle payload, including instrument, session timestamps, OHLC, volume,
adjustment version and provenance. Qualification uses the existing
`dataset.canonical(asdict(candle))` representation already used for quantitative
input hashing. It does not introduce a new stored Revision hash format or modify
revision storage. Multiple payloads for one ID produce
`conflicting_immutable_candle`; no first/last candidate wins.

Identical repeated (revision ID, canonical payload) references are deduplicated
before history, calendar alignment and indicator checks. Completed-session counts
use distinct session intervals, so repeated references cannot manufacture the
30-session minimum. Distinct revisions for the same session remain ambiguous and
fail calendar alignment. Candle/reference pairs can be reordered without changing
qualification or failure reasons; source versions remain separate from stored IDs.

Successful fixtures now use 30 distinct stored candle revision IDs. Regressions
retain the original 30-sessions/one-ID exploit, cover conflicts in every OHLC field
and volume, identical duplicates, insufficient distinct sessions, and reordered
references. This establishes internal consistency of the supplied linkage; a
trusted loader must still verify payloads against actual immutable storage.
Acquisition identity, grant authorization and all non-actionable gates are unchanged.
