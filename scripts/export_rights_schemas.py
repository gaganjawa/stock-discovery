#!/usr/bin/env python3
"""D3-02 strict rights schema export; --check detects contract drift."""
import argparse
import json
from pathlib import Path

from stock_discovery_contracts.rights import Grant, UseRequest, GrantDecision, CleanupPlan

ROOT = Path(__file__).resolve().parents[1] / 'docs/contracts/rights'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for model in (Grant, UseRequest, GrantDecision, CleanupPlan):
        schema = model.model_json_schema()
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        content = json.dumps(schema, indent=2, sort_keys=True) + '\n'
        path = ROOT / (model.__name__.lower() + '-1.0.0.schema.json')
        if args.check:
            if path.read_text() != content:
                raise SystemExit('Schema drift: ' + str(path))
        else:
            path.write_text(content)
    print('PASS: four rights schemas match contracts')


if __name__ == '__main__':
    main()
