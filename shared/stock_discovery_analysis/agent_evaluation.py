"""Paired offline fault-injection evaluation; never a promotion/calibration gate."""
import math
import time
from .agent_fixtures import labelled_cases,case_bundle,candidate_assessment,ScenarioAgent,FixtureTools
from .agent_research import investigate,MockJudge,encode,AGENT_PROMPT_HASH,JUDGE_PROMPT_HASH
from .agent_contracts import AgentPolicy,Rubric
from .rag_contracts import Assessment,Budget
from .rag_research import validate_assessment,PROMPT,PROMPT_HASH
from stock_discovery_contracts.v2 import digest


def fraction(n,d):
    return {'numerator':n,'denominator':d,'value':n/d if d else None}


def wilson(n,d):
    if not d:return None
    z=1.959963984540054
    p=n/d;den=1+z*z/d
    center=(p+z*z/(2*d))/den
    radius=z*math.sqrt(p*(1-p)/d+z*z/(4*d*d))/den
    return [max(0,center-radius),min(1,center+radius)]


def fixed_case(bundle,scenario):
    """D3-07 one-response/early-abstention policy using its actual validator.

    Offline fixture adapter substitutes deliberately faulty model JSON. Database,
    ingestion and scheduler latency are excluded from both arms.
    """
    start=time.perf_counter();units=0
    try:
        if bundle.missing or bundle.contradictions:
            raw=Assessment(issuer_id=bundle.query.issuer_id,horizon=bundle.query.horizon,action='INSUFFICIENT_EVIDENCE',
                claims=(),missing=bundle.missing,contradictions=bundle.contradictions).model_dump_json()
        else:
            request=encode({'instruction':PROMPT,'bundle':bundle.model_dump(mode='json'),'schema':Assessment.model_json_schema()})
            raw=candidate_assessment(bundle,scenario)
            units=len(request.encode())+len(raw.encode())
        final,validator=validate_assessment(raw,bundle)
        result={'assessment':final.model_dump(mode='json'),'action':final.action,'validator':validator,'judge':None}
    except ValueError:
        result={'assessment':None,'action':'INSUFFICIENT_EVIDENCE','validator':{'deterministic':'failed'},'judge':None}
    result.update(accounting={'latency_ms':(time.perf_counter()-start)*1000,'units':units,'actual_cost':'0'})
    return result


def measure(case,bundle,result):
    a=result.get('assessment') or {}
    claims=a.get('claims',[])
    judgments={j['claim_index']:j['support'] for j in (result.get('judge') or {}).get('claims',[])}
    correct=known=0
    for i,claim in enumerate(claims):
        expected=case['scenario'] not in ('fabricated_citation','incorrect_calculation','unsupported_causal')
        predicted=judgments.get(i)
        if predicted is None and result['validator']['deterministic']=='passed' and claim['kind']!='inference':predicted='supported'
        if predicted in ('supported','unsupported'):
            known+=1;correct+=int((predicted=='supported')==expected)
    abstained=result['action']=='INSUFFICIENT_EVIDENCE'
    negative=bool(a.get('contradictions') or 'category:news' in a.get('missing',[]))
    return dict(case_id=case['case_id'],split=case['split'],horizon=case['horizon'],scenario=case['scenario'],
        claim_labels=len(claims),support_known=known,support_correct=correct,
        material_error=case['material_error'],material_false_accept=case['material_error'] and not abstained,
        expected_abstention=case['expected_abstention'],abstained=abstained,
        negative_required=case['negative_evidence_required'],negative_detected=negative,
        requirement_coverage=bundle.coverage,latency_ms=result['accounting']['latency_ms'],
        units=result['accounting']['units'],actual_cost=result['accounting']['actual_cost'])


def aggregate(rows):
    material=[r for r in rows if r['material_error']]
    negative=[r for r in rows if r['negative_required']]
    accepted_errors=sum(r['material_false_accept'] for r in material)
    positive=[r for r in rows if not r['expected_abstention']]
    return dict(cases=len(rows),claim_support_accuracy=fraction(sum(r['support_correct'] for r in rows),sum(r['support_known'] for r in rows)),
        claim_support_classification_coverage=fraction(sum(r['support_known'] for r in rows),sum(r['claim_labels'] for r in rows)),
        material_error_false_acceptance=fraction(accepted_errors,len(material)),material_error_false_acceptance_wilson95=wilson(accepted_errors,len(material)),
        negative_evidence_detection=fraction(sum(r['negative_detected'] for r in negative),len(negative)),
        abstention_quality=fraction(sum(r['abstained']==r['expected_abstention'] for r in rows),len(rows)),
        false_rejection=fraction(sum(r['abstained'] for r in positive),len(positive)),
        mean_requirement_coverage=sum(float(r['requirement_coverage']) for r in rows)/len(rows),
        total_latency_ms=sum(r['latency_ms'] for r in rows),mean_latency_ms=sum(r['latency_ms'] for r in rows)/len(rows),
        model_units=sum(r['units'] for r in rows),actual_model_cost_usd='0')


def evaluate(cases=None):
    cases=cases or labelled_cases()
    rows={'fixed_rag':[],'bounded_agent':[]}
    for case in cases:
        bundle=case_bundle(case)
        fixed=fixed_case(bundle,case['scenario'])
        agent,_=investigate(bundle,policy=AgentPolicy(),budget=Budget(account='SYN-evaluation',max_run_units=500000),
            provider=ScenarioAgent(case['scenario']),judge=MockJudge(),rubric=Rubric(),tools=FixtureTools(),guard=lambda b:None)
        assert agent['baseline_hash']==bundle.content_hash
        rows['fixed_rag'].append(measure(case,bundle,fixed))
        rows['bounded_agent'].append(measure(case,bundle,agent))
    return dict(schema_version='1.0.0',dataset_hash=digest(cases),label_source='synthetic_rule_authored',
        human_reviewed=False,calibration_approved=False,superiority_claim=False,run_kind='offline_mock_fault_injection',
        rubric=Rubric().ref.model_dump(),
        configuration={'fixed_adapter':'SYN-fault-injection-fixed-v1','fixed_prompt_hash':PROMPT_HASH,
            'agent':ScenarioAgent.ref.model_dump(),'judge':MockJudge.ref.model_dump(),
            'agent_prompt_hash':AGENT_PROMPT_HASH,'judge_prompt_hash':JUDGE_PROMPT_HASH,
            'policy':AgentPolicy().ref.model_dump(),'tools':'SYN-fixture-read-only-v1'},
        limitations=['Template-generated synthetic cases are not independent market samples.',
            'Fixture tools cannot discover new real evidence; this evaluates safeguards, not research efficacy.',
            'The conservative mock judge rejects inference by construction; these are not LLM accuracy results.',
            'Latency is observed local controller time; excludes database, ingestion and network.',
            'False acceptance refers to a shadow WATCH candidate, never actionable BUY or paper admission.',
            'Claim accuracy covers classified emitted claims; abstained/unclassified claims are reported separately.',
            'Human labels, reviewer disagreement/adjudication, independent model qualification and frozen acceptance thresholds remain absent.'],
        arms={arm:{'overall':aggregate(items),'by_split':{split:aggregate([r for r in items if r['split']==split]) for split in ('development','holdout') if any(r['split']==split for r in items)},'cases':items} for arm,items in rows.items()})
