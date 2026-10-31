from pathlib import Path
import json
import pytest
from stock_discovery_contracts.v2 import digest
from worker.providers.table_spans import cell_reference,verify_cell

ROOT=Path(__file__).resolve().parents[2]/'docs/research-quality/sources'


def source():return (ROOT/'sec-infy-2025-revenue-excerpt.txt').read_text(),json.loads((ROOT/'sec-infy-2025-revenue-excerpt.json').read_text())['profile']


def test_quarter_versus_annual_and_thousands_are_not_spliced():
    text,p=source()
    for period,value in [('Year ended March 31, 2025','162990'),('Year ended March 31, 2024','153670'),('Three months ended March 31, 2025','40925')]:
        r=cell_reference(text,p,'Total revenue from operations',period)
        assert r['value']==value
        proposal=dict(status='extracted',**{k:r[k] for k in ('value','unit','scope','period','evidence_id','quote')})
        assert verify_cell(proposal,r)['validation']=='exact_table_cell_and_span'
        with pytest.raises(ValueError):verify_cell(dict(proposal,period='Year ended March 31, 2027'),r)


def test_changed_missing_and_conflicting_spans_fail_closed():
    text,p=source()
    with pytest.raises(ValueError):cell_reference(text+'change',p,'Total revenue from operations','Year ended March 31, 2025')
    with pytest.raises(ValueError):cell_reference(text,p,'Total revenue from operations','Year ended March 31, 2027')
    conflict=text+'Total revenue from operations | 1 | 2 | 3 | 4\n';p={**p,'text_hash':digest(conflict)}
    with pytest.raises(ValueError,match='conflicting'):cell_reference(conflict,p,'Total revenue from operations','Year ended March 31, 2025')
