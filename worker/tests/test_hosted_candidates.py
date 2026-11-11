import pytest
from worker.candidate_events import validate_hosted


def test_private_bridge_requires_separate_roles_and_same_host(monkeypatch,tmp_path):
    monkeypatch.setenv('DEPLOYMENT_MODE','private')
    source=tmp_path/'source';target=tmp_path/'target'
    monkeypatch.setenv('CANDIDATE_SOURCE_DATABASE_URL_FILE',str(source))
    monkeypatch.setenv('DATABASE_URL_FILE',str(target))
    good='postgresql://stk_inbox_reader:'+'x'*40+'@database/chartink_inbox'
    source.write_text(good)
    target.write_text('postgresql://stk_candidate_worker:'+'y'*40+'@database/stk_real001_private')
    validate_hosted()
    for value in [good.replace('stk_inbox_reader','chartink_owner'),good.replace('@database','@remote'),
                  good.replace('chartink_inbox','stk_real001_private'),good.replace('x'*40,'weak')]:
        source.write_text(value)
        with pytest.raises(ValueError):validate_hosted()
