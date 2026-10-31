"""Synthetic subprocess protocol probes, NOT actual model inference."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import pytest
from worker.providers.local_cli import LocalCLI
from worker.providers.research_runtime import RuntimeConfig


def fixture(tmp_path,body='print(\'{"claims":[]}\')'):
    exe=tmp_path/'llama-cli';exe.write_text('#!'+str(Path(sys.executable).resolve())+'\n'+body+'\n');exe.chmod(0o700)
    model=tmp_path/'model.gguf';model.write_bytes(b'GGUFsynthetic-not-an-LLM')
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(executable=str(exe),executable_hash=h(exe),model_path=str(model),model_hash=h(model))


def request():return json.dumps(dict(instruction='synthetic only',bundle={},schema={'type':'object'}))


def test_offline_bounded_process_and_private_prompt(tmp_path,monkeypatch):
    body="""import os,sys,json,pathlib
args=sys.argv
assert '--offline' in args and '--single-turn' in args and '--no-display-prompt' in args
assert 'SECRET_TEST_TOKEN' not in os.environ and 'LLAMA_ARG_HF_REPO' not in os.environ
assert 'synthetic only' not in ' '.join(args)
p=pathlib.Path(args[args.index('--file')+1]);assert p.stat().st_mode&0o777==0o600
assert json.loads(p.read_text())['instruction']=='synthetic only'
print('{"claims":[]}')"""
    monkeypatch.setenv('SECRET_TEST_TOKEN','not-a-real-token');monkeypatch.setenv('LLAMA_ARG_HF_REPO','must-not-inherit')
    args=fixture(tmp_path,body);p=LocalCLI('synthetic',**args)
    assert p.assess(request(),max_output_units=300,deadline=time.monotonic()+5)=='{"claims":[]}\n'
    assert p.usage[0]['cost']=='0' and p.usage[0]['token_count'] is None
    changed=LocalCLI('synthetic',**args,context=4096,max_input_bytes=8192)
    assert changed.ref.content_hash!=p.ref.content_hash


@pytest.mark.parametrize('body',["print('x'*1000)","print('not json')","raise SystemExit(1)","import time;time.sleep(5)"])
def test_invalid_output_or_deadline_is_sanitized_and_process_cleaned(tmp_path,body):
    p=LocalCLI('synthetic',**fixture(tmp_path,body))
    with pytest.raises(RuntimeError,match='^local_runtime_failed$'):
        p.assess(request(),max_output_units=300,deadline=time.monotonic()+.3)
    assert p.usage[-1]['status']=='failed_ambiguous_usage'


def test_model_and_binary_changes_fail_before_generation(tmp_path):
    args=fixture(tmp_path);p=LocalCLI('synthetic',**args)
    Path(args['model_path']).write_bytes(b'GGUFchanged')
    with pytest.raises(ValueError,match='model_digest_changed'):p.assess(request(),max_output_units=300,deadline=time.monotonic()+5)
    with pytest.raises(ValueError):LocalCLI('synthetic',**{**args,'executable_hash':'f'*64})


def test_missing_runtime_fails_without_ollama_or_cloud_fallback(tmp_path):
    config=RuntimeConfig(backend='llama_cpp')
    with pytest.raises(ValueError,match='configuration_incomplete'):config.build('not-installed')
    args=fixture(tmp_path)
    config=RuntimeConfig(backend='llama_cpp',executable=args['executable'],executable_sha256=args['executable_hash'],
        models={'synthetic':dict(path=args['model_path'],sha256=args['model_hash'])})
    assert isinstance(config.build('synthetic'),LocalCLI)
