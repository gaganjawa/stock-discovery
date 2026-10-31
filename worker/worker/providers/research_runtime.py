"""Explicit runtime selection, never an automatic cloud or mock fallback."""
from typing import Literal
from pydantic import Field
from stock_discovery_contracts.v2 import Strict,Text,Hash,check
from .ollama import Ollama
from .local_cli import LocalCLI


class ModelFiles(Strict):
    path: Text
    sha256: Hash


class RuntimeConfig(Strict):
    backend: Literal['ollama','llama_cpp']='ollama'
    executable: Text|None=None
    executable_sha256: Hash|None=None
    models: dict[Text,ModelFiles]=Field(default_factory=dict)

    def build(self,model,**kwargs):
        if self.backend=='ollama':return Ollama(model,**kwargs)
        check(self.executable and self.executable_sha256 and model in self.models,'runtime_configuration_incomplete')
        item=self.models[model]
        return LocalCLI(model,executable=self.executable,executable_hash=self.executable_sha256,
            model_path=item.path,model_hash=item.sha256,**kwargs)
