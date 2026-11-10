"""STK-095: storage rejections must remain controlled HTTP responses."""
import json
import pytest
from fastapi import HTTPException
from app import chartink_receiver as receiver
from test_chartink import scanner, payload


@pytest.mark.parametrize('failure,status',[
    (ValueError('event_too_large'),413),
    (ValueError('scanner_version_content_conflict'),409),
    (ValueError('event_identity_conflict'),409),
    (OverflowError('candidate_inbox_capacity_reached'),503),
])
def test_storage_rejection(tmp_path,monkeypatch,failure,status):
    config=tmp_path/'scanner.json'
    config.write_text(scanner().model_dump_json())
    monkeypatch.setenv('CHARTINK_SCANNER_CONFIG',str(config))
    def reject(*args):
        raise failure
    monkeypatch.setattr(receiver.store,'accept',reject)
    with pytest.raises(HTTPException) as result:
        receiver.ingest(None,json.dumps(payload()).encode())
    assert result.value.status_code==status
    assert 'SECRET' not in result.value.detail
