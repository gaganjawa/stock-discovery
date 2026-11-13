"""Observed provider Test shape with URL/identity redacted; live values invented."""
import json
from pathlib import Path
import pytest
from test_chartink import scanner,NOW
from stock_discovery_analysis.chartink import normalize


def provider_payload():
    return json.loads((Path(__file__).parent/'fixtures/chartink_provider_test_v1.json').read_text())


def candidate_payload():
    # Same observed wire container/keys. Domain-valid invented values, not a live receipt.
    p=provider_payload();p.update(stocks='SYN095',trigger_prices='100')
    row={k:100 for k in p['columns'][0]}
    row.update(symbol='syn095',close=100,sector='Synthetic',industry='Invented',marketcapname='Test',rsi14=60)
    p['columns']=[row]
    return p


def test_observed_provider_test_is_not_candidate_evidence():
    p=provider_payload();s=scanner().model_copy(update={'mode':'provider_alert'})
    e=normalize(p,s,NOW)
    assert e['version']=='chartink-provider-test-v1' and e['symbols']==[]
    assert e['delivery_kind']=='provider_test' and 'enrichment' not in e
    assert not e['evaluation_eligible'] and not e['historical_pit_qualified']
    assert 'webhook_url' not in e['payload'] and 'REDACTED' not in json.dumps(e)
    assert normalize(e['payload'],s,NOW)==e
    assert normalize(p,s,NOW.replace(minute=1))['event_id']==e['event_id']


def test_columns_version_alignment_provenance_and_dedupe():
    p=candidate_payload();e=normalize(p,scanner(),NOW)
    assert e['version']=='chartink-event-columns-v1' and e['adapter_version']=='chartink-columns-v1'
    assert e['symbols']==['SYN095']
    row=e['enrichment']['SYN095']
    assert row['values']['rsi14']=='60' and row['field_provenance']['ema10']==['EMA10']
    assert row['field_states']['atr14']=='period_unverified' and row['values']['atr14'] is None
    assert normalize(e['payload'],scanner(),NOW)==e
    assert normalize({**p,'webhook_url':'https://different.invalid/SECRET'},scanner(),NOW)['event_id']==e['event_id']
    p['columns'][0]['volume']=101
    assert normalize(p,scanner(),NOW)['event_id']!=e['event_id']


@pytest.mark.parametrize('change',[
    lambda p:p.update(columns=None),lambda p:p.update(columns={}),lambda p:p.update(columns=[]),
    lambda p:p['columns'].append(p['columns'][0]),lambda p:p['columns'][0].pop('close'),
    lambda p:p['columns'][0].update(unknown=1),lambda p:p['columns'][0].update(symbol='OTHER'),
    lambda p:p['columns'][0].update(symbol=100.4),lambda p:p['columns'][0].update(rsi14=101),
    lambda p:p['columns'][0].update(volume=True),lambda p:p['columns'][0].update(close='NaN'),
    lambda p:p['columns'][0].update(sector=100.6),lambda p:p.update(scan_url='wrong'),
    lambda p:p.update(synthetic_enrichment_v1={}),lambda p:p.update(extra='value'),
])
def test_malformed_candidate_columns_fail_closed(change):
    p=candidate_payload();change(p)
    with pytest.raises(ValueError):normalize(p,scanner(),NOW)


@pytest.mark.parametrize('change',[
    lambda p:p['columns'][0].update(symbol='SYN095'),lambda p:p['columns'][0].update(rsi14=60),
    lambda p:p.update(stocks='SYMBOL 1,SYMBOL 2,SYMBOL 3'),lambda p:p.update(trigger_prices='1,2,3'),
    lambda p:p.update(scan_name='wrong'),lambda p:p['columns'][0].update(unverified=1),
])
def test_near_test_templates_cannot_bypass_validation(change):
    p=provider_payload();change(p)
    with pytest.raises(ValueError):normalize(p,scanner(),NOW)


@pytest.mark.parametrize('field',['AVG_VOLUME20','PREV20_HIGH','close','ema30'])
@pytest.mark.parametrize('value',['1e-1000000','0e1000000','1e-29','1.1234567890123456789012345678'])
def test_decimal_bounds_cover_all_derived_denominators(field,value):
    p=candidate_payload();p['columns'][0][field]=value
    with pytest.raises(ValueError,match='^invalid_enrichment_number$'):
        normalize(p,scanner(),NOW)


def test_decimal_arithmetic_exception_is_sanitized():
    from decimal import localcontext,Overflow
    p=candidate_payload();p['columns'][0]['AVG_VOLUME20']='1e-28'
    with localcontext() as context:
        context.Emax=20;context.traps[Overflow]=True
        with pytest.raises(ValueError,match='^invalid_enrichment_number$'):
            normalize(p,scanner(),NOW)


def test_bounded_decimal_extremes_compute_finite_metrics():
    p=candidate_payload();p['columns'][0]['AVG_VOLUME20']='1e-28'
    e=normalize(p,scanner(),NOW)
    assert e['enrichment']['SYN095']['metrics']['relative_volume']=='1.00E+30'
