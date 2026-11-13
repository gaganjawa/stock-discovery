import json
import pytest
from stock_discovery_analysis.chartink_diagnostics import payload_shape,decode_payload,MAX_NODES
from app import chartink_diagnostics as private


def test_structure_only_for_partial_provider_preview_and_unknown_names():
    # Structure observed in provider View JSON; invented values, NOT a delivered fixture.
    payload={'stocks':'PRIVATE-STOCK','trigger_prices':'987.65','webhook_url':'https://private.invalid/token-secret',
             'columns':[{'symbol':'PRIVATE-STOCK','close':987.65,'EMA10':900}],
             'https://secret.invalid/credential':'TOKEN','PRIVATE-STOCK':'secret','x'*128:'secret'}
    result=payload_shape(payload);encoded=json.dumps(result)
    for value in ('PRIVATE-STOCK','987.65','900','token-secret','private.invalid','TOKEN','secret','x'*128):
        assert value not in encoded
    fields=result['shape']['fields']
    assert fields['columns']['count']==1
    assert fields['columns']['item_types']=={'object':1}
    assert fields['columns']['sampled_shapes'][0]['fields']['close']=={'type':'number'}
    assert fields['stocks']=={'type':'string'}
    assert result['shape']['redacted_field_count']==3


@pytest.mark.parametrize('payload',[None,True,123,'SECRET',[],{},[None,True,1,'secret',{}]])
def test_scalar_values_are_never_retained(payload):
    result=payload_shape(payload)
    assert 'SECRET' not in json.dumps(result) and 'secret' not in json.dumps(result)


def test_bounded_depth_width_and_heterogeneous_counts():
    value={'columns':[{'columns':list(range(500))} for _ in range(500)]}
    result=payload_shape(value)
    assert len(json.dumps(result))<16000
    assert result['shape']['fields']['columns']['count']==500
    assert result['shape']['fields']['columns']['sampled_count']<=16
    assert result['shape']['fields']['columns']['truncated']


@pytest.mark.parametrize('body',[b'{"stocks":"A","stocks":"B"}',b'{"columns":[{"close":1,"close":2}]}',b'{"close":NaN}',b'{"close":Infinity}',b'not-json',b'\xff'])
def test_malformed_json_and_duplicate_keys_fail_closed(body):
    with pytest.raises((ValueError,UnicodeError)):decode_payload(body)


def test_private_diagnostics_opt_in_bounded_and_readable(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr(private,'FILE',tmp_path/'shapes.json')
    monkeypatch.delenv('CHARTINK_REJECTION_DIAGNOSTICS',raising=False)
    private.record({'stocks':'DO-NOT-LOG'},'invalid_payload_fields')
    assert not private.FILE.exists() and private.read()=={'enabled':False}
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    for _ in range(25):private.record({'columns':[{'symbol':'DO-NOT-LOG','close':123}]},'invalid_payload_fields')
    records=private.read()['records']
    assert len(records)==20
    assert 'DO-NOT-LOG' not in private.FILE.read_text()
    assert private.FILE.stat().st_mode&0o777==0o600
    assert capsys.readouterr().out==''


def test_diagnostic_write_failure_does_not_escape(monkeypatch,tmp_path):
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    monkeypatch.setattr(private,'FILE',tmp_path/'absent'/'shapes.json')
    private.record({'stocks':'secret'},'invalid_payload_fields')
    assert private.read()=={'enabled':True,'records':[]}
