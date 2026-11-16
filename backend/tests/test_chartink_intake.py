"""Schema-independent intake, with isolated invented payloads only."""
import json
from datetime import datetime,timezone,timedelta
import pytest
from stock_discovery_analysis.chartink_intake import capture,parse,validate_receipt
from test_chartink import scanner,payload


def test_unknown_schema_retained_and_stable_duplicates_with_private_fields_redacted():
    at=datetime.now(timezone.utc);scan=scanner()
    body={**payload(),'future':{'unknown_rows':[{'new_field':12.5}]},'webhook_url':'https://private.invalid/capability','token':'PRIVATE'}
    e=capture(json.dumps(body).encode(),scan,at,secrets=('PRIVATE',))
    assert e['delivery_kind']=='unclassified' and e['symbols']==[]
    assert json.loads(e['raw_json'])['future']==body['future']
    assert 'PRIVATE' not in json.dumps(e) and 'private.invalid' not in json.dumps(e)
    assert validate_receipt(e,scan)==e
    assert capture(json.dumps(body,indent=2).encode(),scan,at+timedelta(seconds=1))['event_id']==e['event_id']
    with pytest.raises(ValueError,match='invalid_payload_fields'):parse(e)


@pytest.mark.parametrize('mutate',[lambda e:e.update(payload_hash='x'),lambda e:e.update(symbols=['INFY']),lambda e:e.update(body_bytes=65537),lambda e:e.update(raw_json='{}')])
def test_corrupt_feed_receipts_fail_closed(mutate):
    e=capture(json.dumps(payload()).encode(),scanner(),datetime.now(timezone.utc));mutate(e)
    with pytest.raises(ValueError):validate_receipt(e,scanner())


def test_intake_does_not_grant_expired_scanner_authorization():
    scan=scanner();at=scan.enabled_until+timedelta(seconds=1)
    e=capture(json.dumps(payload()).encode(),scan,at)
    assert e['delivery_kind']=='unclassified'
    with pytest.raises(ValueError,match='scanner_authorization_expired'):parse(e)


def test_raw_duplicate_fields_and_malformed_body_survive_redacted_for_diagnosis():
    body=b'{"stocks":"FIRST","stocks":"SECOND","password":{"nested":"PRIVATE"}}'
    e=capture(body,scanner(),datetime.now(timezone.utc))
    assert e['raw_json'].count('"stocks"')==2
    assert 'FIRST' in e['raw_json'] and 'SECOND' in e['raw_json'] and 'PRIVATE' not in e['raw_json']
    with pytest.raises(ValueError,match='duplicate_payload_field'):parse(e)
    e=capture(b'{"stocks":"FIRST","token":"PRIVATE",',scanner(),datetime.now(timezone.utc))
    assert 'FIRST' in e['raw_json'] and 'PRIVATE' not in e['raw_json']
    with pytest.raises(ValueError,match='invalid_json'):parse(e)


def test_nested_secret_values_escaped_keys_and_urls_cannot_enter_raw_receipt():
    body=b'{"future":{"pass\\u0077ord":{"x":"PRIVATE"},"details":"Bearer ABCDEF","url":"https://host.invalid/capability"},"webhook_url":"PRIVATE"}'
    e=capture(body,scanner(),datetime.now(timezone.utc))
    for value in ('PRIVATE','ABCDEF','host.invalid','capability'):
        assert value not in e['raw_json']
    assert json.loads(e['raw_json'])['future']['password']=='[REDACTED]'


def test_redacted_key_collision_is_still_durable_and_cannot_be_admitted():
    e=capture(b'{"https://first.invalid/key":"A","https://second.invalid/key":"B"}',scanner(),datetime.now(timezone.utc))
    assert e['syntax_error']=='privacy_redaction_collision'
    assert validate_receipt(e,scanner())==e
    with pytest.raises(ValueError,match='privacy_redaction_collision'):parse(e)


def test_later_scanner_renewal_does_not_retroactively_authorize_expired_receipt():
    scan=scanner();at=scan.enabled_until+timedelta(seconds=1)
    e=capture(json.dumps(payload()).encode(),scan,at)
    renewed=scan.model_copy(update={'enabled_until':at+timedelta(days=2)})
    with pytest.raises(ValueError,match='scanner_authorization_expired'):parse(e,scanner=renewed)
