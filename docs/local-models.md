# Local model choice

Ollama is the inference runtime. Qwen and DeepSeek are model families that it can run locally; replacing Ollama is not necessary to try them.

The default remains `qwen3.5:4b`. Its quantized weights are smaller than the 9B Qwen and 8B DeepSeek alternatives, making it a conservative starting point for a laptop with limited GPU memory. Weight size is not total runtime memory: context, cache and other processes also consume memory. Larger models may offload to CPU/RAM and take longer. This is a hardware-based choice, not evidence of superior CV quality.

Official references checked November 1, 2026:

- [Qwen 3.5 4B](https://ollama.com/library/qwen3.5:4b): current default; compact local model.
- [Qwen 3.5 9B](https://ollama.com/library/qwen3.5:9b): larger candidate for a controlled quality/speed comparison.
- [DeepSeek R1 8B](https://ollama.com/library/deepseek-r1:8b): distilled reasoning model; not the full DeepSeek model. Reasoning behavior may affect latency and output budgets.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs): JSON Schema constrains response structure, not factual truth.
- [Thinking controls](https://docs.ollama.com/capabilities/thinking): support differs by model. Our requests use `think: false`; a chosen model must pass the actual startup JSON inference check and the CV pipeline's stricter checks.

Select and persist a local model using `job-cv -Model qwen3.5:4b`. The launcher pulls it only when missing. Alternative tags can be selected the same way, but are not certified by the startup check: that checks basic inference, not job selection or PDF quality. Cloud tags are rejected. No API keys or cloud-model fallback are used.

Before changing the default, compare the same saved postings and approved evidence bank across models. Check exact job extraction, complementary project selection, truthful claims, all skills, one-page layout, runtime and memory. Do not treat generic reasoning benchmarks as proof of better CVs.

A small local comparison on November 1, 2026 used two structured requirement-ID cases on a 6 GB RTX 4050 laptop. Both models passed both cases. Qwen took 4.97 and 0.63 seconds; DeepSeek took 49.57 and 27.31 seconds with CPU/GPU offload. Qwen remains the default for latency. This narrow test does not establish comparative CV quality. Reproduce with `python evaluate.py --models qwen3.5:4b deepseek-r1:8b`; the report stays in ignored state storage.
