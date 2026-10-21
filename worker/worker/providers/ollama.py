"""Local Ollama implementations of the existing D3-07/08 provider protocols.

No pulls, cloud fallback or qualification promotion. Caller retains the existing
rights, durable reservation, citation validation and independent judge gates.
"""
import json
import re
import time
from decimal import Decimal
from urllib.parse import urlsplit

import httpx
from stock_discovery_contracts.v2 import Ref, check


def generation_schema(schema):
    """Ollama grammar uses a portable structural subset of JSON Schema.

    This is a generation hint, not the validation schema: keep the original
    contract in the prompt and validate every returned value in D3-07/08.
    The native grammar compiler rejects unanchored patterns and some combined
    bounds. Those constraints remain mandatory in the post-generation contract.
    """
    if isinstance(schema, list):return [generation_schema(v) for v in schema]
    if not isinstance(schema, dict):return schema
    projected={k:generation_schema(v) for k,v in schema.items()
               if k not in ('pattern','minLength','maxLength','minItems','maxItems')}
    # Defaults are accepted by Pydantic, but omitting the financial Fact payload
    # makes a numeric claim unverifiable. Emit explicit fields, including nulls.
    if projected.get('type')=='object' and 'properties' in projected:
        projected['required']=list(projected['properties'])
    return projected


class Ollama:
    local_only = True
    cost_per_unit = Decimal('0')

    def __init__(self, model, *, base_url='http://127.0.0.1:11434', transport=None,
                 context=8192, max_input_bytes=16000, max_model_bytes=6_000_000_000):
        url = urlsplit(base_url)
        check(url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1', 'host.docker.internal')
              and not url.username and not url.password and not url.query and not url.fragment
              and url.path in ('', '/'), 'local Ollama endpoint required')
        check(1024 <= context <= 16384 and 0 < max_input_bytes <= context * 2, 'bounded model context')
        check(isinstance(model, str) and not any(x in model.lower() for x in ('cloud', '://', '/')), 'local model name required')
        self.model, self.context, self.max_input_bytes = model, context, max_input_bytes
        self.client = httpx.Client(base_url=base_url, transport=transport, trust_env=False, follow_redirects=False)
        self.usage = []
        try:
            models = self._call('GET', '/api/tags', None, time.monotonic()+5)['models']
            matches = [m for m in models if m['name'] == model]
            check(len(matches) == 1, 'model_not_installed')
            m = matches[0]
            check(re.fullmatch(r'(sha256:)?[0-9a-f]{64}', m['digest']) is not None, 'model digest unavailable')
            check(type(m['size']) is int and 0 < m['size'] <= max_model_bytes, 'model_resource_limit')
            self.ref = Ref(id=model, version=m['digest'], content_hash=m['digest'].removeprefix('sha256:'))
        except Exception:
            self.client.close()
            raise

    def close(self):
        self.client.close()

    def _call(self, method, path, body, deadline):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('ollama_deadline')
        try:
            with self.client.stream(method, path, json=body, timeout=min(remaining, 120)) as response:
                if response.status_code != 200:
                    raise RuntimeError('ollama_http_'+str(response.status_code))
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    check(len(raw) <= 2_000_000, 'ollama_response_limit')
                    if time.monotonic() >= deadline:
                        raise TimeoutError('ollama_deadline')
            result = json.loads(raw)
            check(isinstance(result, dict) and 'error' not in result, 'ollama_response_error')
            return result
        except httpx.TimeoutException:
            raise TimeoutError('ollama_timeout') from None
        except httpx.HTTPError:
            raise RuntimeError('ollama_unavailable') from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RuntimeError('ollama_invalid_json') from None

    def _pin(self, deadline):
        models = self._call('GET', '/api/tags', None, deadline).get('models', [])
        check(any(m.get('name') == self.model and m.get('digest') == self.ref.version for m in models), 'model_digest_changed')

    def _account(self, result, started, status):
        usage = {k: result.get(k) for k in ('prompt_eval_count','eval_count','total_duration','load_duration')}
        check(all(v is None or type(v) is int and v >= 0 for v in usage.values()), 'invalid_model_usage')
        self.usage.append(dict(model=self.ref.model_dump(), status=status, **usage,
                               wall_ms=round((time.monotonic()-started)*1000), cost='0'))

    def assess(self, request, *, max_output_units, deadline):
        check(len(request.encode()) <= self.max_input_bytes, 'ollama_input_limit')
        check(0 < max_output_units <= 32000, 'ollama_output_limit')
        # A byte is a conservative token upper bound. Reserve output plus template
        # overhead so Ollama cannot silently truncate the grounded source bundle.
        check(len(request.encode())+min(4096,max_output_units)+256 <= self.context, 'ollama_context_limit')
        data = json.loads(request)
        check(isinstance(data.get('schema'), dict), 'structured_schema_required')
        self._pin(deadline)
        started = time.monotonic()
        try:
            result = self._call('POST', '/api/generate', dict(model=self.model, prompt=request,
                stream=False, format=generation_schema(data['schema']), keep_alive=0,
                options=dict(temperature=0, seed=0, num_ctx=self.context,
                             num_predict=min(4096, max_output_units))), deadline)
            self._account(result, started, 'returned')
            check(result.get('model') == self.model and result.get('done') is True
                  and result.get('done_reason') == 'stop', 'ollama_incomplete_generation')
            raw = result.get('response')
            check(isinstance(raw, str) and len(raw.encode()) <= max_output_units, 'ollama_output_limit')
            json.loads(raw)
            self._pin(deadline)
            return raw
        except (ValueError, RuntimeError, TimeoutError):
            self.usage.append(dict(model=self.ref.model_dump(), status='failed_ambiguous_usage',
                                   wall_ms=round((time.monotonic()-started)*1000), cost='0'))
            raise

    # Provider-neutral protocols; schema and deterministic validators remain owned
    # by the existing research/agent/judge callers. Summary uses assess as well.
    step = assess
    judge = assess

    def embed(self, texts, *, deadline):
        check(0 < len(texts) <= 32 and all(isinstance(t, str) and t for t in texts), 'embedding_batch_limit')
        check(sum(len(t.encode()) for t in texts) <= self.max_input_bytes, 'embedding_input_limit')
        self._pin(deadline)
        started = time.monotonic()
        result = self._call('POST', '/api/embed', dict(model=self.model, input=list(texts), truncate=False,
                            keep_alive=0, options={'num_ctx':self.context}), deadline)
        self._account(result, started, 'returned')
        check(result.get('model') == self.model, 'embedding_model_mismatch')
        raw = result.get('embeddings')
        check(isinstance(raw, list) and len(raw) == len(texts), 'embedding_count')
        check(all(isinstance(v, list) and 0 < len(v) <= 4096 for v in raw), 'embedding_dimensions')
        check(len({len(v) for v in raw}) == 1, 'embedding_dimensions')
        check(all(type(x) in (int,float) for row in raw for x in row), 'embedding_number')
        vectors = tuple(tuple(Decimal(str(x)) for x in row) for row in raw)
        check(all(x.is_finite() and abs(x) <= Decimal('1e20') for row in vectors for x in row), 'embedding_number')
        check(all(any(x != 0 for x in row) for row in vectors), 'zero_embedding')
        self._pin(deadline)
        return vectors
