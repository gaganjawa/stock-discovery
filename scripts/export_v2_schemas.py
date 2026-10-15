#!/usr/bin/env python3
"""Reproducible D3-01 JSON Schema export; --check is read-only for CI."""
import argparse
import json
from pathlib import Path

from stock_discovery_contracts.v2 import (
    Bundle, CohortSummary, Horizon, Outcome, Policy, Recommendation,
)

ROOT = Path(__file__).resolve().parents[1] / "docs/contracts/v2/schemas"
MODELS = (Bundle, CohortSummary, Horizon, Outcome, Policy, Recommendation)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for model in MODELS:
        payload = model.model_json_schema()
        payload["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path = ROOT / (model.__name__.lower() + "-2.0.0.schema.json")
        if args.check:
            if path.read_text() != content:
                raise SystemExit("Schema drift: " + str(path))
        else:
            ROOT.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print("PASS: six v2 schemas match typed contracts")


if __name__ == "__main__":
    main()
