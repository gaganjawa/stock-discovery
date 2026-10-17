"""Generate new D3-08 mock evaluation artifacts; no provider or credentials used."""
import argparse
import json
from pathlib import Path
from stock_discovery_analysis.agent_fixtures import labelled_cases
from stock_discovery_analysis.agent_evaluation import evaluate


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=labelled_cases()
    for name,value in (('labels.json',cases),('mock-results.json',evaluate(cases))):
        (args.output_dir/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(f'Wrote {len(cases)} provisional synthetic cases and measured mock comparisons to {args.output_dir}')


if __name__=='__main__':main()
