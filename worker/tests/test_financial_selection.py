import json
from pathlib import Path
import pytest
from worker.financial_span_evaluation import cases
from worker.financial_selection import candidates,resolve
from worker.providers.table_spans import verify_cell


def fixture():
    p=Path(__file__).resolve().parents[2]/'docs/research-quality/sources'
    s=json.loads((p/'sec-infy-2025-revenue-excerpt.json').read_text())
    return cases((p/'sec-infy-2025-revenue-excerpt.txt').read_text(),s['profile'])


@pytest.mark.parametrize('index',range(4))
def test_selection_and_abstention(index):
    c=fixture()[index];cells=candidates(c)
    chosen=next((k for k,v in cells.items() if v==c['expected']),'')
    p,accepted=resolve(json.dumps({'cell_id':chosen}),c,cells)
    assert accepted==(index<2)
    if accepted:
        assert p['value']==c['expected']['value']
        for field,value in [('value','999'),('evidence_id','invented'),('period','future')]:
            with pytest.raises(ValueError):verify_cell({**p,field:value},c['expected'])


def test_wrong_row_period_fabrication_and_schema():
    c=fixture()[0];cells=candidates(c)
    wrong=next(k for k,v in cells.items() if v!=c['expected'])
    for raw in [json.dumps({'cell_id':wrong}),json.dumps({'cell_id':'invented'}),json.dumps({'cell_id':'','value':'999'}),'{}']:
        with pytest.raises(ValueError):resolve(raw,c,cells)


def test_report_never_presents_rejected_claims():
    from worker.financial_selection import research_report
    rows=fixture()
    for case in rows[2:]:
        for raw in ['{"cell_id":"invented"}','{"cell_id":""}','broken JSON']:
            result=research_report(case,raw)
            assert result['status']=='INSUFFICIENT_EVIDENCE' and result['findings']==[] and not result['actionable']
    case=rows[0];key=next(k for k,v in candidates(case).items() if v==case['expected'])
    report=research_report(case,json.dumps({'cell_id':key}))
    assert report['findings'][0]['value']=='162990' and not report['actionable']
