"""Opt-in genuine local inference smoke; no model downloads or qualification.

Run in a native worker environment with PYTHONPATH=shared:worker. Exit nonzero
on an unavailable model or unsupported output. This is not financial calibration.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from worker.providers.ollama import Ollama


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source='https://www.sec.gov/Archives/edgar/data/1067491/000095017025091925/infy-20250331.htm'
    quote='We were incorporated on July 2, 1981, in Pune, Maharashtra, India, as Infosys Consultants Private Limited'
    schema={'type':'object','properties':{'quote':{'type':'string'},'citation':{'type':'string'},'action':{'type':'string','enum':['INSUFFICIENT_EVIDENCE']}},'required':['quote','citation','action'],'additionalProperties':False}
    request=json.dumps(dict(instruction='Copy the exact provided quote and citation. There are no prices or financial metrics. Abstain from investment advice.',schema=schema,source=dict(quote=quote,citation=source)))
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'local_protocol_smoke_only','financial_qualification':'unqualified','source_url':source,'automated_filing_ingestion':False}
    model=Ollama('qwen2.5-coder:7b')
    try:
        raw=model.assess(request,max_output_units=2048,deadline=time.monotonic()+120)
        data=json.loads(raw)
        assert data==dict(quote=quote,citation=source,action='INSUFFICIENT_EVIDENCE'), 'unsupported claim or citation'
        result.update(generation='passed',model=model.ref.model_dump(),output=data,usage=model.usage)
    finally:model.close()
    embedder=Ollama('nomic-embed-text:latest',context=2048,max_input_bytes=2048)
    try:
        vectors=embedder.embed((quote,),deadline=time.monotonic()+60)
        result.update(embeddings='passed',embedding_model=embedder.ref.model_dump(),dimensions=len(vectors[0]),embedding_usage=embedder.usage)
    finally:embedder.close()
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
