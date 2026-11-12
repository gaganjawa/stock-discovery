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


@pytest.mark.parametrize('mode',['missing','invalid','unreadable','missing_grants'])
def test_hosted_view_fails_before_consuming_work(monkeypatch,tmp_path,mode):
    from worker.candidates import cycle
    monkeypatch.setenv('PRIVATE_ACCESS_MODE','authenticated_proxy')
    monkeypatch.delenv('REAL_RESEARCH_VIEW_CONFIG',raising=False)
    path=tmp_path/'view.json'
    if mode!='missing':monkeypatch.setenv('REAL_RESEARCH_VIEW_CONFIG',str(path))
    if mode=='invalid':path.write_text('{}')
    if mode=='missing_grants':
        import json
        path.write_text(json.dumps(dict(sources=dict(grant_file=str(tmp_path/'absent'),retention_days=30),listing_ids=['NSE:SYN'])))
    with pytest.raises(ValueError,match='^hosted_research_configuration_invalid$'):
        cycle(None,remote_pull=False)
