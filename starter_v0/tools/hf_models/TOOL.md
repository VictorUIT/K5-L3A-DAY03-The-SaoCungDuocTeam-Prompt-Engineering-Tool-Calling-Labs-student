---
name: hf_models
track: bonus
kind: live_api
provider: Hugging Face Hub API (no key)
requires_env: []
inputs: [query, sort, limit]
outputs: [items]
side_effect: false
---
# hf_models

Searches models on the Hugging Face Hub via `https://huggingface.co/api/models`,
sorted by `downloads` or `likes` (descending). Returns `items` with `title`
(model id), `url`, `source`, `summary` (task, downloads, likes), `downloads`,
`likes`.

Use when the user wants pretrained / open-weight models to download or run
("model tiếng Việt nhiều lượt tải nhất trên Hugging Face"). Not for code repos
(use `github_repos`) or papers (use `papers`).

Guardrails: empty `query` / unknown `sort` return an error dict without a
network call; `limit` is clamped to 1–20; entries without an id are skipped.
