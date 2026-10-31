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


def test_abstention_context_preserves_conflict_and_missing_period():
    from worker.financial_selection import selection_request
    rows=fixture()
    for i in (2,3):
        c=rows[i];cells=candidates(c);request=json.loads(selection_request(c,cells))
        assert request['schema']['properties']['cell_id']['enum'][0]=='ABSTAIN'
        # All other selectable cells remain; the grammar does not force abstention.
        assert len(request['schema']['properties']['cell_id']['enum'])>1
        assert 'expected' not in request['bundle']
        if i==2:assert c['period'] not in request['bundle']['available_periods']
        else:assert request['bundle']['source_row_counts']['Total revenue from operations']==2
        proposal,accepted=resolve('{"cell_id":"ABSTAIN"}',c,cells)
        assert proposal['status']=='insufficient_evidence' and not accepted
        wrong=next(iter(cells))
        with pytest.raises(ValueError):resolve(json.dumps({'cell_id':wrong}),c,cells)


def test_positive_context_has_unique_source_row_and_exact_period():
    from worker.financial_selection import selection_request
    for c in fixture()[:2]:
        r=json.loads(selection_request(c,candidates(c)))['bundle']
        assert r['source_row_counts']['Total revenue from operations']==1
        assert c['period'] in r['available_periods']


def test_exact_annual_and_quarter_cells_do_not_depend_on_gold_or_model():
    from worker.financial_selection import exact_selection
    case=fixture()[0];case={**case,'expected':{'value':'invented gold'}}
    for period,value in [('Year ended March 31, 2025','162990'),('Year ended March 31, 2024','153670'),('Three months ended March 31, 2025','40925'),('Three months ended March 31, 2024','37923')]:
        r=exact_selection(case,row_label='Total revenue from operations',period=period,scope='consolidated')
        assert r['accepted'] and r['proposal']['value']==value and r['proposal']['period']==period
        assert r['citation']['source_hash']==case['profile']['text_hash'] and not r['actionable']


@pytest.mark.parametrize('variant',['missing_period','conflicting','duplicate','scope','unit','snapshot','label','headers'])
def test_exact_uncertainty_abstains_without_semantic_guess(variant):
    from copy import deepcopy
    from stock_discovery_contracts.v2 import digest
    from worker.financial_selection import exact_selection
    case=deepcopy(fixture()[0]);scope='consolidated';label='Total revenue from operations'
    if variant=='missing_period':case=fixture()[2]
    if variant=='conflicting':case=fixture()[3]
    if variant=='duplicate':
        case['text']+=case['text'].splitlines()[-1]+'\n';case['profile']['text_hash']=digest(case['text'])
    if variant=='scope':scope='standalone'
    if variant=='unit':case['profile']['unit']='UNKNOWN'
    if variant=='snapshot':case['text']+='modified'
    if variant=='label':label='revenue synonym not authenticated'
    if variant=='headers':
        case['text']=case['text'].replace('2025 | 2024 | 2025 | 2024','2025 | 2025 | 2025 | 2025');case['profile']['text_hash']=digest(case['text'])
    r=exact_selection(case,row_label=label,period=case['period'],scope=scope)
    assert r['status']=='INSUFFICIENT_EVIDENCE' and not r['accepted'] and r['proposal'] is None
