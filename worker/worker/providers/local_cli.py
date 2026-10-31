"""Optional offline llama.cpp adapter for the existing research protocol.

Requires owner-installed, hash-pinned executable and GGUF; never installs/pulls.
Source text stays out of process arguments; returned diagnostics contain no paths.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
from decimal import Decimal
from stock_discovery_contracts.v2 import Ref,check,digest


VERSION='local-cli-1'


def file_hash(path,limit):
    check(path.is_file() and 0<path.stat().st_size<=limit,'runtime_file_unavailable_or_oversize')
    h=hashlib.sha256();size=0
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            size+=len(block);check(size<=limit,'runtime_file_oversize');h.update(block)
    return h.hexdigest()


class LocalCLI:
    local_only=True
    cost_per_unit=Decimal('0')

    def __init__(self,model,*,executable,executable_hash,model_path,model_hash,
                 context=8192,max_input_bytes=16000,max_model_bytes=6_000_000_000):
        check(isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',model),'local_model_identifier_required')
        self.executable=Path(executable).resolve();self.model_path=Path(model_path).resolve()
        check(Path(executable).is_absolute() and Path(model_path).is_absolute(),'absolute_runtime_files_required')
        check(self.executable.name=='llama-cli' and os.access(self.executable,os.X_OK),'llama_cli_required')
        check(1024<=context<=16384 and 0<max_input_bytes<=context*2,'bounded_model_context')
        self.context,self.max_input_bytes,self.max_model_bytes=context,max_input_bytes,max_model_bytes
        self.executable_hash,self.model_hash=executable_hash,model_hash
        self._pin()
        with self.model_path.open('rb') as f:check(f.read(4)==b'GGUF','gguf_required')
        self.ref=Ref(id='llama.cpp:'+model,version=model_hash,content_hash=digest([VERSION,model_hash,executable_hash,context,max_input_bytes]))
        self.usage=[]

    def _pin(self):
        check(file_hash(self.executable,500_000_000)==self.executable_hash,'runtime_digest_changed')
        check(file_hash(self.model_path,self.max_model_bytes)==self.model_hash,'model_digest_changed')

    def close(self):pass

    def assess(self,request,*,max_output_units,deadline):
        check(os.name=='posix','posix_runtime_required')
        check(0<max_output_units<=32000 and len(request.encode())<=self.max_input_bytes,'runtime_input_output_bound')
        data=json.loads(request)
        check(isinstance(data.get('instruction'),str) and isinstance(data.get('bundle'),dict) and isinstance(data.get('schema'),dict),'structured_request_required')
        prompt=json.dumps({'instruction':data['instruction'],'bundle':data['bundle']},ensure_ascii=False)
        check(len(prompt.encode())+min(4096,max_output_units)+256<=self.context,'runtime_context_limit')
        self._pin();check(time.monotonic()<deadline,'runtime_deadline')
        started=time.monotonic();process=None;raw=bytearray()
        try:
            with tempfile.TemporaryDirectory(prefix='stk-inference-') as temp:
                prompt_file=Path(temp)/'prompt';schema_file=Path(temp)/'schema'
                prompt_file.write_text(prompt);schema_file.write_text(json.dumps(data['schema']))
                prompt_file.chmod(0o600);schema_file.chmod(0o600)
                args=[str(self.executable),'--model',str(self.model_path),'--offline','--no-mmproj',
                    '--file',str(prompt_file),'--json-schema-file',str(schema_file),'--single-turn',
                    '--ctx-size',str(self.context),'--n-predict',str(min(4096,max_output_units)),
                    '--threads','2','--threads-batch','2','--temp','0','--seed','0','--cache-ram','0',
                    '--no-display-prompt','--no-show-timings','--color','off','--log-disable','--no-warmup']
                # No inherited cloud tokens, model-download flags, logging or proxy settings.
                env={'PATH':str(self.executable.parent)+':/usr/bin:/bin','LANG':'C.UTF-8','TMPDIR':temp}
                process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                    cwd=temp,env=env,start_new_session=True)
                try:
                    with selectors.DefaultSelector() as events:
                        events.register(process.stdout,selectors.EVENT_READ)
                        while events.get_map():
                            remaining=deadline-time.monotonic()
                            if remaining<=0:raise TimeoutError('runtime_deadline')
                            for key,_ in events.select(min(remaining,.1)):
                                block=os.read(key.fileobj.fileno(),8192)
                                if not block:events.unregister(key.fileobj);break
                                raw.extend(block)
                                check(len(raw)<=max_output_units,'runtime_output_limit')
                    check(process.wait(timeout=max(.001,deadline-time.monotonic()))==0,'runtime_exit_failed')
                    check(time.monotonic()<deadline,'runtime_deadline')
                    result=raw.decode('utf-8');check(isinstance(json.loads(result),dict),'runtime_json_object_required')
                    self._pin();check(time.monotonic()<deadline,'runtime_deadline')
                    self.usage.append(dict(model=self.ref.model_dump(),input_bytes=len(prompt.encode()),output_bytes=len(raw),
                        token_count=None,cost='0',wall_ms=round((time.monotonic()-started)*1000),status='returned'))
                    return result
                finally:
                    # Includes descendants spawned by native CLI runtimes, on success too.
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait();process.stdout.close()
        except (OSError,ValueError,TimeoutError,subprocess.SubprocessError):
            self.usage.append(dict(model=self.ref.model_dump(),cost='0',status='failed_ambiguous_usage'))
            raise RuntimeError('local_runtime_failed') from None

    step=assess
    judge=assess
