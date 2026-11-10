"""Explicitly invented wire fixtures; no provider compatibility claim."""
import pytest
from test_chartink import scanner,payload,NOW
from stock_discovery_analysis.chartink import normalize
from stock_discovery_analysis.chartink_enrichment import normalize_fields


def test_synthetic_roundtrip_provenance_and_replay():
    p={**payload(),'synthetic_enrichment_v1':{'INFY':{'close':'1500','volume':200,'AVG_VOLUME20':100,'rsi14':60}}}
    e=normalize(p,scanner(),NOW)
    assert normalize(e['payload'],scanner(),NOW)==e
    assert e['enrichment']['INFY']['metrics']['relative_volume']=='2'
    assert e['enrichment']['INFY']['field_provenance']['avg_volume20']==['AVG_VOLUME20']
    assert e['enrichment']['INFY']['field_states']['ema10']=='missing'
    assert not e['evaluation_eligible']
    assert 'SECRET' not in str(e)
    with pytest.raises(ValueError,match='synthetic_scanner_required'):
        normalize(p,scanner().model_copy(update={'mode':'provider_alert'}),NOW)


@pytest.mark.parametrize('row',[{'RSI14':101},{'volume':-1},{'close':'NaN'},
    {'volume':True},{'EMA10':10,'ema10':11},{'mystery':2}])
def test_invalid_enrichment(row):
    with pytest.raises(ValueError):normalize_fields(row)


def test_atr_requires_verified_period():
    assert normalize_fields({'avg_true_range':10})['field_states']['atr14']=='period_unverified'
    assert normalize_fields({'avg_true_range':10},atr_period=14)['values']['atr14']=='10'


def test_csv_actual_column_aliases_and_duplicate_symbol():
    from stock_discovery_analysis.candidate_csv import events
    raw=b'Symbol,symbol,Stock Name,close,%_change,volume,marketcapname,sector,industry,EMA10,ema30,sma50,rsi14,AVG_VOLUME20,avg_true_range,PREV20_HIGH\nINFY,infy,Example,100,2,200,Large,IT,Software,99,98,97,60,100,3,105\n'
    result,counts=events(raw,scanner(),NOW,session='2026-11-05')
    snapshot=result[0]['enrichment']['INFY']
    assert snapshot['values']['change_pct']=='2'
    assert snapshot['metrics']['relative_volume']=='2'
    assert snapshot['field_states']['atr14']=='period_unverified'
    assert counts['matches']==1
    assert result[0]['completeness']=='partial_unverified'
    with pytest.raises(ValueError,match='ambiguous_csv_symbol'):
        events(raw.replace(b'INFY,infy',b'INFY,OTHER'),scanner(),NOW,session='2026-11-05')
