"""Explicit local development inference on a registered public excerpt.

Uses ONLY an already migrated disposable stk013_test DB; never production data.
No download, paid API, holdout access, promotion or source grant activation.
"""
import argparse,json,os
from pathlib import Path
import psycopg
from stock_discovery_contracts.v2 import digest,check
from stock_discovery_analysis.publication_store import now
from stock_discovery_analysis.financial_evaluation import score_rows
from worker.providers.ollama import Ollama
from worker.financial_span_evaluation import cases,run_case,PROMPT_HASH,BUDGET


class DiagnosticOllama(Ollama):
    def assess(self,*args,**kwargs):
        self.last_response=None
        return super().assess(*args,**kwargs)
    def _call(self,method,path,body,deadline):
        result=super()._call(method,path,body,deadline)
        if method=='POST' and path=='/api/generate':
            text=result.get('response')
            self.last_response=text[:1800] if isinstance(text,str) else None
        return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--execute-local-development',action='store_true',required=True)
    p.add_argument('--models',nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    args=p.parse_args();check(len(args.models)<=2 and len(set(args.models))==len(args.models),'bounded_model_count')
    check(not args.output.exists(),'evaluation_output_already_exists')
    root=Path(__file__).resolve().parents[1];folder=root/'docs/research-quality'
    source=json.loads((folder/'sources/sec-infy-2025-revenue-excerpt.json').read_text())
    text=(folder/'sources/sec-infy-2025-revenue-excerpt.txt').read_text();dataset=cases(text,source['profile'])
    protocol=json.loads(args.protocol.read_text())
    check(protocol['prompt_hash']==PROMPT_HASH,'prompt_changed_requires_new_protocol')
    dataset=[c for c in dataset if c['case_id'] in protocol['cases']]
    check(len(dataset)*len(args.models)<=protocol['maximum_inference_calls'],'protocol_call_bound')
    check(args.models==protocol['models'],'model_plan_changed')
    dev=(folder/'M2-financial-review-packet.json').read_bytes();cutoff=protocol['cutoff_at']
    url=os.environ['STK_TEST_DATABASE_URL'];check(psycopg.conninfo.conninfo_to_dict(url)['dbname']=='stk013_test','disposable_database_required')
    report=dict(kind='actual_local_development_span_evaluation',human_verified=False,holdout_used=False,quality_accepted=False,
        source=source,dataset_hash=digest(dataset),protocol_hash=digest(protocol),prompt_hash=PROMPT_HASH,cutoff_at=cutoff,
        existing_development_packet_sha256=__import__('hashlib').sha256(dev).hexdigest(),models=[])
    with psycopg.connect(url,autocommit=True) as conn:
        for model in args.models:
            provider=DiagnosticOllama(model,context=16384,max_input_bytes=32768,max_model_bytes=7_000_000_000)
            try:
                rows=[run_case(conn,c,source=source,cutoff=cutoff,provider=provider) for c in dataset]
                report['models'].append(dict(model=provider.ref.model_dump(),cases=rows,usage=provider.usage,
                    metrics=score_rows(rows,dataset_hash=digest(dataset),protocol_hash=digest(protocol))))
            finally:provider.close()
            args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{'model':m['model']['id'],'metrics':m['metrics']['metrics'],'counts':m['metrics']['counts']} for m in report['models']]))

if __name__=='__main__':main()
