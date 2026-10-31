"""Recorded deterministic development evaluation; no provider or model runtime."""
import argparse,json,os
from pathlib import Path
import psycopg
from stock_discovery_contracts.v2 import check,digest
from stock_discovery_analysis.agent_evaluation import fraction,wilson
from worker.financial_span_evaluation import cases
from worker.financial_selection import run,EXACT_VERSION

ROOT=Path(__file__).resolve().parents[1]/'docs/research-quality'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();check(not args.output.exists(),'immutable_output_exists')
    url=os.environ['STK_TEST_DATABASE_URL'];check(psycopg.conninfo.conninfo_to_dict(url)['dbname']=='stk013_test','disposable_only')
    source=json.loads((ROOT/'sources/sec-infy-2025-revenue-excerpt.json').read_text())
    text=(ROOT/'sources/sec-infy-2025-revenue-excerpt.txt').read_text();data=cases(text,source['profile'])
    protocol=json.loads((ROOT/'M2-exact-selection-protocol.json').read_text());check(protocol['version']==EXACT_VERSION,'protocol_mismatch')
    check(protocol['cases']==[c['case_id'] for c in data],'case_plan_mismatch')
    with psycopg.connect(url,autocommit=True) as db:
        before=db.execute('SELECT count(*),coalesce(sum(units),0) FROM discovery.rag_reservations').fetchone()
        rows=[run(db,c,source=source,cutoff=source['captured_at']) for c in data]
        repeats=[run(db,c,source=source,cutoff=source['captured_at']) for c in data]
        check(rows==repeats,'non_idempotent_exact_result')
        after=db.execute('SELECT count(*),coalesce(sum(units),0) FROM discovery.rag_reservations').fetchone()
        check(before==after,'exact_route_changed_inference_budget')
    fields=('value','unit','scope','period','evidence_id','quote')
    correct=sum(r['accepted'] and all(r['proposal'][f]==c['expected'][f] for f in fields) for c,r in zip(data[:2],rows[:2]))
    abstained=sum(r['status']=='INSUFFICIENT_EVIDENCE' and not r['accepted'] and r['proposal'] is None for r in rows[2:])
    report=dict(version=EXACT_VERSION,protocol_hash=digest(protocol),source=source,dataset_hash=digest(data),cases=rows,
        human_verified=False,holdout_used=False,quality_accepted=False,model=None,prompt_hash=None,new_model_calls=0,new_reserved_units=0,
        historical_model_reservations='34 / 680000 units preserved in prior immutable reports; not reset or reclassified as this run',
        reservation_change=0,duplicate_result_identical=True,reference_kind='developer/parser reference; not human ground truth',
        metrics=dict(exact_positive_selection=fraction(correct,2),exact_negative_abstention=fraction(abstained,2),
            model_selection_accuracy=None,model_abstention_accuracy=None,positive_wilson95=wilson(correct,2),negative_wilson95=wilson(abstained,2)),
        limitations=['Four known development cases; deterministic reference checks are not independent human quality measurement.','Original-document/PIT/source qualification and semantic research remain unaccepted.'])
    with args.output.open('x') as out:out.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['metrics']))

if __name__=='__main__':main()
