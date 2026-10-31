"""Explicit bounded successor to the preserved M2 span experiment."""
import argparse,json,os
from pathlib import Path
import psycopg
from stock_discovery_contracts.v2 import check,digest
from stock_discovery_analysis.rag_research import reserve
from stock_discovery_analysis.financial_evaluation import score_rows
from worker.financial_span_evaluation import cases,BUDGET
from worker.financial_selection import run,PROMPT_HASH,VERSION
from worker.providers.ollama import Ollama

ROOT=Path(__file__).resolve().parents[1]/'docs/research-quality'

def main():
    check(os.environ.get('STK_EXECUTE_HYBRID')=='1','explicit_local_execution_required')
    url=os.environ['STK_TEST_DATABASE_URL'];check(psycopg.conninfo.conninfo_to_dict(url)['dbname']=='stk013_test','disposable_only')
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text())
    check(protocol['prompt_hash']==PROMPT_HASH and protocol['version']==VERSION,'protocol_mismatch')
    check(protocol['models']==['qwen2.5-coder:7b'] and protocol['maximum_new_calls']==4,'bounded_comparison_required')
    output=args.output;check(not output.exists(),'immutable_output_exists')
    source=json.loads((ROOT/'sources/sec-infy-2025-revenue-excerpt.json').read_text());text=(ROOT/'sources/sec-infy-2025-revenue-excerpt.txt').read_text()
    data=cases(text,source['profile']);budget=BUDGET.model_copy(update={'max_day_units':680000})
    check(protocol['budget']==budget.model_dump(),'budget_mismatch')
    check(protocol['cases']==[c['case_id'] for c in data],'case_plan_mismatch')
    report=dict(protocol=protocol,source=source,models=[],human_verified=False,quality_accepted=False,holdout_used=False)
    with psycopg.connect(url,autocommit=True) as db:
        # Reconstitute prior immutable reservations in this disposable database;
        # never erase/reset those costs to obtain a fresh daily allowance.
        for filename in ['M2-span-actual-development.json','M2-span-serialization-diagnostic.json','M2-hybrid-actual-development.json','M2-hybrid-v2-actual-development.json','M2-hybrid-v3-actual-development.json']:
            old=json.loads((ROOT/filename).read_text())
            for m in old['models']:
                for c in m['cases']:
                    prefix='M2-DEV-SPAN-' if filename.startswith('M2-span-') else 'M2-HYBRID-'
                    reserve(db,prefix+c['request_hash'],c['request_hash'],budget,c['cutoff_at'])
        check(db.execute("SELECT count(*) FROM discovery.rag_reservations WHERE run_id LIKE 'M2-HYBRID-%'").fetchone()[0]>=20,'prior_hybrid_reservations_required')
        for name in protocol['models']:
            provider=Ollama(name,context=16384,max_input_bytes=32768,max_model_bytes=7_000_000_000)
            try:
                rows=[]
                for case in data:
                    rows.append(run(db,case,source=source,cutoff=source['captured_at'],provider=provider,budget=budget,selection_mode='model'))
                    report['current_partial']=dict(model=name,cases=rows)
                    output.write_text(json.dumps(report,indent=2)+'\n')
                report['models'].append(dict(model=provider.ref.model_dump(),cases=rows,usage=provider.usage,
                    metrics=score_rows(rows,dataset_hash=digest(data),protocol_hash=digest(protocol))))
                del report['current_partial']
            finally:provider.close()
            output.write_text(json.dumps(report,indent=2)+'\n')
        report['total_preserved_reservations']=[int(x) for x in db.execute('SELECT count(*),sum(units) FROM discovery.rag_reservations').fetchone()]
        output.write_text(json.dumps(report,indent=2)+'\n')
    print([(m['model']['id'],[(c['case_id'],c['accepted'],c['error'],c['raw_response']) for c in m['cases']]) for m in report['models']])

if __name__=='__main__':main()
