import json
from pathlib import Path
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze
from stock_discovery_analysis.risk import sizing


def test_buy_wait_insufficient_and_future_mutation():
    d=demo_dataset()
    def result(index,data=d):
        return analyze(data,'SYN-ALPHA',d.calendar.sessions[index].closes_at+timedelta(minutes=1),code_version='test',generated_at=d.candles[-1].provenance.fetched_at)
    buy=result(39)
    assert buy['recommendation']['action']=='BUY'
    assert buy['sizing']['risk_reward']==2
    assert buy['recommendation']['earliest_executable_entry_at']>buy['recommendation']['decision_available_at']
    assert buy['recommendation']['rationale']['summary'].count(': met')==3
    wait=result(38)['recommendation']
    assert wait['action']=='WAIT'
    assert ': not met' in wait['rationale']['summary']
    assert 'not eligible' in result(2)['recommendation']['rationale']['summary']
    assert result(2)['recommendation']['action']=='INSUFFICIENT_EVIDENCE'
    cutoff=d.calendar.sessions[39].closes_at
    changed=replace(d,candles=tuple(replace(c,close=c.low) if c.ends_at>cutoff else c for c in d.candles))
    other=result(39,changed)
    for field in ('indicators','sizing'): assert other[field]==buy[field]
    for field in ('action','execution','forecast','rationale'): assert other['recommendation'][field]==buy['recommendation'][field]


def test_sizing_matches_unchanged_contract_reference_and_caps():
    f=json.loads((Path(__file__).resolve().parents[2]/'docs/contracts/examples/capital-risk.synthetic.json').read_text())
    r=sizing(f['sizing'])
    for key,value in r.items(): assert value==D(f['expected'][key])
    assert r['quantity']==20 and r['planned_loss']==D(106)
    assert sizing(f['sizing'],paused=True)['quantity']==0
    assert sizing(f['sizing'],marks_fresh=False)['quantity']==0
    assert sizing(dict(f['sizing'],spendable_cash='0'))['quantity']==0
