"""STK-052/054: non-actionable synthesis of existing, fenced research components.

No inference, acquisition, cache, recommendation or outcome writes. Stored model
selection is identified separately from deterministic arithmetic and source quotes.
"""
import json
from decimal import Context, localcontext

from stock_discovery_contracts.v2 import at, check, digest
from . import factual_research, swing_research
from .publication_store import now
from .rag_contracts import Bundle
from .rag_research import recheck
from .read_fences import guarded_read
from .real_access import source_access
from .real_views import ViewConfig

VERSION = 'combined-research-preview-1'
GATES = ('real_input_acceptance', 'independent_financial_quality',
         'historical_evaluation_acceptance', 'publication_policy_approval')


def compose(listing, cutoff, technical, financial=None, *, gaps=(), mode='real_research'):
    """Project evidence without promoting either component's action."""
    technical_state = {'BUY':'conditions_met', 'WAIT':'conditions_not_met'}.get(
        technical.get('status'), 'insufficient_evidence')
    reasons = set(gaps) | set(GATES)
    if financial is None: reasons.add('verified_financial_research_unavailable')
    if technical_state == 'insufficient_evidence': reasons.update(technical.get('reasons', ()))
    technical_view = dict(condition=technical_state,
        indicators=technical.get('indicators', {}), reasons=technical.get('reasons', []),
        freshness=technical.get('freshness'), analysis_id=technical.get('analysis_id'),
        evidence_revisions=technical.get('evidence_revisions', []),
        strategy_version=technical.get('strategy_version'), policy_version=technical.get('policy_version'))
    report = dict(version=VERSION, mode=mode, listing_id=listing, analysis_cutoff_at=cutoff,
        status='INSUFFICIENT_EVIDENCE', research_only=True, actionable=False,
        publication_authorized=False, paper_admission_authorized=False, trading_authorized=False,
        technical=technical_view, financial=financial, gaps=sorted(reasons),
        acceptance_gates={g:'BLOCKED' for g in GATES},
        conclusion='Component findings are available for research; combined recommendation qualification is blocked.',
        new_model_calls=0, model_accuracy=None,
        replay=dict(status='not_frozen', future_outcomes='not_requested',
            limitation='An as-of reconstruction is not a prospective prediction or a frozen evaluation.'))
    report['report_id'] = digest(report)
    return report


def financial_projection(result, bundle):
    """Only current-version immutable factual reports, never arbitrary assessments.

    Recompute the catalogue with the unchanged verifier. Expose accepted findings
    only, excluding raw model output, rejected prose and pending interpretations.
    """
    report = result.get('factual_report')
    check(result.get('status') == 'completed' and result.get('research_only') is True
          and isinstance(report, dict), 'factual_report_unavailable')
    check(report.get('version') == factual_research.VERSION, 'factual_validator_changed')
    for key in ('issuer_id','listing_id','horizon','cutoff_at'):
        check(report.get(key) == getattr(bundle.query, key), 'factual_identity_mismatch')
    check(report.get('actionable') is False and report.get('qualified') is False
          and report.get('publication') == 'blocked', 'unqualified_report_required')
    check(all(at(f.period_end_at) <= at(bundle.query.cutoff_at) for f in bundle.facts), 'future_financial_period')
    catalogue = factual_research.candidates(bundle)
    check(report.get('candidates') == catalogue, 'factual_catalogue_changed')
    allowed = {digest(c.model_dump(mode='json')) for h in bundle.hits for c in h.citations}
    allowed.update(digest(f.citation.model_dump(mode='json')) for f in bundle.facts)
    fields = ('accepted_claims','accepted_source_excerpts','interpretive_findings')
    for field in fields:
        for claim in report.get(field, []):
            check(claim.get('citations') and all(digest(c) in allowed for c in claim['citations']),
                  'factual_citation_mismatch')
    # Free-form judge support remains uncalibrated. It is not a verified finding.
    interpretations = [c for c in report.get('interpretive_findings', [])
                       if c.get('validation') == 'deterministic_directional_entailment']
    # Reuse the original verifier for cached text as well as arithmetic. A
    # citation's presence alone cannot support a changed number or interpretation.
    selected = lambda c: dict(candidate_id=c['candidate_id'],text=c['text'],
        citation_ids=list(dict.fromkeys(x['evidence_id'] for x in c['citations'])))
    claims=report['accepted_claims']; excerpts=report.get('accepted_source_excerpts', [])
    check(all(c.get('validation') in ('exact_fact_and_citation_passed',
        'deterministic_filing_fact_and_passage_parity') for c in claims), 'unknown_claim_validation')
    checked=factual_research.validate_response(json.dumps(dict(
        factual_claims=[selected(c) for c in claims if c['validation']=='exact_fact_and_citation_passed'],
        extracted_claims=[c['extracted_fields'] for c in claims if c['validation']=='deterministic_filing_fact_and_passage_parity'],
        source_excerpts=[selected(c) for c in excerpts], interpretations=[],
        relations=[dict(candidate_ids=c['candidate_ids'],direction=c['direction']) for c in interpretations])),bundle,catalogue)
    check(not checked['rejected_claims'], 'cached_claim_verification_failed')
    for stored, verified in ((claims,checked['accepted_claims']), (excerpts,checked['accepted_source_excerpts']),
                             (interpretations,checked['interpretive_findings'])):
        check(sorted(map(digest,stored))==sorted(map(digest,verified)), 'cached_claim_changed')
    return dict(cutoff_at=bundle.query.cutoff_at, horizon=bundle.query.horizon,
        model=result.get('model'), prompt_hash=result.get('prompt_hash'), validator_version=report['version'],
        bundle_hash=bundle.content_hash, input_revision_ids=list(bundle.documents),
        trends=[c for c in catalogue if c['kind']=='calculation'],
        findings=checked['accepted_claims'], interpretations=checked['interpretive_findings'],
        source_excerpts=checked['accepted_source_excerpts'],
        uncertainties=checked['limitations'], conflicts=checked['contradictions'],
        pending_interpretation_count=len(report.get('pending_interpretations', [])) +
            len(report.get('interpretive_findings', []))-len(interpretations),
        quality_acceptance='BLOCKED', human_verified=False,
        excerpt_warning='Exact quotations do not verify financial figures, event truth or complete announcement coverage.')


def research(conn, config, listing, *, cutoff_at=None, clock=now):
    config = ViewConfig.model_validate(config)
    cutoff = cutoff_at or clock()
    check(listing in config.listing_ids, 'listing_not_configured')
    technical = swing_research.unavailable(listing, cutoff, ['swing_coverage_review_not_configured'])
    if at(cutoff) > at(clock()):
        return compose(listing, cutoff, technical, gaps=['future_analysis_cutoff'])
    access = source_access(config.sources, clock)
    try:
        with guarded_read(conn, access) as guard:
            if config.swing is not None and config.swing.listing_id == listing:
                with localcontext(Context(prec=28)):
                    technical = swing_research._research(conn, config.swing, listing, cutoff, access, guard)
            # One deterministic latest bundle-backed fixed-RAG run per company.
            # An invalid selected report never falls back to older prose. Failures
            # before retrieval have no bundle/company identity and are not selected.
            row = conn.execute('''SELECT r.run_id,r.payload,b.bundle_hash,b.payload
                FROM discovery.rag_results r JOIN discovery.rag_bundles b USING(bundle_hash)
                WHERE b.payload->'query'->>'listing_id'=%s
                AND b.payload->'query'->>'mode'='live_paper'
                AND (b.payload->'query'->>'cutoff_at')::timestamptz<=%s
                ORDER BY (b.payload->'query'->>'cutoff_at')::timestamptz DESC,r.run_id DESC LIMIT 1''',
                (listing, cutoff)).fetchone()
            financial = None; gaps = []
            if row:
                run_id, result, key, raw = row
                bundle = Bundle.model_validate_json(json.dumps(raw))
                check(bundle.content_hash == key and result.get('bundle_hash') == key, 'bundle_identity')
                guard.bundle(key); recheck(conn, bundle, access)
                # New eligible filings/corrections invalidate stale research. An
                # old report stays immutable and can still be read at its old cutoff.
                current = conn.execute('''SELECT DISTINCT ON (r.source_id,r.logical_key) r.revision_id
                    FROM discovery.revisions r JOIN discovery.evidence_documents d USING(revision_id)
                    WHERE r.listing_id=%s AND r.available_at<=%s
                    AND (r.payload->>'fetched_at')::timestamptz<=%s
                    AND r.payload->>'availability_basis'='observed'
                    AND d.payload->>'category' IN ('annual_report','quarterly_report','announcement','news')
                    ORDER BY r.source_id,r.logical_key,r.sequence DESC''', (listing, cutoff, cutoff)).fetchall()
                current_ids = {r[0] for r in current}
                for rid in current_ids: guard.add(rid)
                if not current_ids or current_ids != set(bundle.documents):
                    gaps.append('financial_research_requires_refresh')
                else:
                    try:
                        financial = dict(financial_projection(result, bundle), run_id=run_id)
                    except (ValueError, KeyError, TypeError):
                        gaps.append('financial_report_validation_unavailable')
                if at(bundle.query.cutoff_at) < at(cutoff): gaps.append('financial_and_technical_cutoffs_differ')
            report = compose(listing, cutoff, technical, financial, gaps=gaps)
            guard.collect(report)
        return report
    except PermissionError:
        # Denial of ANY component withholds the entire composite response.
        return compose(listing, cutoff, swing_research.unavailable(listing, cutoff, []),
                       gaps=['source_access_or_provenance_unavailable'])


def replay_context(frozen):
    """Projection of an existing immutable synthetic decision, never its outcomes.

    Financial evidence is not in the frozen Dataset contract: do not attach a
    later report or relabel a synthetic decision as observed company research.
    """
    rec = frozen['recommendation']
    check(rec['instrument']['instrument_id'].startswith('SYN-') and
          rec['versions']['dataset'].startswith('SYN-'), 'synthetic_replay_required')
    technical = dict(status=rec['action'], indicators=frozen['indicators'],
        reasons=[rec['rationale']['summary']], analysis_id=rec['recommendation_id'],
        strategy_version=rec['strategy']['version'])
    report = compose(rec['instrument']['instrument_id'], rec['information_cutoff_at'], technical,
        gaps=['financial_evidence_not_in_frozen_dataset'], mode='synthetic_replay')
    report['replay'] = dict(status='frozen_technical_only', recommendation_id=rec['recommendation_id'],
        dataset_version=rec['versions']['dataset'], code_version=rec['versions']['code'],
        future_outcomes='hidden_until_explicit_reveal',
        limitation='Synthetic technical outcomes are not an evaluation of AI or combined research.')
    report['report_id'] = digest({k:v for k,v in report.items() if k!='report_id'})
    return report
