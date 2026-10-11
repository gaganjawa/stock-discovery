import json
from pathlib import Path
from stock_discovery_analysis.evaluation import summarize,portfolio


def test_original_contract_metric_parity(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    import validate_evaluation_examples as original
    data=[original.parse((original.ROOT/n).read_text()) for n in
          ('recommendations.synthetic.json','observations.synthetic.json','forecast-outcomes.synthetic.json','trade-outcomes.synthetic.json')]
    rows=original.original_rows(data)
    assert summarize(rows)==original.summarize(rows)
    curve=[{'at':'2025-01-01T00:00:00Z','cash':'500','positions':[{'quantity':'5','mark':'100'}],'external_flow':'0'},
           {'at':'2025-01-02T00:00:00Z','cash':'1000','positions':[{'quantity':'5','mark':'140'}],'external_flow':'500'},
           {'at':'2025-01-03T00:00:00Z','cash':'800','positions':[{'quantity':'5','mark':'72'}],'external_flow':'-200'},
           {'at':'2025-01-04T00:00:00Z','cash':'800','positions':[{'quantity':'5','mark':'95.20'}],'external_flow':'0'}]
    assert portfolio(curve)==original.portfolio(curve)
