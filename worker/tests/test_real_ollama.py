import json
import time
from decimal import Decimal
import httpx
import pytest
from worker.providers.ollama import Ollama

DIGEST='a'*64


def transport(response=None, *, changed=False):
    calls=[]
    def handle(request):
        calls.append(request)
        if request.url.path=='/api/tags':
            return httpx.Response(200,json={'models':[dict(name='local:7b',digest=('b'*64 if changed and len(calls)>1 else DIGEST),size=100)]})
        return httpx.Response(200,json=response or dict(model='local:7b',done=True,done_reason='stop',response='{"action":"WATCH"}',eval_count=5))
    return httpx.MockTransport(handle),calls


def test_real_protocol_request_and_accounting():
    t,calls=transport()
    p=Ollama('local:7b',transport=t)
    payload={'schema':{'type':'object'},'instruction':'use the bundle','bundle':{'evidence':'source'}}
    assert json.loads(p.assess(json.dumps(payload),max_output_units=300,deadline=time.monotonic()+10))=={'action':'WATCH'}
    request=json.loads(calls[2].content)
    assert request['stream'] is False and request['keep_alive']==0
    assert request['options']['num_ctx']==8192
    assert json.loads(request['prompt'])=={'instruction':'use the bundle','bundle':{'evidence':'source'}}
    assert request['format']=={'type':'object'}
    assert p.ref.content_hash==DIGEST and p.usage[0]['eval_count']==5


@pytest.mark.parametrize('url',['https://example.com','http://127.0.0.1.evil','http://user@localhost:11434','http://localhost:11434/?remote=1'])
def test_remote_rejected(url):
    with pytest.raises(ValueError): Ollama('local:7b',base_url=url)


def test_changed_model_and_truncation_fail_closed():
    request=json.dumps({'schema':{'type':'object'},'instruction':'test','bundle':{}})
    t,_=transport(changed=True)
    p=Ollama('local:7b',transport=t)
    with pytest.raises(ValueError,match='digest_changed'):
        p.assess(request,max_output_units=300,deadline=time.monotonic()+10)
    t,_=transport(dict(model='local:7b',done=True,done_reason='length',response='{}'))
    p=Ollama('local:7b',transport=t)
    with pytest.raises(ValueError,match='incomplete'):
        p.step(request,max_output_units=300,deadline=time.monotonic()+10)
    assert p.usage[-1]['status']=='failed_ambiguous_usage'


def test_deadline_input_and_embeddings():
    t,_=transport(dict(model='local:7b',embeddings=[[.1,.2],[.3,.4]]))
    p=Ollama('local:7b',transport=t)
    with pytest.raises(TimeoutError):p.embed(('x',),deadline=0)
    assert p.embed(('x','y'),deadline=time.monotonic()+10)[0][0]==Decimal('.1')
    with pytest.raises(ValueError,match='input_limit'):
        p.assess('x'*16001,max_output_units=300,deadline=time.monotonic()+10)


@pytest.mark.parametrize('response',[{'model':'local:7b','embeddings':[[0,0]]},{'model':'wrong','embeddings':[[1]]},{'model':'local:7b','embeddings':[['1']]}])
def test_bad_vectors(response):
    t,_=transport(response)
    p=Ollama('local:7b',transport=t)
    with pytest.raises(ValueError):p.embed(('x',),deadline=time.monotonic()+10)


def test_context_reservation_rejects_silent_truncation_before_generation():
    t,calls=transport()
    p=Ollama('local:7b',transport=t,context=1024,max_input_bytes=2000)
    request=json.dumps({'schema':{'type':'object'},'instruction':'use evidence','bundle':{'evidence':'x'*600}})
    with pytest.raises(ValueError,match='context_limit'):
        p.assess(request,max_output_units=300,deadline=time.monotonic()+10)
    assert len(calls)==1  # Only installed-model inventory; no inference request.


def test_structured_schema_is_not_counted_as_model_prompt_tokens():
    t,calls=transport()
    p=Ollama('local:7b',transport=t,context=1024,max_input_bytes=2000)
    schema={'type':'object','description':'schema metadata '*100}
    request=json.dumps({'schema':schema,'instruction':'short','bundle':{}})
    p.assess(request,max_output_units=300,deadline=time.monotonic()+10)
    payload=json.loads(calls[2].content)
    assert len(payload['prompt'].encode())<1024
    assert len(payload['format']['description'])>1024


def test_generation_schema_compatibility_does_not_mutate_validation_contract():
    from worker.providers.ollama import generation_schema
    from stock_discovery_analysis.rag_contracts import Assessment
    import copy
    original=Assessment.model_json_schema();snapshot=copy.deepcopy(original)
    projected=generation_schema(original)
    assert original==snapshot and projected!=original
    assert generation_schema({'pattern':r'^[0-9]+$'})=={}
    assert generation_schema({'pattern':r'\S','minLength':1})=={}
    from pydantic import TypeAdapter
    from stock_discovery_contracts.v2 import Text
    with pytest.raises(ValueError):TypeAdapter(Text).validate_python('   ')
