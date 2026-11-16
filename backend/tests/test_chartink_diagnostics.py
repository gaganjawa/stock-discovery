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
    assert 'DO-NOT-LOG' not in json.dumps(private.read())
    assert 'DO-NOT-LOG' in private.FILE.read_text()
    assert private.FILE.stat().st_mode&0o777==0o600
    assert capsys.readouterr().out==''


def test_diagnostic_write_failure_does_not_escape(monkeypatch,tmp_path):
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    monkeypatch.setattr(private,'FILE',tmp_path/'absent'/'shapes.json')
    private.record({'stocks':'secret'},'invalid_payload_fields')
    assert private.read()=={'enabled':True,'available':False}


@pytest.fixture
def capture(monkeypatch, tmp_path):
    monkeypatch.setenv('CHARTINK_REJECTION_DIAGNOSTICS','true')
    monkeypatch.setattr(private,'FILE',tmp_path/'rejections.json')
    monkeypatch.setattr(private,'_last_write_failed',False)
    return private


def test_private_payload_exact_columns_and_secret_file_redaction(capture,monkeypatch,tmp_path,capsys):
    secret='private-capability-value-for-this-regression'
    secret_file=tmp_path/'webhook';secret_file.write_text(secret)
    monkeypatch.setenv('CHARTINK_WEBHOOK_SECRET_FILE',str(secret_file))
    payload={'stocks':'SYN095','webhook_url':'https://private.invalid/'+secret,
             'columns':[{'symbol':'SYN095','close':123,'EMA10':None,'extra_price':False,
                         'password':'NEVER-SAVE','credential':{'value':'NEVER-SAVE'},
                         secret:secret,'website':'https://user:pass@private.invalid/foo',
                         'sector':'Bearer ABCDEFGHIJK','industry':'password=NEVER-SAVE'}]}
    capture.record(payload,'invalid_columns_fields',b'synthetic-body')
    raw=capture.FILE.read_text();entry=json.loads(raw)[0]
    for value in (secret,'NEVER-SAVE','private.invalid','ABCDEFGHIJK'):
        assert value not in raw
    assert entry['body_bytes']==14
    assert entry['body_sha256']==__import__('hashlib').sha256(b'synthetic-body').hexdigest()
    row=entry['column_contract']['rows'][0]
    assert row['missing']==sorted(set(private.COLUMNS)-{'symbol','close','EMA10','sector','industry'})
    assert 'extra_price' in row['extra'] and row['types']['extra_price']=='boolean'
    assert row['types']['close']=='number' and row['types']['EMA10']=='null'
    assert entry['payload']['stocks']=='SYN095'
    assert entry['payload']['columns'][0]['extra_price']=='[REDACTED]'
    assert entry['summary']['received_at'].endswith('+00:00')
    exposed=json.dumps(capture.read())
    for value in ('SYN095','extra_price','body_sha256','column_contract'):
        assert value not in exposed
    assert capsys.readouterr()==('','')


def test_retention_count_bytes_expiry_and_crash_cleanup(capture,monkeypatch):
    monkeypatch.setattr(private.time,'time',lambda:100000)
    monkeypatch.setattr(private,'MAX_ARCHIVE_BYTES',2000)
    for index in range(30):capture.record({'stocks':str(index)},'invalid_columns_fields')
    records=json.loads(capture.FILE.read_text())
    assert 0<len(records)<=20 and capture.FILE.stat().st_size<=2000
    assert records[-1]['payload']['stocks']=='29'
    temp=capture.FILE.with_name(capture.FILE.name+'.tmp')
    temp.write_text('interrupted private payload')
    monkeypatch.setattr(private.time,'time',lambda:100000+private.MAX_AGE_SECONDS)
    assert capture.read()['records']==[]
    assert json.loads(capture.FILE.read_text())==[] and not temp.exists()


@pytest.mark.parametrize('target',['archive','lock','temp','directory','hardlink'])
def test_unsafe_paths_never_overwrite_target(capture,tmp_path,target):
    outside=tmp_path/'outside';outside.write_text('KEEP')
    if target=='directory':
        real=tmp_path/'real';real.mkdir(mode=0o700)
        link=tmp_path/'link';link.symlink_to(real,target_is_directory=True)
        capture.FILE=link/'rejections.json'
    elif target=='hardlink':
        __import__('os').link(outside,capture.FILE)
    else:
        suffix={'archive':'','lock':'.lock','temp':'.tmp'}[target]
        capture.FILE.with_name(capture.FILE.name+suffix).symlink_to(outside)
    capture.record({'stocks':'SYN095'},'invalid_columns_fields')
    assert outside.read_text()=='KEEP'
    assert not capture.read()['available']


def test_private_permissions_and_unavailable_directory(capture,tmp_path):
    capture.record({},'invalid_payload_fields')
    for path in (capture.FILE,capture.FILE.with_name(capture.FILE.name+'.lock')):
        assert path.stat().st_mode&0o777==0o600
    tmp_path.chmod(0o755)
    capture.record({},'invalid_payload_fields')
    assert not capture.read()['available']


def test_bounded_record_and_concurrent_writes(capture,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(private,'MAX_RECORD_BYTES',1000)
    capture.record({'stocks':'x '*2500},'invalid_payload_values')
    entry=json.loads(capture.FILE.read_text())[0]
    assert entry['capture_omitted']=='record_size_limit' and 'payload' not in entry
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i:capture.record({'stocks':str(i)},'invalid_columns_fields'),range(16)))
    records=json.loads(capture.FILE.read_text())
    assert len(records)==17
    assert {r['payload']['stocks'] for r in records[1:]}=={str(i) for i in range(16)}
    assert capture.read()['available']


def test_unparseable_body_is_never_captured(capture):
    capture.record(None,'invalid_json',b'{"password":"NEVER-SAVE",invalid')
    raw=capture.FILE.read_text()
    assert 'NEVER-SAVE' not in raw and 'password' not in raw
    assert json.loads(raw)[0]['payload'] is None


def test_overflow_numeric_json_retains_types_without_nonfinite_archive(capture):
    payload=decode_payload(b'{"columns":[{"close":1e999}]}')
    capture.record(payload,'invalid_enrichment_number')
    entry=json.loads(capture.FILE.read_text())[-1]
    assert entry['payload']['columns'][0]['close']=='[NON_FINITE]'
    assert entry['column_contract']['rows'][0]['types']['close']=='number'
    assert capture.read()['available']
