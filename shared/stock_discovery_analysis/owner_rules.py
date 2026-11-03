"""STK-079: versioned owner starting rules; decisions never activate a rule by themselves.

A rule is only 'eligible_for_activation' when the owner approved this exact ruleset
version and every named gate has recorded passing evidence. Activation itself stays
a separate, explicit policy registration.
"""
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field, model_validator
from stock_discovery_contracts.v2 import Strict, Text, Timestamp, check, digest

GATES = ('owner_approval', 'database_current', 'forward_paper_authorized', 'original_prices_qualified',
         'filing_rights_and_timestamps', 'benchmark_source_permitted', 'independent_ai_review')
Gate = Literal[GATES]
RULESET = Path(__file__).with_name('owner_starting_rules_1_0_0.json')


class Rule(Strict):
    id: Annotated[int, Field(gt=0)]
    section: Text
    rule: Text
    proposed: Text
    gates: Annotated[tuple[Gate, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def owner_gate(self):
        check('owner_approval' in self.gates and len(set(self.gates)) == len(self.gates), 'owner_gate_required')
        return self


class RuleSet(Strict):
    schema_version: Literal['1.0.0']
    ruleset_id: Text
    version: Text
    status: Literal['proposed']
    source: Text
    rules: Annotated[tuple[Rule, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def unique(self):
        check(len({r.id for r in self.rules}) == len(self.rules), 'duplicate_rule_id')
        return self

    @property
    def content_hash(self):
        return digest(self.model_dump(mode='json'))


class Decision(Strict):
    rule_id: Annotated[int, Field(gt=0)]
    decision: Literal['approve', 'change', 'defer']
    value: Text | None = None
    decided_at: Timestamp

    @model_validator(mode='after')
    def changed_value(self):
        check((self.decision == 'change') == (self.value is not None), 'change_requires_value')
        return self


class Decisions(Strict):
    ruleset_id: Text
    ruleset_hash: Text
    signed_by: Text
    decisions: tuple[Decision, ...]


class GateEvidence(Strict):
    passed: bool
    evidence_ref: Text
    recorded_at: Timestamp


def load_ruleset(path=RULESET):
    return RuleSet.model_validate_json(Path(path).read_text())


def evaluate(ruleset, decisions=None, gates=None):
    """Return each rule's state; a decision file for another version is ignored, never merged."""
    gates = {k: v for k, v in (gates or {}).items() if k != 'owner_approval'}
    mismatch = decisions is not None and (decisions.ruleset_id, decisions.ruleset_hash) != (ruleset.ruleset_id, ruleset.content_hash)
    chosen = {} if decisions is None or mismatch else {d.rule_id: d for d in decisions.decisions}
    check(len(chosen) == (0 if decisions is None or mismatch else len(decisions.decisions)), 'duplicate_rule_decision')
    check(set(chosen) <= {r.id for r in ruleset.rules}, 'unknown_rule_decision')
    rows = []
    for rule in ruleset.rules:
        d = chosen.get(rule.id)
        waiting = [g for g in rule.gates if g != 'owner_approval' and not gates.get(g)]
        if d is None:state, waiting = 'proposed_not_decided', ['owner_approval', *waiting]
        elif d.decision == 'defer':state, waiting = 'deferred', ['owner_approval', *waiting]
        else:state = 'approved_inactive' if waiting else 'eligible_for_activation'
        rows.append(dict(id=rule.id, section=rule.section, rule=rule.rule, value=d.value if d and d.value else rule.proposed,
                         decision=d.decision if d else None, state=state, waiting_on=waiting))
    return dict(ruleset_id=ruleset.ruleset_id, version=ruleset.version, ruleset_hash=ruleset.content_hash,
                decision_file='mismatched_version_ignored' if mismatch else 'absent' if decisions is None else 'applied',
                rules=rows, active=0, actionable=False)


def private_gates(path):
    if not path:return {}
    raw = json.loads(Path(path).read_text())
    return {k: GateEvidence.model_validate(v).passed for k, v in raw.items() if k in GATES}
