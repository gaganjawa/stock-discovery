from copy import deepcopy
from datetime import timedelta
import httpx
from app.explanations import explain
from stock_discovery_analysis.dataset import demo_dataset
from stock_discovery_analysis.strategy import analyze


def fixture():
    d=demo_dataset()
    return analyze(d,'SYN-ALPHA',d.calendar.sessions[39].closes_at+timedelta(minutes=1),code_version='test')


def test_disabled_missing_key_and_non_synthetic_never_call_provider(monkeypatch):
    monkeypatch.setattr(httpx,'post',lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden')))
    monkeypatch.setenv('LLM_ENABLED','false')
    a=fixture()
    assert explain(a)['reason']=='llm_disabled'
    monkeypatch.setenv('LLM_ENABLED','true');monkeypatch.delenv('OPENAI_API_KEY_FILE',raising=False)
    monkeypatch.setenv('OPENAI_API_KEY','')
    assert explain(a)['reason']=='api_key_not_configured'
    a['recommendation']['synthetic']=False
    assert explain(a)['reason']=='only_synthetic_inputs_enabled'


def test_provider_request_is_bounded_frozen_and_does_not_mutate_decision(monkeypatch):
    monkeypatch.setenv('LLM_ENABLED','true');monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    monkeypatch.delenv('OPENAI_API_KEY_FILE',raising=False);monkeypatch.setenv('LLM_MAX_OUTPUT_TOKENS','512')
    a=fixture();before=deepcopy(a)
    def post(url,**kw):
        assert url=='https://api.openai.com/v1/responses'
        assert kw['timeout']==20 and kw['json']['store'] is False
        assert kw['json']['max_output_tokens']==512
        assert 'tools' not in kw['json'] and 'test-only-key' not in kw['json']['input']
        assert 'trade_outcomes' not in kw['json']['input']
        return httpx.Response(200,request=httpx.Request('POST',url),json={'status':'completed','model':'test-model','output':[{'type':'message','content':[{'type':'output_text','text':'Fictional explanation.'}]}]})
    monkeypatch.setattr(httpx,'post',post)
    answer=explain(a)
    assert answer['mode']=='llm' and answer['model']=='test-model'
    assert a==before and len(answer['input_hash'])==64


def test_provider_failure_is_safe_fallback(monkeypatch):
    monkeypatch.setenv('LLM_ENABLED','true');monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    monkeypatch.delenv('OPENAI_API_KEY_FILE',raising=False)
    def fail(*a,**k): raise httpx.ReadTimeout('secret provider detail')
    monkeypatch.setattr(httpx,'post',fail)
    answer=explain(fixture())
    assert answer['mode']=='rules' and answer['reason']=='provider_unavailable'
    assert 'secret provider detail' not in str(answer)
