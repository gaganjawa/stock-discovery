"""Development extraction diagnostics; reuses existing evaluation statistics.

No human-ground-truth assertion, holdout access, strategy promotion or trading.
Full failed calls and abstentions remain in denominators.
"""
from decimal import Decimal,InvalidOperation
from .agent_evaluation import fraction,wilson
from stock_discovery_contracts.v2 import check,digest


def score_rows(rows,*,dataset_hash,protocol_hash):
    check(len({r['case_id'] for r in rows})==len(rows),'duplicate_evaluation_case')
    positive=[r for r in rows if r['expected'] is not None]
    negative=[r for r in rows if r['expected'] is None]
    def same(r,field):
        p=r.get('proposal') or {};e=r['expected']
        if r.get('error') or p.get('status')!='extracted':return False
        if field=='value':
            try:return isinstance(p.get(field),str) and Decimal(p[field])==Decimal(e[field])
            except (InvalidOperation,ValueError,TypeError):return False
        return p.get(field)==e[field]
    accepted=[r for r in rows if r['accepted']]
    correct=[r for r in accepted if r['expected'] is not None and all(same(r,f) for f in ('value','unit','scope','period','evidence_id','quote'))]
    abstained=lambda r:(r.get('proposal') or {}).get('status')=='insufficient_evidence' and not r.get('error')
    metrics={name:fraction(sum(same(r,field) for r in positive),len(positive)) for name,field in
        [('numeric_accuracy','value'),('unit_accuracy','unit'),('period_accuracy','period'),('citation_identity','evidence_id'),('source_span_support','quote')]}
    metrics.update(extraction_recall=fraction(sum(r in correct for r in positive),len(positive)),
        unsupported_accepted=fraction(len(accepted)-len(correct),len(accepted)),
        required_abstention=fraction(sum(abstained(r) for r in negative),len(negative)),
        runtime_failure=fraction(sum(bool(r.get('error')) for r in rows),len(rows)))
    metrics['citation_support']=fraction(sum(all(same(r,f) for f in ('value','unit','scope','period','evidence_id','quote')) for r in positive),len(positive))
    conflicts=[r for r in negative if r['case_id']=='conflict']
    metrics['contradiction_abstention']=fraction(sum(abstained(r) for r in conflicts),len(conflicts))
    metrics['abstention_status_only']=fraction(sum((r.get('proposal') or {}).get('status')=='insufficient_evidence' for r in negative),len(negative))
    report=dict(run_kind='development',human_verified=False,holdout_used=False,quality_accepted=False,
        strategy_promotion=False,dataset_hash=dataset_hash,protocol_hash=protocol_hash,cases=len(rows),
        metrics=metrics,counts=dict(positive=len(positive),negative=len(negative),accepted=len(accepted),correct_accepted=len(correct)),
        abstention_wilson95=wilson(sum(abstained(r) for r in negative),len(negative)),
        limitations=['Developer/parser references are not independently human-verified labels.',
            'Field metrics include failed/abstained positive cases; unsupported acceptance uses accepted claims only.',
            'Required abstention is strict response-contract validity; status-only abstention is reported separately.',
            'runtime_failure includes response-contract and JSON errors, not just server failures.',
            'Field accuracy includes non-extraction on positive cases; it does not imply every failure was a wrong numeric prediction.',
            'Small development samples cannot establish general financial accuracy or model superiority.'])
    return dict(report,report_hash=digest(report))
