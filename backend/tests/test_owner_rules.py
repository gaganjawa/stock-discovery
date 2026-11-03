"""STK-079 owner rules: decisions and gates never activate a rule on their own."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from stock_discovery_analysis.owner_rules import Decisions, evaluate, load_ruleset

AT = '2026-11-03T12:00:00Z'


def decisions(ruleset, *items, ruleset_hash=None):
    return Decisions(ruleset_id=ruleset.ruleset_id, ruleset_hash=ruleset_hash or ruleset.content_hash, signed_by='owner',
                     decisions=tuple(dict(rule_id=i, decision=d, value=v, decided_at=AT) for i, d, v in items))


def test_ruleset_matches_the_approval_sheet_and_starts_undecided():
    ruleset = load_ruleset()
    assert [r.id for r in ruleset.rules] == list(range(1, 30)) and ruleset.status == 'proposed'
    result = evaluate(ruleset)
    assert result['active'] == 0 and result['actionable'] is False and result['decision_file'] == 'absent'
    assert {r['state'] for r in result['rules']} == {'proposed_not_decided'}
    assert all(r['waiting_on'][0] == 'owner_approval' for r in result['rules'])


def test_approval_waits_for_every_gate_and_changes_keep_the_owner_value():
    ruleset = load_ruleset()
    owner = decisions(ruleset, (1, 'approve', None), (15, 'approve', None), (21, 'change', '15 bps adverse'), (23, 'defer', None))
    rows = {r['id']: r for r in evaluate(ruleset, owner, {'original_prices_qualified': False, 'owner_approval': True})['rules']}
    assert rows[1]['state'] == 'eligible_for_activation' and rows[1]['waiting_on'] == []
    assert rows[15]['state'] == 'approved_inactive' and rows[15]['waiting_on'] == ['original_prices_qualified']
    assert rows[21]['value'] == '15 bps adverse' and rows[21]['decision'] == 'change'
    assert rows[23]['state'] == 'deferred' and 'benchmark_source_permitted' in rows[23]['waiting_on']
    passed = {r['id']: r for r in evaluate(ruleset, owner, {'original_prices_qualified': True})['rules']}
    assert passed[15]['state'] == 'eligible_for_activation'


def test_decisions_for_another_version_are_ignored_and_bad_files_fail():
    ruleset = load_ruleset()
    stale = evaluate(ruleset, decisions(ruleset, (1, 'approve', None), ruleset_hash='older'))
    assert stale['decision_file'] == 'mismatched_version_ignored' and stale['rules'][0]['state'] == 'proposed_not_decided'
    with pytest.raises(ValueError, match='change_requires_value'):
        decisions(ruleset, (2, 'change', None))
    with pytest.raises(ValueError, match='duplicate_rule_decision'):
        evaluate(ruleset, decisions(ruleset, (2, 'approve', None), (2, 'defer', None)))
    with pytest.raises(ValueError, match='unknown_rule_decision'):
        evaluate(ruleset, decisions(ruleset, (99, 'approve', None)))


def test_rules_api_uses_private_decisions_and_live_database_gate(monkeypatch, tmp_path):
    from app import real_research
    ruleset = load_ruleset()
    path = tmp_path / 'decisions.json'; path.write_text(decisions(ruleset, (27, 'approve', None)).model_dump_json())
    gates = tmp_path / 'gates.json'; gates.write_text(json.dumps({'database_current': {'passed': True, 'evidence_ref': 'forged', 'recorded_at': AT}}))
    monkeypatch.setenv('AUTH_TOKEN', 'x' * 40); monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('REAL_RESEARCH_RULE_DECISIONS', str(path)); monkeypatch.setenv('REAL_RESEARCH_RULE_GATES', str(gates))
    monkeypatch.setattr(real_research, 'schema_state', lambda: dict(state='migration_required'))
    client = TestClient(app)
    assert client.get('/v1/real-research/rules').status_code == 401
    client.post('/api/v1/session', json={'token': 'x' * 40})
    response = client.get('/v1/real-research/rules'); body = response.json()
    assert response.headers['cache-control'] == 'no-store' and body['active'] == 0
    # The live schema check overrides any recorded database gate.
    assert body['rules'][26]['state'] == 'approved_inactive' and body['rules'][26]['waiting_on'] == ['database_current']
    monkeypatch.setattr(real_research, 'schema_state', lambda: dict(state='current'))
    assert client.get('/v1/real-research/rules').json()['rules'][26]['state'] == 'eligible_for_activation'
