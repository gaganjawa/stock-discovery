from uuid import uuid4
import pytest
from stock_discovery_analysis.grant_fence_contracts import RestrictionRequest


@pytest.mark.parametrize('scope',[
    dict(kind='provider'),dict(kind='account',account_ref='SYN-account'),
    dict(kind='grant',account_ref='SYN-account',grant_id='SYN-grant',grant_version='1'),
])
def test_exact_scope_shapes_and_no_destructive_authority(scope):
    request=RestrictionRequest(request_id=uuid4(),source_id='SYN-source',reason='policy_unverified',**scope)
    assert request.deletion_authorized is False
    with pytest.raises(ValueError):RestrictionRequest.model_validate({**request.model_dump(),'deletion_authorized':True})


@pytest.mark.parametrize('changes',[
    {'account_ref':'SYN-extra'}, {'grant_id':'SYN-extra'}, {'grant_version':'2'},
    {'operator':'caller-asserted-admin'}, {'reason':'raw provider text'}, {'policy_hash':'secret'},
    {'source_id':'raw source text'},
])
def test_invalid_scope_and_free_text_rejected(changes):
    data=dict(request_id=uuid4(),kind='provider',source_id='SYN-source',reason='revoked')
    with pytest.raises(ValueError):RestrictionRequest.model_validate({**data,**changes})
