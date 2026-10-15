"""D3-01 acceptance at the contract boundary; no providers, DB or AI required."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from stock_discovery_contracts.v2 import (
    Admission, CohortSummary, Horizon, Outcome, Recommendation, digest,
    parse_json, read_record, validate_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'docs/contracts/v2/examples'


def sample(profile='swing'):
    return json.loads((EXAMPLES / (profile + '.synthetic.json')).read_text())


@pytest.mark.parametrize('profile', ['swing', 'short_term', 'long_term'])
def test_all_horizons_arms_actions_and_blocked_buy(profile):
    bundle = validate_bundle(sample(profile))
    assert {r.cohort.arm for r in bundle.recommendations} == {'quant', 'quant_rag', 'quant_agent', 'traditional_ml'}
    assert {r.action for r in bundle.recommendations} == {'BUY', 'WATCH', 'AVOID', 'INSUFFICIENT_EVIDENCE'}
    blocked = bundle.recommendations[1]
    assert blocked.action == 'BUY' and blocked.paper_admission.quantity is None
    assert bundle.outcomes[0].status == 'provisional'
    assert bundle.outcomes[0].realized_return is None


# Every nested object rejects extensions, not just the root object.
def object_paths(value, prefix=()):
    if isinstance(value, dict):
        yield prefix
        for key, child in value.items():
            yield from object_paths(child, prefix + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from object_paths(child, prefix + (index,))


def test_unknown_fields_rejected_at_every_object_boundary():
    original = sample()
    for path in object_paths(original):
        bad = copy.deepcopy(original)
        target = bad
        for key in path:
            target = target[key]
        target['unexpected'] = True
        with pytest.raises(ValueError):
            validate_bundle(bad)


@pytest.mark.parametrize('field,value', [
    ('action', 'SELL'), ('action', 'WAIT'), ('action', 'buy'),
    ('mode', 'live'), ('mode', 'shadow'), ('mode', 'real_money'),
    ('schema_version', '3.0.0'), ('synthetic', 'true'),
    ('information_cutoff_at', '2025-02-30T10:00:00Z'),
    ('generated_at', '2025-01-06T10:06:00+00:00'),
    ('decision_available_at', '2025-01-06T10:00:00Z'),
    ('baseline_ref', ''), ('revises_id', 'SYN-swing-quant'),
    ('action_reason_codes', []), ('research_ref', 'invented'),
])
def test_strict_recommendation_rejections(field, value):
    payload = sample()
    payload['recommendations'][0][field] = value
    with pytest.raises(ValueError):
        validate_bundle(payload)


@pytest.mark.parametrize('case', [
    'future_publication', 'future_availability', 'restatement', 'unclosed_bar',
    'calendar_hash', 'calendar_ref', 'holding_endpoint', 'unresolved_baseline',
    'foreign_event', 'foreign_assessment', 'failed_judge', 'foreign_snapshot',
    'unknown_citation', 'admit_shadow', 'admit_watch', 'missing_capital',
    'fractional_quantity', 'boolean_quantity', 'non_lot_quantity', 'hidden_quantity',
    'invalid_price', 'numeric_price', 'nan_price', 'missing_entry', 'missing_stop',
    'early_entry', 'unconfigured_policy', 'changed_policy', 'future_policy',
    'failed_ai_buy', 'missing_required', 'outcome_arm', 'outcome_horizon',
    'immature_matured', 'ambiguous_scalar', 'duplicate_id', 'unknown_revision',
])
def test_temporal_reference_risk_research_and_outcome_failures(case):
    b = sample()
    r = b['recommendations'][0]
    e = r['evidence'][0]
    if case == 'future_publication': e['published_at'] = '2025-01-07T10:00:00Z'
    elif case == 'future_availability': e['available_at'] = '2025-01-07T10:00:00Z'
    elif case == 'restatement': e['revision_id'] = 'later-restatement'
    elif case == 'unclosed_bar': e['period_end_at'] = '2025-01-07T10:00:00Z'
    elif case == 'calendar_hash': b['snapshot']['session_closes'].pop(1)
    elif case == 'calendar_ref': r['horizon']['calendar_ref']['version'] = 'later'
    elif case == 'holding_endpoint': r['horizon']['holding_end_at'] = '2025-01-09T10:00:00Z'
    elif case == 'unresolved_baseline': r['baseline_ref'] = 'invented'
    elif case == 'foreign_event': b['snapshot']['references'][-1]['instrument_id'] = 'OTHER'
    elif case == 'foreign_assessment': next(x for x in b['snapshot']['references'] if x['kind']=='judge')['assessment_id']='different'
    elif case == 'failed_judge': next(x for x in b['snapshot']['references'] if x['kind']=='judge')['passed']=False
    elif case == 'foreign_snapshot': r['snapshot_id'] = 'other'
    elif case == 'unknown_citation': r['rationale']['evidence_ids'] = ['invented']
    elif case == 'admit_shadow': r['cohort']['shadow'] = True
    elif case == 'admit_watch': r['action'] = 'WATCH'; r['execution'] = None
    elif case == 'missing_capital': r['risk_context']['capital_profile_ref'] = None
    elif case == 'fractional_quantity': r['paper_admission']['quantity'] = 1.5
    elif case == 'boolean_quantity': r['paper_admission']['quantity'] = True
    elif case == 'non_lot_quantity': r['instrument']['lot_size'] = 10
    elif case == 'hidden_quantity': r['paper_admission']['status'] = 'blocked'
    elif case == 'invalid_price': r['execution']['stop_price'] = '101'
    elif case == 'numeric_price': r['execution']['entry_price'] = 100
    elif case == 'nan_price': r['execution']['entry_price'] = 'NaN'
    elif case == 'missing_entry': r['conditions']['entry'] = []
    elif case == 'missing_stop': r['conditions']['invalidation'] = []
    elif case == 'early_entry': r['execution']['earliest_entry_at'] = r['decision_available_at']
    elif case == 'unconfigured_policy': b['snapshot']['policies'][0]['status'] = 'unconfigured'
    elif case == 'changed_policy': b['snapshot']['policies'][0]['parameters'][0]['value'] = '2'
    elif case == 'future_policy': b['snapshot']['policies'][0]['effective_at'] = '2025-01-07T00:00:00Z'
    elif case == 'failed_ai_buy': r['cohort'].update(arm='quant_agent', capability='researched'); r['research_status']='failed'
    elif case == 'missing_required': r['evidence_quality']['missing_required']=['filing']
    elif case == 'outcome_arm': b['outcomes'][0]['cohort']['config_hash'] = '0'*64
    elif case == 'outcome_horizon': b['outcomes'][0]['horizon']['duration'] = 3
    elif case == 'immature_matured': b['outcomes'][0]['status']='matured'
    elif case == 'ambiguous_scalar': b['outcomes'][0].update(status='ambiguous', realized_return='0')
    elif case == 'duplicate_id': b['recommendations'].append(copy.deepcopy(r))
    elif case == 'unknown_revision': r.update(revises_id='unknown', revision_reason='fixture')
    with pytest.raises(ValueError):
        validate_bundle(b)


def live_record():
    r = sample()['recommendations'][0]
    r.update(mode='live_paper', synthetic=False, availability_simulated=False)
    r['instrument'].update(exchange='NSE', isin='TEST-IDENTITY')
    r['evidence'][0]['availability_basis'] = 'observed'
    return r


def test_live_actual_publication_late_fetch_and_entry():
    r = live_record()
    Recommendation.model_validate(r)
    r['evidence'][0]['fetched_at'] = '2025-01-06T10:06:00Z'
    with pytest.raises(ValueError, match='late live fetch'):
        Recommendation.model_validate(r)
    r = live_record()
    r['generated_at'] = '2025-01-06T10:07:00Z'
    with pytest.raises(ValueError, match='backdated live publication'):
        Recommendation.model_validate(r)


def test_historical_exact_revision_requires_archival_proof():
    r = live_record()
    r.update(mode='historical_reconstructed', availability_simulated=True, generated_at='2025-01-09T10:00:00Z')
    r['evidence'][0].update(fetched_at='2025-01-08T10:00:00Z', availability_basis='verified_archive', archive_verification_ref='archive-exact-revision')
    Recommendation.model_validate(r)
    r['evidence'][0]['archive_verification_ref'] = None
    with pytest.raises(ValueError, match='unverified historical revision'):
        Recommendation.model_validate(r)


@pytest.mark.parametrize('profile', ['swing', 'short_term', 'long_term'])
def test_wrong_horizon_range_and_units(profile):
    h = sample(profile)['recommendations'][0]['horizon']
    h['maximum'] += 1
    with pytest.raises(ValueError): Horizon.model_validate(h)


def test_version_negotiation_preserves_wait_sell_and_daily_outcomes():
    originals = ROOT / 'docs/contracts/examples'
    for filename, kind in [('recommendations.synthetic.json', 'recommendation'), ('forecast-outcomes.synthetic.json', 'outcome'), ('trade-outcomes.synthetic.json', 'outcome')]:
        rows = json.loads((originals / filename).read_text())
        for row in rows:
            assert read_record(json.dumps(row), kind=kind, accepted_versions={'1.0.0'}) == row
            with pytest.raises(ValueError):
                read_record(json.dumps(row), kind=kind, accepted_versions={'2.0.0'})
    actions = {r['action'] for r in json.loads((originals/'recommendations.synthetic.json').read_text())}
    assert {'WAIT', 'SELL'} <= actions
    daily = {'schema_version':'1.1.0', 'status':'provisional'}
    assert read_record(json.dumps(daily), kind='outcome', accepted_versions={'1.1.0'}) == daily
    r = sample()['recommendations'][0]
    assert isinstance(read_record(json.dumps(r), kind='recommendation', accepted_versions={'2.0.0'}), Recommendation)


def test_legacy_validators_and_fixtures_unchanged():
    hashes = json.loads((ROOT / 'docs/contracts/v2/legacy-fixture-sha256.json').read_text())
    assert hashes
    for name, expected in hashes.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
    for name in ('validate_contract_examples.py', 'validate_evaluation_examples.py', 'validate_capital_risk_examples.py'):
        subprocess.run([sys.executable, str(ROOT/'scripts'/name)], cwd=ROOT, check=True, capture_output=True)


@pytest.mark.parametrize('text', ['{"schema_version":"2.0.0","schema_version":"1.0.0"}', '{"x": NaN}', '{"x":Infinity}', '[]'])
def test_strict_json(text):
    with pytest.raises(ValueError): parse_json(text)


def test_zero_pick_and_immature_denominators():
    payload = dict(schema_version='2.0.0', mode='synthetic', profile='long_term', cohort=sample('long_term')['recommendations'][0]['cohort'], decisions=0, buy=0, watch=0, avoid=0, insufficient_evidence=0, research_failed=0, eligible=0, resolved=0, missing=0, ambiguous=0, provisional=0, no_entry=0, net_expectancy=None, metric_unavailable_reason='no_resolved_outcomes')
    CohortSummary.model_validate(payload)
    payload.update(decisions=2, buy=1, insufficient_evidence=1, research_failed=1, eligible=1, provisional=1)
    CohortSummary.model_validate(payload)
    payload.update(net_expectancy='0', metric_unavailable_reason=None)
    with pytest.raises(ValueError, match='zero resolved metric'):
        CohortSummary.model_validate(payload)


def test_generated_schemas_are_current():
    subprocess.run([sys.executable, str(ROOT/'scripts/export_v2_schemas.py'), '--check'], check=True, cwd=ROOT)


def test_actual_daily_v11_output_round_trips_without_conversion():
    from datetime import timedelta
    from stock_discovery_analysis.dataset import canonical, demo_dataset
    from stock_discovery_analysis.replay import simulate
    from stock_discovery_analysis.strategy import analyze

    dataset = demo_dataset()
    cutoff = dataset.calendar.sessions[39].closes_at + timedelta(minutes=1)
    analysis = analyze(dataset, 'SYN-ALPHA', cutoff, code_version='D3-01-test')
    result = simulate(analysis, dataset, cutoff + timedelta(minutes=1))
    text = canonical(result)
    assert read_record(text, kind='outcome', accepted_versions={'1.1.0'}) == json.loads(text)


@pytest.mark.parametrize('case', ['risk_quantity', 'risk_rejected', 'reservation_quantity', 'observation_hash', 'unknown_evaluator', 'observation_cutoff', 'review_cadence', 'empty_policy'])
def test_additional_relational_guards(case):
    b = sample()
    refs = b['snapshot']['references']
    if case == 'risk_quantity': next(r for r in refs if r['kind']=='risk')['quantity'] = 2
    elif case == 'risk_rejected': next(r for r in refs if r['kind']=='risk')['passed'] = False
    elif case == 'reservation_quantity': next(r for r in refs if r['kind']=='reservation')['quantity'] = 2
    elif case == 'observation_hash': b['observation_manifests'][0]['revision_ids'] = ['later']
    elif case == 'unknown_evaluator': b['evaluator_refs'] = []
    elif case == 'observation_cutoff': b['observation_manifests'][0]['observation_cutoff_at'] = '2025-01-08T10:00:00Z'
    elif case == 'review_cadence': b['recommendations'][0]['horizon']['review_cadence'] = 'monthly'
    elif case == 'empty_policy': b['snapshot']['policies'][0]['parameters'] = []
    with pytest.raises(ValueError): validate_bundle(b)


def test_missing_capital_blocks_admission_without_rewriting_research_buy():
    b = sample()
    r = b['recommendations'][0]
    r['risk_context'].update(eligibility='unknown', risk_ref=None, capital_profile_ref=None)
    r['paper_admission'].update(status='blocked', reservation_ref=None, quantity=None, reason='capital_not_configured')
    result = validate_bundle(b).recommendations[0]
    assert result.action == 'BUY'
    assert result.paper_admission.quantity is None


def test_month_end_resolves_preceding_pinned_exchange_session():
    from stock_discovery_contracts.v2 import resolve_endpoint
    h = sample('short_term')['recommendations'][0]['horizon']
    h.update(anchor_at='2025-01-31T10:06:00Z', entry_expires_at='2025-02-03T10:00:00Z', next_review_at='2025-02-07T10:00:00Z', holding_end_at='2025-02-27T10:00:00Z')
    # Explicit fictional closure on Feb 28, rather than assuming weekdays trade.
    sessions = ['2025-02-27T10:00:00Z', '2025-03-03T10:00:00Z']
    assert resolve_endpoint(Horizon.model_validate(h), sessions) == h['holding_end_at']


def test_matured_outcome_is_append_only_and_keeps_provisional_record():
    b = sample()
    old = b['outcomes'][0]
    new = copy.deepcopy(old)
    new.update(outcome_id='SYN-matured', supersedes_outcome_id=old['outcome_id'], evaluated_at='2025-01-08T10:00:00Z', observation_cutoff_at='2025-01-08T10:00:00Z', status='matured', realized_return='0.01')
    manifest = copy.deepcopy(b['observation_manifests'][0])
    manifest['ref']['id'] = 'SYN-later-observations'
    manifest['observation_cutoff_at'] = new['observation_cutoff_at']
    new['observation_manifest_ref'] = manifest['ref']
    b['observation_manifests'].append(manifest)
    b['outcomes'].append(new)
    result = validate_bundle(b)
    assert result.outcomes[0].status == 'provisional'
    assert result.outcomes[-1].status == 'matured'


@pytest.mark.parametrize('case', ['empty_evidence', 'missing_model_version'])
def test_buy_provenance_required(case):
    b = sample()
    r = b['recommendations'][1]
    if case == 'empty_evidence':
        r['evidence'] = []
        r['rationale']['evidence_ids'] = []
        for group in ('entry', 'invalidation', 'review'):
            for condition in r['conditions'][group]:
                condition['evidence_ids'] = []
    else:
        r['versions']['model'] = None
    with pytest.raises(ValueError):
        validate_bundle(b)
