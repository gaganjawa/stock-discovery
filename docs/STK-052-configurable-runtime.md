# STK-052 — Optional research runtimes and actual development execution

PR22 merged at `f05d329296643dab2195748256ecab9bbeb7b432`, after exact-commit CI passed (419 PostgreSQL tests, zero skips, full migration lifecycle). Focused source review found no substantiated verifier blocker. The pending checkpoint was preserved.

## Runtime selection

The existing EvidenceConfig/research-provider protocol now supports explicit runtime selection. Default Ollama remains compatible. Set `embedding_model=null` for lexical retrieval without an embedding runtime. A second backend, `llama_cpp`, accepts owner-installed local `llama-cli` and GGUF files, with expected SHA-256 for each. No runtime, weights, SDK, cloud credential or service is downloaded or activated automatically. Missing configuration fails closed; there is no cloud/mock fallback.

Example private configuration fragment (replace placeholders; not an activation grant):

```json
{
  "embedding_model": null,
  "runtime": {
    "backend": "llama_cpp",
    "executable": "/absolute/path/llama-cli",
    "executable_sha256": "<verified SHA-256>",
    "models": {"local-model": {"path": "/absolute/path/model.gguf", "sha256": "<verified SHA-256>"}}
  },
  "model": "local-model"
}
```

The adapter uses the existing `assess/step/judge`, local-only/zero-API-cost and immutable model-reference contracts. Model bytes, executable bytes and context configuration affect identity. Generation is offline, single turn, two CPU threads, bounded context/output/deadline. Prompts/schema use private temporary files, environment credentials/proxy/download/logging flags are not inherited, output is bounded and parsed strictly, and process groups are killed on success/failure/cancellation. Full deterministic post-generation validators remain authoritative. Native CLI token counts and peak RAM are not measured; bytes/time/cost are recorded. Rehashing model files is bounded but can be expensive.

CLI flags were checked against the [official llama.cpp CLI documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/cli). No actual llama.cpp binary/model was installed here: its tests use clearly labelled synthetic subprocess stubs. Compatibility with a real installed CLI remains operational acceptance work. This adapter does not qualify arbitrary issuer layouts or enable trading.

## Actual local execution

After the owner confirmed the external SSD, `/Volumes/T9/ollama-models` was present. A temporary loopback-only Ollama process used installed `qwen2.5-coder:7b` (digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`, 4,683,087,561 bytes). Lexical retrieval was used; no embeddings, downloads, external providers or paid APIs were called.

Two bounded calls used the production ingestion/research/verifier path against an invented HTML disclosure normalized into explicit source rows, in disposable PostgreSQL. Fixture timestamps are synthetic clocks, not actual historical acquisition claims.

1. Initial call: 0 accepted, 3 rejected. The model correctly proposed the two figures but paired non-null values with non-null missing reasons and invented a candidate ID. Native usage: 1,219 prompt / 1,048 output tokens; 35.649 seconds end-to-end.
2. Extraction-only prompt clarified null handling and prohibited invented candidate IDs; the verifier/schema were not relaxed. The prompt has its own hash for cache identity. Second call: 2 extracted rows accepted, 1 invented-candidate proposal rejected. Native usage: 1,290 prompt / 1,035 output tokens; 27.263 seconds end-to-end.

Accepted rows: fictional revenue 100 INR crore and earnings 20 INR crore, independently normalized to INR and checked against stored deterministic source facts, complete period, scope, revision and exact quotation. An extra unsupported candidate remains visibly rejected. Full result/accounting/model/prompt evidence is in `research-quality/M2-actual-local-development.json`, including the failed first attempt. API cost USD 0; electricity/hardware cost was not measured.

This is one development example with prompt refinement, not an untouched evaluation. It is actual LLM inference, but neither genuine NSE research nor human-verified financial accuracy. No negative actual-model case was run; actual-model abstention accuracy is unavailable. Ten development review cases have provisional developer labels, still `human_verified=false`. The held-out reference registration is empty pending independent human review. Quality metrics remain unavailable until approved human references and independent holdout exist.

## Validation

Before the final prompt refinement: 736 backend/worker tests, 48 focused provider/pilot cases and 30 PostgreSQL filing/RAG cases passed. Post-refinement focused financial/factual/RAG/runtime run: 89 passed. Final full/focused results and exact-commit CI are recorded in the checkpoint/PR. The native-process fixtures test the adapter contract, not actual model quality. Existing original/current grants, read fences, immutable budgets, frozen historical evaluations, publication and paper/trading restrictions remain intact.

Final local reruns: **736 backend/worker passed**, **30 filing/RAG PostgreSQL passed**, **89 focused financial/factual/RAG/runtime passed** (overlapping counts); syntax/JSON/diff checks passed. A temporary loopback Ollama process and task-owned disposable database were stopped/removed afterward. No persistent OS startup or real-data activation was configured. Native CLI hard-crash cleanup and peak memory are not operationally validated; its actual executable was unavailable.
